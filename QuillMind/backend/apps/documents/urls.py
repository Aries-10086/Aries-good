from django.urls import path

from .views import (
    DocumentReviewCreateView,
    DocumentReviewDetailView,
    DocumentReviewListView,
    DocumentReviewTaskStatusView,
)


urlpatterns = [
    path("review", DocumentReviewCreateView.as_view(), name="document-review-create"),
    path(
        "review/<str:task_id>",
        DocumentReviewTaskStatusView.as_view(),
        name="document-review-task",
    ),
    path("reviews", DocumentReviewListView.as_view(), name="document-review-list"),
    path(
        "reviews/<uuid:review_id>",
        DocumentReviewDetailView.as_view(),
        name="document-review-detail",
    ),
]
