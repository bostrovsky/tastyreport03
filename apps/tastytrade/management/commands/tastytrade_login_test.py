from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from utils.tastytrade import tastytrade_login, get_tastytrade_api_config
from apps.tastytrade.models import TastyTradeCredential
from django.utils.dateparse import parse_datetime

class Command(BaseCommand):
    help = 'Test TastyTrade API login using current environment and credentials. Persist session token.'

    def handle(self, *args, **options):
        config = get_tastytrade_api_config()
        self.stdout.write(f"Testing TastyTrade login for environment: {config['env']}")
        result = tastytrade_login()
        if result.get('success', True) and 'data' in result:
            self.stdout.write(self.style.SUCCESS(f"Login successful! Response: {result}"))
            # Use the first superuser for testing
            User = get_user_model()
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                self.stdout.write(self.style.ERROR("No superuser found to associate credentials with."))
                return
            cred, created = TastyTradeCredential.objects.get_or_create(user=user, environment=config['env'])
            cred.username = config['username']
            cred.password = config['password']
            cred.access_token = result['data'].get('session-token')
            cred.refresh_token = ''  # Not used in TastyTrade, placeholder
            print("About to save credential:", cred, "Created:", created)
            cred.save()
            print("Credential saved. PK:", cred.pk)
            self.stdout.write(self.style.SUCCESS(f"Session token saved to TastyTradeCredential for user {user.username}."))
        else:
            self.stdout.write(self.style.ERROR(f"Login failed: {result}")) 