from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce


class TimeStampedModel(models.Model):
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		abstract = True


class Deposit(TimeStampedModel):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deposits')
	amount = models.DecimalField(max_digits=12, decimal_places=2)
	note = models.CharField(max_length=255, blank=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.user.username} deposited {self.amount}"


class LoanRequest(TimeStampedModel):
	class Status(models.TextChoices):
		PENDING = 'PENDING', 'Pending'
		APPROVED = 'APPROVED', 'Approved'
		REJECTED = 'REJECTED', 'Rejected'

	applicant = models.ForeignKey(
		User,
		on_delete=models.CASCADE,
		related_name='loan_requests',
	)
	amount = models.DecimalField(max_digits=12, decimal_places=2)
	purpose = models.TextField()
	status = models.CharField(
		max_length=20,
		choices=Status.choices,
		default=Status.PENDING,
	)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"Loan #{self.pk} by {self.applicant.username} ({self.status})"

	@property
	def yes_votes(self):
		return self.votes.filter(decision=LoanVote.Decision.APPROVE).count()

	@property
	def no_votes(self):
		return self.votes.filter(decision=LoanVote.Decision.REJECT).count()

	@classmethod
	def total_approved_amount(cls):
		return cls.objects.filter(status=cls.Status.APPROVED).aggregate(
			total=Coalesce(Sum('amount'), Decimal('0.00'))
		)['total']


class LoanVote(TimeStampedModel):
	class Decision(models.TextChoices):
		APPROVE = 'APPROVE', 'Approve'
		REJECT = 'REJECT', 'Reject'

	loan_request = models.ForeignKey(
		LoanRequest,
		on_delete=models.CASCADE,
		related_name='votes',
	)
	voter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loan_votes')
	decision = models.CharField(max_length=10, choices=Decision.choices)
	comment = models.CharField(max_length=255, blank=True)

	class Meta:
		unique_together = ('loan_request', 'voter')
		ordering = ['-created_at']

	def clean(self):
		if self.loan_request.applicant_id == self.voter_id:
			raise ValidationError('You cannot vote on your own loan request.')

	def __str__(self):
		return f"{self.voter.username} -> {self.loan_request_id}: {self.decision}"


class ActivityLog(models.Model):
	class Action(models.TextChoices):
		USER_CREATED = 'USER_CREATED', 'User Created'
		DEPOSIT_CREATED = 'DEPOSIT_CREATED', 'Deposit Created'
		LOAN_REQUESTED = 'LOAN_REQUESTED', 'Loan Requested'
		LOAN_VOTED = 'LOAN_VOTED', 'Loan Voted'
		LOAN_STATUS_CHANGED = 'LOAN_STATUS_CHANGED', 'Loan Status Changed'

	actor = models.ForeignKey(
		User,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='activities',
	)
	action = models.CharField(max_length=30, choices=Action.choices)
	description = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']
		verbose_name_plural = 'Activity Logs'

	def __str__(self):
		return f"{self.get_action_display()} at {self.created_at:%Y-%m-%d %H:%M}"
