from rest_framework import serializers

from .models import DocumentReview


TEXT_PREVIEW_LENGTH = 240


def build_text_preview(text: str, max_length: int = TEXT_PREVIEW_LENGTH) -> str:
    normalized = " ".join(str(text).split())
    if len(normalized) <= max_length:
        return normalized
    return f"{normalized[:max_length].rstrip()}…"


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
    text_preview = serializers.SerializerMethodField()
    text_length = serializers.SerializerMethodField()

    class Meta:
        model = DocumentReview
        fields = (
            "review_id",
            "doc_type",
            "risk_count",
            "text_preview",
            "text_length",
            "model_version",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_risk_count(self, obj):
        return len(obj.risks or [])

    def get_text_preview(self, obj):
        return build_text_preview(obj.raw_text)

    def get_text_length(self, obj):
        return len(obj.raw_text or "")


class DocumentReviewResultSerializer(serializers.ModelSerializer):
    review_id = serializers.UUIDField(source="id", read_only=True)
    text_preview = serializers.SerializerMethodField()
    text_length = serializers.SerializerMethodField()

    class Meta:
        model = DocumentReview
        fields = (
            "review_id",
            "doc_type",
            "text_preview",
            "text_length",
            "risks",
            "report",
            "model_version",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_text_preview(self, obj):
        return build_text_preview(obj.raw_text)

    def get_text_length(self, obj):
        return len(obj.raw_text or "")


class DocumentReviewDetailSerializer(serializers.ModelSerializer):
    review_id = serializers.UUIDField(source="id", read_only=True)
    text_length = serializers.SerializerMethodField()

    class Meta:
        model = DocumentReview
        fields = (
            "review_id",
            "doc_type",
            "raw_text",
            "text_length",
            "risks",
            "report",
            "model_version",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_text_length(self, obj):
        return len(obj.raw_text or "")


class DocumentReviewTaskResponseSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    review_id = serializers.UUIDField()
    status = serializers.CharField()
    result = serializers.DictField(required=False)
    error = serializers.CharField(required=False, allow_blank=True)
    review = DocumentReviewDetailSerializer(required=False)
