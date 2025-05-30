from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from apps.tastytrade.models import TastyTradeCredential, Position, Transaction, UserAccountPreferences, DiscoveredAccount
from apps.tastytrade.forms import (
    TastyTradeCredentialForm, AccountPreferencesForm, TrackedAccountsForm, 
    TastyTradePasswordChangeForm, DeleteAccountConfirmationForm
)
from django.utils import timezone
from django.contrib import messages
from django.db import transaction as db_transaction
from .tastytrade_api import TastyTradeAPI
import logging

logger = logging.getLogger(__name__)

# Create your views here.

@login_required
def connect_tastytrade(request):
    user = request.user
    try:
        cred = user.tastytrade_credential
    except TastyTradeCredential.DoesNotExist:
        cred = None

    if request.method == 'POST':
        form = TastyTradeCredentialForm(request.POST, instance=cred, user=user)
        if form.is_valid():
            credential = form.save(commit=False)
            credential.user = user
            # Environment is enforced in the form
            credential.save()
            return redirect('tastytrade_connect')
    else:
        form = TastyTradeCredentialForm(instance=cred, user=user)

    return render(request, 'tastytrade/connect.html', {
        'form': form,
        'credential': cred,
    })

@login_required
def remove_tastytrade_credential(request):
    user = request.user
    try:
        cred = user.tastytrade_credential
        cred.delete()
    except TastyTradeCredential.DoesNotExist:
        pass
    return redirect('tastytrade_connect')

