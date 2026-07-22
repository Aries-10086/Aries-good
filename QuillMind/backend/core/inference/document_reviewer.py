from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
from typing import Any, Callable, Iterable

from django.conf import settings

from core.llm import gateway as default_gateway
from core.prompts import engine as default_prompt_engine


VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
LEVEL_RANK = {"低": 1, "中": 2, "高": 3}
LEVEL_ALIASES = {
    "low": "低",
    "medium": "中",
    "mid": "中",
    "high": "高",
    "低": "低",
    "中": "中",
    "高": "高",
}


class InferenceError(RuntimeError):
    pass


class InferenceUnavailable(InferenceError):
    pass


@dataclass(frozen=True)
class LabelSpec:
    tag: str
    risk_type: str
    level: str


def _softmax(values: Iterable[float]) -> list[float]:
    values = [float(value) for value in values]
    if not values:
        return []
    maximum = max(values)
    exponentials = [math.exp(value - maximum) for value in values]
    total = sum(exponentials)
    return [value / total for value in exponentials]


def _normalize_level(value: Any, default: str = "中") -> str:
    return LEVEL_ALIASES.get(str(value).strip().lower(), default)


def _normalize_risk(risk: dict[str, Any], text_length: int) -> dict[str, Any] | None:
    risk_type = str(risk.get("type", "")).strip()
    if not risk_type:
        return None
    try:
        score = min(1.0, max(0.0, float(risk.get("score", 0))))
        start = min(text_length, max(0, int(risk.get("start", 0))))
        end = min(text_length, max(start, int(risk.get("end", start))))
    except (TypeError, ValueError):
        return None
    if end <= start:
        return None
    return {
        "type": risk_type,
        "score": round(score, 6),
        "start": start,
        "end": end,
        "level": _normalize_level(risk.get("level")),
    }


def merge_risks(
    risks: Iterable[dict[str, Any]],
    *,
    text_length: int,
) -> list[dict[str, Any]]:
    normalized = [
        item
        for risk in risks
        if (item := _normalize_risk(risk, text_length)) is not None
    ]
    normalized.sort(key=lambda item: (item["type"], item["start"], item["end"]))
    merged: list[dict[str, Any]] = []

    for risk in normalized:
        match = next(
            (
                current
                for current in reversed(merged)
                if current["type"] == risk["type"]
                and risk["start"] <= current["end"]
            ),
            None,
        )
        if match is None:
            merged.append(dict(risk))
            continue
        match["start"] = min(match["start"], risk["start"])
        match["end"] = max(match["end"], risk["end"])
        match["score"] = max(match["score"], risk["score"])
        if LEVEL_RANK[risk["level"]] > LEVEL_RANK[match["level"]]:
            match["level"] = risk["level"]

    return sorted(
        merged,
        key=lambda item: (-item["score"], item["start"], item["end"]),
    )


