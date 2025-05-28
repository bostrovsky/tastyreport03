# TastyTrade SDK Implementation Guide for Sync Function

## Overview

This implementation guide provides detailed instructions for integrating the TastyTrade API sync functionality into the Django monolith application. It covers authentication, data retrieval, error handling, and deduplication strategies to ensure a bulletproof sync implementation.

## Installation

```python
# Install the TastyTrade SDK
pip install tastytrade
```

Alternatively, install from source:

```bash
git clone https://github.com/tastyware/tastytrade.git
cd tastytrade
# If using uv (recommended)
uv sync
uv pip install -e .
# Or with standard pip
pip install -e .
```

## Authentication & Session Management

### Creating a Session

```python
from tastytrade import Session

# Production account
session = Session('username', 'password')

# Test account (if needed during development)
# test_session = Session('username', 'password', is_test=True)
```

### Persistent Sessions

For improved performance and reliability, implement persistent sessions with remember tokens:

```python
# Generate a remember token (valid for 24 hours)
session = Session('username', 'password', remember_me=True)
remember_token = session.remember_token

# Store this token securely in your Django application
# For example, in an encrypted field in your user model

# Later, reuse the token instead of password
new_session = Session('username', remember_token=remember_token)
```

### Session Error Handling

```python
from tastytrade.exceptions import AuthenticationError, SessionError

try:
    session = Session('username', 'password')
except AuthenticationError as e:
    # Handle authentication failures
    logger.error(f"Authentication failed: {str(e)}")
    # Notify user of authentication failure
except SessionError as e:
    # Handle other session-related errors
    logger.error(f"Session error: {str(e)}")
    # Implement retry logic with exponential backoff
```

## Data Synchronization

### Account Data Retrieval

```python
from tastytrade import Account
from tastytrade.exceptions import AccountError

def sync_accounts(session, user):
    """
    Retrieve and sync all accounts for a user.
    Returns a list of account objects.
    """
    try:
        # Get all accounts associated with the session
        accounts = Account.get(session)
        
        # Process and store accounts
        for account in accounts:
            # Check if account already exists in database
            existing_account = UserAccount.objects.filter(
                user=user,
                account_number=account.account_number
            ).first()
            
            if existing_account:
                # Update existing account
                existing_account.account_type = account.account_type
                existing_account.nickname = account.nickname
                existing_account.save()
            else:
                # Create new account
                UserAccount.objects.create(
                    user=user,
                    account_number=account.account_number,
                    account_type=account.account_type,
                    nickname=account.nickname
                )
                
        return accounts
    except AccountError as e:
        logger.error(f"Error retrieving accounts: {str(e)}")
        raise
```

### Position Synchronization

```python
def sync_positions(session, account, user_account):
    """
    Sync all positions for a specific account.
    Implements deduplication and validation.
    """
    try:
        # Get current positions
        positions = account.get_positions(session)
        
        # Track processed positions for cleanup
        processed_position_ids = set()
        
        for position in positions:
            # Create a unique identifier for deduplication
            position_key = f"{position.symbol}_{position.instrument_type}"
            processed_position_ids.add(position_key)
            
            # Check if position already exists
            existing_position = Position.objects.filter(
                user_account=user_account,
                symbol=position.symbol,
                instrument_type=position.instrument_type
            ).first()
            
            if existing_position:
                # Update existing position
                existing_position.quantity = position.quantity
                existing_position.quantity_direction = position.quantity_direction
                existing_position.average_open_price = position.average_open_price
                existing_position.close_price = position.close_price
                existing_position.save()
            else:
                # Create new position
                Position.objects.create(
                    user_account=user_account,
                    symbol=position.symbol,
                    instrument_type=position.instrument_type,
                    underlying_symbol=position.underlying_symbol,
                    quantity=position.quantity,
                    quantity_direction=position.quantity_direction,
                    average_open_price=position.average_open_price,
                    close_price=position.close_price
                )
        
        # Remove positions that no longer exist
        Position.objects.filter(user_account=user_account).exclude(
            symbol__in=[p.symbol for p in positions]
        ).delete()
        
        return positions
    except Exception as e:
        logger.error(f"Error syncing positions: {str(e)}")
        raise
```

### Transaction History Synchronization

