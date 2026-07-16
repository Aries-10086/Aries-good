import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models


class StyleProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="style_profiles",
        db_index=True,
    )
    name = models.CharField(max_length=120)
    style_vector = models.JSONField(default=list, blank=True)
    features = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True)
    samples = ArrayField(models.TextField(), default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "style_profiles"
        ordering = ("-updated_at",)
        indexes = [
            models.Index(fields=("user", "name"), name="style_profiles_user_name_idx"),
        ]

    def __str__(self):
        return self.name

    @property
    def sample_count(self):
        return len(self.samples)


class GenerationRecord(models.Model):
    class Feedback(models.TextChoices):
        UP = "up", "有帮助"
        DOWN = "down", "需改进"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="generation_records",
        db_index=True,
    )
    style = models.ForeignKey(
        StyleProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generation_records",
    )
    prompt = models.TextField()
    result = models.TextField()
    model_name = models.CharField(max_length=100, blank=True)
    quality = models.JSONField(default=dict, blank=True)
    feedback = models.CharField(
        max_length=8,
        choices=Feedback.choices,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "generation_records"
        ordering = ("-created_at",)

    def __str__(self):
        return f"Generation record {self.id}"
