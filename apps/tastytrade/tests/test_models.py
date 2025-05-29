"""
Unit tests for TastyTrade models
Financial data requires high confidence - comprehensive testing is essential
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from decimal import Decimal
from datetime import date, datetime, timezone
from apps.tastytrade.models import TastyTradeCredential, Position, Transaction

User = get_user_model()


class TastyTradeCredentialTests(TestCase):
    """Test TastyTrade credential model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_create_credential_production(self):
        """Test creating production credential"""
        credential = TastyTradeCredential.objects.create(
            user=self.user,
            environment='prod',
            username='testuser',
            password='testpass'
        )
        
        self.assertEqual(credential.user, self.user)
        self.assertEqual(credential.environment, 'prod')
        self.assertEqual(credential.username, 'testuser')
        self.assertEqual(credential.password, 'testpass')
        self.assertIsNone(credential.last_sync)
        self.assertIsNotNone(credential.created_at)
        self.assertIsNotNone(credential.updated_at)

    def test_create_credential_sandbox(self):
        """Test creating sandbox credential"""
        credential = TastyTradeCredential.objects.create(
            user=self.user,
            environment='sandbox',
            username='sandboxuser',
            password='sandboxpass'
        )
        
        self.assertEqual(credential.environment, 'sandbox')

    def test_one_credential_per_user(self):
        """Test that each user can only have one credential"""
        TastyTradeCredential.objects.create(
            user=self.user,
            environment='prod',
            username='user1',
            password='pass1'
        )
        
        # Should not be able to create another credential for same user
        with self.assertRaises(IntegrityError):
            TastyTradeCredential.objects.create(
                user=self.user,
                environment='sandbox',
                username='user2',
                password='pass2'
            )

    def test_credential_str_representation(self):
        """Test string representation"""
        credential = TastyTradeCredential.objects.create(
            user=self.user,
            environment='prod',
            username='testuser',
            password='testpass'
        )
        
        expected = f"{self.user.username} (prod)"
        self.assertEqual(str(credential), expected)

    def test_invalid_environment(self):
        """Test that invalid environment raises error"""
        with self.assertRaises(ValidationError):
            credential = TastyTradeCredential(
                user=self.user,
                environment='invalid',
                username='testuser',
                password='testpass'
            )
            credential.full_clean()


