from django.contrib import admin
from .models import TastyTradeCredential

@admin.register(TastyTradeCredential)
class TastyTradeCredentialAdmin(admin.ModelAdmin):
    list_display = ('user', 'environment', 'username', 'created_at', 'updated_at')
    search_fields = ('user__username', 'username')
    list_filter = ('environment',)

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return self.readonly_fields + ('environment',)
        return self.readonly_fields
