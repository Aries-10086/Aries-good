import uuid

from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tasks.models import AsyncTask
from apps.tasks.serializers import AsyncTaskSerializer

from .models import DocumentReview
from .serializers import (
    DocumentReviewCreateSerializer,
    DocumentReviewDetailSerializer,
    DocumentReviewSummarySerializer,
    DocumentReviewTaskResponseSerializer,
)
from .services import (
    DocumentReviewValidationError,
    normalize_review_text,
    read_review_upload,
)
from .tasks import review_document_task


class DocumentReviewPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class DocumentReviewCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DocumentReviewCreateSerializer

    @extend_schema(
        request=DocumentReviewCreateSerializer,
        responses={202: DocumentReviewTaskResponseSerializer},
    )
    def post(self, request):
        serializer = DocumentReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            if data.get("file"):
                raw_text = read_review_upload(data["file"])
            else:
                raw_text = normalize_review_text(data["text"])
        except DocumentReviewValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        review = DocumentReview.objects.create(
            user=request.user,
            raw_text=raw_text,
            doc_type=data["doc_type"],
        )
        task_id = str(uuid.uuid4())
        task = AsyncTask.objects.create(
            task_id=task_id,
            user=request.user,
            type="document_review",
            status=AsyncTask.Status.PENDING,
            result={"review_id": str(review.id)},
        )
        review_document_task.apply_async(
            args=[task.task_id, str(review.id), data.get("model_version") or None],
            task_id=task.task_id,
        )
        return Response(
            {
                "task_id": task.task_id,
                "review_id": review.id,
                "status": task.status,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class DocumentReviewTaskStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DocumentReviewTaskResponseSerializer

    @extend_schema(responses={200: DocumentReviewTaskResponseSerializer})
    def get(self, request, task_id):
        task = AsyncTask.objects.filter(
            user=request.user,
            task_id=task_id,
            type="document_review",
        ).first()
        if task is None:
            return Response({"detail": "任务不存在。"}, status=status.HTTP_404_NOT_FOUND)

        payload = AsyncTaskSerializer(task).data
        review_id = (task.result or {}).get("review_id")
        if task.status == AsyncTask.Status.SUCCESS and review_id:
            review = DocumentReview.objects.filter(
                id=review_id,
                user=request.user,
            ).first()
            if review is not None:
                payload["review"] = DocumentReviewDetailSerializer(review).data
                payload["review_id"] = review.id
        elif review_id:
            payload["review_id"] = review_id
        return Response(payload)


class DocumentReviewListView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DocumentReviewSummarySerializer
    pagination_class = DocumentReviewPagination

    def get_queryset(self):
        return DocumentReview.objects.filter(user=self.request.user)


class DocumentReviewDetailView(RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DocumentReviewDetailSerializer
    lookup_field = "id"
    lookup_url_kwarg = "review_id"

    def get_queryset(self):
        return DocumentReview.objects.filter(user=self.request.user)
