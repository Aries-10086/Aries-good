from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from .rules import AIFlavorHit, detect_ai_flavor


@dataclass(frozen=True)
class GenerationAttempt:
    text: str
    score: float
    hits: list[AIFlavorHit]
    temperature: float
    template_version: str | None


@dataclass(frozen=True)
class DeAIRetryResult:
    text: str
    score: float
    hits: list[AIFlavorHit]
    attempts: list[GenerationAttempt]
    accepted: bool


def generate_with_deai_retry(
    generator: Callable[..., str],
    *,
    threshold: float = 0.7,
    max_retries: int = 2,
    base_temperature: float = 0.7,
    temperature_step: float = 0.15,
    template_versions: Sequence[str] | None = None,
    detector: Callable[[str], tuple[float, list[AIFlavorHit]]] = detect_ai_flavor,
    **generation_context: Any,
) -> DeAIRetryResult:
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1.")
    if not 0 <= max_retries <= 2:
        raise ValueError("max_retries must be between 0 and 2.")

    versions = list(template_versions or ())
    attempts: list[GenerationAttempt] = []

    for attempt_index in range(max_retries + 1):
        temperature = min(base_temperature + temperature_step * attempt_index, 2.0)
        template_version = (
            versions[min(attempt_index, len(versions) - 1)] if versions else None
        )
        call_context = {
            **generation_context,
            "temperature": temperature,
        }

        if template_version is not None:
            call_context["template_version"] = template_version

        text = generator(**call_context)
        score, hits = detector(text)
        attempt = GenerationAttempt(
            text=text,
            score=score,
            hits=hits,
            temperature=temperature,
            template_version=template_version,
        )
        attempts.append(attempt)

        if score <= threshold:
            return DeAIRetryResult(
                text=text,
                score=score,
                hits=hits,
                attempts=attempts,
                accepted=True,
            )

    final_attempt = attempts[-1]
    return DeAIRetryResult(
        text=final_attempt.text,
        score=final_attempt.score,
        hits=final_attempt.hits,
        attempts=attempts,
        accepted=False,
    )
