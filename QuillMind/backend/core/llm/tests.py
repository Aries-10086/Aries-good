from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from django.test import SimpleTestCase, override_settings

from .exceptions import LLMProviderError, LLMRateLimitError
from .gateway import LLMGateway
from .providers import BaseLLMProvider
from .types import LLMMessage, LLMResponse, TokenUsage


class NoopRateLimiter:
    def check(self, user_id):
        return None


class BlockingRateLimiter:
    def check(self, user_id):
        raise LLMRateLimitError("blocked")


class FakeProvider(BaseLLMProvider):
    def __init__(self, name: str, *, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.calls = 0

    def complete(
        self,
        prompt: str,
        *,
        messages: list[LLMMessage] | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        self.calls += 1

        if self.should_fail:
            raise LLMProviderError(f"{self.name} failed")

        return LLMResponse(
            text=f"{prompt}:ok",
            provider=self.name,
            model=model or "mock-model",
            usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        )

    def stream(
        self,
        prompt: str,
        *,
        messages: list[LLMMessage] | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        yield "po"
        yield "ng"


@override_settings(
    LLM_MODEL_PRICING_USD_PER_1K_TOKENS={
        "mock-model": {"input": 0.01, "output": 0.02},
    }
)
class LLMGatewayTests(SimpleTestCase):
    def test_complete_falls_back_to_next_provider(self):
        primary = FakeProvider("primary", should_fail=True)
        backup = FakeProvider("backup")
        gateway = LLMGateway(
            {"primary": primary, "backup": backup},
            provider_order=["primary", "backup"],
            rate_limiter=NoopRateLimiter(),
        )

        response = gateway.complete("ping", user_id="user-1")

        self.assertEqual(response.text, "ping:ok")
        self.assertEqual(response.provider, "backup")
        self.assertEqual(primary.calls, 1)
        self.assertEqual(backup.calls, 1)

    def test_complete_calculates_cost_from_usage(self):
        provider = FakeProvider("primary")
        gateway = LLMGateway(
            {"primary": provider},
            provider_order=["primary"],
            rate_limiter=NoopRateLimiter(),
        )

        response = gateway.complete("ping", model="mock-model")

        self.assertEqual(response.cost_usd, 0.002)

    def test_rate_limit_blocks_before_provider_call(self):
        provider = FakeProvider("primary")
        gateway = LLMGateway(
            {"primary": provider},
            provider_order=["primary"],
            rate_limiter=BlockingRateLimiter(),
        )

        with self.assertRaises(LLMRateLimitError):
            gateway.complete("ping", user_id="user-1")

        self.assertEqual(provider.calls, 0)

    def test_stream_returns_provider_chunks(self):
        provider = FakeProvider("primary")
        gateway = LLMGateway(
            {"primary": provider},
            provider_order=["primary"],
            rate_limiter=NoopRateLimiter(),
        )

        self.assertEqual("".join(gateway.stream("ping")), "pong")
