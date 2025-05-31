"""
Simple Strategy Identification for TastyTrade Tracker

This service automatically identifies trading strategies from transactions that occur close in time
and adds strategy context to positions and transactions views.
"""

from collections import defaultdict
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from .models import Transaction


class SimpleStrategyIdentifier:
    """
    Simple strategy identification based on transaction timing and patterns
    """
    
    def __init__(self):
        self.time_window = timedelta(minutes=2)  # Group transactions within 2 minutes
        
    def identify_strategies_for_transactions(self, transactions):
        """
        Identify strategies from a queryset of transactions and return strategy info
        """
        # Group transactions by underlying and time
        strategy_groups = self._group_transactions_by_context(transactions)
        
        # Identify strategy for each group
        identified_strategies = []
        for group in strategy_groups:
            strategy_info = self._identify_strategy_from_group(group)
            identified_strategies.append(strategy_info)
            
        return identified_strategies
    
    def _group_transactions_by_context(self, transactions):
        """
        Group transactions by underlying symbol and time proximity
        """
        # Sort transactions by time
        sorted_transactions = list(transactions.order_by('trade_date'))
        
        groups = []
        current_group = []
        
        for txn in sorted_transactions:
            # Start new group if no current group or if this transaction is too far in time/symbol
            if not current_group:
                current_group = [txn]
            else:
                last_txn = current_group[-1]
                time_diff = abs((txn.trade_date - last_txn.trade_date).total_seconds())
                same_underlying = self._get_underlying_symbol(txn) == self._get_underlying_symbol(last_txn)
                
                if same_underlying and time_diff <= self.time_window.total_seconds():
                    current_group.append(txn)
                else:
                    # Finalize current group and start new one
                    if current_group:
                        groups.append(current_group)
                    current_group = [txn]
        
        # Add final group
        if current_group:
            groups.append(current_group)
            
        return groups
    
    def _get_underlying_symbol(self, transaction):
        """Extract underlying symbol from transaction"""
        symbol = transaction.symbol or ""
        # For options, extract the underlying (everything before the date/strike)
        # Example: "SPY240315C00520000" -> "SPY"
        if len(symbol) > 6 and symbol[3:9].isdigit():  # Options format
            return symbol[:3]
        return symbol
    
    def _identify_strategy_from_group(self, transactions):
        """
        Identify the strategy type from a group of related transactions
        """
        if len(transactions) == 1:
            return self._identify_single_leg_strategy(transactions[0])
        else:
            return self._identify_multi_leg_strategy(transactions)
    
    def _identify_single_leg_strategy(self, transaction):
        """Identify strategy for single transaction"""
        underlying = self._get_underlying_symbol(transaction)
        
        # Handle null quantities
        quantity = transaction.quantity or 0
        
        # Check if it's an option or stock
        if transaction.option_type:
            if transaction.option_type.lower() == 'call':
                strategy_type = "Long Call" if quantity > 0 else "Short Call"
            else:
                strategy_type = "Long Put" if quantity > 0 else "Short Put"
        else:
            strategy_type = "Long Stock" if quantity > 0 else "Short Stock"
        
        # Handle cases where we can't determine direction
        if quantity == 0:
            if transaction.option_type:
                strategy_type = f"{transaction.option_type.title()} Option"
            else:
                strategy_type = "Stock Transaction"
        
        return {
            'transactions': [transaction],
            'strategy_type': strategy_type,
            'underlying_symbol': underlying,
            'confidence': 85.0 if quantity != 0 else 50.0,
            'description': f"{strategy_type} on {underlying}",
            'legs_count': 1
        }
    
    def _identify_multi_leg_strategy(self, transactions):
        """Identify strategy for multiple related transactions"""
        underlying = self._get_underlying_symbol(transactions[0])
        
        # Analyze the legs
        call_legs = []
        put_legs = []
        stock_legs = []
        
        for txn in transactions:
            if txn.option_type and txn.option_type.strip():
                if txn.option_type.lower() == 'call':
                    call_legs.append(txn)
                else:
                    put_legs.append(txn)
            else:
                stock_legs.append(txn)
        
        # Identify common patterns
        strategy_type = "Custom Strategy"
        confidence = 60.0
        
        if len(transactions) == 2:
            if len(call_legs) == 2:
                strategy_type = "Call Spread"
                confidence = 85.0
            elif len(put_legs) == 2:
                strategy_type = "Put Spread"
                confidence = 85.0
            elif len(call_legs) == 1 and len(put_legs) == 1:
                # Check if same strike (straddle) or different strikes (strangle)
                call_strike = float(call_legs[0].strike) if call_legs[0].strike else 0
                put_strike = float(put_legs[0].strike) if put_legs[0].strike else 0
                if call_strike > 0 and put_strike > 0 and abs(call_strike - put_strike) < 0.01:
                    strategy_type = "Straddle"
                elif call_strike > 0 and put_strike > 0:
                    strategy_type = "Strangle"
                else:
                    strategy_type = "Call/Put Combination"
                confidence = 90.0
            elif len(stock_legs) == 1 and len(call_legs) == 1:
                strategy_type = "Covered Call"
                confidence = 95.0
            elif len(stock_legs) == 1 and len(put_legs) == 1:
                put_quantity = put_legs[0].quantity or 0
                strategy_type = "Cash-Secured Put" if put_quantity < 0 else "Protective Put"
                confidence = 90.0
                
        elif len(transactions) == 4:
            if len(call_legs) == 2 and len(put_legs) == 2:
                strategy_type = "Iron Condor"
                confidence = 85.0
        
        return {
            'transactions': transactions,
            'strategy_type': strategy_type,
            'underlying_symbol': underlying,
            'confidence': confidence,
            'description': f"{strategy_type} on {underlying}",
            'legs_count': len(transactions)
        }


def add_strategy_context_to_transactions(transactions):
    """
    Add strategy information to a queryset of transactions
    Returns list of transaction objects with added strategy_info attribute
    """
    try:
        identifier = SimpleStrategyIdentifier()
        strategies = identifier.identify_strategies_for_transactions(transactions)
        
        # Create a mapping of transaction to strategy
        txn_to_strategy = {}
        for strategy in strategies:
            for txn in strategy['transactions']:
                txn_to_strategy[txn.id] = strategy
        
        # Add strategy_info to each transaction
        enhanced_transactions = []
        for txn in transactions:
            txn.strategy_info = txn_to_strategy.get(txn.id, {
                'strategy_type': 'Unknown',
                'confidence': 0,
                'underlying_symbol': txn.symbol or 'Unknown',
                'legs_count': 1
            })
            enhanced_transactions.append(txn)
        
        return enhanced_transactions
    
    except Exception as e:
        # If strategy identification fails, return transactions with minimal strategy info
        enhanced_transactions = []
        for txn in transactions:
            txn.strategy_info = {
                'strategy_type': 'Error',
                'confidence': 0,
                'underlying_symbol': txn.symbol or 'Unknown',
                'legs_count': 1
            }
            enhanced_transactions.append(txn)
        
        return enhanced_transactions