from django.urls import path

from .views import (
    ChatMessageView,
    ChatSessionDetailView,
    ChatSessionListCreateView,
    ChatSuggestionView,
)


urlpatterns = [
    path("sessions", ChatSessionListCreateView.as_view(), name="chat-session-list"),
    path(
        "sessions/<uuid:session_id>",
        ChatSessionDetailView.as_view(),
        name="chat-session-detail",
    ),
    path(
        "sessions/<uuid:session_id>/messages",
        ChatMessageView.as_view(),
        name="chat-session-message",
    ),
    path(
        "sessions/<uuid:session_id>/suggestions",
        ChatSuggestionView.as_view(),
        name="chat-session-suggestions",
    ),
]
