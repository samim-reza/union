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
        class Status(models.TextChoices):
                PENDING = 'PENDING', 'Pending'
                APPROVED = 'APPROVED', 'Approved'
                REJECTED = 'REJECTED', 'Rejected'

        user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deposits')
        receiver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deposits_received', help_text="Who received this money?")
        amount = models.DecimalField(max_digits=12, decimal_places=2)
        note = models.CharField(max_length=255, blank=True)
        status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

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
		# Only validate if both loan_request_id and voter_id are set
		if self.loan_request_id and self.voter_id:
			if self.loan_request.applicant_id == self.voter_id:
				raise ValidationError('You cannot vote on your own loan request.')

	def __str__(self):
		return f"{self.voter.username} -> {self.loan_request_id}: {self.decision}"



class DepositVote(TimeStampedModel):
        class Decision(models.TextChoices):
                APPROVE = 'APPROVE', 'Approve'
                REJECT = 'REJECT', 'Reject'

        deposit = models.ForeignKey(Deposit, on_delete=models.CASCADE, related_name='votes')
        voter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deposit_votes')
        decision = models.CharField(max_length=10, choices=Decision.choices)

        class Meta:
                unique_together = ('deposit', 'voter')
                ordering = ['-created_at']

        def clean(self):
                if self.deposit_id and self.voter_id:
                        if self.deposit.user_id == self.voter_id:
                                raise ValidationError("You cannot vote on your own deposit.")

        def __str__(self):
                return f"{self.voter.username} -> Deposit #{self.deposit_id}: {self.decision}"

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

class Profile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_of_birth = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.user.username

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    profile, _ = Profile.objects.get_or_create(user=instance)
    # No need to call profile.save() unless we changed it here


class LoanRepayment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        
    loan = models.ForeignKey(LoanRequest, on_delete=models.CASCADE, related_name='repayments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    receiver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_repayments')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.loan.applicant.username} repaid {self.amount}"

class RepaymentVote(TimeStampedModel):
    class Decision(models.TextChoices):
        APPROVE = 'APPROVE', 'Approve'
        REJECT = 'REJECT', 'Reject'

    repayment = models.ForeignKey(LoanRepayment, on_delete=models.CASCADE, related_name='votes')
    voter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='repayment_votes')
    decision = models.CharField(max_length=10, choices=Decision.choices)

    class Meta:
        unique_together = ('repayment', 'voter')

    def clean(self):
        if self.repayment_id and self.voter_id:
            if self.repayment.loan.applicant_id == self.voter_id:
                from django.core.exceptions import ValidationError
                raise ValidationError("You cannot vote on your own repayment.")
