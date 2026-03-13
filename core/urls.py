from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('my/', views.my_portal, name='my-portal'),
    path('users/create/', views.create_user, name='create-user'),
    path('deposits/new/', views.create_deposit, name='create-deposit'),
    path('deposits/', views.deposit_list, name='deposit-list'),
    path('loans/new/', views.create_loan_request, name='create-loan-request'),
    path('loans/', views.loan_list, name='loan-list'),
    path('loans/<int:pk>/', views.loan_detail, name='loan-detail'),
    path('loans/<int:pk>/vote/', views.vote_on_loan, name='vote-on-loan'),
    path('history/', views.activity_list, name='activity-list'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='registration/login.html'),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