@login_required
def sync_tastytrade(request):
    user = request.user
    try:
        credential = user.tastytrade_credential
    except Exception:
        messages.error(request, "No TastyTrade credentials found.")
        return redirect("home")

    api = TastyTradeAPI(credential)
    try:
        print(f"DEBUG: Starting sync process using {api.auth_method} authentication...")
        api.authenticate()
        print(f"DEBUG: Authentication successful! {api.auth_method.title()} token acquired.")
        print("DEBUG: Testing session with user info endpoint...")
        session_test = api.test_session()
        print(f"DEBUG: Session test result: {session_test}")
        print("DEBUG: Now attempting to fetch accounts...")
        account_numbers = api.fetch_accounts()
        print(f"DEBUG: Account numbers retrieved: {account_numbers}")
        if not account_numbers:
            messages.error(request, "No TastyTrade accounts found for this user.")
            return redirect("home")
        with db_transaction.atomic():
            for account_number in account_numbers:
                print(f"DEBUG: Processing account {account_number}")
                
                # Get the most recent transaction date for incremental sync
                last_transaction = Transaction.objects.filter(
                    user=user,
                    credential=credential,
                    tastytrade_account_number=account_number
                ).order_by('-trade_date').first()
                
                start_date = None
                if last_transaction:
                    # Get transactions from 1 day before the last transaction to ensure we don't miss any
                    from datetime import timedelta
                    start_date = last_transaction.trade_date.date() - timedelta(days=1)
                    print(f"DEBUG: Incremental sync from {start_date} (last transaction: {last_transaction.trade_date.date()})")
                else:
                    print(f"DEBUG: First sync - fetching all transactions")
                
                positions = api.fetch_positions(account_number)
                print(f"DEBUG: Retrieved {len(positions)} positions")
                
                transactions = api.fetch_transactions(account_number, start_date=start_date)
                print(f"DEBUG: Retrieved {len(transactions)} transactions")
                # Upsert positions with daily P&L tracking
                for pos in positions:
                    if pos.get("symbol"):  # Only process if we have a symbol
                        # Get current price from API data
                        new_current_price = pos.get("current_price")  # We'll update the API to include this
                        
                        # Find existing position to get previous price
                        try:
                            existing_position = Position.objects.get(
                                user=user,
                                credential=credential,
                                tastytrade_account_number=account_number,
                                asset_type=pos.get("asset_type", "other"),
                                symbol=pos["symbol"],
                                expiry=pos.get("expiry"),
                                strike=pos.get("strike"),
                                option_type=pos.get("option_type"),
                            )
                            # Store current price as previous close price
                            previous_close_price = existing_position.current_price
                        except Position.DoesNotExist:
                            # New position - no previous price
                            previous_close_price = None
                        
                        # Calculate daily unrealized P&L if we have both prices
                        daily_unrealized_pnl = None
                        if previous_close_price and new_current_price:
                            quantity = pos.get("quantity", 0)
                            multiplier = pos.get("multiplier", 1)  # Use multiplier from API
                            price_diff = float(new_current_price) - float(previous_close_price)
                            daily_unrealized_pnl = price_diff * float(quantity) * multiplier
                        
                        # Calculate proper unrealized P&L: (current_price - average_price) × quantity
                        corrected_unrealized_pnl = None
                        if new_current_price and pos.get("average_price"):
                            quantity = pos.get("quantity", 0)
                            multiplier = pos.get("multiplier", 1)
                            avg_price = float(pos.get("average_price", 0))
                            price_diff = float(new_current_price) - avg_price
                            corrected_unrealized_pnl = price_diff * float(quantity) * multiplier
                        
                        Position.objects.update_or_create(
                            user=user,
                            credential=credential,
                            tastytrade_account_number=account_number,
                            asset_type=pos.get("asset_type", "other"),
                            symbol=pos["symbol"],
                            expiry=pos.get("expiry"),
                            strike=pos.get("strike"),
                            option_type=pos.get("option_type"),
                            defaults={
                                "description": pos.get("description", ""),
                                "quantity": pos.get("quantity", 0),
                                "average_price": pos.get("average_price"),
                                "current_price": new_current_price,
                                "previous_close_price": previous_close_price,
                                "market_value": pos.get("market_value"),
                                "unrealized_pnl": corrected_unrealized_pnl if corrected_unrealized_pnl is not None else pos.get("unrealized_pnl"),
                                "daily_unrealized_pnl": daily_unrealized_pnl,
                                "realized_pnl": 0,  # Only set when position is fully closed
                                "delta": pos.get("delta"),
                                "theta": pos.get("theta"),
                                "beta": pos.get("beta"),
                            },
                        )
                # Upsert transactions with deduplication
                transactions_saved = 0
                transactions_skipped = 0
                transactions_updated = 0
                
                # Get existing transaction IDs to avoid unnecessary database queries
                # Only check recent transactions if doing incremental sync
                transaction_filter = {
                    'user': user,
                    'credential': credential,
                    'tastytrade_account_number': account_number
                }
                if start_date:
                    from datetime import timedelta
                    # Include a buffer to ensure we catch all relevant transactions
                    buffer_date = start_date - timedelta(days=2)
                    transaction_filter['trade_date__gte'] = buffer_date
                
                existing_transaction_ids = set(
                    Transaction.objects.filter(**transaction_filter).values_list('transaction_id', flat=True)
                )
                
                for txn in transactions:
                    transaction_id = txn.get("transaction_id")
                    trade_date = txn.get("trade_date")
                    
                    if not transaction_id or not trade_date:
                        transactions_skipped += 1
                        print(f"DEBUG: Skipped transaction - missing ID ({transaction_id}) or date ({trade_date})")
                        continue
                    
                    # Use Django's update_or_create to handle duplicates properly
                    transaction_obj, created = Transaction.objects.update_or_create(
                        user=user,
                        credential=credential,
                        tastytrade_account_number=account_number,
                        transaction_id=transaction_id,
                        defaults={
                            "transaction_type": txn.get("transaction_type", "other"),
                            "symbol": txn.get("symbol", ""),
                            "description": txn.get("description", ""),
                            "quantity": txn.get("quantity"),
                            "price": txn.get("price"),
                            "amount": txn.get("amount", 0),
                            "trade_date": trade_date,
                            "asset_type": txn.get("asset_type", ""),
                            "expiry": txn.get("expiry"),
                            "strike": txn.get("strike"),
                            "option_type": txn.get("option_type"),
                        }
                    )
                    
                    if created:
                        transactions_saved += 1
                    else:
                        transactions_updated += 1
                
                print(f"DEBUG: Transaction summary for account {account_number}: {transactions_saved} new, {transactions_updated} updated, {transactions_skipped} skipped")
            credential.last_sync = timezone.now()
            credential.save(update_fields=["last_sync"])
        messages.success(request, "Sync completed successfully.")
    except Exception as e:
        messages.error(request, f"Sync failed: {e}")
    
    # Return to the page where sync was initiated
    next_url = request.META.get('HTTP_REFERER', '/')
    return redirect(next_url)

