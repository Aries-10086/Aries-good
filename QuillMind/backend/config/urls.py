"""
URL configuration for config project.
"""
from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health_view(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.users.urls")),
    path("api/v1/chat/", include("apps.chat.urls")),
    path("api/v1/health/", health_view),
    path("api/v1/styles/", include("apps.styles.urls")),
    path("api/v1/documents/", include("apps.documents.urls")),
    path("api/v1/tasks/", include("apps.tasks.urls")),
]

if settings.ENABLE_API_DOCS:
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/docs/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
    ]
