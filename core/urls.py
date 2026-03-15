from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('admin/', views.admin_portal, name='admin-portal'),
    path('admin/users/<int:user_id>/deactivate/', views.deactivate_user, name='deactivate-user'),
    path('admin/deposits/<int:pk>/delete/', views.delete_pending_deposit, name='delete-pending-deposit'),
    path('admin/loans/<int:pk>/delete/', views.delete_pending_loan, name='delete-pending-loan'),
    path('admin/repayments/<int:pk>/delete/', views.delete_pending_repayment, name='delete-pending-repayment'),
    path('admin/history/<int:pk>/delete/', views.delete_activity, name='delete-activity'),
    path('my/', views.my_portal, name='my-portal'),
    path('my-portal/', views.my_portal),
    path('profile/update/', views.update_profile, name='update-profile'),
    path('policies/', views.policies, name='policies'),
    path('decisions/', views.decisions, name='decisions'),
    path('users/create/', views.create_user, name='create-user'),
    path('deposits/new/', views.create_deposit, name='create-deposit'),
        path('deposits/', views.deposit_list, name='deposit-list'),
    path('deposits/<int:pk>/', views.deposit_detail, name='deposit-detail'),
    path('deposits/<int:pk>/vote/', views.vote_on_deposit, name='vote-on-deposit'),
    path('loans/new/', views.create_loan_request, name='create-loan-request'),
    path('loans/', views.loan_list, name='loan-list'),
    path('loans/<int:pk>/', views.loan_detail, name='loan-detail'),
    path('loans/<int:pk>/vote/', views.vote_on_loan, name='vote-on-loan'),
    path('loans/<int:pk>/repay/', views.loan_repay, name='loan-repay'),
    path('investments/', views.investment_list, name='investment-list'),
    path('investments/new/', views.create_investment, name='create-investment'),
    path('investments/<int:pk>/', views.investment_detail, name='investment-detail'),
    path('investments/<int:pk>/vote/', views.vote_on_investment, name='vote-on-investment'),
    path('history/', views.activity_list, name='activity-list'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='registration/login.html', redirect_authenticated_user=True),
        name='login',
    ),
    path('logout/', views.custom_logout, name='logout'),
]
