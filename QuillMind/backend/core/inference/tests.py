from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
import time

from django.test import SimpleTestCase

from .document_reviewer import (
    DocumentReviewer,
    InferenceError,
    InferenceUnavailable,
    LLMReviewProvider,
    ONNXReviewProvider,
    merge_risks,
)


class FakeTokenizer:
    is_fast = True

    def __call__(self, text, **kwargs):
        return {
            "input_ids": [
                [101, 1, 2, 0],
                [101, 2, 3, 0],
            ],
            "attention_mask": [
                [1, 1, 1, 0],
                [1, 1, 1, 0],
            ],
            "offset_mapping": [
                [(0, 0), (0, 2), (2, 4), (0, 0)],
                [(0, 0), (2, 4), (4, 6), (0, 0)],
            ],
        }


class FakeSession:
    def __init__(self):
        self.calls = 0

    def get_inputs(self):
        return [
            SimpleNamespace(name="input_ids"),
            SimpleNamespace(name="attention_mask"),
        ]

    def get_modelmeta(self):
        return SimpleNamespace(custom_metadata_map={})

    def run(self, output_names, feed):
        outputs = (
            [
                [5, 0, 0],
                [0, 5, 0],
                [0, 0, 5],
                [5, 0, 0],
            ]
            if self.calls == 0
            else [
                [5, 0, 0],
                [0, 5, 0],
                [0, 0, 5],
                [5, 0, 0],
            ]
        )
        self.calls += 1
        return [[outputs]]


class FakePromptEngine:
    def __init__(self):
        self.context = None

    def render(self, module, **context):
        self.context = {"module": module, **context}
        return "review prompt"


class FakeGateway:
    def __init__(self, text):
        self.text = text
        self.calls = []

    def complete(self, prompt, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        return SimpleNamespace(text=self.text)


def create_model(root: Path, version: str) -> None:
    model_dir = root / version
    model_dir.mkdir(parents=True)
    (model_dir / "model.onnx").write_bytes(b"fake")
    (model_dir / "labels.json").write_text(
        json.dumps(["O", "B-表述歧义:high", "I-表述歧义:high"]),
        encoding="utf-8",
    )


class ONNXReviewProviderTests(SimpleTestCase):
    def test_chunk_inference_merges_overlap_and_returns_sorted_risks(self):
        with TemporaryDirectory() as directory:
            model_root = Path(directory)
            create_model(model_root, "v1.0.0")
            session = FakeSession()
            provider = ONNXReviewProvider(
                model_root=model_root,
                session_factory=lambda path: session,
                tokenizer_factory=lambda path: FakeTokenizer(),
            )

            risks = provider.review("费用永不退还", model_version="v1.0.0")

        self.assertEqual(len(risks), 1)
        self.assertEqual(risks[0]["type"], "表述歧义")
        self.assertEqual(risks[0]["level"], "高")
        self.assertEqual((risks[0]["start"], risks[0]["end"]), (0, 6))
        self.assertGreater(risks[0]["score"], 0.9)
        self.assertEqual(session.calls, 2)

    def test_model_version_loads_and_caches_each_version(self):
        with TemporaryDirectory() as directory:
            model_root = Path(directory)
            create_model(model_root, "blue")
            create_model(model_root, "green")
            loaded = []

            def session_factory(path):
                loaded.append(path.parent.name)
                return FakeSession()

            provider = ONNXReviewProvider(
                model_root=model_root,
                model_version="blue",
                session_factory=session_factory,
                tokenizer_factory=lambda path: FakeTokenizer(),
            )
            provider.review("测试文本内容")
            provider.review("测试文本内容", model_version="green")
            provider.review("测试文本内容", model_version="blue")

        self.assertEqual(loaded, ["blue", "green"])

    def test_invalid_version_cannot_escape_model_root(self):
        provider = ONNXReviewProvider(model_root="/tmp/models")
        with self.assertRaises(InferenceError):
            provider.review("测试", model_version="../secret")

    def test_ten_thousand_characters_complete_under_thirty_seconds(self):
        with TemporaryDirectory() as directory:
            model_root = Path(directory)
            create_model(model_root, "v1.0.0")
            provider = ONNXReviewProvider(
                model_root=model_root,
                session_factory=lambda path: FakeSession(),
                tokenizer_factory=lambda path: FakeTokenizer(),
            )
            started = time.perf_counter()
            risks = provider.review("文" * 10_000)
            elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 30)
        self.assertTrue(risks)
        self.assertEqual(
            set(risks[0]),
            {"type", "score", "start", "end", "level"},
        )

    def test_merge_deduplicates_and_sorts_by_confidence(self):
        risks = merge_risks(
            [
                {"type": "矛盾", "score": 0.7, "start": 4, "end": 8, "level": "中"},
                {"type": "矛盾", "score": 0.9, "start": 6, "end": 10, "level": "高"},
                {"type": "歧义", "score": 0.8, "start": 0, "end": 2, "level": "低"},
            ],
            text_length=20,
        )

        self.assertEqual([risk["type"] for risk in risks], ["矛盾", "歧义"])
        self.assertEqual((risks[0]["start"], risks[0]["end"]), (4, 10))
        self.assertEqual(risks[0]["level"], "高")


class LLMReviewProviderTests(SimpleTestCase):
    def test_llm_baseline_parses_and_normalizes_structured_risks(self):
        prompt_engine = FakePromptEngine()
        gateway = FakeGateway(
            json.dumps(
                {
                    "risks": [
                        {
                            "type": "模糊条款",
                            "score": 1.2,
                            "start": 0,
                            "end": 4,
                            "level": "high",
                        }
                    ]
                }
            )
        )
        provider = LLMReviewProvider(
            llm_gateway=gateway,
            prompt_engine=prompt_engine,
        )

        risks = provider.review(
            "费用另行协商",
            user_id="user-1",
            document_type="合同",
        )

        self.assertEqual(
            risks,
            [
                {
                    "type": "模糊条款",
                    "score": 1.0,
                    "start": 0,
                    "end": 4,
                    "level": "高",
                }
            ],
        )
        self.assertEqual(prompt_engine.context["module"], "documents/review")
        self.assertEqual(prompt_engine.context["document_type"], "合同")
        self.assertEqual(gateway.calls[0]["temperature"], 0.1)

    def test_document_reviewer_falls_back_when_model_is_unavailable(self):
        class MissingONNX:
            def review(self, text, **kwargs):
                raise InferenceUnavailable("missing")

        class Baseline:
            def review(self, text, **kwargs):
                return [
                    {
                        "type": "逻辑漏洞",
                        "score": 0.8,
                        "start": 0,
                        "end": 2,
                        "level": "中",
                    }
                ]

        reviewer = DocumentReviewer(
            onnx_provider=MissingONNX(),
            fallback_provider=Baseline(),
        )

        risks = reviewer.review("测试文本", model_version="v2")

        self.assertEqual(risks[0]["type"], "逻辑漏洞")
