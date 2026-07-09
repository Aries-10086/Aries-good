from django.contrib import admin

from .models import ChatSession


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "goal", "created_at", "updated_at")
    list_filter = ("status", "created_at", "updated_at")
    search_fields = ("user__email", "goal")
    readonly_fields = ("id", "created_at", "updated_at")
