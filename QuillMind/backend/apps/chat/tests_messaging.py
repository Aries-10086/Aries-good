from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import uuid

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase, override_settings
from django.urls import resolve, reverse
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework_simplejwt.tokens import AccessToken

from .auth import JWTQueryAuthMiddleware
from .consumers import ChatConsumer
from .messaging import (
    MAX_REPLY_CHARS,
    ChatReply,
    ChatMessageService,
    classify_emotion,
    truncate_reply,
)
from .views import ChatMessageView, ChatSuggestionView


PERSONA = {
    "role": "老朋友",
    "relationship": "认识多年",
    "tone": ["自然", "轻松"],
    "strategy": ["先回应，再推进"],
    "boundaries": ["不施压"],
    "preferred_phrases": ["有空的话"],
    "avoid_phrases": ["务必"],
    "success_signal": "对方愿意继续沟通",
}


class FakePromptEngine:
    def __init__(self):
        self.contexts = []

    def render(self, module, **context):
        self.contexts.append({"module": module, **context})
        return f"prompt-{len(self.contexts)}"


class FakeStreamGateway:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def stream(self, prompt, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        output = self.outputs[min(len(self.calls) - 1, len(self.outputs) - 1)]
        yield from output


def make_session():
    return SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        persona=PERSONA,
        goal="邀请朋友周末聚餐",
        messages=[],
        updated_at=None,
    )


def install_in_memory_persistence(service, session):
    def append_message(target, message):
        target.messages = [*target.messages, message]
        return list(target.messages)

    def replace_last(target, message):
        messages = list(target.messages)
        if messages and messages[-1]["role"] == "assistant":
            messages[-1] = message
        else:
            messages.append(message)
        target.messages = messages

    service._append_message = append_message
    service._replace_last_assistant = replace_last


