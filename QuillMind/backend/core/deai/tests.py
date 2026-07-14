from __future__ import annotations

import json
from pathlib import Path

from django.test import SimpleTestCase

from .retry import generate_with_deai_retry
from .rules import build_warnings, detect_ai_flavor


EVAL_PATH = Path(__file__).resolve().parents[4] / "docs" / "eval" / "deai_samples.json"


class DeAIRulesTests(SimpleTestCase):
    def test_detects_blacklist_terms_without_rewriting_source(self):
        text = "在当今环境下，要用技术赋能业务，并把数据当成核心抓手。"

        score, hits = detect_ai_flavor(text)

        self.assertGreater(score, 0.7)
        self.assertEqual(text, "在当今环境下，要用技术赋能业务，并把数据当成核心抓手。")
        self.assertEqual({hit.matched for hit in hits}, {"在当今", "赋能", "抓手"})
        self.assertEqual(len(build_warnings(hits)), 3)

    def test_natural_text_has_low_score(self):
        score, hits = detect_ai_flavor("这句话太长了，拆成两句读起来会轻松一点。")

        self.assertLess(score, 0.3)
        self.assertEqual(hits, [])

    def test_evaluation_dataset_meets_score_thresholds(self):
        payload = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
        ai_scores = [
            detect_ai_flavor(sample["text"])[0]
            for sample in payload["samples"]
            if sample["label"] == "ai"
        ]
        human_scores = [
            detect_ai_flavor(sample["text"])[0]
            for sample in payload["samples"]
            if sample["label"] == "human"
        ]

        self.assertEqual(len(ai_scores), 20)
        self.assertEqual(len(human_scores), 20)
        self.assertGreater(sum(ai_scores) / len(ai_scores), 0.7)
        self.assertLess(sum(human_scores) / len(human_scores), 0.3)


class DeAIRetryTests(SimpleTestCase):
    def test_retries_with_higher_temperature_and_next_template(self):
        outputs = [
            "在当今时代，要以创新赋能业务，把平台作为抓手。",
            "这个版本直接说明用户遇到的问题和准备怎么改。",
        ]
        calls = []

        def generator(**kwargs):
            calls.append(kwargs)
            return outputs[len(calls) - 1]

        result = generate_with_deai_retry(
            generator,
            threshold=0.7,
            template_versions=("v1.0.0", "v1.1.0"),
            topic="测试",
        )

        self.assertTrue(result.accepted)
        self.assertEqual(len(result.attempts), 2)
        self.assertEqual(calls[0]["temperature"], 0.7)
        self.assertEqual(calls[1]["temperature"], 0.85)
        self.assertEqual(calls[0]["template_version"], "v1.0.0")
        self.assertEqual(calls[1]["template_version"], "v1.1.0")
        self.assertEqual(calls[1]["topic"], "测试")

    def test_stops_after_two_retries(self):
        calls = []

        def generator(**kwargs):
            calls.append(kwargs)
            return "综上所述，要用技术赋能业务，以数据为抓手推动高质量发展。"

        result = generate_with_deai_retry(generator, threshold=0.7)

        self.assertFalse(result.accepted)
        self.assertEqual(len(calls), 3)
        self.assertEqual(len(result.attempts), 3)
