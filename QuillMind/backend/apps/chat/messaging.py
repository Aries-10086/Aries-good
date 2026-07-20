from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import json
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.llm import gateway as default_gateway
from core.prompts import engine as default_prompt_engine

from .models import ChatSession


MAX_REPLY_CHARS = settings.CHAT_MAX_REPLY_LENGTH
HISTORY_MESSAGE_LIMIT = settings.CHAT_HISTORY_MESSAGE_LIMIT
NEGATIVE_WORDS = ("累", "烦", "不想")
FORBIDDEN_WORDS = (
    "赋能",
    "抓手",
    "综上所述",
    "在当今时代",
    "值得注意的是",
    "具有重要意义",
)
SUGGESTION_STRATEGIES = (
    "先共情回应，再温和推进目标；避免说教。",
    "表达直接但不生硬，给对方一个容易回答的选择。",
    "语气轻松自然，用简短口语降低沟通压力。",
)


@dataclass(frozen=True)
class ChatReply:
    text: str
    emotion: str
    message: dict[str, str]


def classify_emotion(text: str) -> str:
    return "negative" if any(word in text for word in NEGATIVE_WORDS) else "neutral"


def truncate_reply(text: str, max_chars: int = MAX_REPLY_CHARS) -> str:
    normalized = text.strip()
    return normalized if len(normalized) <= max_chars else normalized[:max_chars].rstrip()


class ChatMessageService:
    def __init__(self, *, llm_gateway=None, prompt_engine=None):
        self.llm_gateway = llm_gateway or default_gateway
        self.prompt_engine = prompt_engine or default_prompt_engine

    def reply(
        self,
        *,
        session: ChatSession,
        content: str | None = None,
        regenerate: bool = False,
    ) -> ChatReply:
        chunks = list(
            self.stream_reply(
                session=session,
                content=content,
                regenerate=regenerate,
            )
        )
        text = "".join(chunks)
        return ChatReply(
            text=text,
            emotion=self._latest_emotion(session.messages),
            message=session.messages[-1],
        )

    def stream_reply(
        self,
        *,
        session: ChatSession,
        content: str | None = None,
        regenerate: bool = False,
    ) -> Iterator[str]:
        if regenerate:
            context = self._regeneration_context(session)
            if not any(message.get("role") == "counterpart" for message in context):
                raise ValueError("没有可用于重新生成的对话上下文。")
            emotion = self._latest_emotion(context)
        else:
            if not content or not content.strip():
                raise ValueError("对方说的话不能为空。")
            counterpart = self._message("counterpart", content.strip())
            context = self._append_message(session, counterpart)
            emotion = classify_emotion(content)

        prompt = self._render_reply_prompt(
            session=session,
            messages=context,
            emotion=emotion,
            strategy_instruction=(
                "这是同一上下文的换一条回复，请换用不同措辞和切入方式。"
                if regenerate
                else ""
            ),
        )
        temperature = (
            settings.CHAT_REGENERATE_TEMPERATURE
            if regenerate
            else settings.CHAT_REPLY_BASE_TEMPERATURE
        )
        chunks: list[str] = []
        emitted = 0

        for chunk in self.llm_gateway.stream(
            prompt,
            user_id=session.user_id,
            temperature=temperature,
        ):
            remaining = MAX_REPLY_CHARS - emitted
            if remaining <= 0:
                break
            safe_chunk = chunk[:remaining]
            if safe_chunk:
                chunks.append(safe_chunk)
                emitted += len(safe_chunk)
                yield safe_chunk

        reply_text = truncate_reply("".join(chunks))
        if not reply_text:
            raise ValueError("模型未返回有效回复。")

        assistant = self._message("assistant", reply_text, emotion=emotion)
        if regenerate:
            self._replace_last_assistant(session, assistant)
        else:
            self._append_message(session, assistant)

    def suggestions(
        self,
        *,
        session: ChatSession,
        regenerate: bool = False,
    ) -> list[str]:
        context = self._regeneration_context(session)
        if not any(message.get("role") == "counterpart" for message in context):
            raise ValueError("请先输入对方说的话。")
        emotion = self._latest_emotion(context)
        strategies = SUGGESTION_STRATEGIES if not regenerate else (
            "换一种之前没有用过的切入方式，措辞更灵活自然。",
        )
        suggestions: list[str] = []

        for index, strategy in enumerate(strategies):
            prompt = self._render_reply_prompt(
                session=session,
                messages=context,
                emotion=emotion,
                strategy_instruction=strategy,
            )
            text = "".join(
                self.llm_gateway.stream(
                    prompt,
                    user_id=session.user_id,
                    temperature=(0.75 + index * 0.1) if not regenerate else 1.05,
                )
            )
            suggestion = truncate_reply(text)
            if suggestion:
                suggestions.append(suggestion)

        if len(suggestions) != len(strategies):
            raise ValueError("模型未返回足够的回复建议。")
        return suggestions

    def _render_reply_prompt(
        self,
        *,
        session: ChatSession,
        messages: list[dict[str, Any]],
        emotion: str,
        strategy_instruction: str,
    ) -> str:
        return self.prompt_engine.render(
            "chat/reply",
            version=None,
            user_id=session.user_id,
            persona=json.dumps(session.persona, ensure_ascii=False, indent=2),
            goal=session.goal,
            messages=self._prompt_messages(messages),
            latest_emotion="负面" if emotion == "negative" else "中性",
            max_chars=MAX_REPLY_CHARS,
            strategy_instruction=strategy_instruction,
            forbidden_words=FORBIDDEN_WORDS,
        )

    def _append_message(
        self,
        session: ChatSession,
        message: dict[str, str],
    ) -> list[dict[str, Any]]:
        with transaction.atomic():
            locked = ChatSession.objects.select_for_update().get(id=session.id)
            locked.messages = [*locked.messages, message]
            locked.save(update_fields=("messages", "updated_at"))
        session.messages = locked.messages
        session.updated_at = locked.updated_at
        return list(session.messages)

    def _replace_last_assistant(
        self,
        session: ChatSession,
        message: dict[str, str],
    ) -> None:
        with transaction.atomic():
            locked = ChatSession.objects.select_for_update().get(id=session.id)
            messages = list(locked.messages)
            if messages and messages[-1].get("role") == "assistant":
                messages[-1] = message
            else:
                messages.append(message)
            locked.messages = messages
            locked.save(update_fields=("messages", "updated_at"))
        session.messages = locked.messages
        session.updated_at = locked.updated_at

    def _regeneration_context(self, session: ChatSession) -> list[dict[str, Any]]:
        messages = list(session.messages)
        if messages and messages[-1].get("role") == "assistant":
            return messages[:-1]
        return messages

    def _latest_emotion(self, messages: list[dict[str, Any]]) -> str:
        for message in reversed(messages):
            if message.get("role") == "counterpart":
                return classify_emotion(str(message.get("content", "")))
        return "neutral"

    def _prompt_messages(
        self,
        messages: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        role_labels = {
            "counterpart": "对方",
            "assistant": "我方建议",
        }
        return [
            {
                "role": role_labels.get(
                    str(message.get("role", "")),
                    str(message.get("role", "unknown")),
                ),
                "content": str(message.get("content", "")),
            }
            for message in messages[-HISTORY_MESSAGE_LIMIT:]
        ]

    def _message(self, role: str, content: str, **extra: str) -> dict[str, str]:
        return {
            "role": role,
            "content": content,
            "created_at": timezone.now().isoformat(),
            **extra,
        }
