from __future__ import annotations

import hashlib
import logging
from pathlib import Path, PurePosixPath
from typing import Any

from django.conf import settings
from django.db import DatabaseError
from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError, TemplateNotFound

from .exceptions import PromptRenderError, PromptTemplateNotFound


logger = logging.getLogger(__name__)


class PromptEngine:
    def __init__(self, template_dir: str | Path | None = None, model_class=None):
        self.template_dir = Path(
            template_dir or settings.BASE_DIR / "templates" / "prompts"
        )
        self.model_class = model_class
        self.environment = Environment(
            loader=FileSystemLoader(self.template_dir),
            undefined=StrictUndefined,
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def render(
        self,
        module: str,
        version: str | None = "v1.0.0",
        *,
        user_id: str | int | None = None,
        **context: Any,
    ) -> str:
        module = self._normalize_module(module)
        selected_version = version or self.select_version(module, user_id=user_id)
        db_content = self._get_db_content(module, selected_version)

        try:
            if db_content is not None:
                template = self.environment.from_string(db_content)
            else:
                template = self._get_file_template(module, selected_version)

            return template.render(**context).strip()
        except PromptTemplateNotFound:
            raise
        except TemplateError as exc:
            raise PromptRenderError(
                f"Failed to render {module}@{selected_version}: {exc}"
            ) from exc

    def select_version(self, module: str, *, user_id: str | int | None = None) -> str:
        module = self._normalize_module(module)
        versions = self._get_active_versions(module)

        if not versions:
            return "v1.0.0"

        if user_id is None or len(versions) == 1:
            return versions[0]

        bucket = self._user_bucket(user_id)
        index = min(bucket * len(versions) // 100, len(versions) - 1)
        return versions[index]

    def _get_file_template(self, module: str, version: str):
        candidates = (f"{module}.{version}.j2", f"{module}.j2")

        for candidate in candidates:
            try:
                return self.environment.get_template(candidate)
            except TemplateNotFound:
                continue

        raise PromptTemplateNotFound(
            f"Prompt template {module}@{version} was not found in DB or files."
        )

    def _get_db_content(self, module: str, version: str) -> str | None:
        model = self._get_model()

        if model is None:
            return None

        try:
            template = (
                model.objects.filter(
                    module=module,
                    version=version,
                    is_active=True,
                )
                .only("content")
                .first()
            )
        except DatabaseError:
            logger.warning("Prompt DB lookup failed; falling back to files.", exc_info=True)
            return None

        return template.content if template else None

    def _get_active_versions(self, module: str) -> list[str]:
        model = self._get_model()

        if model is None:
            return []

        try:
            return list(
                model.objects.filter(module=module, is_active=True)
                .order_by("version")
                .values_list("version", flat=True)
            )
        except DatabaseError:
            logger.warning("Prompt version lookup failed; using file default.", exc_info=True)
            return []

    def _get_model(self):
        if self.model_class is not None:
            return self.model_class

        try:
            from apps.prompts.models import PromptTemplate
        except (ImportError, RuntimeError):
            return None

        return PromptTemplate

    def _normalize_module(self, module: str) -> str:
        normalized = module.strip().replace("\\", "/").removesuffix(".j2")
        path = PurePosixPath(normalized)

        if not normalized or path.is_absolute() or ".." in path.parts:
            raise PromptTemplateNotFound(f"Invalid prompt module: {module!r}")

        return path.as_posix()

    def _user_bucket(self, user_id: str | int) -> int:
        digest = hashlib.sha256(str(user_id).encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big") % 100
