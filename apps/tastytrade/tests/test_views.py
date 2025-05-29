"""
Integration tests for TastyTrade views and sync workflows
Tests end-to-end functionality including view logic and database operations
"""

from unittest.mock import Mock, patch
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils import timezone
from datetime import datetime, date
from decimal import Decimal

from apps.tastytrade.models import TastyTradeCredential, Position, Transaction
from apps.tastytrade.views import sync_tastytrade

User = get_user_model()


class TastyTradeViewTests(TestCase):
    """Test TastyTrade views and authentication requirements"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_connect_view_requires_authentication(self):
        """Test that connect view requires user to be logged in"""
        response = self.client.get(reverse('tastytrade_connect'))
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_connect_view_authenticated_no_credential(self):
        """Test connect view for authenticated user without credentials"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('tastytrade_connect'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Connect Your TastyTrade Account')
        self.assertContains(response, 'Connect Account')  # Submit button text

    def test_connect_view_authenticated_with_credential(self):
        """Test connect view for authenticated user with existing credentials"""
        credential = TastyTradeCredential.objects.create(
            user=self.user,
            environment='prod',
            username='existing_user',
            password='existing_pass'
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('tastytrade_connect'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Connected as: existing_user')
        self.assertContains(response, 'Update Credentials')
        self.assertContains(response, 'Remove')

    def test_connect_view_post_create_credential(self):
        """Test creating new credentials via POST"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(reverse('tastytrade_connect'), {
            'username': 'newuser',
            'password': 'newpass'
        })
        
        # Should redirect back to connect page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('tastytrade_connect'))
        
        # Credential should be created
        credential = TastyTradeCredential.objects.get(user=self.user)
        self.assertEqual(credential.username, 'newuser')
        self.assertEqual(credential.password, 'newpass')
        self.assertEqual(credential.environment, 'prod')  # Default

    def test_connect_view_post_update_credential(self):
        """Test updating existing credentials via POST"""
        credential = TastyTradeCredential.objects.create(
            user=self.user,
            environment='prod',
            username='olduser',
            password='oldpass'
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(reverse('tastytrade_connect'), {
            'username': 'updateduser',
            'password': 'updatedpass'
        })
        
        # Should redirect back to connect page
        self.assertEqual(response.status_code, 302)
        
        # Credential should be updated
        credential.refresh_from_db()
        self.assertEqual(credential.username, 'updateduser')
        self.assertEqual(credential.password, 'updatedpass')

    def test_remove_credential_view(self):
        """Test removing credentials"""
        credential = TastyTradeCredential.objects.create(
            user=self.user,
            environment='prod',
            username='toremove',
            password='toremove'
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('tastytrade_remove'))
        
        # Should redirect to connect page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('tastytrade_connect'))
        
        # Credential should be deleted
        self.assertFalse(TastyTradeCredential.objects.filter(user=self.user).exists())

    def test_remove_credential_view_no_credential(self):
        """Test removing credentials when none exist"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('tastytrade_remove'))
        
        # Should still redirect successfully
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('tastytrade_connect'))

    def test_sync_view_requires_authentication(self):
        """Test that sync view requires authentication"""
        response = self.client.post(reverse('tastytrade_sync'))
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_sync_view_no_credentials(self):
        """Test sync view when user has no credentials"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('tastytrade_sync'))
        
        # Should redirect to home with error message
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('home'))
        
        # Check error message was added
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('No TastyTrade credentials found', str(messages[0]))


class SyncWorkflowIntegrationTests(TestCase):
    """Test complete sync workflow including API calls and database operations"""

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

    @patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.fetch_transactions')
    @patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.fetch_positions')
    @patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.fetch_accounts')
    @patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.login')
    def test_successful_sync_workflow(self, mock_login, mock_fetch_accounts, 
                                     mock_fetch_positions, mock_fetch_transactions):
        """Test complete successful sync workflow"""
        
        # Mock API responses
        mock_login.return_value = None
        mock_fetch_accounts.return_value = ['123456789']
        
        mock_fetch_positions.return_value = [
            {
                'asset_type': 'stock',
                'symbol': 'AAPL',
                'description': 'Apple Inc.',
                'quantity': Decimal('100.0000'),
                'average_price': Decimal('150.25'),
                'market_value': Decimal('15025.00'),
                'unrealized_pnl': Decimal('500.00'),
                'realized_pnl': Decimal('200.00'),
                'delta': None,
                'theta': None,
                'beta': None,
                'expiry': None,
                'strike': None,
                'option_type': None
            }
        ]
        
        mock_fetch_transactions.return_value = [
            {
                'transaction_id': 'TXN123',
                'transaction_type': 'trade',
                'symbol': 'AAPL',
                'description': 'Buy 100 AAPL',
                'quantity': Decimal('100.0000'),
                'price': Decimal('150.25'),
                'amount': Decimal('15025.00'),
                'trade_date': datetime(2024, 5, 29, 14, 30, 0, tzinfo=timezone.utc),
                'asset_type': 'stock',
                'expiry': None,
                'strike': None,
                'option_type': None
            }
        ]

        # Perform sync
        from apps.tastytrade.views import sync_tastytrade
        from django.http import HttpRequest
        from django.contrib.auth import get_user
        
        request = HttpRequest()
        request.method = 'POST'
        request.user = self.user
        
        # Mock messages framework
        with patch('apps.tastytrade.views.messages') as mock_messages:
            with patch('apps.tastytrade.views.redirect') as mock_redirect:
                sync_tastytrade(request)
        
        # Verify API methods were called
        mock_login.assert_called_once()
        mock_fetch_accounts.assert_called_once()
        mock_fetch_positions.assert_called_once_with('123456789')
        mock_fetch_transactions.assert_called_once_with('123456789')
        
        # Verify data was saved to database
        self.assertEqual(Position.objects.count(), 1)
        position = Position.objects.first()
        self.assertEqual(position.symbol, 'AAPL')
        self.assertEqual(position.quantity, Decimal('100.0000'))
        self.assertEqual(position.user, self.user)
        
        self.assertEqual(Transaction.objects.count(), 1)
        transaction = Transaction.objects.first()
        self.assertEqual(transaction.transaction_id, 'TXN123')
        self.assertEqual(transaction.symbol, 'AAPL')
        self.assertEqual(transaction.user, self.user)
        
        # Verify last_sync was updated
        self.credential.refresh_from_db()
        self.assertIsNotNone(self.credential.last_sync)
        
        # Verify success message was added
        mock_messages.success.assert_called_once()

    @patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.login')
    def test_sync_workflow_login_failure(self, mock_login):
        """Test sync workflow when login fails"""
        mock_login.side_effect = Exception("Login failed: Invalid credentials")
        
        from django.http import HttpRequest
        
        request = HttpRequest()
        request.method = 'POST'
        request.user = self.user
        
        with patch('apps.tastytrade.views.messages') as mock_messages:
            with patch('apps.tastytrade.views.redirect') as mock_redirect:
                sync_tastytrade(request)
        
        # Verify error message was added
        mock_messages.error.assert_called_once()
        error_message = mock_messages.error.call_args[0][1]
        self.assertIn('Sync failed', error_message)
        self.assertIn('Login failed', error_message)
        
        # Verify no data was saved
        self.assertEqual(Position.objects.count(), 0)
        self.assertEqual(Transaction.objects.count(), 0)

    @patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.fetch_accounts')
    @patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.login')
    def test_sync_workflow_no_accounts(self, mock_login, mock_fetch_accounts):
        """Test sync workflow when no accounts are found"""
        mock_login.return_value = None
        mock_fetch_accounts.return_value = []
        
        from django.http import HttpRequest
        
        request = HttpRequest()
        request.method = 'POST'
        request.user = self.user
        
        with patch('apps.tastytrade.views.messages') as mock_messages:
            with patch('apps.tastytrade.views.redirect') as mock_redirect:
                sync_tastytrade(request)
        
        # Verify error message was added
        mock_messages.error.assert_called_once()
        error_message = mock_messages.error.call_args[0][1]
        self.assertIn('No TastyTrade accounts found', error_message)

    @patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.fetch_transactions')
    @patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.fetch_positions')
    @patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.fetch_accounts')
    @patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.login')
    def test_sync_deduplication(self, mock_login, mock_fetch_accounts, 
                               mock_fetch_positions, mock_fetch_transactions):
        """Test that sync properly handles duplicate data"""
        
        # Create existing position
        existing_position = Position.objects.create(
            user=self.user,
            credential=self.credential,
            tastytrade_account_number='123456789',
            asset_type='stock',
            symbol='AAPL',
            quantity=Decimal('50.0000'),
            average_price=Decimal('140.00')
        )
        
        # Create existing transaction
        existing_transaction = Transaction.objects.create(
            user=self.user,
            credential=self.credential,
            tastytrade_account_number='123456789',
            transaction_id='TXN123',
            transaction_type='trade',
            amount=Decimal('7000.00'),
            trade_date=datetime(2024, 5, 28, 10, 0, 0, tzinfo=timezone.utc)
        )
        
        # Mock API responses with updated data
        mock_login.return_value = None
        mock_fetch_accounts.return_value = ['123456789']
        
        mock_fetch_positions.return_value = [
            {
                'asset_type': 'stock',
                'symbol': 'AAPL',
                'description': 'Apple Inc.',
                'quantity': Decimal('100.0000'),  # Updated quantity
                'average_price': Decimal('150.25'),  # Updated price
                'market_value': Decimal('15025.00'),
                'unrealized_pnl': None,
                'realized_pnl': None,
                'delta': None,
                'theta': None,
                'beta': None,
                'expiry': None,
                'strike': None,
                'option_type': None
            }
        ]
        
        mock_fetch_transactions.return_value = [
            {
                'transaction_id': 'TXN123',  # Same ID as existing
                'transaction_type': 'trade',
                'symbol': 'AAPL',
                'description': 'Updated description',
                'quantity': Decimal('100.0000'),
                'price': Decimal('150.25'),
                'amount': Decimal('15025.00'),  # Updated amount
                'trade_date': datetime(2024, 5, 29, 14, 30, 0, tzinfo=timezone.utc),
                'asset_type': 'stock',
                'expiry': None,
                'strike': None,
                'option_type': None
            }
        ]

        from django.http import HttpRequest
        
        request = HttpRequest()
        request.method = 'POST'
        request.user = self.user
        
        with patch('apps.tastytrade.views.messages'):
            with patch('apps.tastytrade.views.redirect'):
                sync_tastytrade(request)
        
        # Should still have only one position and one transaction
        self.assertEqual(Position.objects.count(), 1)
        self.assertEqual(Transaction.objects.count(), 1)
        
        # But data should be updated
        position = Position.objects.first()
        self.assertEqual(position.quantity, Decimal('100.0000'))
        self.assertEqual(position.average_price, Decimal('150.25'))
        
        transaction = Transaction.objects.first()
        self.assertEqual(transaction.amount, Decimal('15025.00'))
        self.assertEqual(transaction.description, 'Updated description')

    @patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.fetch_transactions')
    @patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.fetch_positions')
    @patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.fetch_accounts')
    @patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.login')
    def test_sync_handles_incomplete_data(self, mock_login, mock_fetch_accounts, 
                                         mock_fetch_positions, mock_fetch_transactions):
        """Test that sync handles incomplete or invalid data gracefully"""
        
        mock_login.return_value = None
        mock_fetch_accounts.return_value = ['123456789']
        
        # Return positions with missing required fields
        mock_fetch_positions.return_value = [
            {
                'asset_type': 'stock',
                'symbol': None,  # Missing required symbol
                'quantity': Decimal('100.0000'),
            },
            {
                'asset_type': 'stock',
                'symbol': 'VALID',  # This one should be saved
                'quantity': Decimal('50.0000'),
            }
        ]
        
        # Return transactions with missing required fields
        mock_fetch_transactions.return_value = [
            {
                'transaction_id': None,  # Missing required ID
                'transaction_type': 'trade',
                'amount': Decimal('1000.00'),
                'trade_date': datetime(2024, 5, 29, 14, 30, 0, tzinfo=timezone.utc),
            },
            {
                'transaction_id': 'VALID123',  # This one should be saved
                'transaction_type': 'trade',
                'amount': Decimal('2000.00'),
                'trade_date': datetime(2024, 5, 29, 14, 30, 0, tzinfo=timezone.utc),
            }
        ]

        from django.http import HttpRequest
        
        request = HttpRequest()
        request.method = 'POST'
        request.user = self.user
        
        with patch('apps.tastytrade.views.messages'):
            with patch('apps.tastytrade.views.redirect'):
                sync_tastytrade(request)
        
        # Should only save valid records
        self.assertEqual(Position.objects.count(), 1)
        position = Position.objects.first()
        self.assertEqual(position.symbol, 'VALID')
        
        self.assertEqual(Transaction.objects.count(), 1)
        transaction = Transaction.objects.first()
        self.assertEqual(transaction.transaction_id, 'VALID123')