from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Placeholder for encrypted TastyTrade credentials (to be implemented later)
    tastytrade_token = models.CharField(max_length=255, blank=True, null=True)
    # Add additional fields as needed

    def __str__(self):
        return self.username