@login_required
def dashboard(request):
    context = {}
    
    # Get today's transactions if user has TastyTrade credential
    try:
        credential = request.user.tastytrade_credential
        context['tastytrade_credential'] = credential
        
        # Get accounts for P&L calculations (available_accounts now from context processor)
        accounts = Position.objects.filter(
            user=request.user, 
            credential=credential
        ).values_list('tastytrade_account_number', flat=True).distinct()
        
        # Get recent transactions (yesterday and today - from previous market close)
        from datetime import date, timedelta
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Recent activity includes yesterday and today (previous close through today)
        recent_transactions = Transaction.objects.filter(
            user=request.user,
            credential=credential,
            trade_date__date__gte=yesterday  # Yesterday and today
        ).order_by('-trade_date', '-created_at')[:10]
        
        # Also get just today's transactions for P&L calculation
        todays_transactions = Transaction.objects.filter(
            user=request.user,
            credential=credential,
            trade_date__date=today
        ).order_by('-trade_date')
        
        context['todays_transactions'] = recent_transactions  # Show recent for display
        context['has_recent_activity'] = recent_transactions.exists()
        context['todays_transactions_count'] = todays_transactions.count()
        context['recent_transactions_date_range'] = f"{yesterday.strftime('%m/%d')} - {today.strftime('%m/%d')}"
        
        # Get summary statistics
        total_positions = Position.objects.filter(user=request.user, credential=credential).count()
        context['total_positions'] = total_positions
        
        # Calculate today's REALIZED P&L from transactions
        from django.db import models
        todays_realized_pnl = todays_transactions.aggregate(
            total_pnl=models.Sum('amount')
        )['total_pnl'] or 0
        context['todays_realized_pnl'] = todays_realized_pnl
        
        # Calculate position statistics
        positions = Position.objects.filter(user=request.user, credential=credential)
        position_stats = positions.aggregate(
            total_unrealized=models.Sum('unrealized_pnl'),
            daily_unrealized=models.Sum('daily_unrealized_pnl'),
            total_market_value=models.Sum('market_value')
        )
        
        total_unrealized_pnl = position_stats['total_unrealized'] or 0
        daily_unrealized_pnl = position_stats['daily_unrealized'] or 0
        total_market_value = position_stats['total_market_value'] or 0
        
        context['total_unrealized_pnl'] = total_unrealized_pnl
        context['daily_unrealized_pnl'] = daily_unrealized_pnl
        context['total_market_value'] = total_market_value
        
        # Calculate total daily P&L (realized + daily unrealized change)
        context['todays_total_pnl'] = todays_realized_pnl + daily_unrealized_pnl
        
        # Calculate per-account statistics for dashboard
        account_stats = {}
        for account in accounts:
            account_positions = positions.filter(tastytrade_account_number=account)
            account_transactions = todays_transactions.filter(tastytrade_account_number=account)
            
            account_portfolio_stats = account_positions.aggregate(
                market_value=models.Sum('market_value'),
                unrealized_pnl=models.Sum('unrealized_pnl'),
                daily_unrealized=models.Sum('daily_unrealized_pnl'),
                delta=models.Sum('delta'),
                theta=models.Sum('theta'),
            )
            
            account_realized_pnl = account_transactions.aggregate(
                total_pnl=models.Sum('amount')
            )['total_pnl'] or 0
            
            account_stats[account] = {
                'positions_count': account_positions.count(),
                'market_value': account_portfolio_stats['market_value'] or 0,
                'unrealized_pnl': account_portfolio_stats['unrealized_pnl'] or 0,
                'daily_unrealized_pnl': account_portfolio_stats['daily_unrealized'] or 0,
                'realized_pnl_today': account_realized_pnl,
                'total_daily_pnl': account_realized_pnl + (account_portfolio_stats['daily_unrealized'] or 0),
                'delta': account_portfolio_stats['delta'],
                'theta': account_portfolio_stats['theta'],
                'transactions_today': account_transactions.count(),
            }
        
        context['account_stats'] = account_stats
        
    except TastyTradeCredential.DoesNotExist:
        context['tastytrade_credential'] = None
        context['todays_transactions'] = []
        context['has_recent_activity'] = False
        context['total_positions'] = 0
        context['todays_pnl'] = 0
    
    return render(request, "home.html", context)

