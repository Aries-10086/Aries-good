from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.urls import resolve, reverse

from .models import StyleProfile
from .serializers import StyleProfileWriteSerializer
from .services import StyleSampleValidationError, prepare_samples
from .views import StyleProfileDetailView, StyleProfileListCreateView


def long_sample(marker: str) -> str:
    return marker + "这是一段用于提取写作风格的完整中文样本。" * 10


EXTRACTION_RESULT = {
    "vector": [0.1, 0.2, 0.3],
    "features": {"average_sentence_length": 18.5},
    "description": "以中等长度句子为主，表达自然。",
}


class StyleSampleValidationTests(SimpleTestCase):
    def test_requires_at_least_three_samples(self):
        with self.assertRaises(StyleSampleValidationError):
            prepare_samples([long_sample("一"), long_sample("二")])

    def test_requires_one_hundred_non_whitespace_characters(self):
        with self.assertRaises(StyleSampleValidationError):
            prepare_samples(["太短"] * 3)

    def test_accepts_text_and_utf8_file_samples(self):
        uploaded = SimpleUploadedFile(
            "sample.md",
            long_sample("文件").encode("utf-8"),
            content_type="text/markdown",
        )

        samples = prepare_samples(
            [long_sample("文本一"), long_sample("文本二")],
            [uploaded],
        )

        self.assertEqual(len(samples), 3)
        self.assertIn("文件", samples[2])


class StyleProfileSerializerTests(SimpleTestCase):
    @patch("apps.styles.serializers.StyleProfile.objects.create")
    @patch("apps.styles.serializers.extract_profile_data", return_value=EXTRACTION_RESULT)
    def test_create_extracts_and_persists_profile(self, extract_mock, create_mock):
        user = SimpleNamespace(id=uuid.uuid4())
        profile = StyleProfile(
            id=uuid.uuid4(),
            name="我的风格",
            samples=[long_sample("一"), long_sample("二"), long_sample("三")],
            style_vector=EXTRACTION_RESULT["vector"],
            features=EXTRACTION_RESULT["features"],
            description=EXTRACTION_RESULT["description"],
        )
        create_mock.return_value = profile
        serializer = StyleProfileWriteSerializer(
            data={
                "name": "我的风格",
                "samples": [long_sample("一"), long_sample("二"), long_sample("三")],
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        result = serializer.save(user=user)

        self.assertIs(result, profile)
        extract_mock.assert_called_once()
        create_mock.assert_called_once()
        self.assertEqual(create_mock.call_args.kwargs["user"], user)
        self.assertEqual(create_mock.call_args.kwargs["description"], EXTRACTION_RESULT["description"])

    @patch("apps.styles.serializers.extract_profile_data", return_value=EXTRACTION_RESULT)
    def test_update_appends_samples_and_reextracts(self, extract_mock):
        profile = StyleProfile(
            id=uuid.uuid4(),
            name="旧名称",
            samples=[long_sample("一"), long_sample("二"), long_sample("三")],
            style_vector=[0.0],
            features={},
            description="",
        )
        serializer = StyleProfileWriteSerializer(
            profile,
            data={"name": "新名称", "samples": [long_sample("追加")]},
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        with patch.object(profile, "save") as save_mock:
            result = serializer.save()

        self.assertEqual(result.name, "新名称")
        self.assertEqual(len(result.samples), 4)
        self.assertEqual(result.style_vector, EXTRACTION_RESULT["vector"])
        extract_mock.assert_called_once()
        save_mock.assert_called_once()


class StyleProfileRoutingTests(SimpleTestCase):
    def test_routes_resolve_to_profile_views(self):
        list_match = resolve("/api/v1/styles/profiles")
        detail_url = reverse(
            "style-profile-detail",
            kwargs={"profile_id": uuid.uuid4()},
        )
        detail_match = resolve(detail_url)

        self.assertIs(list_match.func.view_class, StyleProfileListCreateView)
        self.assertIs(detail_match.func.view_class, StyleProfileDetailView)

    @patch("apps.styles.views.StyleProfile.objects.filter")
    def test_querysets_are_limited_to_current_user(self, filter_mock):
        user = SimpleNamespace(id=uuid.uuid4())

        for view_class in (StyleProfileListCreateView, StyleProfileDetailView):
            view = view_class()
            view.request = SimpleNamespace(user=user)
            view.get_queryset()

        self.assertEqual(filter_mock.call_count, 2)
        for call in filter_mock.call_args_list:
            self.assertEqual(call.kwargs, {"user": user})
