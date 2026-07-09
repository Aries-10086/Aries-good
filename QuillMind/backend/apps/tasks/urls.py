from django.urls import path

from .views import PingTaskView, TaskDetailView


urlpatterns = [
    path("ping/", PingTaskView.as_view(), name="tasks-ping"),
    path("<str:task_id>/", TaskDetailView.as_view(), name="tasks-detail"),
]
