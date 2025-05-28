from django.db import models
from django.conf import settings

# If using Django 5.2+ with encrypted fields, import EncryptedCharField
try:
    from django.db.models import EncryptedCharField
except ImportError:
    EncryptedCharField = models.CharField  # fallback for earlier Django versions

class TastyTradeCredential(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tastytrade_credential')
    environment = models.CharField(max_length=16, choices=[('prod', 'Production'), ('sandbox', 'Sandbox')], default='prod')
    username = models.CharField(max_length=128)
    password = EncryptedCharField(max_length=256)  # encrypted or fallback
    access_token = EncryptedCharField(max_length=512, blank=True, null=True)
    refresh_token = EncryptedCharField(max_length=512, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.environment})"
