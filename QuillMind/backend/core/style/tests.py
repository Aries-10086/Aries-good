from __future__ import annotations

from django.test import SimpleTestCase

from .describe import describe_style
from .embedding import BaseEmbeddingProvider, average_vectors
from .features import extract_features
from .pipeline import extract_style
from .preprocess import preprocess_text
from .similarity import cosine_similarity


class FakeEmbeddingProvider(BaseEmbeddingProvider):
    def embed(
        self,
        texts: list[str],
        *,
        timeout: float | None = None,
    ) -> list[list[float]]:
        vectors = []
        for text in texts:
            if any(word in text for word in ("代码", "接口", "日志", "测试")):
                vectors.append([1.0, 0.1, 0.0])
            else:
                vectors.append([0.0, 0.1, 1.0])
        return vectors


class StylePreprocessTests(SimpleTestCase):
    def test_removes_html_scripts_and_normalizes_whitespace(self):
        source = "<p>你好&nbsp; 世界</p><script>ignore()</script><div>第二段</div>"

        cleaned = preprocess_text(source)

        self.assertEqual(cleaned, "你好 世界\n第二段")


class StyleFeatureTests(SimpleTestCase):
    def test_extracts_sentence_particles_and_punctuation_features(self):
        features = extract_features(
            [
                "其实今天挺忙的吧！不过代码已经写完了。",
                "反正先跑测试嘛……有问题再看日志！",
            ]
        )

        self.assertEqual(features["sample_count"], 2)
        self.assertGreater(features["average_sentence_length"], 0)
        self.assertGreaterEqual(features["tone_particles"]["其实"]["count"], 1)
        self.assertGreaterEqual(features["tone_particles"]["反正"]["count"], 1)
        self.assertGreater(features["punctuation_habits"]["exclamation_ratio"], 0)
        self.assertLessEqual(len(features["top_words"]), 30)

    def test_description_is_ready_for_prompt_injection(self):
        features = extract_features(["其实别急吧！先把接口日志发我。"])

        description = describe_style(features)

        self.assertIn("句", description)
        self.assertIn("其实", description)
        self.assertIn("高频用词", description)


class StyleEmbeddingTests(SimpleTestCase):
    def test_averages_vectors_and_calculates_cosine_similarity(self):
        averaged = average_vectors([[1.0, 0.0], [0.8, 0.2]])

        self.assertEqual(averaged, [0.9, 0.1])
        self.assertGreater(cosine_similarity([1.0, 0.1], [0.9, 0.2]), 0.8)
        self.assertLess(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.5)

    def test_extract_style_returns_vector_features_and_description(self):
        result = extract_style(
            [
                "<p>这段代码先别改，看看日志。</p>",
                "接口报错了吧？先补个测试。",
                "反正代码能跑，明天再整理。",
            ],
            embedding_provider=FakeEmbeddingProvider(),
        )

        self.assertEqual(len(result["vector"]), 3)
        self.assertEqual(result["features"]["sample_count"], 3)
        self.assertTrue(result["description"])

    def test_same_author_profiles_are_closer_than_different_authors(self):
        provider = FakeEmbeddingProvider()
        author_a = extract_style(
            ["代码刚写完。", "接口今天有点慢。", "先看日志吧。"],
            embedding_provider=provider,
        )
        author_a_later = extract_style(
            ["测试先跑一遍。", "日志里能看到报错。", "这个接口明天修。"],
            embedding_provider=provider,
        )
        author_b = extract_style(
            ["花开得正好。", "晚风吹过窗台。", "月亮落在水面。"],
            embedding_provider=provider,
        )

        same_author = cosine_similarity(author_a["vector"], author_a_later["vector"])
        different_author = cosine_similarity(author_a["vector"], author_b["vector"])

        self.assertGreater(same_author, 0.8)
        self.assertLess(different_author, 0.5)