@login_required
def oauth_authorize(request):
    """Initiate OAuth 2.0 authorization flow"""
    user = request.user
    try:
        credential = user.tastytrade_credential
    except TastyTradeCredential.DoesNotExist:
        messages.error(request, "Please create TastyTrade credentials first.")
        return redirect('tastytrade_connect')
    
    api = TastyTradeAPI(credential)
    
    try:
        auth_url = api.get_oauth_authorization_url()
        return redirect(auth_url)
    except Exception as e:
        messages.error(request, f"OAuth authorization failed: {e}")
        return redirect('tastytrade_connect')

@login_required
def oauth_callback(request):
    """Handle OAuth 2.0 authorization callback"""
    user = request.user
    authorization_code = request.GET.get('code')
    error = request.GET.get('error')
    
    if error:
        messages.error(request, f"OAuth authorization was denied: {error}")
        return redirect('tastytrade_connect')
    
    if not authorization_code:
        messages.error(request, "No authorization code received from TastyTrade.")
        return redirect('tastytrade_connect')
    
    try:
        credential = user.tastytrade_credential
    except TastyTradeCredential.DoesNotExist:
        messages.error(request, "No TastyTrade credentials found.")
        return redirect('tastytrade_connect')
    
    api = TastyTradeAPI(credential)
    
    try:
        token_data = api.exchange_code_for_tokens(authorization_code)
        messages.success(request, "OAuth authorization successful! You can now sync your data.")
        return redirect('tastytrade_connect')
    except Exception as e:
        logger.error(f"OAuth token exchange failed: {e}")
        messages.error(request, f"OAuth token exchange failed: {e}")
        return redirect('tastytrade_connect')

@login_required
def oauth_status(request):
    """Check OAuth authorization status"""
    user = request.user
    try:
        credential = user.tastytrade_credential
        api = TastyTradeAPI(credential)
        
        status = {
            'oauth_configured': api._can_use_oauth(),
            'has_access_token': bool(credential.access_token),
            'has_refresh_token': bool(credential.refresh_token),
            'auth_method': api.auth_method,
        }
        
        return JsonResponse(status)
    except TastyTradeCredential.DoesNotExist:
        return JsonResponse({
            'oauth_configured': False,
            'has_access_token': False,
            'has_refresh_token': False,
            'auth_method': 'none',
        })

@login_required
def revoke_oauth(request):
    """Revoke OAuth tokens and clear credential"""
    user = request.user
    try:
        credential = user.tastytrade_credential
        credential.access_token = None
        credential.refresh_token = None
        credential.save()
        messages.success(request, "OAuth authorization has been revoked.")
    except TastyTradeCredential.DoesNotExist:
        messages.error(request, "No TastyTrade credentials found.")
    
    return redirect('tastytrade_connect')

