from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.urls import resolve, reverse

from core.llm import LLMResponse

from .models import ChatSession
from .serializers import ChatSessionCreateSerializer
from .services import PERSONA_FIELDS, PersonaGenerationError, PersonaService
from .views import ChatSessionDetailView, ChatSessionListCreateView


PERSONA = {
    "role": "一位关心朋友近况的老朋友",
    "relationship": "认识多年的朋友",
    "tone": ["自然", "轻松"],
    "strategy": ["先关心近况", "再自然提出邀请"],
    "boundaries": ["不给对方施压"],
    "preferred_phrases": ["周末有空的话，一起吃个饭？"],
    "avoid_phrases": ["务必出席"],
    "success_signal": "对方愿意确认一个方便的时间",
}


class FakePromptEngine:
    def __init__(self):
        self.calls = []

    def render(self, module, **context):
        self.calls.append((module, context))
        return "persona prompt"


class FakeGateway:
    def __init__(self, text):
        self.text = text
        self.calls = []

    def complete(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        return LLMResponse(text=self.text, provider="fake", model="fake")


class PersonaServiceTests(SimpleTestCase):
    def test_generates_complete_persona_from_prompt(self):
        prompt_engine = FakePromptEngine()
        gateway = FakeGateway(json.dumps(PERSONA, ensure_ascii=False))
        service = PersonaService(
            llm_gateway=gateway,
            prompt_engine=prompt_engine,
        )

        persona = service.generate(
            user_id=uuid.uuid4(),
            scene=ChatSession.Scene.INVITE_DINNER,
            relationship="老朋友",
            goal="邀请周末聚餐",
            user_style="短句、自然",
        )

        self.assertEqual(tuple(persona), PERSONA_FIELDS)
        self.assertEqual(persona["role"], PERSONA["role"])
        self.assertEqual(prompt_engine.calls[0][0], "chat/persona")
        context = prompt_engine.calls[0][1]
        self.assertEqual(context["scene"], "邀请聚餐")
        self.assertEqual(context["user_style"], "短句、自然")
        self.assertEqual(gateway.calls[0][1]["temperature"], 0.35)

    def test_accepts_json_code_fence(self):
        service = PersonaService(
            llm_gateway=FakeGateway(
                f"```json\n{json.dumps(PERSONA, ensure_ascii=False)}\n```"
            ),
            prompt_engine=FakePromptEngine(),
        )

        persona = service.generate(
            user_id=uuid.uuid4(),
            scene="custom",
            relationship="同事",
            goal="确认进度",
        )

        self.assertEqual(persona["success_signal"], PERSONA["success_signal"])

    def test_rejects_incomplete_persona(self):
        service = PersonaService(
            llm_gateway=FakeGateway('{"role": "朋友"}'),
            prompt_engine=FakePromptEngine(),
        )

        with self.assertRaises(PersonaGenerationError):
            service.generate(
                user_id=uuid.uuid4(),
                scene="comfort",
                relationship="朋友",
                goal="安慰对方",
            )


class ChatSessionSerializerTests(SimpleTestCase):
    @patch("apps.chat.serializers.ChatSession.objects.create")
    @patch("apps.chat.serializers.PersonaService.generate", return_value=PERSONA)
    def test_create_generates_persona_and_saves_session(
        self,
        generate_mock,
        create_mock,
    ):
        user = SimpleNamespace(id=uuid.uuid4())
        request = SimpleNamespace(user=user)
        session = ChatSession(
            id=uuid.uuid4(),
            scene=ChatSession.Scene.COMFORT,
            relationship="朋友",
            goal="安慰刚经历挫折的朋友",
            persona=PERSONA,
            messages=[],
        )
        create_mock.return_value = session
        serializer = ChatSessionCreateSerializer(
            data={
                "scene": "comfort",
                "relationship": "朋友",
                "goal": "安慰刚经历挫折的朋友",
            },
            context={"request": request},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        result = serializer.save()

        self.assertIs(result, session)
        generate_mock.assert_called_once_with(
            user_id=user.id,
            scene="comfort",
            relationship="朋友",
            goal="安慰刚经历挫折的朋友",
            user_style="",
        )
        self.assertEqual(create_mock.call_args.kwargs["user"], user)
        self.assertEqual(create_mock.call_args.kwargs["persona"], PERSONA)
        self.assertEqual(create_mock.call_args.kwargs["messages"], [])

    def test_rejects_unknown_scene(self):
        serializer = ChatSessionCreateSerializer(
            data={
                "scene": "unknown",
                "relationship": "朋友",
                "goal": "测试",
            },
            context={"request": SimpleNamespace(user=SimpleNamespace())},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("scene", serializer.errors)

    @patch("apps.chat.serializers.StyleProfile.objects.filter")
    def test_style_profile_must_belong_to_current_user(self, filter_mock):
        filter_mock.return_value.first.return_value = None
        user = SimpleNamespace(id=uuid.uuid4())
        profile_id = uuid.uuid4()
        serializer = ChatSessionCreateSerializer(
            data={
                "scene": "urge",
                "relationship": "同事",
                "goal": "确认交付时间",
                "style_profile_id": str(profile_id),
            },
            context={"request": SimpleNamespace(user=user)},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("style_profile_id", serializer.errors)
        filter_mock.assert_called_once_with(id=profile_id, user=user)


class ChatSessionRoutingTests(SimpleTestCase):
    def test_session_routes_resolve(self):
        self.assertIs(
            resolve("/api/v1/chat/sessions").func.view_class,
            ChatSessionListCreateView,
        )
        detail_url = reverse(
            "chat-session-detail",
            kwargs={"session_id": uuid.uuid4()},
        )
        self.assertIs(resolve(detail_url).func.view_class, ChatSessionDetailView)

    @patch("apps.chat.views.ChatSession.objects.filter")
    def test_querysets_are_limited_to_current_user(self, filter_mock):
        queryset = Mock()
        filter_mock.return_value = queryset
        queryset.select_related.return_value = queryset
        queryset.order_by.return_value = queryset
        user = SimpleNamespace(id=uuid.uuid4())

        list_view = ChatSessionListCreateView()
        list_view.request = SimpleNamespace(user=user)
        detail_view = ChatSessionDetailView()
        detail_view.request = SimpleNamespace(user=user)

        self.assertIs(list_view.get_queryset(), queryset)
        self.assertIs(detail_view.get_queryset(), queryset)
        self.assertEqual(filter_mock.call_count, 2)
        for call in filter_mock.call_args_list:
            self.assertEqual(call.kwargs, {"user": user})
