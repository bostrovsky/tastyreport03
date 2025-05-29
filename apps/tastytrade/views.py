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
                positions = api.fetch_positions(account_number)
                print(f"DEBUG: Retrieved {len(positions)} positions")
                transactions = api.fetch_transactions(account_number)
                print(f"DEBUG: Retrieved {len(transactions)} transactions")
                # Upsert positions
                for pos in positions:
                    if pos.get("symbol"):  # Only process if we have a symbol
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
                                "market_value": pos.get("market_value"),
                                "unrealized_pnl": pos.get("unrealized_pnl"),
                                "realized_pnl": pos.get("realized_pnl"),
                                "delta": pos.get("delta"),
                                "theta": pos.get("theta"),
                                "beta": pos.get("beta"),
                            },
                        )
                # Upsert transactions
                for txn in transactions:
                    if txn.get("transaction_id") and txn.get("trade_date"):  # Only process if we have required fields
                        Transaction.objects.update_or_create(
                            user=user,
                            credential=credential,
                            tastytrade_account_number=account_number,
                            transaction_id=txn["transaction_id"],
                            defaults={
                                "transaction_type": txn.get("transaction_type", "other"),
                                "symbol": txn.get("symbol", ""),
                                "description": txn.get("description", ""),
                                "quantity": txn.get("quantity"),
                                "price": txn.get("price"),
                                "amount": txn.get("amount", 0),
                                "trade_date": txn["trade_date"],
                                "asset_type": txn.get("asset_type", ""),
                                "expiry": txn.get("expiry"),
                                "strike": txn.get("strike"),
                                "option_type": txn.get("option_type"),
                            },
                        )
            credential.last_sync = timezone.now()
            credential.save(update_fields=["last_sync"])
        messages.success(request, "Sync completed successfully.")
    except Exception as e:
        messages.error(request, f"Sync failed: {e}")
    return redirect("home")

@login_required
def dashboard(request):
    return render(request, "home.html")

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