@login_required
def positions(request, account_number=None):
    """View current positions with P&L and Greeks, optionally filtered by account"""
    context = {}
    
    try:
        credential = request.user.tastytrade_credential
        context['tastytrade_credential'] = credential
        
        # Set current account for filtering display (available_accounts from context processor)
        context['current_account'] = account_number
        
        # Filter positions by account if specified
        position_filter = {
            'user': request.user,
            'credential': credential
        }
        if account_number:
            position_filter['tastytrade_account_number'] = account_number
        
        all_positions = Position.objects.filter(**position_filter).order_by('tastytrade_account_number', '-market_value')
        
        # Group positions by account
        positions_by_account = {}
        for position in all_positions:
            account = position.tastytrade_account_number
            if account not in positions_by_account:
                positions_by_account[account] = []
            positions_by_account[account].append(position)
        
        context['positions_by_account'] = positions_by_account
        context['positions'] = all_positions  # Keep for backwards compatibility
        context['total_positions'] = all_positions.count()
        
        # Calculate portfolio value, P&L, and Greeks for displayed positions
        from django.db import models
        portfolio_stats = all_positions.aggregate(
            total_market_value=models.Sum('market_value'),
            total_unrealized_pnl=models.Sum('unrealized_pnl'),
            total_realized_pnl=models.Sum('realized_pnl'),
            total_delta=models.Sum('delta'),
            total_theta=models.Sum('theta'),
        )
        
        context.update({
            'total_market_value': portfolio_stats['total_market_value'] or 0,
            'total_unrealized_pnl': portfolio_stats['total_unrealized_pnl'] or 0,
            'total_realized_pnl': portfolio_stats['total_realized_pnl'] or 0,
            'total_delta': portfolio_stats['total_delta'],
            'total_theta': portfolio_stats['total_theta'],
        })
        
        # Calculate portfolio allocation by symbol for pie chart
        total_value = context['total_market_value']
        if total_value > 0:
            symbol_allocations = []
            symbol_values = {}
            
            # Group by symbol and sum market values
            for position in all_positions:
                symbol = position.symbol
                value = position.market_value or 0
                if symbol in symbol_values:
                    symbol_values[symbol] += value
                else:
                    symbol_values[symbol] = value
            
            # Calculate percentages and format for chart
            top_holdings = []
            other_value = 0
            
            # Sort by value descending first
            sorted_symbols = sorted(symbol_values.items(), key=lambda x: x[1], reverse=True)
            
            for symbol, value in sorted_symbols:
                percentage = (value / total_value) * 100
                if percentage >= 3 and len(top_holdings) < 8:  # Show top 8 holdings with at least 3%
                    top_holdings.append({
                        'symbol': symbol,
                        'value': float(value),
                        'percentage': round(percentage, 1)
                    })
                else:
                    other_value += value
            
            # Add "Other" segment if there are remaining holdings
            if other_value > 0:
                other_percentage = (other_value / total_value) * 100
                top_holdings.append({
                    'symbol': 'Other',
                    'value': float(other_value),
                    'percentage': round(other_percentage, 1)
                })
            
            context['portfolio_allocation'] = top_holdings
            
            # Calculate delta risk allocation by symbol for risk chart
            delta_allocations = []
            symbol_deltas = {}
            total_abs_delta = 0
            
            # Group by symbol and sum absolute deltas
            for position in all_positions:
                if position.delta:
                    symbol = position.symbol
                    delta = abs(float(position.delta))
                    total_abs_delta += delta
                    if symbol in symbol_deltas:
                        symbol_deltas[symbol] += delta
                    else:
                        symbol_deltas[symbol] = delta
            
            if total_abs_delta > 0:
                top_delta_risks = []
                other_delta = 0
                
                # Sort by absolute delta descending
                sorted_deltas = sorted(symbol_deltas.items(), key=lambda x: x[1], reverse=True)
                
                for symbol, delta in sorted_deltas:
                    percentage = (delta / total_abs_delta) * 100
                    if percentage >= 3 and len(top_delta_risks) < 8:  # Show top 8 delta risks with at least 3%
                        top_delta_risks.append({
                            'symbol': symbol,
                            'value': float(delta),
                            'percentage': round(percentage, 1)
                        })
                    else:
                        other_delta += delta
                
                # Add "Other" segment if there are remaining deltas
                if other_delta > 0:
                    other_percentage = (other_delta / total_abs_delta) * 100
                    top_delta_risks.append({
                        'symbol': 'Other',
                        'value': float(other_delta),
                        'percentage': round(other_percentage, 1)
                    })
                
                context['delta_risk_allocation'] = top_delta_risks
            else:
                context['delta_risk_allocation'] = []
        else:
            context['portfolio_allocation'] = []
            context['delta_risk_allocation'] = []
        
        # Add account-specific title
        if account_number:
            context['page_title'] = f'Positions - Account {account_number}'
        else:
            context['page_title'] = 'All Positions'
        
    except TastyTradeCredential.DoesNotExist:
        context['tastytrade_credential'] = None
        context['positions'] = []
        context['total_positions'] = 0
        context['total_market_value'] = 0
        context['total_unrealized_pnl'] = 0
        context['total_realized_pnl'] = 0
        context['total_delta'] = None
        context['total_theta'] = None
        context['current_account'] = None
        context['page_title'] = 'Positions'
    
    return render(request, "positions.html", context)

