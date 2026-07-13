from __future__ import annotations

from .exceptions import LLMError, LLMProviderError, LLMRateLimitError
from .gateway import LLMGateway
from .providers import BaseLLMProvider, ClaudeProvider, OpenAIProvider
from .types import LLMMessage, LLMResponse, TokenUsage


class LazyLLMGateway:
    def __init__(self):
        self._gateway: LLMGateway | None = None

    def _get_gateway(self):
        if self._gateway is None:
            self._gateway = LLMGateway.from_settings()

        return self._gateway

    def __getattr__(self, name):
        return getattr(self._get_gateway(), name)


gateway = LazyLLMGateway()

__all__ = (
    "BaseLLMProvider",
    "ClaudeProvider",
    "LLMError",
    "LLMGateway",
    "LLMMessage",
    "LLMProviderError",
    "LLMRateLimitError",
    "LLMResponse",
    "LazyLLMGateway",
    "OpenAIProvider",
    "TokenUsage",
    "gateway",
)
