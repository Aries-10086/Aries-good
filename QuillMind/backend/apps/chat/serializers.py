from __future__ import annotations

from rest_framework import serializers
from rest_framework.exceptions import APIException

from apps.styles.models import StyleProfile
from core.llm import LLMError
from core.prompts import PromptEngineError

from .models import ChatSession
from .services import PersonaGenerationError, PersonaService


class PersonaGenerationUnavailable(APIException):
    status_code = 503
    default_detail = "人设生成服务暂时不可用，请稍后重试。"
    default_code = "persona_generation_unavailable"


class ChatGenerationUnavailable(APIException):
    status_code = 503
    default_detail = "消息生成服务暂时不可用，请稍后重试。"
    default_code = "chat_generation_unavailable"


class ChatMessageRequestSerializer(serializers.Serializer):
    content = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=2000,
    )
    regenerate = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if not attrs.get("regenerate") and not attrs.get("content"):
            raise serializers.ValidationError({"content": "请输入对方说的话。"})
        return attrs


class ChatMessageResponseSerializer(serializers.Serializer):
    message = serializers.DictField()
    emotion = serializers.ChoiceField(choices=("negative", "neutral"))
    messages = serializers.ListField(child=serializers.DictField())


class ChatSuggestionRequestSerializer(serializers.Serializer):
    regenerate = serializers.BooleanField(required=False, default=False)


class ChatSuggestionResponseSerializer(serializers.Serializer):
    suggestions = serializers.ListField(child=serializers.CharField())
    regenerate = serializers.BooleanField()


class ChatSessionSerializer(serializers.ModelSerializer):
    session_id = serializers.UUIDField(source="id", read_only=True)
    style_profile_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )
    style_profile_name = serializers.CharField(
        source="style_profile.name",
        read_only=True,
        default="",
    )
    scene_label = serializers.CharField(source="get_scene_display", read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = (
            "session_id",
            "scene",
            "scene_label",
            "relationship",
            "goal",
            "persona",
            "messages",
            "message_count",
            "style_profile_id",
            "style_profile_name",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_message_count(self, obj) -> int:
        return len(obj.messages)


class ChatSessionCreateSerializer(serializers.Serializer):
    scene = serializers.ChoiceField(choices=ChatSession.Scene.choices)
    relationship = serializers.CharField(max_length=120)
    goal = serializers.CharField(max_length=255)
    style_profile_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_style_profile_id(self, value):
        if value is None:
            return None
        request = self.context["request"]
        profile = StyleProfile.objects.filter(id=value, user=request.user).first()
        if profile is None:
            raise serializers.ValidationError("风格档案不存在或不属于当前用户。")
        return profile

    def create(self, validated_data):
        request = self.context["request"]
        profile = validated_data.pop("style_profile_id", None)
        try:
            persona = PersonaService().generate(
                user_id=request.user.id,
                scene=validated_data["scene"],
                relationship=validated_data["relationship"],
                goal=validated_data["goal"],
                user_style=profile.description if profile else "",
            )
        except (LLMError, PromptEngineError, PersonaGenerationError) as exc:
            raise PersonaGenerationUnavailable() from exc

        return ChatSession.objects.create(
            user=request.user,
            style_profile=profile,
            persona=persona,
            messages=[],
            **validated_data,
        )
