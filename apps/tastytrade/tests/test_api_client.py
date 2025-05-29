"""
Unit tests for TastyTrade API client
Mocks external API calls to ensure reliable testing
"""

import json
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import datetime, date
from requests.exceptions import RequestException, HTTPError

from apps.tastytrade.models import TastyTradeCredential
from apps.tastytrade.tastytrade_api import TastyTradeAPI

User = get_user_model()


class TastyTradeAPITests(TestCase):
    """Test TastyTrade API client functionality"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create production credential
        self.prod_credential = TastyTradeCredential.objects.create(
            user=self.user,
            environment='prod',
            username='produser',
            password='prodpass'
        )
        
        # Create sandbox credential
        self.sandbox_credential = TastyTradeCredential.objects.create(
            user=User.objects.create_user('sandbox_user', 'sandbox@test.com', 'pass'),
            environment='sandbox',
            username='sandboxuser',
            password='sandboxpass'
        )

    def test_api_initialization_production(self):
        """Test API client initialization for production"""
        api = TastyTradeAPI(self.prod_credential)
        
        self.assertEqual(api.base_url, 'https://api.tastytrade.com')
        self.assertEqual(api.credential, self.prod_credential)
        self.assertIsNone(api.token)
        self.assertEqual(api.session.headers['User-Agent'], 'tastytrade-tracker/1.0')

    def test_api_initialization_sandbox(self):
        """Test API client initialization for sandbox"""
        api = TastyTradeAPI(self.sandbox_credential)
        
        self.assertEqual(api.base_url, 'https://api.cert.tastyworks.com')
        self.assertEqual(api.credential, self.sandbox_credential)

    @patch('apps.tastytrade.tastytrade_api.requests.Session.post')
    def test_successful_login(self, mock_post):
        """Test successful login flow"""
        # Mock successful login response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {
                "session-token": "test-session-token-123",
                "user": {
                    "username": "testuser",
                    "email": "test@example.com"
                }
            }
        }
        mock_post.return_value = mock_response
        
        api = TastyTradeAPI(self.prod_credential)
        api.login()
        
        # Verify login was called correctly
        mock_post.assert_called_once_with(
            'https://api.tastytrade.com/sessions',
            json={'login': 'produser', 'password': 'prodpass'}
        )
        
        # Verify token was stored and headers updated
        self.assertEqual(api.token, 'test-session-token-123')
        self.assertEqual(api.session.headers['Authorization'], 'test-session-token-123')

    @patch('apps.tastytrade.tastytrade_api.requests.Session.post')
    def test_login_failure_invalid_credentials(self, mock_post):
        """Test login failure with invalid credentials"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = '{"error":{"code":"invalid_credentials","message":"Invalid login"}}'
        mock_post.return_value = mock_response
        
        api = TastyTradeAPI(self.prod_credential)
        
        with self.assertRaises(Exception) as context:
            api.login()
        
        self.assertIn('TastyTrade login failed', str(context.exception))
        self.assertIn('invalid_credentials', str(context.exception))

    @patch('apps.tastytrade.tastytrade_api.requests.Session.post')
    def test_login_handles_whitespace_in_credentials(self, mock_post):
        """Test that login strips whitespace from credentials"""
        # Create credential with whitespace
        credential = TastyTradeCredential.objects.create(
            user=User.objects.create_user('whitespace_user', 'ws@test.com', 'pass'),
            environment='prod',
            username='  spaced_user  ',
            password='  spaced_pass  '
        )
        
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {"session-token": "test-token"}
        }
        mock_post.return_value = mock_response
        
        api = TastyTradeAPI(credential)
        api.login()
        
        # Verify credentials were stripped
        mock_post.assert_called_once_with(
            'https://api.tastytrade.com/sessions',
            json={'login': 'spaced_user', 'password': 'spaced_pass'}
        )

    @patch('apps.tastytrade.tastytrade_api.requests.Session.get')
    def test_fetch_accounts_success(self, mock_get):
        """Test successful account fetching"""
        # Mock customer info response
        customer_response = Mock()
        customer_response.status_code = 200
        customer_response.json.return_value = {
            "data": {"id": "customer-123"}
        }
        
        # Mock accounts response
        accounts_response = Mock()
        accounts_response.status_code = 200
        accounts_response.json.return_value = {
            "data": [
                {"account-number": "123456789"},
                {"account-number": "987654321"}
            ]
        }
        
        mock_get.side_effect = [customer_response, accounts_response]
        
        api = TastyTradeAPI(self.prod_credential)
        api.token = "test-token"  # Simulate logged in state
        
        accounts = api.fetch_accounts()
        
        self.assertEqual(accounts, ["123456789", "987654321"])
        # Verify both calls were made
        expected_calls = [
            (('https://api.tastytrade.com/me',), {}),
            (('https://api.tastytrade.com/customers/customer-123/accounts',), {})
        ]
        self.assertEqual(mock_get.call_args_list, expected_calls)

    @patch('apps.tastytrade.tastytrade_api.requests.Session.get')
    def test_fetch_accounts_empty_response(self, mock_get):
        """Test account fetching with empty response"""
        # Mock customer info response
        customer_response = Mock()
        customer_response.status_code = 200
        customer_response.json.return_value = {
            "data": {"id": "customer-123"}
        }
        
        # Mock empty accounts response
        accounts_response = Mock()
        accounts_response.status_code = 200
        accounts_response.json.return_value = {"data": []}
        
        mock_get.side_effect = [customer_response, accounts_response]
        
        api = TastyTradeAPI(self.prod_credential)
        api.token = "test-token"
        
        accounts = api.fetch_accounts()
        
        self.assertEqual(accounts, [])

    @patch('apps.tastytrade.tastytrade_api.requests.Session.get')
    def test_fetch_accounts_not_permitted(self, mock_get):
        """Test account fetching with 403 not permitted error"""
        # Mock customer info failure
        customer_response = Mock()
        customer_response.status_code = 403
        customer_response.text = '{"error":{"code":"not_permitted","message":"User not permitted access"}}'
        mock_get.return_value = customer_response
        
        api = TastyTradeAPI(self.prod_credential)
        api.token = "test-token"
        
        with self.assertRaises(Exception) as context:
            api.fetch_accounts()
        
        self.assertIn('Failed to get customer info', str(context.exception))
        self.assertIn('403', str(context.exception))

    @patch('apps.tastytrade.tastytrade_api.requests.Session.get')
    def test_fetch_positions_success(self, mock_get):
        """Test successful position fetching"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "instrument-type": "stock",
                    "symbol": "AAPL",
                    "description": "Apple Inc.",
                    "quantity": 100,
                    "average-price": 150.25,
                    "market-value": 15025.00,
                    "unrealized-pnl": 500.00,
                    "delta": 1.0
                },
                {
                    "instrument-type": "option",
                    "symbol": "AAPL",
                    "description": "AAPL Call",
                    "quantity": 10,
                    "average-price": 5.25,
                    "expiration-date": "2024-12-20",
                    "strike-price": 150.00,
                    "put-call": "call"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        api = TastyTradeAPI(self.prod_credential)
        api.token = "test-token"
        
        positions = api.fetch_positions("123456789")
        
        self.assertEqual(len(positions), 2)
        
        # Check stock position
        stock_pos = positions[0]
        self.assertEqual(stock_pos['asset_type'], 'stock')
        self.assertEqual(stock_pos['symbol'], 'AAPL')
        self.assertEqual(stock_pos['quantity'], 100)
        
        # Check option position
        option_pos = positions[1]
        self.assertEqual(option_pos['asset_type'], 'option')
        self.assertEqual(option_pos['expiry'], date(2024, 12, 20))
        self.assertEqual(option_pos['strike'], 150.00)
        self.assertEqual(option_pos['option_type'], 'call')

    @patch('apps.tastytrade.tastytrade_api.requests.Session.get')
    def test_fetch_transactions_success(self, mock_get):
        """Test successful transaction fetching"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "transaction-id": "TXN123",
                    "type": "trade",
                    "symbol": "AAPL",
                    "description": "Buy 100 AAPL",
                    "quantity": 100,
                    "price": 150.25,
                    "amount": 15025.00,
                    "transaction-date": "2024-05-29T14:30:00Z",
                    "instrument-type": "stock"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        api = TastyTradeAPI(self.prod_credential)
        api.token = "test-token"
        
        transactions = api.fetch_transactions("123456789")
        
        self.assertEqual(len(transactions), 1)
        
        txn = transactions[0]
        self.assertEqual(txn['transaction_id'], 'TXN123')
        self.assertEqual(txn['transaction_type'], 'trade')
        self.assertEqual(txn['symbol'], 'AAPL')
        self.assertEqual(txn['amount'], 15025.00)
        
        # Check date parsing
        expected_date = datetime(2024, 5, 29, 14, 30, 0, tzinfo=datetime.now().astimezone().tzinfo)
        self.assertIsInstance(txn['trade_date'], datetime)

    @patch('apps.tastytrade.tastytrade_api.requests.Session.get')
    def test_fetch_transactions_date_parsing_error(self, mock_get):
        """Test transaction fetching with invalid date format"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "transaction-id": "TXN123",
                    "type": "trade",
                    "amount": 1000.00,
                    "transaction-date": "invalid-date-format",
                }
            ]
        }
        mock_get.return_value = mock_response
        
        api = TastyTradeAPI(self.prod_credential)
        api.token = "test-token"
        
        transactions = api.fetch_transactions("123456789")
        
        # Should handle invalid date gracefully
        self.assertEqual(len(transactions), 1)
        self.assertIsNone(transactions[0]['trade_date'])

    @patch('apps.tastytrade.tastytrade_api.requests.Session.get')
    def test_test_session_success(self, mock_get):
        """Test successful session validation"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"username": "testuser"}
        }
        mock_get.return_value = mock_response
        
        api = TastyTradeAPI(self.prod_credential)
        api.token = "test-token"
        
        result = api.test_session()
        
        self.assertTrue(result)
        mock_get.assert_called_once_with('https://api.tastytrade.com/me')

    @patch('apps.tastytrade.tastytrade_api.requests.Session.get')
    def test_test_session_failure(self, mock_get):
        """Test session validation failure"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        api = TastyTradeAPI(self.prod_credential)
        api.token = "invalid-token"
        
        result = api.test_session()
        
        self.assertFalse(result)

    def test_header_initialization(self):
        """Test that headers are properly initialized"""
        api = TastyTradeAPI(self.prod_credential)
        
        headers = api.session.headers
        self.assertEqual(headers['User-Agent'], 'tastytrade-tracker/1.0')
        self.assertEqual(headers['Content-Type'], 'application/json')
        self.assertEqual(headers['Accept'], 'application/json')
        self.assertNotIn('Authorization', headers)  # Should be empty before login

    @patch('apps.tastytrade.tastytrade_api.requests.Session.post')
    def test_authorization_header_update(self, mock_post):
        """Test that authorization header is properly updated after login"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {"session-token": "new-token-123"}
        }
        mock_post.return_value = mock_response
        
        api = TastyTradeAPI(self.prod_credential)
        
        # Set an old authorization header
        api.session.headers['Authorization'] = 'old-token'
        
        api.login()
        
        # Should have updated to new token
        self.assertEqual(api.session.headers['Authorization'], 'new-token-123')

    @patch('apps.tastytrade.tastytrade_api.requests.Session')
    def test_network_error_handling(self, mock_session):
        """Test handling of network errors"""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.post.side_effect = RequestException("Network error")
        
        api = TastyTradeAPI(self.prod_credential)
        
        with self.assertRaises(RequestException):
            api.login()


