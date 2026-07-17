from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.generics import ListCreateAPIView, RetrieveDestroyAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import ChatSession
from .serializers import ChatSessionCreateSerializer, ChatSessionSerializer


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