@login_required  
def transactions(request, account_number=None):
    """View transaction history with filters and search, optionally filtered by account"""
    context = {}
    
    try:
        credential = request.user.tastytrade_credential
        context['tastytrade_credential'] = credential
        
        # Set current account for filtering display (available_accounts from context processor)
        context['current_account'] = account_number
        
        # Filter transactions by account if specified
        transaction_filter = {
            'user': request.user,
            'credential': credential
        }
        if account_number:
            transaction_filter['tastytrade_account_number'] = account_number
        
        transactions = Transaction.objects.filter(**transaction_filter).order_by('-trade_date')
        
        # Apply search filter if provided
        search_query = request.GET.get('search', '').strip()
        if search_query:
            from django.db import models
            transactions = transactions.filter(
                models.Q(symbol__icontains=search_query) |
                models.Q(description__icontains=search_query) |
                models.Q(transaction_type__icontains=search_query)
            )
            context['search_query'] = search_query
        
        # Apply transaction type filter
        transaction_type = request.GET.get('type', '').strip()
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)
            context['selected_type'] = transaction_type
        
        # Get unique transaction types for filter dropdown
        transaction_types = Transaction.objects.filter(
            user=request.user,
            credential=credential
        ).values_list('transaction_type', flat=True).distinct().order_by('transaction_type')
        
        context['transaction_types'] = [t for t in transaction_types if t]
        
        # Pagination - 50 transactions per page
        from django.core.paginator import Paginator
        paginator = Paginator(transactions, 50)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['transactions'] = page_obj
        context['total_transactions'] = transactions.count()
        
        # Calculate summary statistics for filtered transactions  
        from django.db import models
        summary_stats = transactions.aggregate(
            total_amount=models.Sum('amount'),
            avg_amount=models.Avg('amount'),
        )
        
        context.update({
            'total_amount': summary_stats['total_amount'] or 0,
            'avg_amount': summary_stats['avg_amount'] or 0,
        })
        
        # Add account-specific title
        if account_number:
            context['page_title'] = f'Transactions - Account {account_number}'
        else:
            context['page_title'] = 'All Transactions'
        
    except TastyTradeCredential.DoesNotExist:
        context['tastytrade_credential'] = None
        context['transactions'] = []
        context['total_transactions'] = 0
        context['transaction_types'] = []
        context['total_amount'] = 0
        context['avg_amount'] = 0
        context['current_account'] = None
        context['page_title'] = 'Transactions'
    
    return render(request, "transactions.html", context)


@login_required
def settings(request):
    """Main settings page"""
    context = {}
    
    try:
        credential = request.user.tastytrade_credential
        context['tastytrade_credential'] = credential
        
        # Get or create user preferences
        preferences, created = UserAccountPreferences.objects.get_or_create(
            user=request.user,
            credential=credential,
            defaults={
                'tracked_accounts': [],
                'save_credentials': True,
                'auto_sync_frequency': 'manual',
                'keep_historical_data_on_account_removal': True,
            }
        )
        context['preferences'] = preferences
        
        # Get discovered accounts
        discovered_accounts = DiscoveredAccount.objects.filter(
            user=request.user,
            credential=credential
        ).order_by('account_number')
        context['discovered_accounts'] = discovered_accounts
        
        # Get account statistics
        account_stats = {}
        for account in discovered_accounts:
            if account.is_tracked:
                positions_count = Position.objects.filter(
                    user=request.user,
                    credential=credential,
                    tastytrade_account_number=account.account_number
                ).count()
                
                transactions_count = Transaction.objects.filter(
                    user=request.user,
                    credential=credential,
                    tastytrade_account_number=account.account_number
                ).count()
                
                account_stats[account.account_number] = {
                    'positions': positions_count,
                    'transactions': transactions_count,
                }
        
        context['account_stats'] = account_stats
        
    except TastyTradeCredential.DoesNotExist:
        context['tastytrade_credential'] = None
        context['preferences'] = None
        context['discovered_accounts'] = []
        context['account_stats'] = {}
    
    return render(request, "tastytrade/settings.html", context)


