from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


LLMMessage = dict[str, str]


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    raw: Any | None = None
    cost_usd: float = 0.0
