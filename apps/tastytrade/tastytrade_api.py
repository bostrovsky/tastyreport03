import requests
from django.utils import timezone
from datetime import datetime, timedelta
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class TastyTradeAPI:
    PROD_BASE_URL = 'https://api.tastytrade.com'
    SANDBOX_BASE_URL = 'https://api.cert.tastyworks.com'
    USER_AGENT = 'tastytrade-tracker/1.0'
    HEADERS = {
        'User-Agent': USER_AGENT,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    # OAuth 2.0 Configuration - loaded dynamically in __init__

    def __init__(self, credential):
        self.credential = credential
        
        # Load OAuth configuration dynamically
        self.OAUTH_CLIENT_ID = getattr(settings, 'TASTYTRADE_OAUTH_CLIENT_ID', None)
        self.OAUTH_CLIENT_SECRET = getattr(settings, 'TASTYTRADE_OAUTH_CLIENT_SECRET', None)
        self.OAUTH_REDIRECT_URI = getattr(settings, 'TASTYTRADE_OAUTH_REDIRECT_URI', None)
        
        # Set base URL based on environment
        if credential.environment == 'sandbox':
            self.base_url = self.SANDBOX_BASE_URL
        else:
            self.base_url = self.PROD_BASE_URL
        print(f"DEBUG: Using API base URL: {self.base_url} (environment: {credential.environment})")
        self.session = requests.Session()
        self.token = None
        self.access_token = None
        self.token_expires_at = None
        self.session.headers.update(self.HEADERS)
        
        # Try OAuth first if available, fallback to session auth
        self.auth_method = 'oauth' if self._can_use_oauth() else 'session'
    
    def _can_use_oauth(self):
        """Check if OAuth 2.0 can be used"""
        return (
            self.OAUTH_CLIENT_ID and 
            self.OAUTH_CLIENT_SECRET and 
            (self.credential.access_token or self.credential.refresh_token)
        )
    
    def authenticate(self):
        """Main authentication method that chooses between OAuth and session auth"""
        if self.auth_method == 'oauth':
            return self._oauth_authenticate()
        else:
            return self.login()
    
    def _oauth_authenticate(self):
        """Authenticate using OAuth 2.0 access tokens"""
        if self.credential.access_token and self._is_token_valid():
            self._set_oauth_header()
            return True
        elif self.credential.refresh_token:
            return self._refresh_access_token()
        else:
            raise Exception("No valid OAuth tokens available. Please re-authorize.")
    
    def _is_token_valid(self):
        """Check if current access token is still valid"""
        if not self.token_expires_at:
            # Assume token needs refresh if we don't have expiry info
            return False
        return timezone.now() < self.token_expires_at
    
    def _set_oauth_header(self):
        """Set OAuth Bearer token in session headers"""
        if "Authorization" in self.session.headers:
            del self.session.headers["Authorization"]
        self.session.headers.update({
            "Authorization": f"Bearer {self.credential.access_token}",
            "User-Agent": self.USER_AGENT,
        })
        self.access_token = self.credential.access_token
    
    def _refresh_access_token(self):
        """Refresh the OAuth access token using refresh token"""
        url = f"{self.base_url}/oauth/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.credential.refresh_token,
            "client_id": self.OAUTH_CLIENT_ID,
            "client_secret": self.OAUTH_CLIENT_SECRET,
        }
        
        logger.info(f"Refreshing OAuth token from {url}")
        resp = self.session.post(url, json=data)
        
        if resp.status_code != 200:
            logger.error(f"Token refresh failed: {resp.status_code} {resp.text}")
            raise Exception(f"OAuth token refresh failed: {resp.text}")
        
        token_data = resp.json()
        
        # Update credential with new tokens
        self.credential.access_token = token_data.get("access_token")
        if "refresh_token" in token_data:
            self.credential.refresh_token = token_data.get("refresh_token")
        
        # Calculate token expiry (15 minutes as per docs)
        expires_in = token_data.get("expires_in", 900)  # default 15 minutes
        self.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
        
        self.credential.save()
        self._set_oauth_header()
        
        logger.info("OAuth token refreshed successfully")
        return True
    
    def get_oauth_authorization_url(self):
        """Generate OAuth authorization URL for initial user consent"""
        if not self.OAUTH_CLIENT_ID or not self.OAUTH_REDIRECT_URI:
            raise Exception("OAuth client ID and redirect URI must be configured")
        
        params = {
            "response_type": "code",
            "client_id": self.OAUTH_CLIENT_ID,
            "redirect_uri": self.OAUTH_REDIRECT_URI,
            "scope": "read",  # Adjust scope as needed
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.base_url}/oauth/authorize?{query_string}"
    
    def exchange_code_for_tokens(self, authorization_code):
        """Exchange OAuth authorization code for access and refresh tokens"""
        url = f"{self.base_url}/oauth/token"
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "client_id": self.OAUTH_CLIENT_ID,
            "client_secret": self.OAUTH_CLIENT_SECRET,
            "redirect_uri": self.OAUTH_REDIRECT_URI,
        }
        
        resp = self.session.post(url, json=data)
        
        if resp.status_code != 200:
            raise Exception(f"OAuth code exchange failed: {resp.text}")
        
        token_data = resp.json()
        
        # Save tokens to credential
        self.credential.access_token = token_data.get("access_token")
        self.credential.refresh_token = token_data.get("refresh_token")
        
        # Calculate token expiry
        expires_in = token_data.get("expires_in", 900)
        self.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
        
        self.credential.save()
        self._set_oauth_header()
        
        return token_data

    def login(self):
        username = self.credential.username.strip()
        password = self.credential.password.strip()
        print(f"DEBUG: Logging in with username='{username}' password='***' environment='{self.credential.environment}'")
        print(f"DEBUG: Using URL: {self.base_url}/sessions")
        url = f"{self.base_url}/sessions"
        resp = self.session.post(url, json={
            "login": username,
            "password": password,
        })
        print(f"DEBUG: Response {resp.status_code} {resp.text}")
        if resp.status_code != 201:
            raise Exception(f"TastyTrade login failed: {resp.text}")
        data = resp.json()
        self.token = data["data"]["session-token"]
        
        # Extract user info from session response
        user_data = data.get("data", {}).get("user", {})
        self.user_external_id = user_data.get("external-id")
        self.username = user_data.get("username")
        
        print(f"DEBUG: Got token: {self.token[:20]}...")
        print(f"DEBUG: User external ID: {self.user_external_id}")
        print(f"DEBUG: Username: {self.username}")
        
        # Remove any old Authorization header before setting a new one
        if "Authorization" in self.session.headers:
            del self.session.headers["Authorization"]
        # Per docs, do NOT prefix with 'Bearer ', just use the token
        self.session.headers.update({
            "Authorization": self.token,
            "User-Agent": self.USER_AGENT,  # Always ensure User-Agent is present
        })

    def test_session(self):
        """Test if the current authentication (OAuth or session) is working"""
        # Try to get accounts as a way to test the session
        url = f"{self.base_url}/customers/me/accounts"
        print(f"DEBUG: Testing {self.auth_method} auth with accounts endpoint {url}")
        resp = self.session.get(url)
        print(f"DEBUG: Session test response {resp.status_code} {resp.text[:200]}...")
        
        # If OAuth token expired, try to refresh
        if resp.status_code == 401 and self.auth_method == 'oauth':
            print("DEBUG: OAuth token may have expired, attempting refresh")
            try:
                self._refresh_access_token()
                resp = self.session.get(url)
                print(f"DEBUG: Session test after token refresh {resp.status_code} {resp.text[:200]}...")
            except Exception as e:
                print(f"DEBUG: Token refresh failed: {e}")
        
        return resp.status_code == 200

    def get_customer_id(self):
        """Get the customer ID - use 'me' as it works with TastyTrade API"""
        print(f"DEBUG: Using 'me' as customer ID (TastyTrade convention)")
        return "me"

    def fetch_accounts(self):
        # First try to get the customer ID and use the proper endpoint
        try:
            customer_id = self.get_customer_id()
            
            # Then fetch accounts using the customer ID
            url = f"{self.base_url}/customers/{customer_id}/accounts"
            print(f"DEBUG: Fetching accounts from {url}")
            print(f"DEBUG: Headers being sent: {dict(self.session.headers)}")
            resp = self.session.get(url)
            print(f"DEBUG: Accounts response {resp.status_code} {resp.text}")
            if resp.status_code == 200:
                data = resp.json()
                # Handle the new response format: data.items[].account
                items = data.get("data", {}).get("items", [])
                accounts = [item["account"]["account-number"] for item in items if "account" in item]
                print(f"DEBUG: Found accounts: {accounts}")
                return accounts
        except Exception as e:
            print(f"DEBUG: Customer ID approach failed: {e}")
        
        # Fallback: try the original /accounts endpoint directly
        print(f"DEBUG: Trying fallback /accounts endpoint")
        url = f"{self.base_url}/accounts"
        print(f"DEBUG: Fetching accounts from {url}")
        print(f"DEBUG: Headers being sent: {dict(self.session.headers)}")
        resp = self.session.get(url)
        print(f"DEBUG: Accounts response {resp.status_code} {resp.text}")
        if resp.status_code == 200:
            data = resp.json()
            # Try both response formats
            if "items" in data.get("data", {}):
                # New format: data.items[].account
                items = data.get("data", {}).get("items", [])
                accounts = [item["account"]["account-number"] for item in items if "account" in item]
            else:
                # Old format: data[]
                accounts = [acct["account-number"] for acct in data.get("data", [])]
            print(f"DEBUG: Found accounts: {accounts}")
            return accounts
        
        # If both approaches fail, raise the final error
        raise Exception(f"Failed to fetch accounts: Status {resp.status_code}, Response: {resp.text}")

    def fetch_positions(self, account_number):
        url = f"{self.base_url}/accounts/{account_number}/positions"
        print(f"DEBUG: Fetching positions from {url}")
        print(f"DEBUG: Headers being sent: {dict(self.session.headers)}")
        resp = self.session.get(url)
        print(f"DEBUG: Positions response {resp.status_code} {resp.text}")
        if resp.status_code != 200:
            raise Exception(f"Failed to fetch positions: Status {resp.status_code}, Response: {resp.text}")
        data = resp.json()
        positions = []
        # Handle the new response format: data.items[]
        items = data.get("data", {}).get("items", [])
        print(f"DEBUG: Retrieved {len(items)} positions")
        for pos in items:
            print(f"DEBUG: Raw position data: {pos}")
            
            # Parse expiry date if it's a string
            expiry = pos.get("expiration-date")
            if isinstance(expiry, str):
                try:
                    from datetime import datetime
                    expiry = datetime.fromisoformat(expiry).date()
                except (ValueError, AttributeError):
                    expiry = None
            
            # Calculate market value and unrealized P&L from available fields
            quantity = pos.get("quantity", 0)
            close_price = float(pos.get("close-price", 0)) if pos.get("close-price") else 0
            average_open_price = float(pos.get("average-open-price", 0)) if pos.get("average-open-price") else 0
            multiplier = pos.get("multiplier", 1)
            
            market_value = quantity * close_price * multiplier if close_price else None
            unrealized_pnl = (close_price - average_open_price) * quantity * multiplier if close_price and average_open_price else None
            
            # Calculate Greeks using Black-Scholes model
            delta = None
            theta = None
            instrument_type = pos.get("instrument-type")
            print(f"DEBUG: Position {pos.get('symbol')} - instrument-type: {instrument_type}, put-call: {pos.get('put-call')}, strike: {pos.get('strike-price')}")
            
            if instrument_type and "option" in instrument_type.lower():
                from .options_pricing import calculate_option_greeks
                print(f"DEBUG: Calculating Greeks for option {pos.get('symbol')}")
                delta, theta = calculate_option_greeks(
                    symbol=pos.get("symbol", ""),
                    current_price=close_price,
                    strike_price=pos.get("strike-price"),
                    expiry_date=expiry,
                    option_type=pos.get("put-call")
                )
                print(f"DEBUG: Calculated Greeks - Delta: {delta}, Theta: {theta}")
            elif instrument_type and instrument_type.lower() == "equity":
                # Stocks have delta of 0, theta of 0
                print(f"DEBUG: Setting equity Greeks for {pos.get('symbol')}")
                delta = 0.0
                theta = 0.0
            else:
                print(f"DEBUG: No Greeks calculated for {pos.get('symbol')} - instrument type: {instrument_type}")
            
            # Scale Greeks by position size for portfolio calculations
            if delta is not None:
                delta = delta * quantity * multiplier
            if theta is not None:
                theta = theta * quantity * multiplier
            
            print(f"DEBUG: Final Greeks for {pos.get('symbol')} - Delta: {delta}, Theta: {theta} (scaled by quantity {quantity})")
            
            positions.append({
                "asset_type": pos.get("instrument-type", "other"),
                "symbol": pos.get("symbol"),
                "description": pos.get("underlying-symbol", ""),  # Use underlying symbol as description
                "quantity": quantity,
                "average_price": average_open_price if average_open_price else None,
                "current_price": close_price if close_price else None,
                "market_value": market_value,
                "unrealized_pnl": unrealized_pnl,
                "realized_pnl": float(pos.get("realized-today", 0)) if pos.get("realized-today") else 0,
                "delta": delta,
                "theta": theta,
                "beta": None,   # Not available in basic positions endpoint
                "expiry": expiry,
                "strike": pos.get("strike-price"),
                "option_type": pos.get("put-call"),
                "multiplier": multiplier,  # Include multiplier for daily P&L calculation
            })
        return positions


    def fetch_transactions(self, account_number, start_date=None):
        url = f"{self.base_url}/accounts/{account_number}/transactions"
        
        # Add date filtering if start_date is provided
        params = {}
        if start_date:
            # Format date as YYYY-MM-DD for TastyTrade API
            if hasattr(start_date, 'strftime'):
                start_date_str = start_date.strftime('%Y-%m-%d')
            else:
                start_date_str = start_date
            params['start-date'] = start_date_str
            print(f"DEBUG: Fetching transactions from {start_date_str} onwards")
        
        print(f"DEBUG: Fetching transactions from {url}")
        print(f"DEBUG: Query params: {params}")
        print(f"DEBUG: Headers being sent: {dict(self.session.headers)}")
        
        resp = self.session.get(url, params=params)
        print(f"DEBUG: Transactions response {resp.status_code}")
        if resp.status_code != 200:
            raise Exception(f"Failed to fetch transactions: Status {resp.status_code}, Response: {resp.text}")
        data = resp.json()
        transactions = []
        # Handle the new response format: data.items[]
        items = data.get("data", {}).get("items", [])
        print(f"DEBUG: Retrieved {len(items)} transactions")
        for txn in items:
            # Debug: Print first transaction to see available fields
            if len(transactions) == 0:
                print(f"DEBUG: First transaction fields: {list(txn.keys())}")
                print(f"DEBUG: Transaction date value: {txn.get('transaction-date')}")
                # Check for other potential time fields
                potential_time_fields = ['time', 'executed-at', 'trade-time', 'timestamp', 'created-at', 'executed-time']
                for field in potential_time_fields:
                    if field in txn:
                        print(f"DEBUG: Found time field '{field}': {txn.get(field)}")
            
            # Parse transaction date if it's a string
            trade_date = txn.get("transaction-date")
            if isinstance(trade_date, str):
                try:
                    from datetime import datetime
                    from django.utils import timezone
                    # Parse the date and make it timezone aware
                    if 'T' in trade_date:
                        # Full datetime
                        trade_date = datetime.fromisoformat(trade_date.replace('Z', '+00:00'))
                    else:
                        # Date only - parse and make timezone aware
                        trade_date = datetime.fromisoformat(trade_date)
                        trade_date = timezone.make_aware(trade_date, timezone.get_current_timezone())
                except (ValueError, AttributeError):
                    trade_date = None
            
            # Parse expiry date if it's a string
            expiry = txn.get("expiration-date")
            if isinstance(expiry, str):
                try:
                    from datetime import datetime
                    expiry = datetime.fromisoformat(expiry).date()
                except (ValueError, AttributeError):
                    expiry = None
            
            transactions.append({
                "transaction_id": txn.get("id"),  # Fixed: was "transaction-id"
                "transaction_type": txn.get("transaction-type", "other"),  # Fixed: was "type"
                "symbol": txn.get("symbol", ""),
                "description": txn.get("description", ""),
                "quantity": txn.get("quantity"),
                "price": txn.get("price"),
                "amount": txn.get("net-value"),  # Fixed: was "amount" 
                "trade_date": trade_date,
                "asset_type": txn.get("instrument-type", ""),
                "expiry": expiry,
                "strike": txn.get("strike-price"),
                "option_type": txn.get("put-call"),
            })
        return transactions 