@login_required
def account_preferences(request):
    """Manage account preferences"""
    try:
        credential = request.user.tastytrade_credential
        preferences, created = UserAccountPreferences.objects.get_or_create(
            user=request.user,
            credential=credential
        )
    except TastyTradeCredential.DoesNotExist:
        messages.error(request, "Please connect your TastyTrade account first.")
        return redirect('tastytrade_connect')
    
    if request.method == 'POST':
        form = AccountPreferencesForm(
            request.POST,
            instance=preferences,
            user=request.user,
            credential=credential
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Account preferences updated successfully.")
            return redirect('settings')
    else:
        form = AccountPreferencesForm(
            instance=preferences,
            user=request.user,
            credential=credential
        )
    
    return render(request, "tastytrade/account_preferences.html", {'form': form})


@login_required
def manage_tracked_accounts(request):
    """Manage which accounts to track"""
    try:
        credential = request.user.tastytrade_credential
    except TastyTradeCredential.DoesNotExist:
        messages.error(request, "Please connect your TastyTrade account first.")
        return redirect('tastytrade_connect')
    
    if request.method == 'POST':
        form = TrackedAccountsForm(
            request.POST,
            user=request.user,
            credential=credential
        )
        if form.is_valid():
            # Update tracked status for each account
            discovered_accounts = DiscoveredAccount.objects.filter(
                user=request.user,
                credential=credential
            )
            
            for account in discovered_accounts:
                field_name = f'account_{account.account_number}'
                name_field = f'name_{account.account_number}'
                
                if field_name in form.cleaned_data:
                    account.is_tracked = form.cleaned_data[field_name]
                    
                if name_field in form.cleaned_data and form.cleaned_data[name_field]:
                    account.account_name = form.cleaned_data[name_field]
                    
                account.save()
            
            messages.success(request, "Account tracking preferences updated.")
            return redirect('settings')
    else:
        form = TrackedAccountsForm(
            user=request.user,
            credential=credential
        )
    
    return render(request, "tastytrade/manage_tracked_accounts.html", {'form': form})


@login_required  
def change_tastytrade_password(request):
    """Change TastyTrade password"""
    try:
        credential = request.user.tastytrade_credential
    except TastyTradeCredential.DoesNotExist:
        messages.error(request, "Please connect your TastyTrade account first.")
        return redirect('tastytrade_connect')
    
    if request.method == 'POST':
        form = TastyTradePasswordChangeForm(request.POST)
        if form.is_valid():
            # Verify current password by testing authentication
            from .tastytrade_api import TastyTradeAPI
            test_credential = TastyTradeCredential(
                user=request.user,
                environment=credential.environment,
                username=credential.username,
                password=form.cleaned_data['current_password']
            )
            
            api = TastyTradeAPI(test_credential)
            try:
                api.authenticate()
                # If authentication succeeds, update the password
                credential.password = form.cleaned_data['new_password']
                credential.save()
                messages.success(request, "TastyTrade password updated successfully.")
                return redirect('settings')
            except Exception as e:
                form.add_error('current_password', 'Current password is incorrect.')
    else:
        form = TastyTradePasswordChangeForm()
    
    return render(request, "tastytrade/change_tastytrade_password.html", {'form': form})


@login_required
def delete_account(request):
    """Delete TastyTrade Tracker account"""
    try:
        credential = request.user.tastytrade_credential
    except TastyTradeCredential.DoesNotExist:
        messages.error(request, "No TastyTrade account found to delete.")
        return redirect('home')
    
    if request.method == 'POST':
        form = DeleteAccountConfirmationForm(request.POST)
        if form.is_valid():
            keep_data = form.cleaned_data['keep_data']
            
            if not keep_data:
                # Delete all related data
                Position.objects.filter(user=request.user, credential=credential).delete()
                Transaction.objects.filter(user=request.user, credential=credential).delete()
                DiscoveredAccount.objects.filter(user=request.user, credential=credential).delete()
                
                try:
                    UserAccountPreferences.objects.filter(user=request.user, credential=credential).delete()
                except UserAccountPreferences.DoesNotExist:
                    pass
            
            # Delete the credential
            credential.delete()
            
            messages.success(request, "Your TastyTrade Tracker account has been deleted.")
            return redirect('home')
    else:
        form = DeleteAccountConfirmationForm()
    
    # Get data summary for user to understand what will be deleted
    positions_count = Position.objects.filter(user=request.user, credential=credential).count()
    transactions_count = Transaction.objects.filter(user=request.user, credential=credential).count()
    
    context = {
        'form': form,
        'positions_count': positions_count,
        'transactions_count': transactions_count,
    }
    
    return render(request, "tastytrade/delete_account.html", context)
