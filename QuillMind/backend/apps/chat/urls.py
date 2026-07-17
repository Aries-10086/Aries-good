from django.urls import path

from .views import ChatSessionDetailView, ChatSessionListCreateView


urlpatterns = [
    path("sessions", ChatSessionListCreateView.as_view(), name="chat-session-list"),
    path(
        "sessions/<uuid:session_id>",
        ChatSessionDetailView.as_view(),
        name="chat-session-detail",
    ),
]
