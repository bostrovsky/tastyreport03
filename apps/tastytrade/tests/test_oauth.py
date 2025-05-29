from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.tastytrade.models import TastyTradeCredential
from apps.tastytrade.tastytrade_api import TastyTradeAPI

User = get_user_model()


class OAuthAPIClientTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.credential = TastyTradeCredential.objects.create(
            user=self.user,
            environment='sandbox',
            username='test_user',
            password='test_pass'
        )

    def test_oauth_client_configuration_check(self):
        """Test OAuth client configuration detection"""
        # Test with OAuth configured
        with patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.OAUTH_CLIENT_ID', 'test_client_id'), \
             patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.OAUTH_CLIENT_SECRET', 'test_client_secret'):
            
            self.credential.access_token = 'test_access_token'
            self.credential.save()
            
            api = TastyTradeAPI(self.credential)
            self.assertTrue(api._can_use_oauth())
            self.assertEqual(api.auth_method, 'oauth')

    def test_oauth_disabled_fallback_to_session(self):
        """Test fallback to session auth when OAuth not configured"""
        with patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.OAUTH_CLIENT_ID', None), \
             patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.OAUTH_CLIENT_SECRET', None):
            
            api = TastyTradeAPI(self.credential)
            self.assertFalse(api._can_use_oauth())
            self.assertEqual(api.auth_method, 'session')

    def test_oauth_authorization_url_generation(self):
        """Test OAuth authorization URL generation"""
        with patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.OAUTH_CLIENT_ID', 'test_client_id'), \
             patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.OAUTH_CLIENT_SECRET', 'test_client_secret'), \
             patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.OAUTH_REDIRECT_URI', 'http://localhost:8000/callback'):
            
            api = TastyTradeAPI(self.credential)
            auth_url = api.get_oauth_authorization_url()
            
            self.assertIn('https://api.cert.tastyworks.com/oauth/authorize', auth_url)
            self.assertIn('client_id=test_client_id', auth_url)
            self.assertIn('redirect_uri=http://localhost:8000/callback', auth_url)
            self.assertIn('response_type=code', auth_url)

    @patch('apps.tastytrade.tastytrade_api.requests.Session.post')
    @patch('apps.tastytrade.tastytrade_api.settings')
    def test_oauth_token_exchange(self, mock_settings, mock_post):
        """Test OAuth authorization code to token exchange"""
        mock_settings.TASTYTRADE_OAUTH_CLIENT_ID = 'test_client_id'
        mock_settings.TASTYTRADE_OAUTH_CLIENT_SECRET = 'test_client_secret'
        mock_settings.TASTYTRADE_OAUTH_REDIRECT_URI = 'http://localhost:8000/callback'
        
        # Mock successful token response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'expires_in': 900
        }
        mock_post.return_value = mock_response
        
        api = TastyTradeAPI(self.credential)
        token_data = api.exchange_code_for_tokens('test_auth_code')
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], 'https://api.cert.tastyworks.com/oauth/token')
        
        # Verify token data
        self.assertEqual(token_data['access_token'], 'new_access_token')
        self.assertEqual(token_data['refresh_token'], 'new_refresh_token')
        
        # Verify credential was updated
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.access_token, 'new_access_token')
        self.assertEqual(self.credential.refresh_token, 'new_refresh_token')

    @patch('apps.tastytrade.tastytrade_api.requests.Session.post')
    @patch('apps.tastytrade.tastytrade_api.settings')
    def test_oauth_token_refresh(self, mock_settings, mock_post):
        """Test OAuth token refresh functionality"""
        mock_settings.TASTYTRADE_OAUTH_CLIENT_ID = 'test_client_id'
        mock_settings.TASTYTRADE_OAUTH_CLIENT_SECRET = 'test_client_secret'
        
        self.credential.refresh_token = 'test_refresh_token'
        self.credential.save()
        
        # Mock successful refresh response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'refreshed_access_token',
            'refresh_token': 'new_refresh_token',
            'expires_in': 900
        }
        mock_post.return_value = mock_response
        
        api = TastyTradeAPI(self.credential)
        success = api._refresh_access_token()
        
        self.assertTrue(success)
        
        # Verify credential was updated
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.access_token, 'refreshed_access_token')
        self.assertEqual(self.credential.refresh_token, 'new_refresh_token')

    def test_oauth_token_expiry_check(self):
        """Test OAuth token expiry validation"""
        with patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.OAUTH_CLIENT_ID', 'test_client_id'), \
             patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.OAUTH_CLIENT_SECRET', 'test_client_secret'):
            
            # Set up a real current time (no mocking needed)
            current_time = timezone.now()
            
            api = TastyTradeAPI(self.credential)
            
            # Test token not expired
            api.token_expires_at = current_time + timedelta(minutes=5)
            self.assertTrue(api._is_token_valid())
            
            # Test token expired
            api.token_expires_at = current_time - timedelta(minutes=5)
            self.assertFalse(api._is_token_valid())
            
            # Test no expiry time
            api.token_expires_at = None
            self.assertFalse(api._is_token_valid())

    @patch('apps.tastytrade.tastytrade_api.requests.Session.get')
    def test_oauth_authentication_with_refresh(self, mock_get):
        """Test OAuth authentication with automatic token refresh"""
        with patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.OAUTH_CLIENT_ID', 'test_client_id'), \
             patch('apps.tastytrade.tastytrade_api.TastyTradeAPI.OAUTH_CLIENT_SECRET', 'test_client_secret'):
            
            self.credential.access_token = 'expired_token'
            self.credential.refresh_token = 'valid_refresh_token'
            self.credential.save()
            
            api = TastyTradeAPI(self.credential)
            
            # Mock initial 401 response (expired token)
            mock_expired_response = Mock()
            mock_expired_response.status_code = 401
            mock_expired_response.text = 'Token expired'
            
            # Mock successful response after refresh
            mock_success_response = Mock()
            mock_success_response.status_code = 200
            mock_success_response.text = '{"data": {"user": "test"}}'
            
            mock_get.side_effect = [mock_expired_response, mock_success_response]
            
            # Mock the token refresh
            with patch.object(api, '_refresh_access_token', return_value=True):
                result = api.test_session()
                self.assertTrue(result)
            
            # Verify two calls were made (initial + retry)
            self.assertEqual(mock_get.call_count, 2)


class OAuthViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.credential = TastyTradeCredential.objects.create(
            user=self.user,
            environment='sandbox',
            username='test_user',
            password='test_pass'
        )

    def test_oauth_authorize_view_requires_login(self):
        """Test OAuth authorize view requires authentication"""
        url = reverse('tastytrade_oauth_authorize')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_oauth_authorize_view_requires_credential(self):
        """Test OAuth authorize view requires existing credential"""
        self.client.login(username='testuser', password='testpass123')
        self.credential.delete()  # Remove credential
        
        url = reverse('tastytrade_oauth_authorize')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to connect

    @patch('apps.tastytrade.views.TastyTradeAPI')
    def test_oauth_authorize_view_success(self, mock_api_class):
        """Test successful OAuth authorization initiation"""
        self.client.login(username='testuser', password='testpass123')
        
        # Mock API instance
        mock_api = Mock()
        mock_api.get_oauth_authorization_url.return_value = 'https://tastytrade.com/oauth/auth?client_id=test'
        mock_api_class.return_value = mock_api
        
        url = reverse('tastytrade_oauth_authorize')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('tastytrade.com', response.url)

    def test_oauth_callback_view_with_error(self):
        """Test OAuth callback view handles authorization errors"""
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('tastytrade_oauth_callback')
        response = self.client.get(url, {'error': 'access_denied'})
        
        self.assertEqual(response.status_code, 302)  # Redirect
        
    def test_oauth_callback_view_missing_code(self):
        """Test OAuth callback view handles missing authorization code"""
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('tastytrade_oauth_callback')
        response = self.client.get(url)  # No code parameter
        
        self.assertEqual(response.status_code, 302)  # Redirect

    @patch('apps.tastytrade.views.TastyTradeAPI')
    def test_oauth_callback_view_success(self, mock_api_class):
        """Test successful OAuth callback with authorization code"""
        self.client.login(username='testuser', password='testpass123')
        
        # Mock API instance
        mock_api = Mock()
        mock_api.exchange_code_for_tokens.return_value = {
            'access_token': 'test_token',
            'refresh_token': 'test_refresh'
        }
        mock_api_class.return_value = mock_api
        
        url = reverse('tastytrade_oauth_callback')
        response = self.client.get(url, {'code': 'test_auth_code'})
        
        self.assertEqual(response.status_code, 302)  # Redirect
        mock_api.exchange_code_for_tokens.assert_called_once_with('test_auth_code')

    def test_oauth_status_view_json_response(self):
        """Test OAuth status view returns JSON status"""
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('tastytrade_oauth_status')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = response.json()
        self.assertIn('oauth_configured', data)
        self.assertIn('has_access_token', data)
        self.assertIn('has_refresh_token', data)
        self.assertIn('auth_method', data)

    def test_oauth_revoke_view(self):
        """Test OAuth token revocation"""
        self.client.login(username='testuser', password='testpass123')
        
        # Set up tokens
        self.credential.access_token = 'test_access_token'
        self.credential.refresh_token = 'test_refresh_token'
        self.credential.save()
        
        url = reverse('tastytrade_oauth_revoke')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)  # Redirect
        
        # Verify tokens were cleared
        self.credential.refresh_from_db()
        self.assertIsNone(self.credential.access_token)
        self.assertIsNone(self.credential.refresh_token)


