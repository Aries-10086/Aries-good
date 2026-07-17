from django.contrib import admin

from .models import ChatSession


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "scene",
        "relationship",
        "status",
        "goal",
        "created_at",
        "updated_at",
    )
    list_filter = ("scene", "status", "created_at", "updated_at")
    search_fields = ("user__email", "relationship", "goal")
    readonly_fields = ("id", "persona", "messages", "created_at", "updated_at")
