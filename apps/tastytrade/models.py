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
    last_sync = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.environment})"

class Position(models.Model):
    ASSET_TYPE_CHOICES = [
        ("stock", "Stock"),
        ("option", "Option"),
        ("future", "Future"),
        ("crypto", "Crypto"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    credential = models.ForeignKey('TastyTradeCredential', on_delete=models.CASCADE)
    tastytrade_account_number = models.CharField(max_length=32)
    asset_type = models.CharField(max_length=16, choices=ASSET_TYPE_CHOICES)
    symbol = models.CharField(max_length=64)
    description = models.CharField(max_length=256, blank=True)
    quantity = models.DecimalField(max_digits=20, decimal_places=4)
    average_price = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    current_price = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    previous_close_price = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    market_value = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    unrealized_pnl = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    daily_unrealized_pnl = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    realized_pnl = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    cash_collected = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)  # Total cash from this position
    delta = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    theta = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    beta = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    expiry = models.DateField(null=True, blank=True)
    strike = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    option_type = models.CharField(max_length=4, choices=[("call", "Call"), ("put", "Put")], null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "credential", "tastytrade_account_number", "asset_type", "symbol", "expiry", "strike", "option_type")
        indexes = [
            models.Index(fields=["user", "tastytrade_account_number", "asset_type", "symbol"]),
        ]

    def __str__(self):
        return f"{self.symbol} ({self.asset_type}) - {self.quantity}"

class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ("trade", "Trade"),
        ("dividend", "Dividend"),
        ("fee", "Fee"),
        ("interest", "Interest"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    credential = models.ForeignKey('TastyTradeCredential', on_delete=models.CASCADE)
    tastytrade_account_number = models.CharField(max_length=32)
    transaction_id = models.CharField(max_length=64, unique=True)
    transaction_type = models.CharField(max_length=16, choices=TRANSACTION_TYPE_CHOICES)
    symbol = models.CharField(max_length=64, blank=True)
    description = models.CharField(max_length=256, blank=True)
    quantity = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    price = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    trade_date = models.DateTimeField()
    asset_type = models.CharField(max_length=16, blank=True)
    expiry = models.DateField(null=True, blank=True)
    strike = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    option_type = models.CharField(max_length=4, choices=[("call", "Call"), ("put", "Put")], null=True, blank=True)
    
    # Strategy relationship
    strategy = models.ForeignKey('TradingStrategy', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', help_text="Associated trading strategy")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "tastytrade_account_number", "transaction_type", "symbol"]),
        ]
        ordering = ["-trade_date"]

    def __str__(self):
        return f"{self.transaction_type} {self.symbol} {self.amount} on {self.trade_date}"


class UserAccountPreferences(models.Model):
    """User preferences for TastyTrade account management"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tastytrade_preferences')
    credential = models.ForeignKey('TastyTradeCredential', on_delete=models.CASCADE)
    
    # Account tracking preferences
    tracked_accounts = models.JSONField(default=list, help_text="List of account numbers to sync and track")
    save_credentials = models.BooleanField(default=True, help_text="Whether to save TastyTrade credentials")
    
    # Sync preferences
    auto_sync_frequency = models.CharField(
        max_length=20, 
        choices=[
            ('manual', 'Manual Only'),
            ('daily', 'Daily'),
            ('hourly', 'Hourly'),
        ],
        default='manual'
    )
    
    # Data retention preferences
    keep_historical_data_on_account_removal = models.BooleanField(
        default=True, 
        help_text="Keep historical data when removing an account from tracking"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Preferences for {self.user.username}"


class DiscoveredAccount(models.Model):
    """Track discovered TastyTrade accounts and user's choice to include them"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    credential = models.ForeignKey('TastyTradeCredential', on_delete=models.CASCADE)
    account_number = models.CharField(max_length=32)
    
    # Account status
    is_tracked = models.BooleanField(default=False, help_text="Whether user chose to track this account")
    discovered_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    
    # Account metadata
    account_type = models.CharField(max_length=50, blank=True, help_text="IRA, Individual, etc.")
    account_name = models.CharField(max_length=100, blank=True, help_text="User-friendly name")
    
    class Meta:
        unique_together = ('user', 'credential', 'account_number')
        indexes = [
            models.Index(fields=['user', 'credential', 'is_tracked']),
        ]
    
    def __str__(self):
        status = "Tracked" if self.is_tracked else "Not Tracked"
        return f"Account {self.account_number} ({status})"


class TradingStrategy(models.Model):
    """Represents a trading strategy that groups related transactions"""
    STRATEGY_TYPE_CHOICES = [
        # Single leg strategies
        ('long_stock', 'Long Stock'),
        ('short_stock', 'Short Stock'),
        ('long_call', 'Long Call'),
        ('short_call', 'Short Call'),
        ('long_put', 'Long Put'),
        ('short_put', 'Short Put'),
        
        # Multi-leg strategies
        ('covered_call', 'Covered Call'),
        ('cash_secured_put', 'Cash Secured Put'),
        ('protective_put', 'Protective Put'),
        ('bull_call_spread', 'Bull Call Spread'),
        ('bear_call_spread', 'Bear Call Spread'),
        ('bull_put_spread', 'Bull Put Spread'),
        ('bear_put_spread', 'Bear Put Spread'),
        ('long_straddle', 'Long Straddle'),
        ('short_straddle', 'Short Straddle'),
        ('long_strangle', 'Long Strangle'),
        ('short_strangle', 'Short Strangle'),
        ('iron_condor', 'Iron Condor'),
        ('iron_butterfly', 'Iron Butterfly'),
        ('calendar_spread', 'Calendar Spread'),
        ('diagonal_spread', 'Diagonal Spread'),
        
        # Complex strategies
        ('collar', 'Collar'),
        ('jade_lizard', 'Jade Lizard'),
        ('big_lizard', 'Big Lizard'),
        ('broken_wing_butterfly', 'Broken Wing Butterfly'),
        
        # User defined
        ('custom', 'Custom Strategy'),
        ('unassigned', 'Unassigned Transactions'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('partially_closed', 'Partially Closed'),
        ('expired', 'Expired'),
        ('assigned', 'Assigned'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    credential = models.ForeignKey('TastyTradeCredential', on_delete=models.CASCADE)
    account_number = models.CharField(max_length=32)
    
    # Strategy identification
    strategy_type = models.CharField(max_length=32, choices=STRATEGY_TYPE_CHOICES)
    underlying_symbol = models.CharField(max_length=64)
    custom_name = models.CharField(max_length=128, blank=True, help_text="User-defined name for custom strategies")
    
    # Strategy details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    is_system_inferred = models.BooleanField(default=True, help_text="True if auto-detected, False if user-created")
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="System confidence in strategy identification (0-100)")
    
    # Financial data
    max_profit = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    max_loss = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    breakeven_points = models.JSONField(default=list, help_text="List of breakeven prices")
    
    # Dates
    opened_date = models.DateTimeField()
    closed_date = models.DateTimeField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    # Metadata
    notes = models.TextField(blank=True)
    tags = models.JSONField(default=list, help_text="User-defined tags")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'account_number', 'underlying_symbol']),
            models.Index(fields=['strategy_type', 'status']),
            models.Index(fields=['opened_date']),
        ]
        ordering = ['-opened_date']

    def __str__(self):
        name = self.custom_name if self.custom_name else self.get_strategy_type_display()
        return f"{name} - {self.underlying_symbol} ({self.status})"

    @property
    def net_pnl(self):
        """Calculate net P&L from all transactions in this strategy"""
        return self.transactions.aggregate(
            total=models.Sum('amount')
        )['total'] or 0

    @property
    def days_to_expiry(self):
        """Calculate days to expiry if applicable"""
        if self.expiry_date:
            from django.utils import timezone
            return (self.expiry_date - timezone.now().date()).days
        return None


class StrategyLeg(models.Model):
    """Represents individual legs of a multi-leg strategy"""
    strategy = models.ForeignKey(TradingStrategy, on_delete=models.CASCADE, related_name='legs')
    
    # Position details
    symbol = models.CharField(max_length=64)
    asset_type = models.CharField(max_length=16)
    quantity = models.DecimalField(max_digits=20, decimal_places=4)
    
    # Options-specific fields
    expiry = models.DateField(null=True, blank=True)
    strike = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    option_type = models.CharField(max_length=4, choices=[("call", "Call"), ("put", "Put")], null=True, blank=True)
    
    # Financial data
    average_price = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    current_value = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['strike', 'expiry']

    def __str__(self):
        if self.asset_type == 'option':
            return f"{self.quantity} {self.symbol} {self.strike}{self.option_type} {self.expiry}"
        return f"{self.quantity} {self.symbol}"


class StrategyEditHistory(models.Model):
    """Audit log for strategy edits to enable undo/redo"""
    ACTION_CHOICES = [
        ('create', 'Create Strategy'),
        ('update', 'Update Strategy'),
        ('delete', 'Delete Strategy'),
        ('merge', 'Merge Strategies'),
        ('split', 'Split Strategy'),
        ('reassign_transaction', 'Reassign Transaction'),
        ('add_transaction', 'Add Transaction'),
        ('remove_transaction', 'Remove Transaction'),
    ]

    strategy = models.ForeignKey(TradingStrategy, on_delete=models.CASCADE, related_name='edit_history', null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    
    # Store previous state for undo
    previous_state = models.JSONField(help_text="Previous state data for undo")
    new_state = models.JSONField(help_text="New state data for redo")
    
    # Context
    reason = models.CharField(max_length=256, blank=True)
    affected_transactions = models.JSONField(default=list, help_text="List of transaction IDs affected")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} by {self.user.username} at {self.created_at}"
