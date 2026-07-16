from django.urls import path

from .views import (
    GenerationFeedbackView,
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
    path(
        "generations/<uuid:generation_id>/feedback",
        GenerationFeedbackView.as_view(),
        name="style-generation-feedback",
    ),
    path("profiles", StyleProfileListCreateView.as_view(), name="style-profile-list"),
    path(
        "profiles/<uuid:profile_id>",
        StyleProfileDetailView.as_view(),
        name="style-profile-detail",
    ),
]