class OAuthIntegrationTestCase(TestCase):
    """Integration tests for OAuth functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.credential = TastyTradeCredential.objects.create(
            user=self.user,
            environment='sandbox',
            username='test_user',
            password='test_pass'
        )

    @patch('apps.tastytrade.tastytrade_api.requests.Session')
    @patch('apps.tastytrade.tastytrade_api.settings')
    def test_oauth_end_to_end_flow(self, mock_settings, mock_session_class):
        """Test complete OAuth flow from authorization to API calls"""
        # Configure OAuth settings
        mock_settings.TASTYTRADE_OAUTH_CLIENT_ID = 'test_client_id'
        mock_settings.TASTYTRADE_OAUTH_CLIENT_SECRET = 'test_client_secret'
        mock_settings.TASTYTRADE_OAUTH_REDIRECT_URI = 'http://localhost:8000/callback'
        
        # Mock session responses
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Mock token exchange response
        token_response = Mock()
        token_response.status_code = 200
        token_response.json.return_value = {
            'access_token': 'oauth_access_token',
            'refresh_token': 'oauth_refresh_token',
            'expires_in': 900
        }
        
        # Mock API call response
        api_response = Mock()
        api_response.status_code = 200
        api_response.json.return_value = {'data': {'username': 'test_user'}}
        
        mock_session.post.return_value = token_response
        mock_session.get.return_value = api_response
        mock_session.headers = {}
        
        # Initialize API client
        api = TastyTradeAPI(self.credential)
        
        # Step 1: Exchange authorization code for tokens
        token_data = api.exchange_code_for_tokens('test_auth_code')
        
        # Verify token exchange
        self.assertEqual(token_data['access_token'], 'oauth_access_token')
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.access_token, 'oauth_access_token')
        
        # Step 2: Make authenticated API call
        success = api.test_session()
        self.assertTrue(success)
        
        # Verify Bearer token was used
        expected_header = {'Authorization': 'Bearer oauth_access_token', 'User-Agent': api.USER_AGENT}
        for key, value in expected_header.items():
            self.assertEqual(mock_session.headers[key], value)

    @patch('apps.tastytrade.tastytrade_api.settings')
    def test_oauth_graceful_fallback_to_session_auth(self, mock_settings):
        """Test graceful fallback to session auth when OAuth fails"""
        # Configure OAuth but don't set tokens
        mock_settings.TASTYTRADE_OAUTH_CLIENT_ID = 'test_client_id'
        mock_settings.TASTYTRADE_OAUTH_CLIENT_SECRET = 'test_client_secret'
        
        # No OAuth tokens set on credential
        api = TastyTradeAPI(self.credential)
        
        # Should fall back to session auth
        self.assertEqual(api.auth_method, 'session')
        
        # Should be able to authenticate via session
        with patch.object(api, 'login') as mock_login:
            api.authenticate()
            mock_login.assert_called_once()