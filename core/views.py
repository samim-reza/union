from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AdminUserCreationForm, DepositForm, LoanRequestForm, LoanVoteForm
from .models import ActivityLog, Deposit, LoanRequest, LoanVote


def _is_admin(user):
	return user.is_authenticated and (user.is_staff or user.is_superuser)


def _create_activity(actor, action, description):
	ActivityLog.objects.create(actor=actor, action=action, description=description)


@login_required
def dashboard(request):
	total_deposits = Deposit.objects.aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))[
		'total'
	]
	total_borrowed = LoanRequest.total_approved_amount()
	union_balance = total_deposits - total_borrowed

	active_users = User.objects.filter(is_active=True)
	member_count = active_users.count() or 1

	contribution_rows = (
		active_users.annotate(total_contributed=Coalesce(Sum('deposits__amount'), Decimal('0.00')))
		.order_by('-total_contributed', 'username')
	)

	contributions = []
	for member in contribution_rows:
		percentage = (
			(member.total_contributed / total_deposits) * 100
			if total_deposits > 0
			else Decimal('0.00')
		)
		contributions.append(
			{
				'member': member,
				'total_contributed': member.total_contributed,
				'percentage': round(percentage, 2),
			}
		)

	recent_deposits = Deposit.objects.select_related('user')[:10]
	recent_activities = ActivityLog.objects.select_related('actor')[:12]

	context = {
		'total_deposits': total_deposits,
		'total_borrowed': total_borrowed,
		'union_balance': union_balance,
		'member_count': member_count,
		'contributions': contributions,
		'recent_deposits': recent_deposits,
		'recent_activities': recent_activities,
	}
	return render(request, 'core/dashboard.html', context)


@login_required
def my_portal(request):
	my_total_deposits = request.user.deposits.aggregate(
		total=Coalesce(Sum('amount'), Decimal('0.00'))
	)['total']
	my_approved_loans = request.user.loan_requests.filter(
		status=LoanRequest.Status.APPROVED
	).aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']
	my_balance = my_total_deposits - my_approved_loans

	my_recent_deposits = request.user.deposits.all()[:8]
	my_recent_loans = request.user.loan_requests.all()[:8]

	context = {
		'my_total_deposits': my_total_deposits,
		'my_approved_loans': my_approved_loans,
		'my_balance': my_balance,
		'my_recent_deposits': my_recent_deposits,
		'my_recent_loans': my_recent_loans,
	}
	return render(request, 'core/my_portal.html', context)


@user_passes_test(_is_admin)
def create_user(request):
	if request.method == 'POST':
		form = AdminUserCreationForm(request.POST)
		if form.is_valid():
			user = form.save()
			_create_activity(
				request.user,
				ActivityLog.Action.USER_CREATED,
				f"Created user account for {user.username}.",
			)
			messages.success(request, f'User {user.username} created successfully.')
			return redirect('dashboard')
	else:
		form = AdminUserCreationForm()
	return render(request, 'core/create_user.html', {'form': form})


@login_required
def create_deposit(request):
	if request.method == 'POST':
		form = DepositForm(request.POST)
		if form.is_valid():
			deposit = form.save(commit=False)
			deposit.user = request.user
			deposit.save()
			_create_activity(
				request.user,
				ActivityLog.Action.DEPOSIT_CREATED,
				f"{request.user.username} deposited {deposit.amount}.",
			)
			messages.success(request, 'Deposit recorded successfully.')
			return redirect('my-portal')
	else:
		form = DepositForm()
	return render(request, 'core/deposit_form.html', {'form': form})


@login_required
def create_loan_request(request):
	if request.method == 'POST':
		form = LoanRequestForm(request.POST)
		if form.is_valid():
			loan = form.save(commit=False)
			loan.applicant = request.user
			loan.save()

			_create_activity(
				request.user,
				ActivityLog.Action.LOAN_REQUESTED,
				f"{request.user.username} requested a loan of {loan.amount}.",
			)

			recipients = list(
				User.objects.filter(is_active=True)
				.exclude(id=request.user.id)
				.exclude(email='')
				.values_list('email', flat=True)
			)
			if recipients:
				send_mail(
					subject=f'New Loan Request from {request.user.username}',
					message=(
						f"A new loan request was submitted.\n\n"
						f"Applicant: {request.user.get_full_name() or request.user.username}\n"
						f"Amount: {loan.amount}\n"
						f"Purpose: {loan.purpose}\n\n"
						f"Please log in to review and vote."
					),
					from_email=None,
					recipient_list=recipients,
					fail_silently=True,
				)

			messages.success(
				request,
				'Loan request submitted. Members have been notified by email.',
			)
			return redirect('loan-detail', pk=loan.pk)
	else:
		form = LoanRequestForm()
	return render(request, 'core/loan_form.html', {'form': form})