class ONNXReviewProvider:
    def __init__(
        self,
        *,
        model_root: str | Path | None = None,
        model_version: str | None = None,
        max_tokens: int | None = None,
        stride: int | None = None,
        threshold: float | None = None,
        session_factory: Callable[[Path], Any] | None = None,
        tokenizer_factory: Callable[[Path], Any] | None = None,
    ):
        self.model_root = Path(
            model_root
            or settings.DOCUMENT_REVIEW_MODEL_ROOT
        )
        self.default_version = (
            model_version or settings.DOCUMENT_REVIEW_MODEL_VERSION
        )
        self.max_tokens = max_tokens or settings.DOCUMENT_REVIEW_MAX_TOKENS
        self.stride = stride if stride is not None else settings.DOCUMENT_REVIEW_CHUNK_STRIDE
        self.threshold = (
            threshold
            if threshold is not None
            else settings.DOCUMENT_REVIEW_SCORE_THRESHOLD
        )
        self.session_factory = session_factory or self._create_session
        self.tokenizer_factory = tokenizer_factory or self._create_tokenizer
        self._resources: dict[str, tuple[Any, Any, dict[int, Any]]] = {}

    def review(
        self,
        text: str,
        *,
        model_version: str | None = None,
        **_: Any,
    ) -> list[dict[str, Any]]:
        if not text:
            return []
        version = self._validate_version(model_version or self.default_version)
        session, tokenizer, labels = self._load_resources(version)
        encoded = tokenizer(
            text,
            max_length=self.max_tokens,
            truncation=True,
            stride=self.stride,
            return_overflowing_tokens=True,
            return_offsets_mapping=True,
            padding="max_length",
        )
        offsets = encoded.get("offset_mapping")
        if offsets is None:
            raise InferenceError("Tokenizer must provide offset_mapping.")

        input_names = {item.name for item in session.get_inputs()}
        risks: list[dict[str, Any]] = []
        for chunk_index, chunk_offsets in enumerate(offsets):
            feed = self._session_inputs(encoded, chunk_index, input_names)
            outputs = session.run(None, feed)
            if not outputs:
                raise InferenceError("ONNX model returned no outputs.")
            risks.extend(
                self._decode_chunk(
                    outputs[0],
                    chunk_offsets,
                    labels,
                )
            )
        return merge_risks(risks, text_length=len(text))

    def _load_resources(self, version: str):
        if version in self._resources:
            return self._resources[version]
        model_dir = self.model_root / version
        model_path = model_dir / "model.onnx"
        if not model_path.is_file():
            raise InferenceUnavailable(
                f"Document review model {version!r} is not installed."
            )
        try:
            session = self.session_factory(model_path)
            tokenizer = self.tokenizer_factory(model_dir)
            labels = self._load_labels(model_dir, session)
        except InferenceError:
            raise
        except Exception as exc:
            raise InferenceUnavailable(
                f"Failed to load document review model {version!r}."
            ) from exc
        if not labels:
            raise InferenceUnavailable(
                f"Document review model {version!r} has no label metadata."
            )
        self._resources[version] = (session, tokenizer, labels)
        return self._resources[version]

    def _create_session(self, model_path: Path):
        try:
            import onnxruntime
        except ImportError as exc:
            raise InferenceUnavailable("onnxruntime is not installed.") from exc
        return onnxruntime.InferenceSession(
            str(model_path),
            providers=["CPUExecutionProvider"],
        )

    def _create_tokenizer(self, model_dir: Path):
        try:
            from transformers import AutoTokenizer
        except ImportError as exc:
            raise InferenceUnavailable("transformers is not installed.") from exc
        tokenizer = AutoTokenizer.from_pretrained(
            str(model_dir),
            local_files_only=True,
            use_fast=True,
        )
        if not getattr(tokenizer, "is_fast", False):
            raise InferenceUnavailable(
                "A fast tokenizer is required for span offsets."
            )
        return tokenizer

    def _load_labels(self, model_dir: Path, session) -> dict[int, Any]:
        labels_path = model_dir / "labels.json"
        raw: Any = None
        if labels_path.is_file():
            raw = json.loads(labels_path.read_text(encoding="utf-8"))
        else:
            metadata = getattr(session.get_modelmeta(), "custom_metadata_map", {})
            if metadata.get("labels"):
                raw = json.loads(metadata["labels"])
        if isinstance(raw, list):
            return dict(enumerate(raw))
        if isinstance(raw, dict):
            return {int(index): value for index, value in raw.items()}
        return {}

    def _session_inputs(
        self,
        encoded: dict[str, Any],
        chunk_index: int,
        input_names: set[str],
    ) -> dict[str, Any]:
        try:
            import numpy
        except ImportError as exc:
            raise InferenceUnavailable("numpy is not installed.") from exc
        feed = {}
        for name in input_names:
            if name not in encoded:
                continue
            feed[name] = numpy.asarray(
                [encoded[name][chunk_index]],
                dtype=numpy.int64,
            )
        if not feed:
            raise InferenceError("Tokenizer outputs do not match ONNX model inputs.")
        return feed

    def _decode_chunk(
        self,
        output: Any,
        offsets: Iterable[Iterable[int]],
        labels: dict[int, Any],
    ) -> list[dict[str, Any]]:
        logits = output.tolist() if hasattr(output, "tolist") else output
        if logits and isinstance(logits[0], list) and logits[0]:
            if isinstance(logits[0][0], list):
                logits = logits[0]
            elif len(logits) == 1:
                logits = [logits[0]]

        risks: list[dict[str, Any]] = []
        active: dict[str, Any] | None = None
        for token_logits, offset in zip(logits, offsets):
            start, end = int(offset[0]), int(offset[1])
            if end <= start:
                continue
            probabilities = _softmax(token_logits)
            if not probabilities:
                continue
            label_index = max(range(len(probabilities)), key=probabilities.__getitem__)
            spec = self._label_spec(labels.get(label_index, "O"))
            score = probabilities[label_index]
            if spec.tag == "O" or score < self.threshold:
                if active is not None:
                    risks.append(active)
                    active = None
                continue

            continues = (
                spec.tag == "I"
                and active is not None
                and active["type"] == spec.risk_type
            )
            if continues:
                active["end"] = end
                active["score"] = max(active["score"], score)
                if LEVEL_RANK[spec.level] > LEVEL_RANK[active["level"]]:
                    active["level"] = spec.level
                continue
            if active is not None:
                risks.append(active)
            active = {
                "type": spec.risk_type,
                "score": score,
                "start": start,
                "end": end,
                "level": spec.level,
            }
        if active is not None:
            risks.append(active)
        return risks

    def _label_spec(self, raw: Any) -> LabelSpec:
        if isinstance(raw, dict):
            tag = str(raw.get("tag", "B")).upper()
            return LabelSpec(
                tag=tag if tag in {"B", "I", "O"} else "B",
                risk_type=str(raw.get("type", "")).strip(),
                level=_normalize_level(raw.get("level")),
            )
        label = str(raw).strip()
        if not label or label.upper() == "O":
            return LabelSpec("O", "", "中")
        tag = "B"
        if len(label) > 2 and label[1] == "-" and label[0].upper() in {"B", "I"}:
            tag, label = label[0].upper(), label[2:]
        level = "中"
        for separator in ("|", ":"):
            if separator in label:
                possible_type, possible_level = label.rsplit(separator, 1)
                normalized_level = _normalize_level(possible_level, default="")
                if normalized_level:
                    label, level = possible_type, normalized_level
                break
        return LabelSpec(tag, label, level)

    def _validate_version(self, version: str) -> str:
        if not VERSION_PATTERN.fullmatch(version):
            raise InferenceError("Invalid document review model version.")
        return version