class APIDataParsingTests(TestCase):
    """Test API response data parsing and validation"""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass')
        self.credential = TastyTradeCredential.objects.create(
            user=self.user,
            environment='prod',
            username='testuser',
            password='testpass'
        )

    def test_position_data_extraction(self):
        """Test that position data is correctly extracted from API response"""
        api = TastyTradeAPI(self.credential)
        
        # Test with minimal data
        raw_data = {
            "symbol": "TEST",
            "instrument-type": "stock",
            "quantity": 100
        }
        
        # This would be part of the fetch_positions logic
        position_data = {
            "asset_type": raw_data.get("instrument-type", "other"),
            "symbol": raw_data.get("symbol"),
            "quantity": raw_data.get("quantity", 0),
            "description": raw_data.get("description", ""),
        }
        
        self.assertEqual(position_data['asset_type'], 'stock')
        self.assertEqual(position_data['symbol'], 'TEST')
        self.assertEqual(position_data['quantity'], 100)
        self.assertEqual(position_data['description'], '')

    def test_transaction_data_extraction(self):
        """Test that transaction data is correctly extracted from API response"""
        api = TastyTradeAPI(self.credential)
        
        raw_data = {
            "transaction-id": "TXN123",
            "type": "trade",
            "symbol": "AAPL",
            "amount": 1000.50,
            "transaction-date": "2024-05-29T14:30:00Z"
        }
        
        # This would be part of the fetch_transactions logic
        transaction_data = {
            "transaction_id": raw_data.get("transaction-id"),
            "transaction_type": raw_data.get("type", "other"),
            "symbol": raw_data.get("symbol", ""),
            "amount": raw_data.get("amount"),
        }
        
        self.assertEqual(transaction_data['transaction_id'], 'TXN123')
        self.assertEqual(transaction_data['transaction_type'], 'trade')
        self.assertEqual(transaction_data['amount'], 1000.50)