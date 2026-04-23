from django.contrib import admin
from .models import Cruise, CruiseFile


class CruiseFileInline(admin.TabularInline):
    model = CruiseFile
    extra = 1
    fields = ('file_name', 'file_type', 'file_path', 'description')
    readonly_fields = ('uploaded_at', 'updated_at')


@admin.register(Cruise)
class CruiseAdmin(admin.ModelAdmin):
    list_display = ('cruise_no', 'ship_name', 'chief_scientist_name', 'area', 'period_from', 'status')
    list_filter = ('status', 'period_from', 'area', 'ship_name')
    search_fields = ('cruise_no', 'ship_name', 'chief_scientist_name', 'area', 'objective')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CruiseFileInline]
    
    fieldsets = (
        ('Cruise Identification', {
            'fields': ('cruise_no', 'cruise_name', 'ship_name'),
        }),
        ('Schedule', {
            'fields': ('period_from', 'period_to'),
        }),
        ('Details', {
            'fields': ('chief_scientist_name', 'area', 'objective', 'description', 'status'),
        }),
        ('Files & Links', {
            'fields': ('files_link',),
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(CruiseFile)
class CruiseFileAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'cruise', 'file_type', 'uploaded_at')
    list_filter = ('file_type', 'uploaded_at', 'cruise')
    search_fields = ('file_name', 'cruise__cruise_no', 'description')
    readonly_fields = ('uploaded_at', 'updated_at')
    
    fieldsets = (
        ('File Information', {
            'fields': ('file_name', 'file_type', 'file_path', 'file_size'),
        }),
        ('Association', {
            'fields': ('cruise',),
        }),
        ('Description', {
            'fields': ('description',),
        }),
        ('System Information', {
            'fields': ('uploaded_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
