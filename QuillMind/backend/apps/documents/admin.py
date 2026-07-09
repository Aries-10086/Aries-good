from django.contrib import admin

from .models import DocumentReview


@admin.register(DocumentReview)
class DocumentReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "model_version", "created_at", "updated_at")
    list_filter = ("model_version", "created_at")
    search_fields = ("user__email", "raw_text", "report")
    readonly_fields = ("id", "created_at", "updated_at")
