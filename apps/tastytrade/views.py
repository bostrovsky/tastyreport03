from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from apps.tastytrade.models import TastyTradeCredential, Position, Transaction
from apps.tastytrade.forms import TastyTradeCredentialForm
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
        
        # Get today's transactions (limit to 10 most recent)
        from datetime import date
        today = date.today()
        
        todays_transactions = Transaction.objects.filter(
            user=request.user,
            credential=credential,
            trade_date__date=today
        ).order_by('-trade_date')[:10]
        
        context['todays_transactions'] = todays_transactions
        context['has_recent_activity'] = todays_transactions.exists()
        
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
def positions(request):
    """View current positions with P&L and Greeks"""
    context = {}
    
    try:
        credential = request.user.tastytrade_credential
        context['tastytrade_credential'] = credential
        
        # Get all positions for the user, grouped by account
        all_positions = Position.objects.filter(
            user=request.user, 
            credential=credential
        ).order_by('tastytrade_account_number', '-market_value')
        
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
        
        # Calculate total portfolio value, P&L, and Greeks
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
        
    except TastyTradeCredential.DoesNotExist:
        context['tastytrade_credential'] = None
        context['positions'] = []
        context['total_positions'] = 0
        context['total_market_value'] = 0
        context['total_unrealized_pnl'] = 0
        context['total_realized_pnl'] = 0
        context['total_delta'] = None
        context['total_theta'] = None
    
    return render(request, "positions.html", context)

@login_required  
def transactions(request):
    """View transaction history with filters and search"""
    context = {}
    
    try:
        credential = request.user.tastytrade_credential
        context['tastytrade_credential'] = credential
        
        # Get all transactions for the user
        transactions = Transaction.objects.filter(
            user=request.user,
            credential=credential
        ).order_by('-trade_date')
        
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
        
    except TastyTradeCredential.DoesNotExist:
        context['tastytrade_credential'] = None
        context['transactions'] = []
        context['total_transactions'] = 0
        context['transaction_types'] = []
        context['total_amount'] = 0
        context['avg_amount'] = 0
    
    return render(request, "transactions.html", context)