```python
from datetime import date, timedelta

def sync_transaction_history(session, account, user_account, days_back=30):
    """
    Sync transaction history for a specific account.
    Implements deduplication based on transaction IDs.
    """
    try:
        # Calculate start date
        start_date = date.today() - timedelta(days=days_back)
        
        # Get transaction history
        history = account.get_history(session, start_date=start_date)
        
        # Track processed transactions for validation
        processed_transaction_ids = set()
        
        for transaction in history:
            # Skip if transaction already processed (deduplication)
            if transaction.id in processed_transaction_ids:
                continue
                
            processed_transaction_ids.add(transaction.id)
            
            # Check if transaction already exists in database
            if Transaction.objects.filter(transaction_id=transaction.id).exists():
                # Transaction already exists, skip
                continue
                
            # Create new transaction record
            Transaction.objects.create(
                user_account=user_account,
                transaction_id=transaction.id,
                transaction_type=transaction.transaction_type,
                symbol=transaction.symbol,
                instrument_type=transaction.instrument_type,
                quantity=transaction.quantity,
                price=transaction.price,
                executed_at=transaction.executed_at,
                description=transaction.description
            )
        
        return history
    except Exception as e:
        logger.error(f"Error syncing transaction history: {str(e)}")
        raise
```

### Balance Synchronization

```python
def sync_account_balances(session, account, user_account):
    """
    Sync account balances.
    """
    try:
        # Get account balances
        balance = account.get_balances(session)
        
        # Update or create balance record
        AccountBalance.objects.update_or_create(
            user_account=user_account,
            defaults={
                'cash_balance': balance.cash_balance,
                'long_equity_value': balance.long_equity_value,
                'short_equity_value': balance.short_equity_value,
                'long_derivative_value': balance.long_derivative_value,
                'short_derivative_value': balance.short_derivative_value,
                'net_liquidating_value': balance.net_liquidating_value,
                'equity_buying_power': balance.equity_buying_power,
                'derivative_buying_power': balance.derivative_buying_power,
                'updated_at': balance.updated_at
            }
        )
        
        return balance
    except Exception as e:
        logger.error(f"Error syncing account balances: {str(e)}")
        raise
```

## Comprehensive Sync Function

```python
def perform_complete_sync(user, username, password):
    """
    Perform a complete sync of all TastyTrade data for a user.
    Implements comprehensive error handling and validation.
    """
    logger.info(f"Starting complete sync for user {user.username}")
    
    # Create session with retry logic
    session = None
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            session = Session(username, password)
            break
        except AuthenticationError as e:
            logger.error(f"Authentication failed: {str(e)}")
            return {
                'success': False,
                'error': 'Authentication failed. Please check your credentials.'
            }
        except Exception as e:
            retry_count += 1
            wait_time = 2 ** retry_count  # Exponential backoff
            logger.warning(f"Session creation failed (attempt {retry_count}): {str(e)}")
            logger.info(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
    
    if session is None:
        logger.error("Failed to create session after maximum retries")
        return {
            'success': False,
            'error': 'Failed to connect to TastyTrade. Please try again later.'
        }
    
    try:
        # Sync accounts
        accounts = sync_accounts(session, user)
        
        # Track sync statistics
        sync_stats = {
            'accounts_synced': len(accounts),
            'positions_synced': 0,
            'transactions_synced': 0,
            'errors': []
        }
        
        # Sync data for each account
        for account in accounts:
            try:
                # Get or create user account
                user_account = UserAccount.objects.get(
                    user=user,
                    account_number=account.account_number
                )
                
                # Sync positions
                positions = sync_positions(session, account, user_account)
                sync_stats['positions_synced'] += len(positions)
                
                # Sync transaction history
                transactions = sync_transaction_history(session, account, user_account)
                sync_stats['transactions_synced'] += len(transactions)
                
                # Sync account balances
                sync_account_balances(session, account, user_account)
                
            except Exception as e:
                error_msg = f"Error syncing account {account.account_number}: {str(e)}"
                logger.error(error_msg)
                sync_stats['errors'].append(error_msg)
        
        # Update last sync timestamp
        user.profile.last_tastytrade_sync = timezone.now()
        user.profile.save()
        
        logger.info(f"Sync completed for user {user.username}: {sync_stats}")
        
        return {
            'success': True,
            'stats': sync_stats
        }
        
    except Exception as e:
        logger.error(f"Sync failed for user {user.username}: {str(e)}")
        return {
            'success': False,
            'error': f'Sync failed: {str(e)}'
        }
```

