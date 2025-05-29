"""
Test fixtures and data factories for TastyTrade tests
Provides consistent test data for financial data testing
"""

from decimal import Decimal
from datetime import datetime, date, timezone
from django.contrib.auth import get_user_model
from apps.tastytrade.models import TastyTradeCredential, Position, Transaction

User = get_user_model()


class TastyTradeTestDataFactory:
    """Factory for creating test data objects"""
    
    @staticmethod
    def create_test_user(username='testuser', email='test@example.com', password='testpass123'):
        """Create a test user"""
        return User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
    
    @staticmethod
    def create_test_credential(user, environment='prod', username='testuser', password='testpass'):
        """Create a test TastyTrade credential"""
        return TastyTradeCredential.objects.create(
            user=user,
            environment=environment,
            username=username,
            password=password
        )
    
    @staticmethod
    def create_test_stock_position(user, credential, symbol='AAPL', quantity='100.0000'):
        """Create a test stock position"""
        return Position.objects.create(
            user=user,
            credential=credential,
            tastytrade_account_number='123456789',
            asset_type='stock',
            symbol=symbol,
            description=f'{symbol} Stock',
            quantity=Decimal(quantity),
            average_price=Decimal('150.2500'),
            market_value=Decimal('15025.00'),
            unrealized_pnl=Decimal('500.00'),
            realized_pnl=Decimal('200.00')
        )
    
    @staticmethod
    def create_test_option_position(user, credential, symbol='AAPL', option_type='call'):
        """Create a test option position"""
        return Position.objects.create(
            user=user,
            credential=credential,
            tastytrade_account_number='123456789',
            asset_type='option',
            symbol=symbol,
            description=f'{symbol} Dec 20 2024 150 {option_type.title()}',
            quantity=Decimal('10.0000'),
            average_price=Decimal('5.2500'),
            market_value=Decimal('5250.00'),
            delta=Decimal('0.6500'),
            theta=Decimal('-0.0250'),
            beta=Decimal('1.2000'),
            expiry=date(2024, 12, 20),
            strike=Decimal('150.0000'),
            option_type=option_type
        )
    
    @staticmethod
    def create_test_trade_transaction(user, credential, transaction_id='TXN123', symbol='AAPL'):
        """Create a test trade transaction"""
        return Transaction.objects.create(
            user=user,
            credential=credential,
            tastytrade_account_number='123456789',
            transaction_id=transaction_id,
            transaction_type='trade',
            symbol=symbol,
            description=f'Buy 100 {symbol}',
            quantity=Decimal('100.0000'),
            price=Decimal('150.2500'),
            amount=Decimal('15025.00'),
            trade_date=datetime(2024, 5, 29, 14, 30, 0, tzinfo=timezone.utc),
            asset_type='stock'
        )
    
    @staticmethod
    def create_test_dividend_transaction(user, credential, transaction_id='DIV123', symbol='AAPL'):
        """Create a test dividend transaction"""
        return Transaction.objects.create(
            user=user,
            credential=credential,
            tastytrade_account_number='123456789',
            transaction_id=transaction_id,
            transaction_type='dividend',
            symbol=symbol,
            description=f'{symbol} Dividend',
            amount=Decimal('24.00'),
            trade_date=datetime(2024, 5, 29, 9, 0, 0, tzinfo=timezone.utc)
        )


