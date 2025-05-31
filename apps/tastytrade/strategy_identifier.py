"""
Strategy Identification Service for TastyTrade Tracker

This service automatically identifies trading strategies from individual transactions
and groups them into net positions. It implements the strategy identification logic
required by the PRD.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Tuple, Optional
from django.db import transaction
from django.utils import timezone

from .models import Transaction, TradingStrategy, StrategyLeg, StrategyEditHistory


class StrategyIdentifier:
    """
    Identifies trading strategies from individual transactions using pattern matching
    and options strategy recognition algorithms.
    """
    
    def __init__(self):
        self.confidence_threshold = 75.0  # Minimum confidence to auto-assign strategy
        
    def identify_strategies_for_user(self, user, account_number=None):
        """
        Main entry point: analyze all transactions for a user and identify strategies
        """
        transactions = Transaction.objects.filter(
            user=user,
            strategy__isnull=True  # Only unassigned transactions
        )
        
        if account_number:
            transactions = transactions.filter(tastytrade_account_number=account_number)
        
        # Group transactions by underlying symbol and time proximity
        grouped_transactions = self._group_transactions_by_context(transactions)
        
        strategies_created = []
        
        for group_key, group_transactions in grouped_transactions.items():
            strategies = self._identify_strategies_in_group(group_transactions)
            strategies_created.extend(strategies)
        
        return strategies_created
    
    def _group_transactions_by_context(self, transactions):
        """
        Group transactions by underlying symbol and time proximity to identify
        potential multi-leg strategies
        """
        groups = defaultdict(list)
        
        for txn in transactions.order_by('trade_date'):
            # Extract underlying symbol (remove option suffixes)
            underlying = self._extract_underlying_symbol(txn.symbol)
            
            # Group by underlying and day (strategies usually executed same day)
            group_key = (
                underlying,
                txn.trade_date.date(),
                txn.tastytrade_account_number
            )
            
            groups[group_key].append(txn)
        
        return groups
    
    def _extract_underlying_symbol(self, symbol):
        """Extract underlying symbol from options notation"""
        # Handle various symbol formats (AAPL, AAPL240315C00150000, etc.)
        if len(symbol) <= 5:
            return symbol  # Likely stock symbol
        
        # Options typically have underlying + date + type + strike
        # Extract first part before numbers
        underlying = ''
        for char in symbol:
            if char.isalpha():
                underlying += char
            else:
                break
        
        return underlying if underlying else symbol
    
    def _identify_strategies_in_group(self, transactions):
        """
        Identify specific trading strategies within a group of related transactions
        """
        strategies = []
        
        # Separate by asset type
        stock_txns = [t for t in transactions if t.asset_type == 'stock']
        option_txns = [t for t in transactions if t.asset_type == 'option']
        
        if not transactions:
            return strategies
        
        underlying = self._extract_underlying_symbol(transactions[0].symbol)
        
        # Single transaction strategies
        if len(transactions) == 1:
            strategy = self._identify_single_leg_strategy(transactions[0])
            if strategy:
                strategies.append(strategy)
        
        # Multi-leg option strategies
        elif option_txns:
            strategy = self._identify_option_strategy(option_txns, stock_txns, underlying)
            if strategy:
                strategies.append(strategy)
        
        # Stock-only strategies
        elif stock_txns:
            strategy = self._identify_stock_strategy(stock_txns, underlying)
            if strategy:
                strategies.append(strategy)
        
        return strategies
    
    def _identify_single_leg_strategy(self, transaction):
        """Identify single-leg strategies"""
        if transaction.asset_type == 'stock':
            strategy_type = 'long_stock' if transaction.quantity > 0 else 'short_stock'
        elif transaction.asset_type == 'option':
            if transaction.quantity > 0:
                strategy_type = 'long_call' if transaction.option_type == 'call' else 'long_put'
            else:
                strategy_type = 'short_call' if transaction.option_type == 'call' else 'short_put'
        else:
            return None
        
        return self._create_strategy(
            strategy_type=strategy_type,
            underlying=self._extract_underlying_symbol(transaction.symbol),
            transactions=[transaction],
            confidence=95.0,
            user=transaction.user,
            account_number=transaction.tastytrade_account_number
        )
    
    def _identify_option_strategy(self, option_txns, stock_txns, underlying):
        """Identify multi-leg option strategies"""
        
        # Group by expiry and strike for pattern matching
        legs = self._parse_option_legs(option_txns)
        
        # Try to match known multi-leg patterns
        strategy_type, confidence = self._match_option_strategy_pattern(legs, stock_txns)
        
        if strategy_type and confidence >= self.confidence_threshold:
            all_transactions = option_txns + stock_txns
            return self._create_strategy(
                strategy_type=strategy_type,
                underlying=underlying,
                transactions=all_transactions,
                confidence=confidence,
                user=option_txns[0].user,
                account_number=option_txns[0].tastytrade_account_number
            )
        
        return None
    
    def _parse_option_legs(self, option_txns):
        """Parse option transactions into standardized leg format"""
        legs = []
        
        for txn in option_txns:
            legs.append({
                'symbol': txn.symbol,
                'strike': float(txn.strike) if txn.strike else 0,
                'expiry': txn.expiry,
                'option_type': txn.option_type,
                'quantity': float(txn.quantity) if txn.quantity else 0,
                'price': float(txn.price) if txn.price else 0,
                'amount': float(txn.amount),
                'transaction': txn
            })
        
        return sorted(legs, key=lambda x: (x['expiry'], x['strike']))
    
    def _match_option_strategy_pattern(self, legs, stock_txns):
        """
        Match option leg patterns to known strategies
        Returns (strategy_type, confidence_score)
        """
        
        # Two-leg strategies
        if len(legs) == 2:
            return self._match_two_leg_strategy(legs)
        
        # Four-leg strategies (Iron Condor, Iron Butterfly)
        elif len(legs) == 4:
            return self._match_four_leg_strategy(legs)
        
        # Stock + Option combinations
        elif len(legs) == 1 and stock_txns:
            return self._match_stock_option_combo(legs[0], stock_txns)
        
        # Default: custom strategy
        return 'custom', 60.0
    
    def _match_two_leg_strategy(self, legs):
        """Match two-leg option strategies"""
        leg1, leg2 = legs[0], legs[1]
        
        # Same expiry required for spreads
        if leg1['expiry'] != leg2['expiry']:
            return 'custom', 50.0
        
        # Same option type = vertical spread
        if leg1['option_type'] == leg2['option_type']:
            if leg1['option_type'] == 'call':
                if leg1['quantity'] > 0 and leg2['quantity'] < 0:
                    return ('bull_call_spread' if leg1['strike'] < leg2['strike'] 
                           else 'bear_call_spread'), 90.0
            else:  # puts
                if leg1['quantity'] > 0 and leg2['quantity'] < 0:
                    return ('bear_put_spread' if leg1['strike'] > leg2['strike'] 
                           else 'bull_put_spread'), 90.0
        
        # Different option types = straddle/strangle
        else:
            if leg1['strike'] == leg2['strike']:
                return ('long_straddle' if leg1['quantity'] > 0 
                       else 'short_straddle'), 85.0
            else:
                return ('long_strangle' if leg1['quantity'] > 0 
                       else 'short_strangle'), 85.0
        
        return 'custom', 60.0
    
    def _match_four_leg_strategy(self, legs):
        """Match four-leg strategies like Iron Condor"""
        # Check for Iron Condor pattern (short strangle + long strangle protection)
        strikes = [leg['strike'] for leg in legs]
        quantities = [leg['quantity'] for leg in legs]
        
        # Iron Condor: sell middle strikes, buy outer strikes
        if (len(set(strikes)) == 4 and 
            quantities[0] > 0 and quantities[1] < 0 and 
            quantities[2] < 0 and quantities[3] > 0):
            return 'iron_condor', 85.0
        
        return 'custom', 50.0
    
    def _match_stock_option_combo(self, option_leg, stock_txns):
        """Match stock + option combinations"""
        stock_quantity = sum(float(txn.quantity) for txn in stock_txns if txn.quantity)
        option_quantity = option_leg['quantity']
        
        # Covered Call: Long stock + Short call
        if (stock_quantity > 0 and option_quantity < 0 and 
            option_leg['option_type'] == 'call'):
            return 'covered_call', 95.0
        
        # Protective Put: Long stock + Long put
        elif (stock_quantity > 0 and option_quantity > 0 and 
              option_leg['option_type'] == 'put'):
            return 'protective_put', 95.0
        
        # Cash Secured Put: Short put (assumes cash available)
        elif option_quantity < 0 and option_leg['option_type'] == 'put':
            return 'cash_secured_put', 80.0
        
        return 'custom', 60.0
    
    def _identify_stock_strategy(self, stock_txns, underlying):
        """Identify stock-only strategies"""
        total_quantity = sum(float(txn.quantity) for txn in stock_txns if txn.quantity)
        
        strategy_type = 'long_stock' if total_quantity > 0 else 'short_stock'
        
        return self._create_strategy(
            strategy_type=strategy_type,
            underlying=underlying,
            transactions=stock_txns,
            confidence=90.0,
            user=stock_txns[0].user,
            account_number=stock_txns[0].tastytrade_account_number
        )
    
    def _create_strategy(self, strategy_type, underlying, transactions, confidence, user, account_number):
        """Create a TradingStrategy instance and assign transactions"""
        
        # Calculate dates
        trade_dates = [txn.trade_date for txn in transactions]
        opened_date = min(trade_dates)
        
        # Find expiry date from options
        expiry_dates = [txn.expiry for txn in transactions if txn.expiry]
        expiry_date = min(expiry_dates) if expiry_dates else None
        
        with transaction.atomic():
            # Create strategy
            strategy = TradingStrategy.objects.create(
                user=user,
                credential=transactions[0].credential,
                account_number=account_number,
                strategy_type=strategy_type,
                underlying_symbol=underlying,
                status='open',
                is_system_inferred=True,
                confidence_score=Decimal(str(confidence)),
                opened_date=opened_date,
                expiry_date=expiry_date
            )
            
            # Assign transactions to strategy
            for txn in transactions:
                txn.strategy = strategy
                txn.save()
            
            # Create strategy legs
            self._create_strategy_legs(strategy, transactions)
            
            # Log creation
            StrategyEditHistory.objects.create(
                strategy=strategy,
                user=user,
                action='create',
                previous_state={},
                new_state={
                    'strategy_type': strategy_type,
                    'underlying': underlying,
                    'confidence': confidence,
                    'transaction_count': len(transactions)
                },
                reason='System auto-identification'
            )
        
        return strategy
    
    def _create_strategy_legs(self, strategy, transactions):
        """Create StrategyLeg instances for the strategy"""
        
        # Group transactions by identical instrument
        leg_groups = defaultdict(list)
        
        for txn in transactions:
            leg_key = (
                txn.symbol,
                txn.asset_type,
                txn.expiry,
                txn.strike,
                txn.option_type
            )
            leg_groups[leg_key].append(txn)
        
        # Create a leg for each unique instrument
        for leg_key, leg_txns in leg_groups.items():
            symbol, asset_type, expiry, strike, option_type = leg_key
            
            # Sum quantities for net position
            total_quantity = sum(float(txn.quantity) for txn in leg_txns if txn.quantity)
            
            # Calculate average price (weighted by quantity)
            total_value = sum(float(txn.price * txn.quantity) for txn in leg_txns 
                            if txn.price and txn.quantity)
            avg_price = total_value / total_quantity if total_quantity != 0 else 0
            
            StrategyLeg.objects.create(
                strategy=strategy,
                symbol=symbol,
                asset_type=asset_type,
                quantity=Decimal(str(total_quantity)),
                expiry=expiry,
                strike=strike,
                option_type=option_type,
                average_price=Decimal(str(avg_price)) if avg_price else None
            )


def run_strategy_identification(user, account_number=None):
    """
    Convenience function to run strategy identification
    """
    identifier = StrategyIdentifier()
    return identifier.identify_strategies_for_user(user, account_number)