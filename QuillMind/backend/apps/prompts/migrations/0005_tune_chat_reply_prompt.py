from django.db import migrations


SCENE_SECTION = """## 当前场景
{{ scene | default("自定义") }}
场景调优要求：{{ scene_guidance | default("依据人设和关系自然回应。") }}

"""

REPLY_REQUIREMENTS = """## 回复要求
- 回复不超过 {{ max_chars | default(150) }} 字。
- 通常用 1—3 个短句、20—80 字；像真人即时聊天，不写成通知、总结或小作文。
- 先回应对方刚说的内容，再自然推进目标；若对方情绪为负面，先接住情绪并弱化或暂停推进。
- 语气、称呼和关系距离必须与人设一致。
- 人设卡片是多轮对话中的固定约束，不得因对方临时措辞改变身份、关系或沟通边界。
- 最多提出一个问题；能用陈述句说清时不要反问。
- 只输出回复正文，不加引号、标签或解释。

[禁止事项]
- 禁止使用“赋能、抓手、综上所述、在当今时代、值得注意的是、具有重要意义、作为一个 AI、以下是、总的来说”等 AI 腔词语。
- 禁止客服腔，例如“我理解您的感受”“感谢您的反馈”“建议您适当休息”。
- 禁止套用“首先…其次…最后…”结构，禁止结尾附加“希望以上内容对你有所帮助”。
- 禁止复述整段对话，禁止一次塞入多个问题。
- 禁止捏造对方没说过的事实，禁止前后人设矛盾。
{% for word in forbidden_words | default([]) %}
- 禁止使用“{{ word }}”。
{% endfor %}"""


def tune_chat_reply_prompt(apps, schema_editor):
    PromptTemplate = apps.get_model("prompts", "PromptTemplate")
    template = PromptTemplate.objects.filter(
        module="chat/reply",
        version="v1.0.0",
    ).first()
    if not template:
        return

    content = template.content
    if "## 当前场景" not in content:
        content = content.replace(
            "## 对话记录",
            f"{SCENE_SECTION}## 对话记录",
        )
    requirements_start = content.find("## 回复要求")
    if requirements_start >= 0:
        content = content[:requirements_start] + REPLY_REQUIREMENTS
    template.content = content
    template.changelog = "按场景调优口语化、负面情绪响应、人设稳定与 AI 味约束"
    template.save(update_fields=("content", "changelog", "updated_at"))


class Migration(migrations.Migration):
    dependencies = [
        ("prompts", "0004_add_chat_reply_strategy"),
    ]

    operations = [
        migrations.RunPython(tune_chat_reply_prompt, migrations.RunPython.noop),
    ]
