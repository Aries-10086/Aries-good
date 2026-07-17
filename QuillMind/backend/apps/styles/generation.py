from __future__ import annotations

from dataclasses import asdict, dataclass
import time
from typing import Any, Callable, Iterator

from django.conf import settings

from core.deai import AIFlavorHit, detect_ai_flavor
from core.llm import gateway as default_gateway
from core.prompts import engine as default_prompt_engine
from core.style import OpenAIEmbeddingProvider, cosine_similarity

from .models import GenerationRecord, StyleProfile


AI_FLAVOR_THRESHOLD = settings.STYLE_AI_FLAVOR_THRESHOLD
STYLE_SIMILARITY_THRESHOLD = settings.STYLE_SIMILARITY_THRESHOLD
MAX_RETRIES = settings.STYLE_GENERATION_MAX_RETRIES
TOTAL_TIMEOUT_SECONDS = settings.STYLE_GENERATION_TIMEOUT_SECONDS


class StyleGenerationTimeout(TimeoutError):
    pass


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
        clock: Callable[[], float] = time.monotonic,
    ):
        self.llm_gateway = llm_gateway or default_gateway
        self.prompt_engine = prompt_engine or default_prompt_engine
        self.embedding_provider = embedding_provider or OpenAIEmbeddingProvider()
        self.detector = detector
        self.clock = clock

    def generate(
        self,
        *,
        user,
        profile: StyleProfile,
        topic: str,
        outline: str = "",
        keywords: list[str] | None = None,
        tone_slider: int = 50,
    ) -> StyleGenerationResult:
        attempts: list[GenerationAttempt] = []
        keywords = keywords or []
        deadline = self.clock() + TOTAL_TIMEOUT_SECONDS

        for attempt_number in range(1, MAX_RETRIES + 2):
            prompt, temperature = self._build_attempt(
                profile=profile,
                topic=topic,
                outline=outline,
                keywords=keywords,
                tone_slider=tone_slider,
                attempt_number=attempt_number,
                previous_attempt=attempts[-1] if attempts else None,
            )
            text = "".join(
                self.llm_gateway.stream(
                    prompt,
                    user_id=user.id,
                    temperature=temperature,
                    timeout=self._remaining(deadline),
                )
            ).strip()
            self._remaining(deadline)
            attempt = self._evaluate_attempt(
                number=attempt_number,
                prompt=prompt,
                text=text,
                temperature=temperature,
                profile=profile,
                deadline=deadline,
            )
            attempts.append(attempt)

            if attempt.quality.accepted:
                break

        record = self._save_record(
            user=user,
            profile=profile,
            topic=topic,
            keywords=keywords,
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
        keywords: list[str] | None = None,
        tone_slider: int = 50,
    ) -> Iterator[dict[str, Any]]:
        attempts: list[GenerationAttempt] = []
        keywords = keywords or []
        deadline = self.clock() + TOTAL_TIMEOUT_SECONDS

        for attempt_number in range(1, MAX_RETRIES + 2):
            prompt, temperature = self._build_attempt(
                profile=profile,
                topic=topic,
                outline=outline,
                keywords=keywords,
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
                timeout=self._remaining(deadline),
            ):
                self._remaining(deadline)
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
                deadline=deadline,
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
            keywords=keywords,
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
        keywords: list[str],
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
        if keywords:
            constraints.append(f"自然融入这些关键词：{'、'.join(keywords)}")
        if previous_attempt is not None:
            constraints.append(self._retry_constraint(previous_attempt.quality))

        prompt = self.prompt_engine.render(
            "styles/generate",
            version=None,
            user_id=profile.user_id,
            task=topic,
            style_description=profile.description,
            style_features=self._prompt_features(profile.features),
            style_samples=self._style_examples(getattr(profile, "samples", [])),
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
        deadline: float,
    ) -> GenerationAttempt:
        ai_score, hits = self.detector(text)
        generated_vector = self.embedding_provider.embed(
            [text],
            timeout=self._remaining(deadline),
        )[0]
        self._remaining(deadline)
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

    def _save_record(self, *, user, profile, topic, keywords, attempts):
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
                "keywords": keywords,
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

    def _remaining(self, deadline: float) -> float:
        remaining = deadline - self.clock()
        if remaining <= 0:
            raise StyleGenerationTimeout(
                f"生成超过 {TOTAL_TIMEOUT_SECONDS:g} 秒时间预算。"
            )
        return remaining

    def _style_examples(self, samples: list[str]) -> list[str]:
        examples = []
        for sample in samples[:2]:
            normalized = " ".join(sample.split())
            if normalized:
                examples.append(normalized[:600])
        return examples

    def _prompt_features(self, features: dict[str, Any]) -> dict[str, str]:
        result: dict[str, str] = {}
        average = features.get("average_sentence_length")
        deviation = features.get("sentence_length_std")
        if average is not None:
            result["平均句长"] = f"{average} 字"
        if deviation is not None:
            result["句长波动"] = f"{deviation} 字"

        top_words = [
            str(item.get("word"))
            for item in features.get("top_words", [])[:12]
            if isinstance(item, dict) and item.get("word")
        ]
        if top_words:
            result["高频词"] = "、".join(top_words)

        particles = []
        for particle, data in features.get("tone_particles", {}).items():
            if isinstance(data, dict) and data.get("count", 0):
                particles.append(f"{particle}（每百字 {data.get('per_100_chars', 0)} 次）")
        if particles:
            result["常用语气词"] = "、".join(particles)

        punctuation = features.get("punctuation_habits", {})
        if isinstance(punctuation, dict):
            habits = []
            if punctuation.get("exclamation_count", 0):
                habits.append(f"感叹号占比 {punctuation.get('exclamation_ratio', 0)}")
            if punctuation.get("ellipsis_count", 0):
                habits.append(f"省略号占比 {punctuation.get('ellipsis_ratio', 0)}")
            if habits:
                result["标点习惯"] = "；".join(habits)
        return result
