from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch
import uuid

from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.tasks.models import AsyncTask

from .models import DocumentReview
from .serializers import build_text_preview
from .services import DocumentReviewService, enrich_risks, normalize_review_text
from .views import DocumentReviewCreateView, DocumentReviewTaskStatusView


class DocumentReviewServiceTests(SimpleTestCase):
    def test_enrich_risks_adds_quote_and_report_fields(self):
        raw_text = "服务费用在任何情况下均不退还。"
        risks = enrich_risks(
            raw_text,
            [
                {
                    "type": "模糊条款",
                    "score": 0.9,
                    "start": 0,
                    "end": 14,
                    "level": "高",
                }
            ],
        )

        self.assertEqual(risks[0]["quote"], raw_text[:14])
        self.assertIn("模糊条款", risks[0]["reason"])
        self.assertIn("suggestion", risks[0])

    def test_normalize_review_text_rejects_empty_and_long_input(self):
        with self.assertRaises(ValueError):
            normalize_review_text("   ")
        with self.assertRaises(ValueError):
            normalize_review_text("文" * 20_001)

    def test_build_text_preview_truncates_long_text(self):
        preview = build_text_preview("这是一段" * 100)

        self.assertLessEqual(len(preview), 241)
        self.assertTrue(preview.endswith("…"))

    @patch("apps.documents.services.generate_with_deai_retry")
    def test_review_persists_risks_and_report(self, retry_mock):
        retry_mock.return_value = SimpleNamespace(text="报告正文", accepted=True)
        review = DocumentReview(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            raw_text="费用永不退还。",
            doc_type=DocumentReview.DocType.CONTRACT,
        )

        class FakeReviewer:
            def review(self, text, **kwargs):
                return [
                    {
                        "type": "退款条款",
                        "score": 0.88,
                        "start": 0,
                        "end": 6,
                        "level": "高",
                    }
                ]

        class FakeGateway:
            def complete(self, prompt, **kwargs):
                return SimpleNamespace(text="不应直接返回")

        class FakePromptEngine:
            def render(self, module, **context):
                return f"{module}-{context['document_type']}"

        service = DocumentReviewService(
            reviewer=FakeReviewer(),
            llm_gateway=FakeGateway(),
            prompt_engine=FakePromptEngine(),
        )

        review.save = lambda update_fields=None: None
        result = service.review(review=review, user_id=review.user_id)

        self.assertEqual(result.risks[0]["quote"], "费用永不退还")
        self.assertEqual(result.report, "报告正文")


class DocumentReviewViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = SimpleNamespace(id=uuid.uuid4(), is_authenticated=True)

    @patch("apps.documents.views.transaction.atomic", return_value=nullcontext())
    @patch("apps.documents.views.review_document_task")
    @patch("apps.documents.views.transaction.on_commit", side_effect=lambda callback: callback())
    def test_create_review_returns_task_and_review_ids(
        self,
        _on_commit_mock,
        task_mock,
        _atomic_mock,
    ):
        request = self.factory.post(
            "/api/v1/documents/review",
            {"text": "费用在任何情况下均不退还。", "doc_type": "contract"},
            format="json",
        )
        force_authenticate(request, user=self.user)

        with patch.object(DocumentReview.objects, "create") as create_mock:
            review = SimpleNamespace(id=uuid.uuid4())
            create_mock.return_value = review
            with patch.object(AsyncTask.objects, "create") as task_create_mock:
                task = SimpleNamespace(
                    task_id=str(uuid.uuid4()),
                    status=AsyncTask.Status.PENDING,
                )
                task_create_mock.return_value = task
                response = DocumentReviewCreateView.as_view()(request)

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["review_id"], review.id)
        task_mock.apply_async.assert_called_once()

    @patch("apps.documents.views.DocumentReviewResultSerializer")
    @patch("apps.documents.views.DocumentReview.objects.filter")
    @patch("apps.documents.views.AsyncTask.objects.filter")
    def test_task_status_includes_review_when_success(
        self,
        task_filter_mock,
        review_filter_mock,
        serializer_mock,
    ):
        review_id = uuid.uuid4()
        task = SimpleNamespace(
            task_id="task-1",
            type="document_review",
            status=AsyncTask.Status.SUCCESS,
            result={"review_id": str(review_id)},
            error="",
            id=review_id,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        task_filter_mock.return_value.first.return_value = task
        review = SimpleNamespace(
            id=review_id,
            doc_type="contract",
            raw_text="测试文本",
            risks=[],
            report="报告",
            model_version="v1.0.0",
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        review_filter_mock.return_value.first.return_value = review
        serializer_mock.return_value.data = {"report": "报告"}
        request = self.factory.get("/api/v1/documents/review/task-1")
        force_authenticate(request, user=self.user)

        response = DocumentReviewTaskStatusView.as_view()(request, task_id="task-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["review"]["report"], "报告")
