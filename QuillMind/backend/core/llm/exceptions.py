class LLMError(Exception):
    """Base exception for LLM gateway failures."""


class LLMProviderError(LLMError):
    """Raised when a provider cannot complete a request."""


class LLMRateLimitError(LLMError):
    """Raised when a user exceeds the configured gateway rate limit."""
