from rest_framework import serializers

from .models import DocumentReview


class DocumentReviewCreateSerializer(serializers.Serializer):
    text = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=20000,
    )
    doc_type = serializers.ChoiceField(
        choices=DocumentReview.DocType.choices,
        default=DocumentReview.DocType.GENERAL,
    )
    model_version = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
    )
    file = serializers.FileField(required=False, allow_empty_file=False)

    def validate(self, attrs):
        if not attrs.get("text") and not attrs.get("file"):
            raise serializers.ValidationError("请粘贴文本或上传文件。")
        return attrs


class DocumentReviewSummarySerializer(serializers.ModelSerializer):
    review_id = serializers.UUIDField(source="id", read_only=True)
    risk_count = serializers.SerializerMethodField()

    class Meta:
        model = DocumentReview
        fields = (
            "review_id",
            "doc_type",
            "risk_count",
            "model_version",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_risk_count(self, obj):
        return len(obj.risks or [])


class DocumentReviewDetailSerializer(serializers.ModelSerializer):
    review_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = DocumentReview
        fields = (
            "review_id",
            "doc_type",
            "raw_text",
            "risks",
            "report",
            "model_version",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class DocumentReviewTaskResponseSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    review_id = serializers.UUIDField()
    status = serializers.CharField()
    result = serializers.DictField(required=False)
    error = serializers.CharField(required=False, allow_blank=True)
    review = DocumentReviewDetailSerializer(required=False)
