from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any

from django.conf import settings

from .exceptions import LLMProviderError
from .types import LLMMessage, LLMResponse, TokenUsage


class BaseLLMProvider(ABC):
    name: str

    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        messages: list[LLMMessage] | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    def stream(
        self,
        prompt: str,
        *,
        messages: list[LLMMessage] | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        raise NotImplementedError


class OpenAIProvider(BaseLLMProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None, default_model: str | None = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.default_model = default_model or settings.LLM_OPENAI_MODEL
        self._client = None

    @property
    def client(self):
        if not self.api_key:
            raise LLMProviderError("OPENAI_API_KEY is not configured.")

        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise LLMProviderError("The openai package is not installed.") from exc

            self._client = OpenAI(api_key=self.api_key)

        return self._client

    def complete(
        self,
        prompt: str,
        *,
        messages: list[LLMMessage] | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        model_name = model or self.default_model
        response = self.client.chat.completions.create(
            model=model_name,
            messages=self._messages(prompt, messages),
            **kwargs,
        )
        choice = response.choices[0]
        usage = self._usage(response)

        return LLMResponse(
            text=choice.message.content or "",
            provider=self.name,
            model=model_name,
            usage=usage,
            raw=response,
        )

    def stream(
        self,
        prompt: str,
        *,
        messages: list[LLMMessage] | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        stream = self.client.chat.completions.create(
            model=model or self.default_model,
            messages=self._messages(prompt, messages),
            stream=True,
            **kwargs,
        )

        for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield token

    def _messages(self, prompt: str, messages: list[LLMMessage] | None) -> list[LLMMessage]:
        if messages:
            return messages

        return [{"role": "user", "content": prompt}]

    def _usage(self, response: Any) -> TokenUsage:
        raw_usage = getattr(response, "usage", None)

        if raw_usage is None:
            return TokenUsage()

        prompt_tokens = int(getattr(raw_usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(raw_usage, "completion_tokens", 0) or 0)
        total_tokens = int(
            getattr(raw_usage, "total_tokens", 0) or prompt_tokens + completion_tokens
        )

        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )


class ClaudeProvider(BaseLLMProvider):
    name = "claude"

    def complete(
        self,
        prompt: str,
        *,
        messages: list[LLMMessage] | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        raise LLMProviderError("ClaudeProvider is reserved for phase two.")

    def stream(
        self,
        prompt: str,
        *,
        messages: list[LLMMessage] | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        raise LLMProviderError("ClaudeProvider is reserved for phase two.")
