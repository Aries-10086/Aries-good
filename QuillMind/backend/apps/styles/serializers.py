from __future__ import annotations

from rest_framework import serializers
from rest_framework.exceptions import APIException

from core.style import EmbeddingError

from .models import StyleProfile
from .services import StyleSampleValidationError, extract_profile_data, prepare_samples


class StyleExtractionUnavailable(APIException):
    status_code = 503
    default_detail = "风格提取服务暂时不可用，请稍后重试。"
    default_code = "style_extraction_unavailable"


class StyleProfileListSerializer(serializers.ModelSerializer):
    profile_id = serializers.UUIDField(source="id", read_only=True)
    sample_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = StyleProfile
        fields = (
            "profile_id",
            "name",
            "sample_count",
            "description",
            "created_at",
            "updated_at",
        )


class StyleProfileDetailSerializer(serializers.ModelSerializer):
    profile_id = serializers.UUIDField(source="id", read_only=True)
    sample_count = serializers.IntegerField(read_only=True)
    vector_dimension = serializers.SerializerMethodField()

    class Meta:
        model = StyleProfile
        fields = (
            "profile_id",
            "name",
            "sample_count",
            "samples",
            "style_vector",
            "vector_dimension",
            "features",
            "description",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_vector_dimension(self, obj) -> int:
        return len(obj.style_vector)


class StyleProfileWriteSerializer(serializers.ModelSerializer):
    samples = serializers.ListField(
        child=serializers.CharField(trim_whitespace=False, allow_blank=False),
        required=False,
        write_only=True,
    )
    files = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        write_only=True,
    )

    class Meta:
        model = StyleProfile
        fields = ("name", "samples", "files")
        extra_kwargs = {"name": {"required": False}}

    def validate(self, attrs):
        is_create = self.instance is None
        if is_create and not attrs.get("name"):
            raise serializers.ValidationError({"name": "请输入风格档案名称。"})

        has_new_samples = "samples" in attrs or "files" in attrs
        if is_create or has_new_samples:
            try:
                attrs["_prepared_samples"] = prepare_samples(
                    attrs.pop("samples", []),
                    attrs.pop("files", []),
                    minimum_count=3 if is_create else 1,
                )
            except StyleSampleValidationError as exc:
                raise serializers.ValidationError({"samples": str(exc)}) from exc

        return attrs

    def create(self, validated_data):
        samples = validated_data.pop("_prepared_samples")
        result = self._extract(samples)
        return StyleProfile.objects.create(
            user=validated_data.pop("user"),
            samples=samples,
            style_vector=result["vector"],
            features=result["features"],
            description=result["description"],
            **validated_data,
        )

    def update(self, instance, validated_data):
        new_samples = validated_data.pop("_prepared_samples", None)

        if "name" in validated_data:
            instance.name = validated_data["name"]

        update_fields = ["name", "updated_at"]
        if new_samples is not None:
            combined_samples = [*instance.samples, *new_samples]
            result = self._extract(combined_samples)
            instance.samples = combined_samples
            instance.style_vector = result["vector"]
            instance.features = result["features"]
            instance.description = result["description"]
            update_fields.extend(("samples", "style_vector", "features", "description"))

        instance.save(update_fields=update_fields)
        return instance

    def _extract(self, samples):
        try:
            return extract_profile_data(samples)
        except EmbeddingError as exc:
            raise StyleExtractionUnavailable() from exc