class PositionTests(TestCase):
    """Test Position model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.credential = TastyTradeCredential.objects.create(
            user=self.user,
            environment='prod',
            username='testuser',
            password='testpass'
        )

    def test_create_stock_position(self):
        """Test creating a stock position"""
        position = Position.objects.create(
            user=self.user,
            credential=self.credential,
            tastytrade_account_number='123456789',
            asset_type='stock',
            symbol='AAPL',
            description='Apple Inc.',
            quantity=Decimal('100.0000'),
            average_price=Decimal('150.2500'),
            market_value=Decimal('15025.00'),
            unrealized_pnl=Decimal('500.00'),
            realized_pnl=Decimal('200.00')
        )
        
        self.assertEqual(position.user, self.user)
        self.assertEqual(position.credential, self.credential)
        self.assertEqual(position.asset_type, 'stock')
        self.assertEqual(position.symbol, 'AAPL')
        self.assertEqual(position.quantity, Decimal('100.0000'))
        self.assertEqual(position.average_price, Decimal('150.2500'))
        self.assertIsNotNone(position.last_updated)

    def test_create_option_position(self):
        """Test creating an option position"""
        expiry_date = date(2024, 12, 20)
        position = Position.objects.create(
            user=self.user,
            credential=self.credential,
            tastytrade_account_number='123456789',
            asset_type='option',
            symbol='AAPL',
            description='AAPL Dec 20 2024 150 Call',
            quantity=Decimal('10.0000'),
            average_price=Decimal('5.2500'),
            market_value=Decimal('5250.00'),
            delta=Decimal('0.6500'),
            theta=Decimal('-0.0250'),
            expiry=expiry_date,
            strike=Decimal('150.0000'),
            option_type='call'
        )
        
        self.assertEqual(position.asset_type, 'option')
        self.assertEqual(position.expiry, expiry_date)
        self.assertEqual(position.strike, Decimal('150.0000'))
        self.assertEqual(position.option_type, 'call')
        self.assertEqual(position.delta, Decimal('0.6500'))

    def test_position_unique_together_constraint(self):
        """Test unique_together constraint for positions"""
        expiry_date = date(2024, 12, 20)
        
        # Create first option position with specific values
        Position.objects.create(
            user=self.user,
            credential=self.credential,
            tastytrade_account_number='123456789',
            asset_type='option',
            symbol='AAPL',
            quantity=Decimal('10.0000'),
            expiry=expiry_date,
            strike=Decimal('150.0000'),
            option_type='call'
        )
        
        # Attempting to create duplicate option position should fail
        with self.assertRaises(IntegrityError):
            Position.objects.create(
                user=self.user,
                credential=self.credential,
                tastytrade_account_number='123456789',
                asset_type='option',
                symbol='AAPL',
                quantity=Decimal('20.0000'),  # Different quantity, but same unique fields
                expiry=expiry_date,
                strike=Decimal('150.0000'),
                option_type='call'
            )

    def test_position_allows_different_option_types(self):
        """Test that positions with different option types are allowed"""
        expiry_date = date(2024, 12, 20)
        
        # Create call option
        Position.objects.create(
            user=self.user,
            credential=self.credential,
            tastytrade_account_number='123456789',
            asset_type='option',
            symbol='AAPL',
            quantity=Decimal('10.0000'),
            expiry=expiry_date,
            strike=Decimal('150.0000'),
            option_type='call'
        )
        
        # Creating put option with same other fields should work
        Position.objects.create(
            user=self.user,
            credential=self.credential,
            tastytrade_account_number='123456789',
            asset_type='option',
            symbol='AAPL',
            quantity=Decimal('10.0000'),
            expiry=expiry_date,
            strike=Decimal('150.0000'),
            option_type='put'  # Different option type
        )
        
        # Should have 2 positions
        self.assertEqual(Position.objects.count(), 2)

    def test_position_str_representation(self):
        """Test string representation"""
        position = Position.objects.create(
            user=self.user,
            credential=self.credential,
            tastytrade_account_number='123456789',
            asset_type='stock',
            symbol='AAPL',
            quantity=Decimal('100.0000')
        )
        
        expected = "AAPL (stock) - 100.0000"
        self.assertEqual(str(position), expected)


class TransactionTests(TestCase):
    """Test Transaction model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.credential = TastyTradeCredential.objects.create(
            user=self.user,
            environment='prod',
            username='testuser',
            password='testpass'
        )

    def test_create_trade_transaction(self):
        """Test creating a trade transaction"""
        trade_date = datetime(2024, 5, 29, 14, 30, 0, tzinfo=timezone.utc)
        transaction = Transaction.objects.create(
            user=self.user,
            credential=self.credential,
            tastytrade_account_number='123456789',
            transaction_id='TXN123456',
            transaction_type='trade',
            symbol='AAPL',
            description='Buy 100 AAPL',
            quantity=Decimal('100.0000'),
            price=Decimal('150.2500'),
            amount=Decimal('15025.00'),
            trade_date=trade_date,
            asset_type='stock'
        )
        
        self.assertEqual(transaction.user, self.user)
        self.assertEqual(transaction.transaction_id, 'TXN123456')
        self.assertEqual(transaction.transaction_type, 'trade')
        self.assertEqual(transaction.symbol, 'AAPL')
        self.assertEqual(transaction.quantity, Decimal('100.0000'))
        self.assertEqual(transaction.amount, Decimal('15025.00'))
        self.assertEqual(transaction.trade_date, trade_date)

    def test_create_dividend_transaction(self):
        """Test creating a dividend transaction"""
        trade_date = datetime(2024, 5, 29, 14, 30, 0, tzinfo=timezone.utc)
        transaction = Transaction.objects.create(
            user=self.user,
            credential=self.credential,
            tastytrade_account_number='123456789',
            transaction_id='DIV123456',
            transaction_type='dividend',
            symbol='AAPL',
            description='AAPL Dividend',
            amount=Decimal('24.00'),
            trade_date=trade_date
        )
        
        self.assertEqual(transaction.transaction_type, 'dividend')
        self.assertIsNone(transaction.quantity)
        self.assertIsNone(transaction.price)

    def test_transaction_unique_id_constraint(self):
        """Test unique transaction_id constraint"""
        trade_date = datetime(2024, 5, 29, 14, 30, 0, tzinfo=timezone.utc)
        
        # Create first transaction
        Transaction.objects.create(
            user=self.user,
            credential=self.credential,
            tastytrade_account_number='123456789',
            transaction_id='TXN123456',
            transaction_type='trade',
            amount=Decimal('1000.00'),
            trade_date=trade_date
        )
        
        # Attempting to create transaction with same ID should fail
        with self.assertRaises(IntegrityError):
            Transaction.objects.create(
                user=self.user,
                credential=self.credential,
                tastytrade_account_number='987654321',
                transaction_id='TXN123456',  # Same ID
                transaction_type='trade',
                amount=Decimal('2000.00'),
                trade_date=trade_date
            )

    def test_transaction_ordering(self):
        """Test transaction ordering by trade_date descending"""
        date1 = datetime(2024, 5, 28, 14, 30, 0, tzinfo=timezone.utc)
        date2 = datetime(2024, 5, 29, 14, 30, 0, tzinfo=timezone.utc)
        
        # Create transactions in random order
        txn2 = Transaction.objects.create(
            user=self.user,
            credential=self.credential,
            tastytrade_account_number='123456789',
            transaction_id='TXN2',
            transaction_type='trade',
            amount=Decimal('2000.00'),
            trade_date=date2
        )
        
        txn1 = Transaction.objects.create(
            user=self.user,
            credential=self.credential,
            tastytrade_account_number='123456789',
            transaction_id='TXN1',
            transaction_type='trade',
            amount=Decimal('1000.00'),
            trade_date=date1
        )
        
        # Should be ordered by trade_date descending (newest first)
        transactions = list(Transaction.objects.all())
        self.assertEqual(transactions[0], txn2)  # More recent date first
        self.assertEqual(transactions[1], txn1)

    def test_transaction_str_representation(self):
        """Test string representation"""
        trade_date = datetime(2024, 5, 29, 14, 30, 0, tzinfo=timezone.utc)
        transaction = Transaction.objects.create(
            user=self.user,
            credential=self.credential,
            tastytrade_account_number='123456789',
            transaction_id='TXN123456',
            transaction_type='trade',
            symbol='AAPL',
            amount=Decimal('15025.00'),
            trade_date=trade_date
        )
        
        expected = f"trade AAPL 15025.00 on {trade_date}"
        self.assertEqual(str(transaction), expected)


