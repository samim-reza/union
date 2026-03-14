from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AdminUserCreationForm, DepositForm, LoanRequestForm, LoanVoteForm, DepositVoteForm
from .models import ActivityLog, Deposit, LoanRequest, LoanVote, DepositVote, LoanRepayment


def _is_admin(user):
	return user.is_authenticated and user.username.lower() in {'samim', 'arafat'}


def _create_activity(actor, action, description):
	ActivityLog.objects.create(actor=actor, action=action, description=description)


def _notify_members_for_approval(actor, subject, body):
	members = User.objects.filter(is_active=True)
	if actor is not None:
		members = members.exclude(pk=actor.pk)
	recipient_list = [member.email for member in members if member.email]
	if recipient_list:
		send_mail(
			subject,
			body,
			'noreply@unionledger.com',
			recipient_list,
			fail_silently=True,
		)


@login_required
def dashboard(request):
	total_deposits = Deposit.objects.filter(status='APPROVED').aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))[
		'total'
	]
	total_borrowed = LoanRequest.total_approved_amount()
	union_balance = total_deposits - total_borrowed

	active_users = User.objects.filter(is_active=True)

	contribution_rows = (
		active_users.annotate(total_contributed=Coalesce(Sum('deposits__amount', filter=Q(deposits__status='APPROVED')), Decimal('0.00')))
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
		'contributions': contributions,
		'recent_deposits': recent_deposits,
		'recent_activities': recent_activities,
	}
	return render(request, 'core/dashboard.html', context)


@login_required
def my_portal(request):
	my_total_deposits = request.user.deposits.filter(status='APPROVED').aggregate(
		total=Coalesce(Sum('amount'), Decimal('0.00'))
	)['total']
	my_approved_loans = request.user.loan_requests.filter(
		status=LoanRequest.Status.APPROVED
	).aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']
	my_balance = my_total_deposits - my_approved_loans

	recent_deposits = request.user.deposits.all()[:10]
	recent_loan_requests = request.user.loan_requests.all()[:10]

	context = {
		'my_total_deposits': my_total_deposits,
		'my_approved_loans': my_approved_loans,
		'my_balance': my_balance,
		'recent_deposits': recent_deposits,
		'recent_loan_requests': recent_loan_requests,
	}
	return render(request, 'core/my_portal.html', context)


@login_required
@user_passes_test(_is_admin)
def create_user(request):
	if request.method == 'POST':
		form = AdminUserCreationForm(request.POST)
		if form.is_valid():
			user = form.save()
			_create_activity(request.user, ActivityLog.Action.USER_CREATED, f"User {user.username} created.")
			messages.success(request, f"User {user.username} created successfully.")
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
			_notify_members_for_approval(
				request.user,
				f"New Deposit Approval Needed: {request.user.get_full_name() or request.user.username}",
				(
					f"A new deposit request of {deposit.amount} was submitted by "
					f"{request.user.get_full_name() or request.user.username}.\n\n"
					f"Receiver: {deposit.receiver.get_full_name() if deposit.receiver else 'Not provided'}\n"
					f"Note: {deposit.note or 'N/A'}\n\n"
					"Please login and review this approval request."
				),
			)
			messages.success(request, f"Deposit of {deposit.amount} submitted for approval.")
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

			try:
				members = User.objects.filter(is_active=True).exclude(pk=request.user.pk)
				send_mail(
					f"New Loan Request from {request.user.get_full_name() or request.user.username}",
					f"A new loan request of {loan.amount} has been made for: {loan.purpose}\n\n"
					f"Please login to vote on this request.",
					'noreply@unionledger.com',
					[member.email for member in members if member.email],
					fail_silently=True,
				)
			except Exception:
				pass

			messages.success(request, "Loan request submitted successfully. Members will be notified.")
			return redirect('my-portal')
	else:
		form = LoanRequestForm()
	return render(request, 'core/loan_form.html', {'form': form})


@login_required
def loan_list(request):
	loans = LoanRequest.objects.select_related('applicant').all()
	paginator = Paginator(loans, 10)
	page_obj = paginator.get_page(request.GET.get('page'))
	return render(request, 'core/loan_list.html', {'page_obj': page_obj})


@login_required
def deposit_list(request):
	deposits = Deposit.objects.select_related('user').all()
	show_mine = request.GET.get('mine')
	if show_mine:
		deposits = deposits.filter(user=request.user)
	paginator = Paginator(deposits, 10)
	page_obj = paginator.get_page(request.GET.get('page'))
	return render(request, 'core/deposit_list.html', {'page_obj': page_obj, 'show_mine': show_mine})


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

		vote = LoanVote(
			loan_request=loan,
			voter=request.user,
			decision=form.cleaned_data['decision'],
			comment=form.cleaned_data.get('comment', ''),
		)
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

