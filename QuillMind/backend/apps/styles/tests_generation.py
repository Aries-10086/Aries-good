from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.urls import resolve, reverse
from rest_framework.test import APIRequestFactory, force_authenticate

from .generation import StyleGenerationService, StyleGenerationTimeout
from .models import GenerationRecord
from .views import GenerationFeedbackView, GenerationHistoryView, StyleGenerateView


class FakePromptEngine:
    def __init__(self):
        self.contexts = []

    def render(self, module, **context):
        self.contexts.append({"module": module, **context})
        return f"prompt-{len(self.contexts)}"


class FakeGateway:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def stream(self, prompt, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        yield from self.outputs[len(self.calls) - 1]


class FakeEmbeddingProvider:
    def __init__(self, vectors):
        self.vectors = list(vectors)
        self.calls = []

    def embed(self, texts, *, timeout=None):
        self.calls.append(texts)
        return [self.vectors[len(self.calls) - 1]]


class StyleGenerationServiceTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id=uuid.uuid4())
        self.profile = SimpleNamespace(
            id=uuid.uuid4(),
            user_id=self.user.id,
            style_vector=[1.0, 0.0],
            description="短句、自然、口语化",
            features={
                "average_sentence_length": 12,
                "top_words": [{"word": "其实", "count": 3}],
            },
            samples=["这是第一篇风格参考样本。" * 20, "这是第二篇风格参考样本。" * 20],
        )

    @patch("apps.styles.generation.GenerationRecord.objects.create")
    def test_retries_low_similarity_then_saves_accepted_result(self, create_mock):
        record = SimpleNamespace(id=uuid.uuid4(), result="第二版")
        create_mock.return_value = record
        gateway = FakeGateway([["第一版"], ["第二版"]])
        prompt_engine = FakePromptEngine()
        embedding = FakeEmbeddingProvider([[0.0, 1.0], [1.0, 0.0]])
        service = StyleGenerationService(
            llm_gateway=gateway,
            prompt_engine=prompt_engine,
            embedding_provider=embedding,
            detector=lambda text: (0.1, []),
        )

        result = service.generate(
            user=self.user,
            profile=self.profile,
            topic="写一封邀请",
            keywords=["周末", "咖啡"],
            tone_slider=80,
        )

        self.assertEqual(len(result.attempts), 2)
        self.assertFalse(result.attempts[0].quality.accepted)
        self.assertTrue(result.attempts[1].quality.accepted)
        self.assertGreater(gateway.calls[1]["temperature"], gateway.calls[0]["temperature"])
        self.assertEqual(
            prompt_engine.contexts[0]["style_features"]["高频词"],
            "其实",
        )
        self.assertEqual(len(prompt_engine.contexts[0]["style_samples"]), 2)
        self.assertIn("上一次未达标", prompt_engine.contexts[1]["constraints"][-1])
        self.assertIn("周末、咖啡", prompt_engine.contexts[0]["constraints"][-1])
        self.assertEqual(create_mock.call_args.kwargs["result"], "第二版")
        self.assertEqual(create_mock.call_args.kwargs["quality"]["attempt_count"], 2)
        self.assertEqual(
            create_mock.call_args.kwargs["quality"]["keywords"],
            ["周末", "咖啡"],
        )

    @patch("apps.styles.generation.GenerationRecord.objects.create")
    def test_stops_after_two_retries(self, create_mock):
        create_mock.return_value = SimpleNamespace(id=uuid.uuid4(), result="第三版")
        service = StyleGenerationService(
            llm_gateway=FakeGateway([["第一版"], ["第二版"], ["第三版"]]),
            prompt_engine=FakePromptEngine(),
            embedding_provider=FakeEmbeddingProvider(
                [[0.0, 1.0], [0.0, 1.0], [0.0, 1.0]]
            ),
            detector=lambda text: (0.9, []),
        )

        result = service.generate(
            user=self.user,
            profile=self.profile,
            topic="测试",
        )

        self.assertEqual(len(result.attempts), 3)
        self.assertFalse(result.attempts[-1].quality.accepted)
        create_mock.assert_called_once()

    @patch("apps.styles.generation.GenerationRecord.objects.create")
    def test_stream_emits_retry_reset_and_complete_events(self, create_mock):
        record_id = uuid.uuid4()
        create_mock.return_value = SimpleNamespace(
            id=record_id,
            result="通过",
            quality={"accepted": True},
        )
        service = StyleGenerationService(
            llm_gateway=FakeGateway([["未", "通过"], ["通", "过"]]),
            prompt_engine=FakePromptEngine(),
            embedding_provider=FakeEmbeddingProvider([[0.0, 1.0], [1.0, 0.0]]),
            detector=lambda text: (0.1, []),
        )

        events = list(
            service.stream(
                user=self.user,
                profile=self.profile,
                topic="测试",
            )
        )

        event_names = [event["event"] for event in events]
        self.assertIn("retry", event_names)
        second_attempt = [
            event
            for event in events
            if event["event"] == "attempt" and event["data"]["attempt"] == 2
        ][0]
        self.assertTrue(second_attempt["data"]["reset"])
        self.assertEqual(events[-1]["event"], "complete")
        self.assertEqual(events[-1]["data"]["generation_id"], str(record_id))

    @patch("apps.styles.generation.GenerationRecord.objects.create")
    def test_stops_retry_when_total_time_budget_is_exhausted(self, create_mock):
        clock_values = iter([0, 0, 0, 0, 0, 31])
        service = StyleGenerationService(
            llm_gateway=FakeGateway([["未通过"], ["不应生成"]]),
            prompt_engine=FakePromptEngine(),
            embedding_provider=FakeEmbeddingProvider([[0.0, 1.0]]),
            detector=lambda text: (0.1, []),
            clock=lambda: next(clock_values),
        )

        with self.assertRaises(StyleGenerationTimeout):
            service.generate(
                user=self.user,
                profile=self.profile,
                topic="测试时间预算",
            )

        create_mock.assert_not_called()


class StyleGenerationApiTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = SimpleNamespace(id=uuid.uuid4(), is_authenticated=True)
        self.profile = SimpleNamespace(
            id=uuid.uuid4(),
            user_id=self.user.id,
            style_vector=[1.0],
        )

    def test_generation_routes_resolve(self):
        self.assertIs(resolve("/api/v1/styles/generate").func.view_class, StyleGenerateView)
        self.assertIs(
            resolve("/api/v1/styles/generations").func.view_class,
            GenerationHistoryView,
        )
        feedback_url = reverse(
            "style-generation-feedback",
            kwargs={"generation_id": uuid.uuid4()},
        )
        self.assertIs(resolve(feedback_url).func.view_class, GenerationFeedbackView)

    @patch("apps.styles.views.StyleGenerationService")
    @patch("apps.styles.views.get_object_or_404")
    def test_sse_response_contains_named_events(self, get_object_mock, service_class):
        get_object_mock.return_value = self.profile
        service_class.return_value.stream.return_value = iter(
            [
                {"event": "token", "data": {"attempt": 1, "text": "你好"}},
                {
                    "event": "complete",
                    "data": {"generation_id": str(uuid.uuid4())},
                },
            ]
        )
        request = self.factory.post(
            "/api/v1/styles/generate?stream=true",
            {
                "profile_id": str(self.profile.id),
                "topic": "写一封邀请",
                "tone_slider": 60,
            },
            format="json",
        )
        force_authenticate(request, user=self.user)

        response = StyleGenerateView.as_view()(request)
        body = b"".join(response.streaming_content).decode("utf-8")

        self.assertEqual(response["Content-Type"], "text/event-stream")
        self.assertIn("event: token", body)
        self.assertIn("event: complete", body)
        self.assertIn(json.dumps("你好", ensure_ascii=False), body)
        get_object_mock.assert_called_once()
        self.assertEqual(get_object_mock.call_args.kwargs["user"], self.user)

    @patch("apps.styles.views.get_object_or_404")
    def test_generation_rejects_profile_without_style_vector(self, get_object_mock):
        get_object_mock.return_value = SimpleNamespace(
            id=self.profile.id,
            user_id=self.user.id,
            style_vector=[],
        )
        request = self.factory.post(
            "/api/v1/styles/generate",
            {
                "profile_id": str(self.profile.id),
                "topic": "测试",
            },
            format="json",
        )
        force_authenticate(request, user=self.user)

        response = StyleGenerateView.as_view()(request)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["detail"].code, "style_profile_not_ready")

    @patch("apps.styles.views.GenerationRecord.objects.filter")
    def test_history_queryset_is_owner_scoped(self, filter_mock):
        queryset = Mock()
        filter_mock.return_value = queryset
        queryset.select_related.return_value = queryset
        queryset.order_by.return_value = queryset
        view = GenerationHistoryView()
        view.request = SimpleNamespace(user=self.user)

        self.assertIs(view.get_queryset(), queryset)
        filter_mock.assert_called_once_with(user=self.user)

    @patch("apps.styles.views.get_object_or_404")
    def test_feedback_is_saved_on_owned_record(self, get_object_mock):
        record = GenerationRecord(
            id=uuid.uuid4(),
            result="生成结果",
            model_name="test-model",
            quality={},
        )
        get_object_mock.return_value = record
        request = self.factory.post(
            f"/api/v1/styles/generations/{record.id}/feedback",
            {"feedback": "up"},
            format="json",
        )
        force_authenticate(request, user=self.user)

        with patch.object(record, "save") as save_mock:
            response = GenerationFeedbackView.as_view()(request, generation_id=record.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(record.feedback, "up")
        save_mock.assert_called_once_with(update_fields=("feedback", "updated_at"))
        self.assertEqual(get_object_mock.call_args.kwargs["user"], self.user)