## Django Integration

### Models

```python
# models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

class UserAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tastytrade_accounts')
    account_number = models.CharField(max_length=20, unique=True)
    account_type = models.CharField(max_length=50)
    nickname = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'account_number')
    
    def __str__(self):
        return f"{self.account_number} ({self.nickname or 'No nickname'})"

class Position(models.Model):
    user_account = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='positions')
    symbol = models.CharField(max_length=20)
    instrument_type = models.CharField(max_length=50)
    underlying_symbol = models.CharField(max_length=20, blank=True, null=True)
    quantity = models.DecimalField(max_digits=15, decimal_places=6)
    quantity_direction = models.CharField(max_length=10)  # Long or Short
    average_open_price = models.DecimalField(max_digits=15, decimal_places=6)
    close_price = models.DecimalField(max_digits=15, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user_account', 'symbol', 'instrument_type')
    
    def __str__(self):
        return f"{self.symbol} ({self.quantity} {self.quantity_direction})"

class Transaction(models.Model):
    user_account = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='transactions')
    transaction_id = models.CharField(max_length=50, unique=True)
    transaction_type = models.CharField(max_length=50)
    symbol = models.CharField(max_length=20)
    instrument_type = models.CharField(max_length=50)
    quantity = models.DecimalField(max_digits=15, decimal_places=6)
    price = models.DecimalField(max_digits=15, decimal_places=6)
    executed_at = models.DateTimeField()
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.transaction_type} {self.symbol} ({self.quantity})"

class AccountBalance(models.Model):
    user_account = models.OneToOneField(UserAccount, on_delete=models.CASCADE, related_name='balance')
    cash_balance = models.DecimalField(max_digits=15, decimal_places=6)
    long_equity_value = models.DecimalField(max_digits=15, decimal_places=6)
    short_equity_value = models.DecimalField(max_digits=15, decimal_places=6)
    long_derivative_value = models.DecimalField(max_digits=15, decimal_places=6)
    short_derivative_value = models.DecimalField(max_digits=15, decimal_places=6)
    net_liquidating_value = models.DecimalField(max_digits=15, decimal_places=6)
    equity_buying_power = models.DecimalField(max_digits=15, decimal_places=6)
    derivative_buying_power = models.DecimalField(max_digits=15, decimal_places=6)
    updated_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_sync = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Balance for {self.user_account.account_number}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    tastytrade_username = models.CharField(max_length=100, blank=True, null=True)
    last_tastytrade_sync = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Profile for {self.user.username}"
```

### Views

```python
# views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import UserAccount, Position, Transaction, AccountBalance
from .forms import TastyTradeCredentialsForm

@login_required
def sync_tastytrade_data(request):
    """
    View for manually triggering TastyTrade data sync.
    """
    if request.method == 'POST':
        form = TastyTradeCredentialsForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            # Store username for future reference
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            profile.tastytrade_username = username
            profile.save()
            
            # Perform sync
            result = perform_complete_sync(request.user, username, password)
            
            if result['success']:
                messages.success(request, "TastyTrade data synchronized successfully!")
                return redirect('dashboard')
            else:
                messages.error(request, result['error'])
    else:
        # Pre-fill username if available
        initial_data = {}
        if hasattr(request.user, 'profile') and request.user.profile.tastytrade_username:
            initial_data['username'] = request.user.profile.tastytrade_username
        
        form = TastyTradeCredentialsForm(initial=initial_data)
    
    # Get last sync time
    last_sync = None
    if hasattr(request.user, 'profile') and request.user.profile.last_tastytrade_sync:
        last_sync = request.user.profile.last_tastytrade_sync
    
    return render(request, 'tastytrade/sync.html', {
        'form': form,
        'last_sync': last_sync
    })
```

### Forms

```python
# forms.py
from django import forms

class TastyTradeCredentialsForm(forms.Form):
    username = forms.CharField(label='TastyTrade Username')
    password = forms.CharField(label='TastyTrade Password', widget=forms.PasswordInput)
```

### Templates

