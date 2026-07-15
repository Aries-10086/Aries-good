from django.contrib import admin

from .models import GenerationRecord, StyleProfile


@admin.register(StyleProfile)
class StyleProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "sample_count", "created_at", "updated_at")
    search_fields = ("name", "user__email")
    readonly_fields = ("id", "sample_count", "created_at", "updated_at")


@admin.register(GenerationRecord)
class GenerationRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "style", "model_name", "created_at")
    list_filter = ("model_name", "created_at")
    search_fields = ("user__email", "prompt", "result")
    readonly_fields = ("id", "quality", "created_at", "updated_at")
