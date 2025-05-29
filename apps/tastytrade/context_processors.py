def tastytrade_credential(request):
    if request.user.is_authenticated:
        try:
            return {'tastytrade_credential': request.user.tastytrade_credential}
        except Exception:
            return {'tastytrade_credential': None}
    return {'tastytrade_credential': None} 