from __future__ import annotations

from .engine import PromptEngine
from .exceptions import PromptEngineError, PromptRenderError, PromptTemplateNotFound


class LazyPromptEngine:
    def __init__(self):
        self._engine: PromptEngine | None = None

    def _get_engine(self):
        if self._engine is None:
            self._engine = PromptEngine()

        return self._engine

    def __getattr__(self, name):
        return getattr(self._get_engine(), name)


engine = LazyPromptEngine()

__all__ = (
    "LazyPromptEngine",
    "PromptEngine",
    "PromptEngineError",
    "PromptRenderError",
    "PromptTemplateNotFound",
    "engine",
)