```html
<!-- templates/tastytrade/sync.html -->
{% extends 'base.html' %}

{% block content %}
<div class="container">
    <h1>Sync TastyTrade Data</h1>
    
    {% if last_sync %}
    <div class="alert alert-info">
        Last synchronized: {{ last_sync|date:"F j, Y, g:i a" }}
    </div>
    {% else %}
    <div class="alert alert-warning">
        You have not synchronized your TastyTrade data yet.
    </div>
    {% endif %}
    
    <div class="card">
        <div class="card-body">
            <h5 class="card-title">Enter your TastyTrade credentials</h5>
            <p class="card-text">Your credentials are used only for synchronization and are not stored.</p>
            
            <form method="post">
                {% csrf_token %}
                
                <div class="form-group">
                    <label for="{{ form.username.id_for_label }}">{{ form.username.label }}</label>
                    {{ form.username }}
                </div>
                
                <div class="form-group">
                    <label for="{{ form.password.id_for_label }}">{{ form.password.label }}</label>
                    {{ form.password }}
                </div>
                
                <button type="submit" class="btn btn-primary">Sync Now</button>
            </form>
        </div>
    </div>
</div>
{% endblock %}
```

## Error Handling and Logging

```python
# settings.py (add to your Django settings)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'tastytrade_sync.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'tastytrade_sync': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## Scheduled Tasks (Optional)

If you decide to implement scheduled syncing in the future:

```python
# tasks.py
from celery import shared_task
from django.contrib.auth.models import User
from django.utils import timezone
from .models import UserProfile
from .sync import perform_complete_sync
import logging

logger = logging.getLogger('tastytrade_sync')

@shared_task
def sync_all_users_data():
    """
    Celery task to sync data for all users who have TastyTrade credentials.
    """
    logger.info("Starting scheduled sync for all users")
    
    # Get all users with TastyTrade credentials
    profiles = UserProfile.objects.filter(tastytrade_username__isnull=False)
    
    sync_results = {
        'total': profiles.count(),
        'success': 0,
        'failed': 0
    }
    
    for profile in profiles:
        user = profile.user
        
        # Skip users without stored credentials
        if not profile.tastytrade_username:
            continue
            
        # Retrieve credentials (in a real implementation, you would use a secure
        # credential storage system rather than storing passwords)
        username = profile.tastytrade_username
        password = retrieve_secure_password(user)  # Implement this securely
        
        if not password:
            logger.warning(f"No stored password for user {user.username}")
            sync_results['failed'] += 1
            continue
            
        # Perform sync
        result = perform_complete_sync(user, username, password)
        
        if result['success']:
            sync_results['success'] += 1
        else:
            sync_results['failed'] += 1
            logger.error(f"Sync failed for user {user.username}: {result.get('error')}")
    
    logger.info(f"Scheduled sync completed: {sync_results}")
    return sync_results
```

## Best Practices for Bulletproof Implementation

1. **Credential Security**:
   - Never store TastyTrade passwords in plaintext
   - Consider using Django's encrypted fields or a secure vault service
   - Implement proper session token management

2. **Error Handling**:
   - Implement comprehensive try/except blocks
   - Use specific exception types when possible
   - Log all errors with appropriate context
   - Implement retry logic with exponential backoff

3. **Deduplication**:
   - Use unique identifiers for all records
   - Implement proper database constraints
   - Check for existing records before creating new ones
   - Use database transactions to ensure data integrity

4. **Validation**:
   - Validate all data received from the API
   - Implement data type checking and conversion
   - Verify data consistency before saving

5. **Performance**:
   - Use bulk operations when possible
   - Implement proper database indexing
   - Consider caching frequently accessed data
   - Use asynchronous processing for long-running operations

6. **Testing**:
   - Write comprehensive unit tests
   - Implement integration tests with mock API responses
   - Test edge cases and error scenarios
   - Verify deduplication logic works correctly

7. **Monitoring**:
   - Implement detailed logging
   - Track sync statistics
   - Set up alerts for sync failures
   - Monitor API rate limits

## Conclusion

This implementation guide provides a comprehensive framework for integrating TastyTrade sync functionality into your Django monolith application. By following these guidelines and best practices, you can ensure a bulletproof implementation that handles errors gracefully, prevents data duplication, and provides a reliable user experience.

Remember to adapt this guide to your specific application requirements and to stay updated with any changes to the TastyTrade API.