class LLMReviewProvider:
    def __init__(self, *, llm_gateway=None, prompt_engine=None):
        self.llm_gateway = llm_gateway or default_gateway
        self.prompt_engine = prompt_engine or default_prompt_engine

    def review(
        self,
        text: str,
        *,
        user_id: str | int | None = None,
        document_type: str = "通用",
        **_: Any,
    ) -> list[dict[str, Any]]:
        if not text:
            return []
        prompt = self.prompt_engine.render(
            "documents/review",
            version=None,
            user_id=user_id,
            document_type=document_type,
            text=text,
        )
        response = self.llm_gateway.complete(
            prompt,
            user_id=user_id,
            temperature=0.1,
        )
        return self._parse(response.text, text)

    def _parse(self, raw_text: str, source_text: str) -> list[dict[str, Any]]:
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            cleaned = "\n".join(lines[1:-1]).strip()
        try:
            payload = json.loads(cleaned)
        except (TypeError, json.JSONDecodeError) as exc:
            raise InferenceError("LLM review returned invalid JSON.") from exc
        risks = payload.get("risks", []) if isinstance(payload, dict) else payload
        if not isinstance(risks, list):
            raise InferenceError("LLM review risks must be a JSON array.")
        return merge_risks(
            (risk for risk in risks if isinstance(risk, dict)),
            text_length=len(source_text),
        )


class DocumentReviewer:
    def __init__(self, *, onnx_provider=None, fallback_provider=None):
        self.onnx_provider = onnx_provider or ONNXReviewProvider()
        self.fallback_provider = fallback_provider or LLMReviewProvider()

    def review(
        self,
        text: str,
        *,
        model_version: str | None = None,
        user_id: str | int | None = None,
        document_type: str = "通用",
    ) -> list[dict[str, Any]]:
        if not text:
            return []
        try:
            return self.onnx_provider.review(
                text,
                model_version=model_version,
            )
        except InferenceUnavailable:
            return self.fallback_provider.review(
                text,
                user_id=user_id,
                document_type=document_type,
            )
