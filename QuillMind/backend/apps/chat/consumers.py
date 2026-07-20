from __future__ import annotations

import asyncio

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .messaging import ChatMessageService
from .models import ChatSession


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.session = await self._get_session(user.id, self.session_id)
        if self.session is None:
            await self.close(code=4404)
            return

        self.generating = False
        await self.accept()

    async def receive_json(self, content, **kwargs):
        if self.generating:
            await self.send_json(
                {"event": "error", "detail": "上一条回复仍在生成中。"}
            )
            return

        action = content.get("action", "message")
        regenerate = action == "regenerate"
        message = str(content.get("content", "")).strip()
        if not regenerate and not message:
            await self.send_json({"event": "error", "detail": "请输入对方说的话。"})
            return

        self.generating = True
        await self.send_json(
            {
                "event": "start",
                "regenerate": regenerate,
                "emotion": self._emotion(message) if message else None,
            }
        )
        try:
            await self._stream_to_socket(message or None, regenerate)
            last_message = await self._last_message(self.session_id)
            await self.send_json(
                {
                    "event": "complete",
                    "message": last_message,
                }
            )
        except Exception:
            await self.send_json(
                {"event": "error", "detail": "回复生成失败，请稍后重试。"}
            )
        finally:
            self.generating = False

    async def _stream_to_socket(self, content: str | None, regenerate: bool):
        queue: asyncio.Queue[tuple[str, object]] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def produce():
            try:
                service = ChatMessageService()
                for token in service.stream_reply(
                    session=self.session,
                    content=content,
                    regenerate=regenerate,
                ):
                    loop.call_soon_threadsafe(queue.put_nowait, ("token", token))
            except Exception as exc:
                loop.call_soon_threadsafe(queue.put_nowait, ("error", exc))
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, ("done", None))

        producer = asyncio.create_task(asyncio.to_thread(produce))
        try:
            while True:
                event, data = await queue.get()
                if event == "token":
                    await self.send_json({"event": "token", "text": data})
                elif event == "error":
                    raise data
                elif event == "done":
                    break
        finally:
            await producer

    @database_sync_to_async
    def _get_session(self, user_id, session_id):
        return (
            ChatSession.objects.filter(
                id=session_id,
                user_id=user_id,
                status=ChatSession.Status.ACTIVE,
            )
            .select_related("user")
            .first()
        )

    @database_sync_to_async
    def _last_message(self, session_id):
        session = ChatSession.objects.only("messages").get(id=session_id)
        return session.messages[-1] if session.messages else None

    def _emotion(self, text: str) -> str:
        from .messaging import classify_emotion

        return classify_emotion(text)
