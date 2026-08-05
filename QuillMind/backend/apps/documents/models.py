import uuid

from django.conf import settings
from django.db import models


class DocumentReview(models.Model):
    class DocType(models.TextChoices):
        CONTRACT = "contract", "合同"
        REPORT = "report", "报告"
        TESTIMONY = "testimony", "口供"
        GENERAL = "general", "通用"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="document_reviews",
        db_index=True,
    )
    raw_text = models.TextField()
    doc_type = models.CharField(
        max_length=32,
        choices=DocType.choices,
        default=DocType.GENERAL,
        db_index=True,
    )
    risks = models.JSONField(default=list, blank=True)
    report = models.TextField(blank=True)
    model_version = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "document_reviews"
        ordering = ("-created_at",)

    def __str__(self):
        return f"Document review {self.id}"
