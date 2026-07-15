from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable, Iterator

from django.conf import settings

from core.deai import AIFlavorHit, detect_ai_flavor
from core.llm import gateway as default_gateway
from core.prompts import engine as default_prompt_engine
from core.style import OpenAIEmbeddingProvider, cosine_similarity

from .models import GenerationRecord, StyleProfile


AI_FLAVOR_THRESHOLD = 0.7
STYLE_SIMILARITY_THRESHOLD = 0.75
MAX_RETRIES = 2


@dataclass(frozen=True)
class GenerationQuality:
    ai_flavor_score: float
    style_similarity: float
    accepted: bool
    ai_flavor_hits: list[dict[str, Any]]


@dataclass(frozen=True)
class GenerationAttempt:
    number: int
    prompt: str
    text: str
    temperature: float
    quality: GenerationQuality


@dataclass(frozen=True)
class StyleGenerationResult:
    record: GenerationRecord
    attempts: list[GenerationAttempt]


class StyleGenerationService:
    def __init__(
        self,
        *,
        llm_gateway=None,
        prompt_engine=None,
        embedding_provider=None,
        detector: Callable[[str], tuple[float, list[AIFlavorHit]]] = detect_ai_flavor,
    ):
        self.llm_gateway = llm_gateway or default_gateway
        self.prompt_engine = prompt_engine or default_prompt_engine
        self.embedding_provider = embedding_provider or OpenAIEmbeddingProvider()
        self.detector = detector

    def generate(
        self,
        *,
        user,
        profile: StyleProfile,
        topic: str,
        outline: str = "",
        tone_slider: int = 50,
    ) -> StyleGenerationResult:
        attempts: list[GenerationAttempt] = []

        for attempt_number in range(1, MAX_RETRIES + 2):
            prompt, temperature = self._build_attempt(
                profile=profile,
                topic=topic,
                outline=outline,
                tone_slider=tone_slider,
                attempt_number=attempt_number,
                previous_attempt=attempts[-1] if attempts else None,
            )
            text = "".join(
                self.llm_gateway.stream(
                    prompt,
                    user_id=user.id,
                    temperature=temperature,
                )
            ).strip()
            attempt = self._evaluate_attempt(
                number=attempt_number,
                prompt=prompt,
                text=text,
                temperature=temperature,
                profile=profile,
            )
            attempts.append(attempt)

            if attempt.quality.accepted:
                break

        record = self._save_record(
            user=user,
            profile=profile,
            topic=topic,
            attempts=attempts,
        )
        return StyleGenerationResult(record=record, attempts=attempts)

    def stream(
        self,
        *,
        user,
        profile: StyleProfile,
        topic: str,
        outline: str = "",
        tone_slider: int = 50,
    ) -> Iterator[dict[str, Any]]:
        attempts: list[GenerationAttempt] = []

        for attempt_number in range(1, MAX_RETRIES + 2):
            prompt, temperature = self._build_attempt(
                profile=profile,
                topic=topic,
                outline=outline,
                tone_slider=tone_slider,
                attempt_number=attempt_number,
                previous_attempt=attempts[-1] if attempts else None,
            )
            yield {
                "event": "attempt",
                "data": {
                    "attempt": attempt_number,
                    "temperature": temperature,
                    "reset": attempt_number > 1,
                },
            }
            chunks: list[str] = []

            for chunk in self.llm_gateway.stream(
                prompt,
                user_id=user.id,
                temperature=temperature,
            ):
                chunks.append(chunk)
                yield {
                    "event": "token",
                    "data": {"attempt": attempt_number, "text": chunk},
                }

            attempt = self._evaluate_attempt(
                number=attempt_number,
                prompt=prompt,
                text="".join(chunks).strip(),
                temperature=temperature,
                profile=profile,
            )
            attempts.append(attempt)
            yield {
                "event": "quality",
                "data": {"attempt": attempt_number, **asdict(attempt.quality)},
            }

            if attempt.quality.accepted:
                break
            if attempt_number <= MAX_RETRIES:
                yield {
                    "event": "retry",
                    "data": {
                        "attempt": attempt_number,
                        "reason": self._retry_reason(attempt.quality),
                    },
                }

        record = self._save_record(
            user=user,
            profile=profile,
            topic=topic,
            attempts=attempts,
        )
        yield {
            "event": "complete",
            "data": {
                "generation_id": str(record.id),
                "result": record.result,
                "quality": record.quality,
            },
        }

    def _build_attempt(
        self,
        *,
        profile: StyleProfile,
        topic: str,
        outline: str,
        tone_slider: int,
        attempt_number: int,
        previous_attempt: GenerationAttempt | None,
    ) -> tuple[str, float]:
        temperature = min(0.55 + tone_slider / 250 + (attempt_number - 1) * 0.15, 1.4)
        constraints = [
            self._tone_constraint(tone_slider),
            "围绕主题写作，不补造未提供的事实。",
        ]
        if outline:
            constraints.append(f"按这个大纲展开：{outline}")
        if previous_attempt is not None:
            constraints.append(self._retry_constraint(previous_attempt.quality))

        prompt = self.prompt_engine.render(
            "styles/generate",
            version=None,
            user_id=profile.user_id,
            task=topic,
            style_description=profile.description,
            style_features=profile.features,
            constraints=constraints,
            forbidden_words=[
                "赋能",
                "抓手",
                "综上所述",
                "在当今时代",
                "具有重要意义",
            ],
        )
        return prompt, round(temperature, 2)

    def _evaluate_attempt(
        self,
        *,
        number: int,
        prompt: str,
        text: str,
        temperature: float,
        profile: StyleProfile,
    ) -> GenerationAttempt:
        ai_score, hits = self.detector(text)
        generated_vector = self.embedding_provider.embed([text])[0]
        similarity = cosine_similarity(generated_vector, profile.style_vector)
        quality = GenerationQuality(
            ai_flavor_score=round(ai_score, 4),
            style_similarity=round(similarity, 4),
            accepted=(
                ai_score <= AI_FLAVOR_THRESHOLD
                and similarity >= STYLE_SIMILARITY_THRESHOLD
            ),
            ai_flavor_hits=[asdict(hit) for hit in hits],
        )
        return GenerationAttempt(
            number=number,
            prompt=prompt,
            text=text,
            temperature=temperature,
            quality=quality,
        )

    def _save_record(self, *, user, profile, topic, attempts):
        final_attempt = attempts[-1]
        return GenerationRecord.objects.create(
            user=user,
            style=profile,
            prompt=final_attempt.prompt,
            result=final_attempt.text,
            model_name=settings.LLM_OPENAI_MODEL,
            quality={
                **asdict(final_attempt.quality),
                "attempt_count": len(attempts),
                "topic": topic,
            },
        )

    def _tone_constraint(self, tone_slider: int) -> str:
        if tone_slider <= 30:
            return "整体偏正式，措辞准确克制，但不要写成公文。"
        if tone_slider >= 70:
            return "整体偏口语，像真人自然表达，可使用短句和适度语气词。"
        return "正式与口语保持平衡，清楚自然，不刻意端着。"

    def _retry_constraint(self, quality: GenerationQuality) -> str:
        reasons = []
        if quality.ai_flavor_score > AI_FLAVOR_THRESHOLD:
            reasons.append("删除模板化套话，改成具体、自然的表达")
        if quality.style_similarity < STYLE_SIMILARITY_THRESHOLD:
            reasons.append("更严格遵循风格描述中的句长、语气词和标点习惯")
        return "上一次未达标，请" + "；".join(reasons) + "。"

    def _retry_reason(self, quality: GenerationQuality) -> list[str]:
        reasons = []
        if quality.ai_flavor_score > AI_FLAVOR_THRESHOLD:
            reasons.append("ai_flavor")
        if quality.style_similarity < STYLE_SIMILARITY_THRESHOLD:
            reasons.append("style_similarity")
        return reasons
