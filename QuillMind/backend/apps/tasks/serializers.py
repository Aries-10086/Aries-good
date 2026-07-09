from rest_framework import serializers

from .models import AsyncTask


class AsyncTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsyncTask
        fields = (
            "id",
            "task_id",
            "type",
            "status",
            "result",
            "error",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
