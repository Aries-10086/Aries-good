import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AsyncTask(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_id = models.CharField(max_length=255, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="async_tasks",
        db_index=True,
    )
    type = models.CharField(max_length=80)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    result = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "async_tasks"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("user", "status"), name="async_tasks_user_status_idx"),
            models.Index(fields=("type", "status"), name="async_tasks_type_status_idx"),
        ]

    def __str__(self):
        return self.task_id

    def mark_running(self):
        self.status = self.Status.RUNNING
        self.error = ""
        self.updated_at = timezone.now()
        self.save(update_fields=("status", "error", "updated_at"))

    def mark_success(self, result=None):
        self.status = self.Status.SUCCESS
        self.result = result or {}
        self.error = ""
        self.updated_at = timezone.now()
        self.save(update_fields=("status", "result", "error", "updated_at"))

    def mark_failed(self, error):
        self.status = self.Status.FAILED
        self.error = str(error)
        self.updated_at = timezone.now()
        self.save(update_fields=("status", "error", "updated_at"))
