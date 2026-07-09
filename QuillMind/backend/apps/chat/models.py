import uuid

from django.conf import settings
from django.db import models


class ChatSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"
        CLOSED = "closed", "Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
        db_index=True,
    )
    persona = models.JSONField(default=dict, blank=True)
    messages = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    goal = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_sessions"
        ordering = ("-updated_at",)
        indexes = [
            models.Index(fields=("status", "updated_at"), name="chat_status_updated_idx"),
        ]

    def __str__(self):
        return self.goal or f"Chat session {self.id}"
