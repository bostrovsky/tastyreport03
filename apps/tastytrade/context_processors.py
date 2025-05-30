"""
Context processors for TastyTrade app
"""
from apps.tastytrade.models import Position, Transaction, TastyTradeCredential


def tastytrade_credential(request):
    """
    Add TastyTrade credential to template context on all pages
    """
    context = {
        'tastytrade_credential': None,
    }
    
    if request.user.is_authenticated:
        try:
            credential = request.user.tastytrade_credential
            context['tastytrade_credential'] = credential
        except TastyTradeCredential.DoesNotExist:
            pass
    
    return context


def tastytrade_accounts(request):
    """
    Add available TastyTrade accounts to template context on all pages
    """
    context = {
        'available_accounts': [],
        'user_has_tastytrade': False,
    }
    
    if request.user.is_authenticated:
        try:
            credential = request.user.tastytrade_credential
            context['user_has_tastytrade'] = True
            
            # Get available accounts from positions (most reliable source)
            accounts = Position.objects.filter(
                user=request.user, 
                credential=credential
            ).values_list('tastytrade_account_number', flat=True).distinct().order_by('tastytrade_account_number')
            
            context['available_accounts'] = list(accounts)
            
        except TastyTradeCredential.DoesNotExist:
            # User doesn't have TastyTrade credential
            pass
    
    return context