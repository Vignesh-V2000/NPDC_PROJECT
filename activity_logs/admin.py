from django.contrib import admin
from .models import ActivityLog, SiteHit

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('action_type', 'actor', 'action_time', 'status', 'ip_address', 'path')
    list_filter = ('action_type', 'status', 'action_time')
    search_fields = ('actor__username', 'remarks', 'ip_address', 'path')
    readonly_fields = ('action_time',)

@admin.register(SiteHit)
class SiteHitAdmin(admin.ModelAdmin):
    list_display = ('action_type', 'action_time', 'ip_address', 'path', 'remarks', 'status')
    list_filter = ('status', 'action_time')
    search_fields = ('remarks', 'ip_address', 'path')
    readonly_fields = ('action_time', 'actor', 'action_type', 'remarks', 'status', 'ip_address', 'entity_name', 'path')
    ordering = ('-action_time',)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(actor__isnull=True, action_type='ACCESS')
