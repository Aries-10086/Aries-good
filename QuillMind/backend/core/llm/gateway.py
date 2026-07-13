from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Any

from django.conf import settings

from .exceptions import LLMProviderError
from .providers import BaseLLMProvider, ClaudeProvider, OpenAIProvider
from .rate_limit import RedisRateLimiter
from .types import LLMMessage, LLMResponse, TokenUsage


logger = logging.getLogger(__name__)


class LLMGateway:
    def __init__(
        self,
        providers: dict[str, BaseLLMProvider],
        *,
        provider_order: list[str],
        rate_limiter: RedisRateLimiter | None = None,
    ):
        self.providers = providers
        self.provider_order = provider_order
        self.rate_limiter = rate_limiter or RedisRateLimiter()

    @classmethod
    def from_settings(cls):
        providers: dict[str, BaseLLMProvider] = {
            "openai": OpenAIProvider(),
            "claude": ClaudeProvider(),
        }
        provider_order = [
            provider.strip()
            for provider in settings.LLM_PROVIDER_ORDER.split(",")
            if provider.strip()
        ]

        return cls(providers, provider_order=provider_order)

    def register(self, provider: BaseLLMProvider):
        self.providers[provider.name] = provider

    def complete(
        self,
        prompt: str,
        *,
        user_id: str | int | None = None,
        provider: str | None = None,
        messages: list[LLMMessage] | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        self.rate_limiter.check(user_id)
        errors: list[Exception] = []

        for provider_name in self._provider_names(provider):
            llm_provider = self.providers.get(provider_name)

            if llm_provider is None:
                errors.append(LLMProviderError(f"Provider {provider_name} is not registered."))
                continue

            start = time.perf_counter()

            try:
                response = llm_provider.complete(
                    prompt,
                    messages=messages,
                    model=model,
                    **kwargs,
                )
                latency_ms = int((time.perf_counter() - start) * 1000)
                response = self._with_cost(response)
                self._log_call(response, latency_ms, user_id=user_id, status="success")
                return response
            except Exception as exc:
                latency_ms = int((time.perf_counter() - start) * 1000)
                errors.append(exc)
                logger.warning(
                    "LLM provider failed",
                    extra={
                        "provider": provider_name,
                        "latency_ms": latency_ms,
                        "user_id": user_id,
                        "status": "failed",
                    },
                    exc_info=True,
                )

        raise LLMProviderError("All LLM providers failed.") from (errors[-1] if errors else None)

    def stream(
        self,
        prompt: str,
        *,
        user_id: str | int | None = None,
        provider: str | None = None,
        messages: list[LLMMessage] | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        self.rate_limiter.check(user_id)
        errors: list[Exception] = []

        for provider_name in self._provider_names(provider):
            llm_provider = self.providers.get(provider_name)

            if llm_provider is None:
                errors.append(LLMProviderError(f"Provider {provider_name} is not registered."))
                continue

            try:
                yield from llm_provider.stream(
                    prompt,
                    messages=messages,
                    model=model,
                    **kwargs,
                )
                return
            except Exception as exc:
                errors.append(exc)
                logger.warning("LLM stream provider failed", extra={"provider": provider_name})

        raise LLMProviderError("All LLM stream providers failed.") from (
            errors[-1] if errors else None
        )

    def _provider_names(self, provider: str | None):
        if provider:
            return [provider]

        return self.provider_order

    def _with_cost(self, response: LLMResponse) -> LLMResponse:
        rates = settings.LLM_MODEL_PRICING_USD_PER_1K_TOKENS.get(response.model, {})
        input_rate = float(rates.get("input", 0))
        output_rate = float(rates.get("output", 0))
        cost = (
            response.usage.prompt_tokens / 1000 * input_rate
            + response.usage.completion_tokens / 1000 * output_rate
        )

        return LLMResponse(
            text=response.text,
            provider=response.provider,
            model=response.model,
            usage=response.usage or TokenUsage(),
            raw=response.raw,
            cost_usd=cost,
        )

    def _log_call(
        self,
        response: LLMResponse,
        latency_ms: int,
        *,
        user_id: str | int | None,
        status: str,
    ):
        logger.info(
            "LLM call completed",
            extra={
                "provider": response.provider,
                "model": response.model,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "latency_ms": latency_ms,
                "cost_usd": response.cost_usd,
                "user_id": user_id,
                "status": status,
            },
        )
