from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView, ListCreateAPIView, RetrieveDestroyAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from core.llm import LLMError
from core.prompts import PromptEngineError

from .messaging import ChatMessageService
from .models import ChatSession
from .serializers import (
    ChatGenerationUnavailable,
    ChatMessageRequestSerializer,
    ChatMessageResponseSerializer,
    ChatSessionCreateSerializer,
    ChatSessionSerializer,
    ChatSuggestionRequestSerializer,
    ChatSuggestionResponseSerializer,
)


class ChatSessionPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ChatSessionListCreateView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ChatSessionPagination

    def get_queryset(self):
        return (
            ChatSession.objects.filter(user=self.request.user)
            .select_related("style_profile")
            .order_by("-updated_at")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ChatSessionCreateSerializer
        return ChatSessionSerializer

    @extend_schema(
        request=ChatSessionCreateSerializer,
        responses={201: ChatSessionSerializer},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = serializer.save()
        return Response(
            ChatSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )


class ChatSessionDetailView(RetrieveDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChatSessionSerializer
    lookup_field = "id"
    lookup_url_kwarg = "session_id"

    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user).select_related(
            "style_profile"
        )


class OwnedChatSessionMixin:
    def get_session(self):
        return get_object_or_404(
            ChatSession,
            id=self.kwargs["session_id"],
            user=self.request.user,
            status=ChatSession.Status.ACTIVE,
        )


class ChatMessageView(OwnedChatSessionMixin, GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChatMessageRequestSerializer

    @extend_schema(
        request=ChatMessageRequestSerializer,
        responses={200: ChatMessageResponseSerializer},
    )
    def post(self, request, session_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        session = self.get_session()

        try:
            reply = ChatMessageService().reply(
                session=session,
                content=data.get("content"),
                regenerate=data["regenerate"],
            )
        except (LLMError, PromptEngineError, ValueError) as exc:
            raise ChatGenerationUnavailable() from exc

        return Response(
            {
                "message": reply.message,
                "emotion": reply.emotion,
                "messages": session.messages,
            }
        )


class ChatSuggestionView(OwnedChatSessionMixin, GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChatSuggestionRequestSerializer

    @extend_schema(
        request=ChatSuggestionRequestSerializer,
        responses={200: ChatSuggestionResponseSerializer},
    )
    def post(self, request, session_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        regenerate = serializer.validated_data["regenerate"]
        session = self.get_session()

        try:
            suggestions = ChatMessageService().suggestions(
                session=session,
                regenerate=regenerate,
            )
        except (LLMError, PromptEngineError, ValueError) as exc:
            raise ChatGenerationUnavailable() from exc

        return Response(
            {
                "suggestions": suggestions,
                "regenerate": regenerate,
            }
        )
