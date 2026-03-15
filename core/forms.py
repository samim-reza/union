from django import forms
from decimal import Decimal

from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.db.models.functions import Coalesce

from .models import (
    Deposit,
    DepositVote,
    InvestmentDecision,
    InvestmentVote,
    LoanRepayment,
    LoanRequest,
    LoanVote,
    Profile,
    RepaymentVote,
)

class AdminUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].help_text = password_validation.password_validators_help_text_html()
        self.fields['password1'].widget.attrs.update({'autocomplete': 'new-password'})
        self.fields['password2'].widget.attrs.update({'autocomplete': 'new-password'})

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

class DepositForm(forms.ModelForm):
    class Meta:
        model = Deposit
        fields = ('amount', 'receiver', 'note')
        widgets = {
            'amount': forms.NumberInput(attrs={'step': '1', 'min': '1'}),
            'note': forms.TextInput(attrs={'placeholder': 'Optional note about this deposit'}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None:
            if amount % 1 != 0:
                raise ValidationError("Amount must be an integer.")
        return amount

class LoanRequestForm(forms.ModelForm):
    class Meta:
        model = LoanRequest
        fields = ('amount', 'purpose')
        widgets = {
            'amount': forms.NumberInput(attrs={'step': '1', 'min': '1'}),
            'purpose': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Why do you need this loan?'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        total_deposits = Deposit.objects.filter(status='APPROVED').aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']
        total_borrowed = LoanRequest.total_approved_amount()
        union_balance = total_deposits - total_borrowed
        self.fields['amount'].widget.attrs['max'] = str(int(union_balance))
        # adding a js onchange alert is also possible here with onchange parameter or just rely on max attribute which produces HTML5 popup.
        self.fields['amount'].widget.attrs['oninput'] = f"if(this.value > {int(union_balance)}) {{ alert('Maximum allowable requested amount is ৳{int(union_balance)}'); this.value = {int(union_balance)}; }}"

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None:
            if amount % 1 != 0:
                raise ValidationError("Amount must be an integer.")
            
            # Check available balance
            total_deposits = Deposit.objects.filter(status='APPROVED').aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']
            total_borrowed = LoanRequest.total_approved_amount()
            union_balance = total_deposits - total_borrowed
            
            if amount > union_balance:
                raise ValidationError(f"You cannot request more than the current available balance (৳{union_balance:g}).")

        return amount

class LoanVoteForm(forms.ModelForm):
    class Meta:
        model = LoanVote
        fields = ('decision', 'comment')
        exclude = ('loan_request', 'voter')
        widgets = {
            'decision': forms.RadioSelect,
            'comment': forms.TextInput(attrs={'placeholder': 'Optional comment'}),
        }

class DepositVoteForm(forms.ModelForm):
    class Meta:
        model = DepositVote
        fields = ('decision',)
        exclude = ('deposit', 'voter')
        widgets = {
            'decision': forms.RadioSelect,
        }


class UserUpdateForm(forms.ModelForm):
    # For updating the built-in auth.User model fields
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
        
class ProfileUpdateForm(forms.ModelForm):
    # For updating Profile fields
    class Meta:
        model = Profile
        fields = ('date_of_birth',)
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

class LoanRepaymentForm(forms.ModelForm):
    class Meta:
        model = LoanRepayment
        fields = ('amount', 'receiver')
        widgets = {
            'amount': forms.NumberInput(attrs={'step': '1', 'min': '1'}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None:
            if amount % 1 != 0:
                raise ValidationError("Amount must be an integer.")
        return amount

class RepaymentVoteForm(forms.ModelForm):
    class Meta:
        model = RepaymentVote
        fields = ('decision',)
        widgets = {
            'decision': forms.RadioSelect,
        }


class InvestmentDecisionForm(forms.ModelForm):
    class Meta:
        model = InvestmentDecision
        fields = (
            'invest_to',
            'invested_amount',
            'invested_on',
            'received_amount',
            'received_on',
            'percentage_snapshot',
            'note',
        )
        widgets = {
            'invest_to': forms.TextInput(attrs={'placeholder': 'Example: OLI'}),
            'invested_amount': forms.NumberInput(attrs={'step': '1', 'min': '1'}),
            'invested_on': forms.DateInput(attrs={'type': 'date'}),
            'received_amount': forms.NumberInput(attrs={'step': '1', 'min': '0'}),
            'received_on': forms.DateInput(attrs={'type': 'date'}),
            'percentage_snapshot': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Paste member percentage breakdown here'}),
            'note': forms.TextInput(attrs={'placeholder': 'Optional note'}),
        }

    def clean_invested_amount(self):
        amount = self.cleaned_data.get('invested_amount')
        if amount is not None and amount % 1 != 0:
            raise ValidationError('Invested amount must be an integer.')
        return amount

    def clean_received_amount(self):
        amount = self.cleaned_data.get('received_amount')
        if amount is not None and amount % 1 != 0:
            raise ValidationError('Received amount must be an integer.')
        return amount


class InvestmentVoteForm(forms.ModelForm):
    class Meta:
        model = InvestmentVote
        fields = ('decision', 'comment')
        widgets = {
            'decision': forms.RadioSelect,
            'comment': forms.TextInput(attrs={'placeholder': 'Optional comment'}),
        }
