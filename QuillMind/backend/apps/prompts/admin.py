from django.contrib import admin

from .models import PromptTemplate


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ("module", "version", "is_active", "created_at", "updated_at")
    list_editable = ("is_active",)
    list_filter = ("module", "is_active", "created_at")
    search_fields = ("module", "version", "content", "changelog")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("module", "-version")
    actions = ("activate_versions", "deactivate_versions")

    @admin.action(description="激活所选模板版本")
    def activate_versions(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"已激活 {updated} 个模板版本。")

    @admin.action(description="停用所选模板版本")
    def deactivate_versions(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"已停用 {updated} 个模板版本。")
