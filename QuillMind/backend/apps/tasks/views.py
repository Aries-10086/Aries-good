import uuid

from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AsyncTask
from .serializers import AsyncTaskSerializer
from .tasks import ping_task


class TaskDetailView(RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AsyncTaskSerializer
    lookup_field = "task_id"
    lookup_url_kwarg = "task_id"

    def get_queryset(self):
        return AsyncTask.objects.filter(user=self.request.user)


class PingTaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AsyncTaskSerializer

    @extend_schema(responses={202: AsyncTaskSerializer})
    def post(self, request):
        task_id = str(uuid.uuid4())
        task = AsyncTask.objects.create(
            task_id=task_id,
            user=request.user,
            type="ping",
            status=AsyncTask.Status.PENDING,
        )
        ping_task.apply_async(args=[task.task_id], task_id=task.task_id)
        return Response(AsyncTaskSerializer(task).data, status=status.HTTP_202_ACCEPTED)
