from django.urls import path
from . import views

urlpatterns = [
    path('connect/', views.connect_tastytrade, name='tastytrade_connect'),
    path('remove/', views.remove_tastytrade_credential, name='tastytrade_remove'),
    path('sync/', views.sync_tastytrade, name='tastytrade_sync'),
    path('oauth/authorize/', views.oauth_authorize, name='tastytrade_oauth_authorize'),
    path('oauth/callback/', views.oauth_callback, name='tastytrade_oauth_callback'),
    path('oauth/status/', views.oauth_status, name='tastytrade_oauth_status'),
    path('oauth/revoke/', views.revoke_oauth, name='tastytrade_oauth_revoke'),
] 