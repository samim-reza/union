from django.contrib import admin

from .models import ActivityLog, Deposit, LoanRequest, LoanVote


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
	list_display = ('user', 'amount', 'created_at')
	search_fields = ('user__username', 'user__email')
	list_filter = ('created_at',)


@admin.register(LoanRequest)
class LoanRequestAdmin(admin.ModelAdmin):
	list_display = ('id', 'applicant', 'amount', 'status', 'created_at')
	search_fields = ('applicant__username', 'purpose')
	list_filter = ('status', 'created_at')


@admin.register(LoanVote)
class LoanVoteAdmin(admin.ModelAdmin):
	list_display = ('loan_request', 'voter', 'decision', 'created_at')
	search_fields = ('loan_request__id', 'voter__username')
	list_filter = ('decision', 'created_at')


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
	list_display = ('action', 'actor', 'description', 'created_at')
	search_fields = ('description', 'actor__username')
	list_filter = ('action', 'created_at')
