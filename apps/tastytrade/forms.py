from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from .models import TastyTradeCredential, UserAccountPreferences, DiscoveredAccount


class TastyTradeCredentialForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="Your TastyTrade password"
    )
    
    class Meta:
        model = TastyTradeCredential
        fields = ['environment', 'username', 'password']
        widgets = {
            'environment': forms.Select(attrs={'class': 'form-select'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Make environment read-only in production
        self.fields['environment'].initial = 'prod'
        self.fields['environment'].widget.attrs['readonly'] = True

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        instance.environment = 'prod'  # Enforce production
        if commit:
            instance.save()
        return instance


class AccountPreferencesForm(forms.ModelForm):
    """Form for managing user account tracking preferences"""
    
    class Meta:
        model = UserAccountPreferences
        fields = [
            'save_credentials',
            'auto_sync_frequency', 
            'keep_historical_data_on_account_removal'
        ]
        widgets = {
            'save_credentials': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'auto_sync_frequency': forms.Select(attrs={'class': 'form-select'}),
            'keep_historical_data_on_account_removal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.credential = kwargs.pop('credential', None)
        super().__init__(*args, **kwargs)


class TrackedAccountsForm(forms.Form):
    """Form for selecting which discovered accounts to track"""
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.credential = kwargs.pop('credential', None)
        super().__init__(*args, **kwargs)
        
        if self.user and self.credential:
            # Get all discovered accounts for this user
            discovered_accounts = DiscoveredAccount.objects.filter(
                user=self.user,
                credential=self.credential
            ).order_by('account_number')
            
            for account in discovered_accounts:
                field_name = f'account_{account.account_number}'
                self.fields[field_name] = forms.BooleanField(
                    label=f'Account {account.account_number}',
                    initial=account.is_tracked,
                    required=False,
                    widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
                    help_text=f'Track positions and transactions for this account'
                )
                
                # Add account name field if user wants to customize
                name_field = f'name_{account.account_number}'
                self.fields[name_field] = forms.CharField(
                    label=f'Display Name for {account.account_number}',
                    initial=account.account_name or f'Account {account.account_number}',
                    required=False,
                    widget=forms.TextInput(attrs={
                        'class': 'form-control form-control-sm',
                        'placeholder': f'Account {account.account_number}'
                    })
                )


class TastyTradePasswordChangeForm(forms.Form):
    """Form for changing TastyTrade password (separate from Django password)"""
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Current TastyTrade Password",
        help_text="Your current TastyTrade password for verification"
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="New TastyTrade Password",
        help_text="Your new TastyTrade password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Confirm New Password",
        help_text="Re-enter your new password"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError("New passwords don't match.")
        
        return cleaned_data


class DeleteAccountConfirmationForm(forms.Form):
    """Form for confirming account deletion"""
    confirmation = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Type "DELETE" to confirm'
        }),
        label="Confirmation",
        help_text="Type 'DELETE' in capital letters to confirm account deletion"
    )
    keep_data = forms.BooleanField(
        label="Keep historical trading data",
        help_text="If checked, your positions and transaction history will be preserved",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean_confirmation(self):
        confirmation = self.cleaned_data.get('confirmation')
        if confirmation != 'DELETE':
            raise forms.ValidationError("You must type 'DELETE' exactly to confirm.")
        return confirmation 