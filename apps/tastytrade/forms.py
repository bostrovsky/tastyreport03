from django import forms
from apps.tastytrade.models import TastyTradeCredential

class TastyTradeCredentialForm(forms.ModelForm):
    class Meta:
        model = TastyTradeCredential
        fields = ['username', 'password']  # environment is set in __init__
        widgets = {
            'password': forms.PasswordInput(render_value=True),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Always default to production environment
        self.instance.environment = 'prod'
        # Only show environment field to superusers for debugging
        if user and user.is_superuser:
            self.fields['environment'] = forms.ChoiceField(
                choices=TastyTradeCredential._meta.get_field('environment').choices,
                initial='prod'
            ) 