class MockTastyTradeAPIResponses:
    """Mock API responses for testing"""
    
    @staticmethod
    def successful_login_response():
        """Mock successful login response"""
        return {
            "data": {
                "session-token": "test-session-token-12345",
                "user": {
                    "username": "testuser",
                    "email": "test@example.com",
                    "external-id": "test-user-id"
                },
                "session-expiration": "2024-05-30T15:39:02.806Z"
            },
            "context": "/sessions"
        }
    
    @staticmethod
    def accounts_response():
        """Mock accounts API response"""
        return {
            "data": [
                {
                    "account-number": "123456789",
                    "account-type": "Individual",
                    "status": "Active"
                },
                {
                    "account-number": "987654321",
                    "account-type": "IRA",
                    "status": "Active"
                }
            ]
        }
    
    @staticmethod
    def positions_response():
        """Mock positions API response"""
        return {
            "data": [
                {
                    "instrument-type": "stock",
                    "symbol": "AAPL",
                    "description": "Apple Inc.",
                    "quantity": 100,
                    "average-price": 150.25,
                    "market-value": 15025.00,
                    "unrealized-pnl": 500.00,
                    "realized-pnl": 200.00,
                    "delta": 1.0,
                    "theta": 0.0,
                    "beta": 1.2
                },
                {
                    "instrument-type": "option",
                    "symbol": "SPY",
                    "description": "SPY Dec 20 2024 450 Call",
                    "quantity": 5,
                    "average-price": 8.50,
                    "market-value": 4250.00,
                    "unrealized-pnl": -125.00,
                    "delta": 0.65,
                    "theta": -0.025,
                    "beta": 0.95,
                    "expiration-date": "2024-12-20",
                    "strike-price": 450.00,
                    "put-call": "call"
                },
                {
                    "instrument-type": "option",
                    "symbol": "QQQ",
                    "description": "QQQ Jan 17 2025 380 Put",
                    "quantity": -2,
                    "average-price": 12.75,
                    "market-value": -2550.00,
                    "unrealized-pnl": 200.00,
                    "delta": -0.35,
                    "theta": -0.015,
                    "beta": 1.1,
                    "expiration-date": "2025-01-17",
                    "strike-price": 380.00,
                    "put-call": "put"
                }
            ]
        }
    
    @staticmethod
    def transactions_response():
        """Mock transactions API response"""
        return {
            "data": [
                {
                    "transaction-id": "TXN123456",
                    "type": "trade",
                    "symbol": "AAPL",
                    "description": "Buy 100 AAPL",
                    "quantity": 100,
                    "price": 150.25,
                    "amount": 15025.00,
                    "transaction-date": "2024-05-29T14:30:00Z",
                    "instrument-type": "stock"
                },
                {
                    "transaction-id": "TXN789012",
                    "type": "trade",
                    "symbol": "SPY",
                    "description": "Buy to Open 5 SPY Dec 20 2024 450 Call",
                    "quantity": 5,
                    "price": 8.50,
                    "amount": 4250.00,
                    "transaction-date": "2024-05-28T11:15:00Z",
                    "instrument-type": "option",
                    "expiration-date": "2024-12-20",
                    "strike-price": 450.00,
                    "put-call": "call"
                },
                {
                    "transaction-id": "DIV345678",
                    "type": "dividend",
                    "symbol": "AAPL",
                    "description": "AAPL Dividend Payment",
                    "amount": 24.00,
                    "transaction-date": "2024-05-15T09:00:00Z",
                    "instrument-type": "stock"
                },
                {
                    "transaction-id": "FEE901234",
                    "type": "fee",
                    "description": "Regulatory Fee",
                    "amount": -1.50,
                    "transaction-date": "2024-05-29T14:30:00Z"
                }
            ]
        }
    
    @staticmethod
    def user_info_response():
        """Mock user info API response"""
        return {
            "data": {
                "username": "testuser",
                "email": "test@example.com",
                "external-id": "test-user-id",
                "is-confirmed": True
            }
        }
    
    @staticmethod
    def error_response_401():
        """Mock 401 Unauthorized error response"""
        return {
            "error": {
                "code": "invalid_credentials",
                "message": "Invalid login, please check your username and password."
            }
        }
    
    @staticmethod
    def error_response_403():
        """Mock 403 Not Permitted error response"""
        return {
            "error": {
                "code": "not_permitted",
                "message": "User not permitted access"
            }
        }
    
    @staticmethod
    def empty_data_response():
        """Mock empty data response"""
        return {
            "data": []
        }


class FinancialTestDataValidation:
    """Utilities for validating financial data in tests"""
    
    @staticmethod
    def validate_decimal_precision(value, max_digits, decimal_places):
        """Validate decimal field precision"""
        if value is None:
            return True
        
        # Convert to string to check precision
        str_value = str(value)
        if '.' in str_value:
            integer_part, decimal_part = str_value.split('.')
            total_digits = len(integer_part) + len(decimal_part)
            return (total_digits <= max_digits and 
                   len(decimal_part) <= decimal_places)
        else:
            return len(str_value) <= max_digits
    
    @staticmethod
    def validate_position_data(position_dict):
        """Validate position data structure and types"""
        required_fields = ['asset_type', 'symbol', 'quantity']
        
        for field in required_fields:
            if field not in position_dict:
                return False, f"Missing required field: {field}"
        
        # Validate data types
        if not isinstance(position_dict['quantity'], (int, float, Decimal)):
            return False, "Quantity must be numeric"
        
        if position_dict['asset_type'] not in ['stock', 'option', 'future', 'crypto', 'other']:
            return False, f"Invalid asset_type: {position_dict['asset_type']}"
        
        return True, "Valid"
    
    @staticmethod
    def validate_transaction_data(transaction_dict):
        """Validate transaction data structure and types"""
        required_fields = ['transaction_id', 'transaction_type', 'amount', 'trade_date']
        
        for field in required_fields:
            if field not in transaction_dict:
                return False, f"Missing required field: {field}"
        
        # Validate data types
        if not isinstance(transaction_dict['amount'], (int, float, Decimal)):
            return False, "Amount must be numeric"
        
        if not isinstance(transaction_dict['trade_date'], datetime):
            return False, "Trade date must be datetime"
        
        return True, "Valid"
    
    @staticmethod
    def calculate_position_pnl(positions):
        """Calculate total P&L from positions for validation"""
        total_unrealized = Decimal('0.00')
        total_realized = Decimal('0.00')
        
        for position in positions:
            if position.unrealized_pnl:
                total_unrealized += position.unrealized_pnl
            if position.realized_pnl:
                total_realized += position.realized_pnl
        
        return {
            'total_unrealized': total_unrealized,
            'total_realized': total_realized,
            'total_pnl': total_unrealized + total_realized
        }


# Test data constants
TEST_ACCOUNT_NUMBERS = ['123456789', '987654321', '555666777']

TEST_SYMBOLS = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'SPY', 'QQQ', 'IWM']

TEST_OPTION_STRIKES = [Decimal('100.00'), Decimal('150.00'), Decimal('200.00'), 
                      Decimal('250.00'), Decimal('300.00')]

TEST_OPTION_EXPIRIES = [
    date(2024, 6, 21),
    date(2024, 7, 19),
    date(2024, 8, 16),
    date(2024, 9, 20),
    date(2024, 12, 20),
    date(2025, 1, 17)
]