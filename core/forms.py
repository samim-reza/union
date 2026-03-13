from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Deposit, LoanRequest, LoanVote


class AdminUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')


class DepositForm(forms.ModelForm):
    class Meta:
        model = Deposit
        fields = ('amount', 'note')
        widgets = {
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
            'note': forms.TextInput(attrs={'placeholder': 'Optional note about this deposit'}),
        }


class LoanRequestForm(forms.ModelForm):
    class Meta:
        model = LoanRequest
        fields = ('amount', 'purpose')
        widgets = {
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
            'purpose': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Why do you need this loan?'}),
        }


class LoanVoteForm(forms.ModelForm):
    class Meta:
        model = LoanVote
        fields = ('decision', 'comment')
        widgets = {
            'decision': forms.RadioSelect,
            'comment': forms.TextInput(attrs={'placeholder': 'Optional comment'}),
        }
