from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import StyleProfile
from .serializers import (
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