@login_required
def loan_list(request):
	loans = LoanRequest.objects.select_related('applicant').all()
	paginator = Paginator(loans, 8)
	page_obj = paginator.get_page(request.GET.get('page'))
	return render(request, 'core/loan_list.html', {'page_obj': page_obj})


@login_required
def deposit_list(request):
	show_mine = request.GET.get('mine') == '1'
	deposits = Deposit.objects.select_related('user').all()
	if show_mine:
		deposits = deposits.filter(user=request.user)

	paginator = Paginator(deposits, 10)
	page_obj = paginator.get_page(request.GET.get('page'))
	return render(
		request,
		'core/deposit_list.html',
		{'page_obj': page_obj, 'show_mine': show_mine},
	)


@login_required
def activity_list(request):
	activities = ActivityLog.objects.select_related('actor').all()
	paginator = Paginator(activities, 12)
	page_obj = paginator.get_page(request.GET.get('page'))
	return render(request, 'core/activity_list.html', {'page_obj': page_obj})


@login_required
def loan_detail(request, pk):
	loan = get_object_or_404(LoanRequest.objects.select_related('applicant'), pk=pk)
	user_vote = LoanVote.objects.filter(loan_request=loan, voter=request.user).first()
	total_members = User.objects.filter(is_active=True).count()
	required_votes = (total_members // 2) + 1
	can_vote = request.user != loan.applicant and user_vote is None and loan.status == LoanRequest.Status.PENDING

	context = {
		'loan': loan,
		'votes': loan.votes.select_related('voter').all(),
		'user_vote': user_vote,
		'can_vote': can_vote,
		'vote_form': LoanVoteForm(),
		'required_votes': required_votes,
	}
	return render(request, 'core/loan_detail.html', context)


@login_required
def vote_on_loan(request, pk):
	loan = get_object_or_404(LoanRequest, pk=pk)
	if request.user == loan.applicant:
		messages.error(request, 'You cannot vote on your own loan request.')
		return redirect('loan-detail', pk=loan.pk)

	if loan.status != LoanRequest.Status.PENDING:
		messages.error(request, 'Voting is closed for this request.')
		return redirect('loan-detail', pk=loan.pk)

	if request.method != 'POST':
		return redirect('loan-detail', pk=loan.pk)

	form = LoanVoteForm(request.POST)
	if not form.is_valid():
		messages.error(request, 'Invalid vote submission.')
		return redirect('loan-detail', pk=loan.pk)

	with transaction.atomic():
		existing_vote = LoanVote.objects.filter(
			loan_request=loan,
			voter=request.user,
		).exists()
		if existing_vote:
			messages.warning(request, 'You already voted on this request.')
			return redirect('loan-detail', pk=loan.pk)

		vote = form.save(commit=False)
		vote.loan_request = loan
		vote.voter = request.user
		vote.save()

		_create_activity(
			request.user,
			ActivityLog.Action.LOAN_VOTED,
			(
				f"{request.user.username} voted {vote.decision.lower()} "
				f"on loan request #{loan.pk}."
			),
		)

		total_members = User.objects.filter(is_active=True).count()
		required_votes = (total_members // 2) + 1
		yes_votes = loan.yes_votes
		no_votes = loan.no_votes

		old_status = loan.status
		if yes_votes >= required_votes:
			loan.status = LoanRequest.Status.APPROVED
		elif no_votes >= required_votes:
			loan.status = LoanRequest.Status.REJECTED
		elif yes_votes + no_votes >= total_members - 1 and yes_votes <= no_votes:
			loan.status = LoanRequest.Status.REJECTED

		if loan.status != old_status:
			loan.save(update_fields=['status', 'updated_at'])
			_create_activity(
				request.user,
				ActivityLog.Action.LOAN_STATUS_CHANGED,
				f"Loan request #{loan.pk} status changed to {loan.status}.",
			)

	messages.success(request, 'Your vote has been recorded.')
	return redirect('loan-detail', pk=loan.pk)
