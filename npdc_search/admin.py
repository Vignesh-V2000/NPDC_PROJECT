from django.contrib import admin
from .models import SearchLog


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'query', 'result_count', 'is_zero_result', 'response_time_ms']
    list_filter = ['is_zero_result', 'timestamp']
    search_fields = ['query', 'user__username', 'ip_address']
    readonly_fields = ['user', 'query', 'filters', 'result_count', 'is_zero_result', 
                       'response_time_ms', 'timestamp', 'ip_address', 'user_agent', 'session_key']
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
