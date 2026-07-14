class PromptEngineError(Exception):
    """Base exception for prompt rendering failures."""


class PromptTemplateNotFound(PromptEngineError):
    """Raised when neither an active DB template nor a file template exists."""


class PromptRenderError(PromptEngineError):
    """Raised when a template cannot be rendered with the supplied context."""