from django.contrib.auth import logout
from django.shortcuts import redirect

def custom_logout(request):
    logout(request)
    return redirect('login')

@login_required
def deposit_detail(request, pk):
        deposit = get_object_or_404(Deposit.objects.select_related('user', 'receiver'), pk=pk)
        user_vote = DepositVote.objects.filter(deposit=deposit, voter=request.user).first()
        
        yes_votes = deposit.votes.filter(decision=DepositVote.Decision.APPROVE).count()
        required_votes = 2
        
        can_vote = request.user != deposit.user and user_vote is None and deposit.status == Deposit.Status.PENDING
        
        context = {
                'deposit': deposit,
                'votes': deposit.votes.select_related('voter').all(),
                'yes_votes': yes_votes,
                'required_votes': required_votes,
                'can_vote': can_vote,
                'vote_form': DepositVoteForm(),
        }
        return render(request, 'core/deposit_detail.html', context)

@login_required
def vote_on_deposit(request, pk):
        deposit = get_object_or_404(Deposit, pk=pk)
        if request.user == deposit.user:
                messages.error(request, 'You cannot vote on your own deposit.')
                return redirect('deposit-detail', pk=deposit.pk)

        if deposit.status != Deposit.Status.PENDING:
                messages.error(request, 'This deposit is no longer pending.')
                return redirect('deposit-detail', pk=deposit.pk)

        existing_vote = DepositVote.objects.filter(deposit=deposit, voter=request.user).first()
        if existing_vote:
                messages.warning(request, 'You have already voted on this deposit.')
                return redirect('deposit-detail', pk=deposit.pk)

        if request.method == 'POST':
                form = DepositVoteForm(request.POST)
                if form.is_valid():
                        vote = DepositVote(
                                deposit=deposit,
                                voter=request.user,
                                decision=form.cleaned_data['decision']
                        )
                        vote.save()
                        
                        ActivityLog.objects.create(
                                actor=request.user,
                                action=ActivityLog.Action.LOAN_VOTED, # Reusing simple action for now
                                description=f"Voted {vote.get_decision_display()} on deposit #{deposit.pk} by {deposit.user.username}"
                        )
                        
                        yes_votes = deposit.votes.filter(decision=DepositVote.Decision.APPROVE).count()
                        no_votes = deposit.votes.filter(decision=DepositVote.Decision.REJECT).count()
                        
                        if yes_votes >= 2:
                                deposit.status = Deposit.Status.APPROVED
                                deposit.save()
                                ActivityLog.objects.create(
                                        actor=None,
                                        action=ActivityLog.Action.DEPOSIT_CREATED,
                                        description=f"Deposit #{deposit.pk} approved and added to balance."
                                )
                        elif no_votes >= 2:
                                deposit.status = Deposit.Status.REJECTED
                                deposit.save()
                                
                        messages.success(request, 'Your vote has been recorded.')
                else:
                        messages.error(request, 'Invalid vote submission.')
        return redirect('deposit-detail', pk=deposit.pk)

from django.contrib import messages
from django.db import transaction
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from .forms import UserUpdateForm, ProfileUpdateForm

@login_required
def update_profile(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, instance=request.user.profile)
        password_form = PasswordChangeForm(request.user, request.POST)
        
        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                user_form.save()
                profile_form.save()
                if password_form.is_valid() and password_form.cleaned_data.get('old_password'):
                    user = password_form.save()
                    update_session_auth_hash(request, user)
                messages.success(request, 'Your profile was successfully updated!')
                return redirect('my-portal')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)
        password_form = PasswordChangeForm(request.user)
        
    return render(request, 'core/profile_update.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'password_form': password_form
    })


@login_required
def loan_repay(request, pk):
	from .forms import LoanRepaymentForm

	loan = get_object_or_404(LoanRequest, pk=pk)
	if request.method == 'POST':
		form = LoanRepaymentForm(request.POST)
		if form.is_valid():
			repayment = form.save(commit=False)
			repayment.loan = loan
			repayment.save()
			_notify_members_for_approval(
				request.user,
				f"Loan Repayment Approval Needed: Loan #{loan.pk}",
				(
					f"A loan repayment request of {repayment.amount} was submitted for Loan #{loan.pk}.\n"
					f"Borrower: {loan.applicant.get_full_name() or loan.applicant.username}\n"
					f"Receiver: {repayment.receiver.get_full_name() if repayment.receiver else 'Not provided'}\n\n"
					"Please login and review this approval request."
				),
			)
			messages.success(request, 'Loan repayment initiated. Waiting for approval.')
			return redirect('loan-detail', pk=loan.pk)
	else:
		form = LoanRepaymentForm()

	return render(request, 'core/loan_repay.html', {'form': form, 'loan': loan})

