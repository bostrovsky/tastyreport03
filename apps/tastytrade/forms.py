from django import forms
from apps.tastytrade.models import TastyTradeCredential

class TastyTradeCredentialForm(forms.ModelForm):
    class Meta:
        model = TastyTradeCredential
        fields = ['username', 'password']  # environment is set in __init__

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not user.is_superuser:
            self.instance.environment = 'prod'
        else:
            self.fields['environment'] = forms.ChoiceField(
                choices=TastyTradeCredential._meta.get_field('environment').choices
            ) 