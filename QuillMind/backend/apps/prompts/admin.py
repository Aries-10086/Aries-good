from django.contrib import admin

from .models import PromptTemplate


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ("module", "version", "is_active", "created_at", "updated_at")
    list_filter = ("module", "is_active", "created_at")
    search_fields = ("module", "version", "content", "changelog")
    readonly_fields = ("id", "created_at", "updated_at")
