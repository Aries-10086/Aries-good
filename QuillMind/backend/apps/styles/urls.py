from django.urls import path

from .views import (
    GenerationHistoryView,
    StyleGenerateView,
    StyleProfileDetailView,
    StyleProfileListCreateView,
)


urlpatterns = [
    path("generate", StyleGenerateView.as_view(), name="style-generate"),
    path(
        "generations",
        GenerationHistoryView.as_view(),
        name="style-generation-list",
    ),
    path("profiles", StyleProfileListCreateView.as_view(), name="style-profile-list"),
    path(
        "profiles/<uuid:profile_id>",
        StyleProfileDetailView.as_view(),
        name="style-profile-detail",
    ),
]
