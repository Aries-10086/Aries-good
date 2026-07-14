from django.urls import path

from .views import StyleProfileDetailView, StyleProfileListCreateView


urlpatterns = [
    path("profiles", StyleProfileListCreateView.as_view(), name="style-profile-list"),
    path(
        "profiles/<uuid:profile_id>",
        StyleProfileDetailView.as_view(),
        name="style-profile-detail",
    ),
]
