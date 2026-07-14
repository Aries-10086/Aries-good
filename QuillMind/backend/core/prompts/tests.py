from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from django.conf import settings
from django.test import SimpleTestCase

from .engine import PromptEngine
from .exceptions import PromptRenderError


class FakeQuerySet:
    def __init__(self, records):
        self.records = records

    def only(self, *fields):
        return self

    def first(self):
        return self.records[0] if self.records else None

    def order_by(self, *fields):
        self.records = sorted(self.records, key=lambda item: item.version)
        return self

    def values_list(self, field, flat=False):
        return [getattr(record, field) for record in self.records]


class FakeManager:
    def __init__(self, records):
        self.records = records

    def filter(self, **filters):
        matches = [
            record
            for record in self.records
            if all(getattr(record, field) == value for field, value in filters.items())
        ]
        return FakeQuerySet(matches)


def fake_model(*records):
    return type("FakePromptTemplate", (), {"objects": FakeManager(list(records))})


class PromptEngineTests(SimpleTestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.template_dir = Path(self.temp_dir.name)
        (self.template_dir / "styles").mkdir()
        (self.template_dir / "styles" / "generate.j2").write_text(
            "任务：{{ task }}；语气：{{ style_features.tone }}",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_renders_file_template_with_style_features(self):
        engine = PromptEngine(self.template_dir, model_class=fake_model())

        rendered = engine.render(
            "styles/generate",
            "v1.0.0",
            task="写一封邀请函",
            style_features={"tone": "自然"},
        )

        self.assertEqual(rendered, "任务：写一封邀请函；语气：自然")

    def test_active_database_template_overrides_file(self):
        record = SimpleNamespace(
            module="styles/generate",
            version="v1.0.0",
            content="DB：{{ task }}",
            is_active=True,
        )
        engine = PromptEngine(self.template_dir, model_class=fake_model(record))

        rendered = engine.render(
            "styles/generate",
            "v1.0.0",
            task="数据库模板",
        )

        self.assertEqual(rendered, "DB：数据库模板")

    def test_missing_context_raises_render_error(self):
        engine = PromptEngine(self.template_dir, model_class=fake_model())

        with self.assertRaises(PromptRenderError):
            engine.render("styles/generate", "v1.0.0", task="缺少风格")

    def test_ab_selection_is_stable_for_same_user(self):
        records = [
            SimpleNamespace(
                module="styles/generate",
                version="v1.0.0",
                content="A",
                is_active=True,
            ),
            SimpleNamespace(
                module="styles/generate",
                version="v1.1.0",
                content="B",
                is_active=True,
            ),
        ]
        engine = PromptEngine(self.template_dir, model_class=fake_model(*records))

        first = engine.select_version("styles/generate", user_id="user-42")
        second = engine.select_version("styles/generate", user_id="user-42")

        self.assertEqual(first, second)
        self.assertIn(first, {"v1.0.0", "v1.1.0"})


class PromptV1TemplateTests(SimpleTestCase):
    def setUp(self):
        self.engine = PromptEngine(
            settings.BASE_DIR / "templates" / "prompts",
            model_class=fake_model(),
        )

    def test_all_v1_templates_render_with_forbidden_section(self):
        cases = {
            "styles/extract": {
                "samples": ["其实别急吧，先看看日志。", "反正今天能修完。"],
            },
            "styles/generate": {
                "task": "写一封周五聚餐邀请",
                "style_description": "短句、口语化、偶尔使用“吧”",
                "style_features": {"平均句长": 12, "语气词": ["吧"]},
                "audience": "同事",
            },
            "chat/persona": {
                "scene": "邀请朋友周末打球",
                "relationship": "认识多年的朋友",
                "goal": "确认对方是否有空",
                "user_style": "自然、直接、会开一点玩笑",
            },
            "chat/reply": {
                "persona": {"tone": ["自然", "轻松"]},
                "goal": "约定周六下午见面",
                "messages": [
                    {"role": "friend", "content": "这周可能有点忙"},
                    {"role": "user", "content": "那周末呢？"},
                ],
                "latest_emotion": "犹豫",
            },
            "documents/report": {
                "document_type": "合同",
                "document_summary": "服务采购合同",
                "risks": [
                    {
                        "level": "高",
                        "type": "退款条款",
                        "quote": "费用不予退还",
                        "reason": "未区分违约责任",
                        "suggestion": "补充可退款情形和时间",
                    }
                ],
            },
        }

        for module, context in cases.items():
            with self.subTest(module=module):
                rendered = self.engine.render(module, "v1.0.0", **context)
                self.assertIn("[禁止事项]", rendered)
                self.assertNotIn("{{", rendered)
                self.assertNotIn("{%", rendered)
