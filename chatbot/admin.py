from django.contrib import admin
from .models import ChatConversation, ChatMessage


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'user', 'is_admin', 'created_at']
    list_filter = ['is_admin', 'created_at']
    search_fields = ['session_id', 'user__username']
    ordering = ['-created_at']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'message_type', 'content_preview', 'timestamp']
    list_filter = ['message_type', 'timestamp']
    search_fields = ['content']
    ordering = ['-timestamp']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'
