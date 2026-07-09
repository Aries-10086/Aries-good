from django.contrib import admin

from .models import AsyncTask


@admin.register(AsyncTask)
class AsyncTaskAdmin(admin.ModelAdmin):
    list_display = ("task_id", "user", "type", "status", "created_at", "updated_at")
    list_filter = ("type", "status", "created_at", "updated_at")
    search_fields = ("task_id", "user__email", "error")
    readonly_fields = ("id", "created_at", "updated_at")
