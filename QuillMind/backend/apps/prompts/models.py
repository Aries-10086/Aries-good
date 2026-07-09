import uuid

from django.db import models


class PromptTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.CharField(max_length=80)
    version = models.CharField(max_length=40)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    changelog = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "prompt_templates"
        ordering = ("module", "-updated_at")
        indexes = [
            models.Index(fields=("module", "is_active"), name="prompt_module_active_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("module", "version"),
                name="prompt_module_version_uniq",
            ),
        ]

    def __str__(self):
        return f"{self.module}@{self.version}"