class ModelValidationTests(TestCase):
    """Test model validations for financial data integrity"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.credential = TastyTradeCredential.objects.create(
            user=self.user,
            environment='prod',
            username='testuser',
            password='testpass'
        )

    def test_decimal_precision_validation(self):
        """Test that decimal fields maintain proper precision"""
        position = Position.objects.create(
            user=self.user,
            credential=self.credential,
            tastytrade_account_number='123456789',
            asset_type='stock',
            symbol='TEST',
            quantity=Decimal('100.1234'),  # 4 decimal places
            average_price=Decimal('150.1234'),  # 4 decimal places
            market_value=Decimal('15012.34'),  # 2 decimal places
        )
        
        # Refresh from database to check stored precision
        position.refresh_from_db()
        self.assertEqual(position.quantity, Decimal('100.1234'))
        self.assertEqual(position.average_price, Decimal('150.1234'))
        self.assertEqual(position.market_value, Decimal('15012.34'))

    def test_required_fields_validation(self):
        """Test that required fields are enforced"""
        # Position without required user should fail
        with self.assertRaises(IntegrityError):
            Position.objects.create(
                credential=self.credential,
                tastytrade_account_number='123456789',
                asset_type='stock',
                symbol='TEST',
                quantity=Decimal('100.0000')
            )

    def test_choice_field_validation(self):
        """Test that choice fields only accept valid values"""
        with self.assertRaises(ValidationError):
            position = Position(
                user=self.user,
                credential=self.credential,
                tastytrade_account_number='123456789',
                asset_type='invalid_type',  # Invalid choice
                symbol='TEST',
                quantity=Decimal('100.0000')
            )
            position.full_clean()