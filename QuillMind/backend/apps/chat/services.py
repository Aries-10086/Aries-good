from __future__ import annotations

import json
from typing import Any

from core.llm import gateway as default_gateway
from core.prompts import engine as default_prompt_engine

from .models import ChatSession


PERSONA_FIELDS = (
    "role",
    "relationship",
    "tone",
    "strategy",
    "boundaries",
    "preferred_phrases",
    "avoid_phrases",
    "success_signal",
)
PERSONA_LIST_FIELDS = (
    "tone",
    "strategy",
    "boundaries",
    "preferred_phrases",
    "avoid_phrases",
)


class PersonaGenerationError(RuntimeError):
    pass


class PersonaService:
    def __init__(self, *, llm_gateway=None, prompt_engine=None):
        self.llm_gateway = llm_gateway or default_gateway
        self.prompt_engine = prompt_engine or default_prompt_engine

    def generate(
        self,
        *,
        user_id,
        scene: str,
        relationship: str,
        goal: str,
        user_style: str = "",
    ) -> dict[str, Any]:
        prompt = self.prompt_engine.render(
            "chat/persona",
            version=None,
            user_id=user_id,
            scene=self._scene_label(scene),
            relationship=relationship,
            goal=goal,
            user_style=user_style,
            counterpart={},
        )
        response = self.llm_gateway.complete(
            prompt,
            user_id=user_id,
            temperature=0.35,
        )
        return self._parse_persona(response.text)

    def _scene_label(self, scene: str) -> str:
        return dict(ChatSession.Scene.choices).get(scene, scene)

    def _parse_persona(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            cleaned = "\n".join(lines[1:-1]).strip()

        try:
            persona = json.loads(cleaned)
        except (json.JSONDecodeError, TypeError) as exc:
            raise PersonaGenerationError("人设服务返回了无效 JSON。") from exc

        if not isinstance(persona, dict):
            raise PersonaGenerationError("人设卡片必须是 JSON 对象。")

        missing = [field for field in PERSONA_FIELDS if not persona.get(field)]
        if missing:
            raise PersonaGenerationError(
                f"人设卡片缺少字段：{', '.join(missing)}。"
            )

        if any(not isinstance(persona[field], list) for field in PERSONA_LIST_FIELDS):
            raise PersonaGenerationError("人设卡片中的语气和策略字段必须是数组。")
        if not isinstance(persona["role"], str) or not isinstance(
            persona["relationship"], str
        ):
            raise PersonaGenerationError("人设卡片中的身份和关系必须是文本。")
        if not isinstance(persona["success_signal"], str):
            raise PersonaGenerationError("人设卡片中的成功信号必须是文本。")

        return {field: persona[field] for field in PERSONA_FIELDS}