class ChatMessageServiceTests(SimpleTestCase):
    def test_emotion_rule_and_reply_truncation(self):
        self.assertEqual(classify_emotion("最近有点累，不想出门"), "negative")
        self.assertEqual(classify_emotion("周末有空吗"), "neutral")
        self.assertEqual(len(truncate_reply("好" * 200)), MAX_REPLY_CHARS)

    def test_reply_streams_and_appends_counterpart_and_assistant(self):
        session = make_session()
        prompt_engine = FakePromptEngine()
        gateway = FakeStreamGateway([["别急，", "先休息一下，周末有空再说。"]])
        service = ChatMessageService(
            llm_gateway=gateway,
            prompt_engine=prompt_engine,
        )
        install_in_memory_persistence(service, session)

        reply = service.reply(session=session, content="我今天好累，不想动")

        self.assertEqual(reply.emotion, "negative")
        self.assertEqual(
            [message["role"] for message in session.messages],
            ["counterpart", "assistant"],
        )
        self.assertLessEqual(len(reply.text), MAX_REPLY_CHARS)
        context = prompt_engine.contexts[0]
        self.assertEqual(json.loads(context["persona"]), PERSONA)
        self.assertEqual(context["latest_emotion"], "负面")
        self.assertEqual(context["messages"][-1]["role"], "对方")

    def test_regenerate_replaces_last_reply_with_higher_temperature(self):
        session = make_session()
        session.messages = [
            {"role": "counterpart", "content": "这周太忙了"},
            {"role": "assistant", "content": "旧回复"},
        ]
        gateway = FakeStreamGateway([["新的回复"]])
        service = ChatMessageService(
            llm_gateway=gateway,
            prompt_engine=FakePromptEngine(),
        )
        install_in_memory_persistence(service, session)

        reply = service.reply(session=session, regenerate=True)

        self.assertEqual(reply.text, "新的回复")
        self.assertEqual(len(session.messages), 2)
        self.assertEqual(session.messages[-1]["content"], "新的回复")
        self.assertEqual(gateway.calls[0]["temperature"], 1.0)

    def test_suggestions_return_three_strategies_and_swap_returns_one(self):
        session = make_session()
        session.messages = [{"role": "counterpart", "content": "我有点烦"}]
        gateway = FakeStreamGateway(
            [["建议一"], ["建议二"], ["建议三"], ["换一个建议"]]
        )
        service = ChatMessageService(
            llm_gateway=gateway,
            prompt_engine=FakePromptEngine(),
        )

        suggestions = service.suggestions(session=session)
        swapped = service.suggestions(session=session, regenerate=True)

        self.assertEqual(suggestions, ["建议一", "建议二", "建议三"])
        self.assertEqual(swapped, ["换一个建议"])
        self.assertEqual(gateway.calls[-1]["temperature"], 1.05)

    def test_twenty_rounds_keep_the_same_persona(self):
        session = make_session()
        prompt_engine = FakePromptEngine()
        service = ChatMessageService(
            llm_gateway=FakeStreamGateway([["收到，我们慢慢聊。"]]),
            prompt_engine=prompt_engine,
        )
        install_in_memory_persistence(service, session)

        for index in range(20):
            service.reply(session=session, content=f"第 {index + 1} 轮对方消息")

        self.assertEqual(len(session.messages), 40)
        self.assertEqual(len(prompt_engine.contexts), 20)
        self.assertTrue(
            all(
                json.loads(context["persona"]) == PERSONA
                for context in prompt_engine.contexts
            )
        )
        self.assertLessEqual(
            len(prompt_engine.contexts[-1]["messages"]),
            40,
        )


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
    SIMPLE_JWT={
        "SIGNING_KEY": "test-signing-key-that-is-at-least-thirty-two-bytes",
    },
)
class ChatMessageRoutingTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = SimpleNamespace(id=uuid.uuid4(), is_authenticated=True)
        self.session = make_session()

    def test_message_and_suggestion_routes_resolve(self):
        session_id = uuid.uuid4()
        message_url = reverse(
            "chat-session-message",
            kwargs={"session_id": session_id},
        )
        suggestion_url = reverse(
            "chat-session-suggestions",
            kwargs={"session_id": session_id},
        )

        self.assertIs(resolve(message_url).func.view_class, ChatMessageView)
        self.assertIs(resolve(suggestion_url).func.view_class, ChatSuggestionView)

    @patch("apps.chat.views.ChatMessageService")
    @patch("apps.chat.views.get_object_or_404")
    def test_message_api_returns_generated_message(
        self,
        get_object_mock,
        service_class,
    ):
        message = {
            "role": "assistant",
            "content": "先休息一下，有空再聊。",
        }
        self.session.messages = [
            {"role": "counterpart", "content": "今天好累"},
            message,
        ]
        get_object_mock.return_value = self.session
        service_class.return_value.reply.return_value = ChatReply(
            text=message["content"],
            emotion="negative",
            message=message,
        )
        request = self.factory.post(
            f"/api/v1/chat/sessions/{self.session.id}/messages",
            {"content": "今天好累"},
            format="json",
        )
        force_authenticate(request, user=self.user)

        response = ChatMessageView.as_view()(request, session_id=self.session.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["emotion"], "negative")
        self.assertEqual(response.data["message"], message)
        self.assertEqual(get_object_mock.call_args.kwargs["user"], self.user)

    @patch("apps.chat.views.ChatMessageService")
    @patch("apps.chat.views.get_object_or_404")
    def test_suggestion_api_supports_swap(
        self,
        get_object_mock,
        service_class,
    ):
        get_object_mock.return_value = self.session
        service_class.return_value.suggestions.return_value = ["换一个建议"]
        request = self.factory.post(
            f"/api/v1/chat/sessions/{self.session.id}/suggestions",
            {"regenerate": True},
            format="json",
        )
        force_authenticate(request, user=self.user)

        response = ChatSuggestionView.as_view()(
            request,
            session_id=self.session.id,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["regenerate"])
        self.assertEqual(response.data["suggestions"], ["换一个建议"])

    def test_invalid_websocket_token_is_anonymous(self):
        captured = {}

        async def app(scope, receive, send):
            captured["user"] = scope["user"]

        middleware = JWTQueryAuthMiddleware(app)

        async def run():
            await middleware(
                {"query_string": b"token=invalid"},
                lambda: None,
                lambda message: None,
            )

        async_to_sync(run)()
        self.assertIsInstance(captured["user"], AnonymousUser)

    @patch("apps.chat.auth._get_user", new_callable=AsyncMock)
    def test_valid_websocket_token_sets_authenticated_user(self, get_user_mock):
        user = SimpleNamespace(id=uuid.uuid4(), is_authenticated=True)
        get_user_mock.return_value = user
        token = AccessToken()
        token["user_id"] = str(user.id)
        captured = {}

        async def app(scope, receive, send):
            captured["user"] = scope["user"]

        middleware = JWTQueryAuthMiddleware(app)

        async def run():
            await middleware(
                {"query_string": f"token={token}".encode()},
                lambda: None,
                lambda message: None,
            )

        async_to_sync(run)()
        self.assertIs(captured["user"], user)
        get_user_mock.assert_awaited_once_with(str(user.id))

    def test_websocket_rejects_invalid_jwt(self):
        from config.asgi import application

        async def run():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/chat/{uuid.uuid4()}/?token=invalid",
                headers=[
                    (b"host", b"localhost"),
                    (b"origin", b"http://localhost"),
                ],
            )
            connected, close_code = await communicator.connect()
            await communicator.disconnect()
            return connected, close_code

        connected, close_code = async_to_sync(run)()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4401)

    @patch("apps.chat.consumers.ChatMessageService.stream_reply")
    @patch.object(ChatConsumer, "_last_message", new_callable=AsyncMock)
    @patch.object(ChatConsumer, "_get_session", new_callable=AsyncMock)
    @patch("apps.chat.auth._get_user", new_callable=AsyncMock)
    def test_websocket_pushes_token_stream(
        self,
        get_user_mock,
        get_session_mock,
        last_message_mock,
        stream_mock,
    ):
        from config.asgi import application

        user = SimpleNamespace(id=uuid.uuid4(), is_authenticated=True)
        session = make_session()
        session.user_id = user.id
        get_user_mock.return_value = user
        get_session_mock.return_value = session
        last_message = {"role": "assistant", "content": "先休息一下。"}
        last_message_mock.return_value = last_message
        stream_mock.return_value = iter(["先休息", "一下。"])
        token = AccessToken()
        token["user_id"] = str(user.id)

        async def run():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/chat/{session.id}/?token={token}",
                headers=[
                    (b"host", b"localhost"),
                    (b"origin", b"http://localhost"),
                ],
            )
            connected, _ = await communicator.connect()
            await communicator.send_json_to(
                {"action": "message", "content": "我今天有点累"}
            )
            events = [await communicator.receive_json_from() for _ in range(4)]
            await communicator.disconnect()
            return connected, events

        connected, events = async_to_sync(run)()

        self.assertTrue(connected)
        self.assertEqual(
            [event["event"] for event in events],
            ["start", "token", "token", "complete"],
        )
        self.assertEqual(events[1]["text"] + events[2]["text"], "先休息一下。")
        self.assertEqual(events[-1]["message"], last_message)
