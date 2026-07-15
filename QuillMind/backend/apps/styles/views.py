import json

from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status
from rest_framework.generics import (
    GenericAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from core.llm import LLMError
from core.prompts import PromptEngineError
from core.style import EmbeddingError

from .generation import StyleGenerationService
from .models import GenerationRecord, StyleProfile
from .serializers import (
    GenerationRecordSerializer,
    StyleGenerationRequestSerializer,
    StyleGenerationUnavailable,
    StyleProfileDetailSerializer,
    StyleProfileListSerializer,
    StyleProfileWriteSerializer,
)


class StyleProfilePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class StyleProfileListCreateView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StyleProfilePagination

    def get_queryset(self):
        return StyleProfile.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return StyleProfileWriteSerializer
        return StyleProfileListSerializer

    @extend_schema(
        request=StyleProfileWriteSerializer,
        responses={201: StyleProfileDetailSerializer},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save(user=request.user)
        response = StyleProfileDetailSerializer(profile)
        return Response(response.data, status=status.HTTP_201_CREATED)


class StyleProfileDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"
    lookup_url_kwarg = "profile_id"

    def get_queryset(self):
        return StyleProfile.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method == "PUT":
            return StyleProfileWriteSerializer
        return StyleProfileDetailSerializer

    @extend_schema(
        request=StyleProfileWriteSerializer,
        responses={200: StyleProfileDetailSerializer},
    )
    def put(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = StyleProfileWriteSerializer(
            instance,
            data=request.data,
            partial=partial,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return Response(StyleProfileDetailSerializer(profile).data)


class StyleGenerateView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StyleGenerationRequestSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="stream",
                type=bool,
                location=OpenApiParameter.QUERY,
                description="为 true 时返回 text/event-stream。",
            )
        ],
        request=StyleGenerationRequestSerializer,
        responses={200: GenerationRecordSerializer},
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        profile = get_object_or_404(
            StyleProfile,
            id=data["profile_id"],
            user=request.user,
        )
        service = StyleGenerationService()

        if request.query_params.get("stream", "").lower() == "true":
            response = StreamingHttpResponse(
                self._sse_events(
                    service.stream(
                        user=request.user,
                        profile=profile,
                        topic=data["topic"],
                        outline=data["outline"],
                        tone_slider=data["tone_slider"],
                    )
                ),
                content_type="text/event-stream",
            )
            response["Cache-Control"] = "no-cache"
            response["X-Accel-Buffering"] = "no"
            return response

        try:
            result = service.generate(
                user=request.user,
                profile=profile,
                topic=data["topic"],
                outline=data["outline"],
                tone_slider=data["tone_slider"],
            )
        except (EmbeddingError, LLMError, PromptEngineError) as exc:
            raise StyleGenerationUnavailable() from exc
        return Response(GenerationRecordSerializer(result.record).data)

    def _sse_events(self, events):
        try:
            for event in events:
                payload = json.dumps(event["data"], ensure_ascii=False)
                yield f"event: {event['event']}\ndata: {payload}\n\n"
        except Exception:
            payload = json.dumps(
                {"detail": "生成失败，请稍后重试。"},
                ensure_ascii=False,
            )
            yield f"event: error\ndata: {payload}\n\n"


class GenerationHistoryView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = GenerationRecordSerializer
    pagination_class = StyleProfilePagination

    def get_queryset(self):
        return (
            GenerationRecord.objects.filter(user=self.request.user)
            .select_related("style")
            .order_by("-created_at")
        )