@login_required
def decisions(request):
    pending_deposits = Deposit.objects.filter(status='PENDING')
    pending_loans = LoanRequest.objects.filter(status='PENDING')
    pending_repayments = LoanRepayment.objects.filter(status='PENDING')
    
    return render(request, 'core/decisions.html', {
        'pending_deposits': pending_deposits,
        'pending_loans': pending_loans,
        'pending_repayments': pending_repayments
    })


@login_required
@user_passes_test(_is_admin)
def admin_portal(request):
	users = User.objects.order_by('username')
	pending_deposits = Deposit.objects.filter(status=Deposit.Status.PENDING).select_related('user')[:25]
	pending_loans = LoanRequest.objects.filter(status=LoanRequest.Status.PENDING).select_related('applicant')[:25]
	pending_repayments = LoanRepayment.objects.filter(status=LoanRepayment.Status.PENDING).select_related('loan__applicant')[:25]
	recent_activities = ActivityLog.objects.select_related('actor')[:40]
	return render(
		request,
		'core/admin_portal.html',
		{
			'users': users,
			'pending_deposits': pending_deposits,
			'pending_loans': pending_loans,
			'pending_repayments': pending_repayments,
			'recent_activities': recent_activities,
		},
	)


@login_required
@user_passes_test(_is_admin)
def deactivate_user(request, user_id):
	if request.method != 'POST':
		return redirect('admin-portal')

	target_user = get_object_or_404(User, pk=user_id)
	target_username = target_user.username.lower()
	if target_username in {'samim', 'arafat'}:
		messages.error(request, 'Admin users cannot remove another admin.')
		return redirect('admin-portal')

	if not target_user.is_active:
		messages.info(request, f'{target_user.username} is already inactive.')
		return redirect('admin-portal')

	target_user.is_active = False
	target_user.save(update_fields=['is_active'])
	_create_activity(request.user, ActivityLog.Action.USER_CREATED, f"{request.user.username} deactivated user {target_user.username}.")
	messages.success(request, f'{target_user.username} has been removed from active members.')
	return redirect('admin-portal')


@login_required
@user_passes_test(_is_admin)
def delete_pending_deposit(request, pk):
	if request.method != 'POST':
		return redirect('admin-portal')
	deposit = get_object_or_404(Deposit, pk=pk)
	if deposit.status != Deposit.Status.PENDING:
		messages.error(request, 'Only pending deposits can be deleted from admin portal.')
		return redirect('admin-portal')
	deposit.delete()
	messages.success(request, f'Pending deposit #{pk} deleted.')
	return redirect('admin-portal')


@login_required
@user_passes_test(_is_admin)
def delete_pending_loan(request, pk):
	if request.method != 'POST':
		return redirect('admin-portal')
	loan = get_object_or_404(LoanRequest, pk=pk)
	if loan.status != LoanRequest.Status.PENDING:
		messages.error(request, 'Only pending loans can be deleted from admin portal.')
		return redirect('admin-portal')
	loan.delete()
	messages.success(request, f'Pending loan #{pk} deleted.')
	return redirect('admin-portal')


@login_required
@user_passes_test(_is_admin)
def delete_pending_repayment(request, pk):
	if request.method != 'POST':
		return redirect('admin-portal')
	repayment = get_object_or_404(LoanRepayment, pk=pk)
	if repayment.status != LoanRepayment.Status.PENDING:
		messages.error(request, 'Only pending repayments can be deleted from admin portal.')
		return redirect('admin-portal')
	repayment.delete()
	messages.success(request, f'Pending repayment #{pk} deleted.')
	return redirect('admin-portal')


@login_required
@user_passes_test(_is_admin)
def delete_activity(request, pk):
	if request.method != 'POST':
		return redirect('admin-portal')
	activity = get_object_or_404(ActivityLog, pk=pk)
	activity.delete()
	messages.success(request, 'History record deleted.')
	return redirect('admin-portal')


@login_required
def policies(request):
	return render(request, 'core/policies.html')
