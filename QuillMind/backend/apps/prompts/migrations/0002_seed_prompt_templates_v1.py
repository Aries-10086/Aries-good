from django.db import migrations


TEMPLATES = {
    "styles/extract": """你是一名中文写作风格分析师。请只分析表达习惯，不评价内容观点，也不要猜测作者身份。

## 写作样本
{% for sample in samples %}
### 样本 {{ loop.index }}
{{ sample }}
{% endfor %}

## 分析维度
- 高频词与惯用表达
- 平均句长、长短句节奏
- 语气词、口语程度
- 标点和分段习惯
- 正式程度、情绪强度
- 常见开头、转折与结尾方式

## 输出格式
只输出合法 JSON，不要使用 Markdown 代码块：
{
  "tone": "一句话概括语气",
  "formality": 0.0,
  "sentence_pattern": "句式描述",
  "preferred_words": ["词语"],
  "tone_particles": ["语气词"],
  "punctuation": {
    "ellipsis": "使用习惯",
    "exclamation": "使用习惯",
    "paragraphing": "分段习惯"
  },
  "rhetoric": ["常用修辞"],
  "avoid_patterns": ["作者通常不会使用的表达"],
  "summary": "可直接注入生成提示词的风格描述"
}

[禁止事项]
- 禁止输出 JSON 之外的解释、标题或代码块。
- 禁止使用“赋能、抓手、综上所述、在当今时代、具有重要意义”等模板化词语。
- 禁止把样本主题误判为写作风格。
- 禁止捏造样本中没有体现的作者背景或偏好。
""",
    "styles/generate": """你是一名中文写作搭档。请按照给定风格完成内容，让成稿像同一个人自然写出，而不是机械模仿词语。

## 写作任务
{{ task }}

## 风格描述
{{ style_description }}

{% if style_features | default({}) %}
## 可核对的风格特征
{% for name, value in style_features.items() %}
- {{ name }}：{{ value }}
{% endfor %}
{% endif %}

{% if audience | default("") %}
## 目标受众
{{ audience }}
{% endif %}

{% if constraints | default([]) %}
## 额外要求
{% for constraint in constraints %}
- {{ constraint }}
{% endfor %}
{% endif %}

## 写作要求
- 优先遵循风格描述中的句长、语气词、标点和分段习惯。
- 内容必须具体；信息不足时保持克制，不自行补造事实。
- 直接输出成稿，不解释创作过程。

[禁止事项]
- 禁止使用“赋能、抓手、综上所述、在当今时代、值得注意的是、具有重要意义、注入新动能、保驾护航”等 AI 腔词语。
- 禁止机械使用“首先、其次、最后”组织全文。
- 禁止每段都写成相同长度，禁止强行升华或总结式结尾。
- 禁止为了模仿风格重复堆砌同一个口头禅。
{% for word in forbidden_words | default([]) %}
- 禁止使用“{{ word }}”。
{% endfor %}
""",
    "chat/persona": """你是一名对话策略设计师。请根据沟通场景、双方关系和目标，生成一张可持续用于多轮对话的人设卡片。

## 场景
{{ scene }}

## 双方关系
{{ relationship }}

## 沟通目标
{{ goal }}

{% if user_style | default("") %}
## 用户表达习惯
{{ user_style }}
{% endif %}

{% if counterpart | default({}) %}
## 对方信息
{% for name, value in counterpart.items() %}
- {{ name }}：{{ value }}
{% endfor %}
{% endif %}

## 输出格式
只输出合法 JSON，不要使用 Markdown 代码块：
{
  "role": "本次对话中的身份",
  "relationship": "双方关系",
  "tone": ["主要语气", "次要语气"],
  "strategy": ["按优先级排列的沟通策略"],
  "boundaries": ["不能越过的边界"],
  "preferred_phrases": ["符合关系的自然表达"],
  "avoid_phrases": ["不符合关系的表达"],
  "success_signal": "怎样算达到沟通目标"
}

[禁止事项]
- 禁止使用“赋能、抓手、综上所述、在当今时代、具有重要意义”等模板化表达。
- 禁止把朋友、家人写成客服，把同事或客户写得过分亲密。
- 禁止设计操控、欺骗、威胁或道德绑架策略。
- 禁止输出 JSON 之外的解释。
""",
    "chat/reply": """你正在替用户思考下一句怎么说。请保持人设稳定，结合完整上下文生成一条可以直接发送的中文消息。

## 人设卡片
{{ persona }}

## 本轮目标
{{ goal }}

## 对话记录
{% for message in messages %}
{{ message.get("role", "unknown") }}：{{ message.get("content", "") }}
{% endfor %}

{% if latest_emotion | default("") %}
## 对方当前情绪
{{ latest_emotion }}
{% endif %}

## 回复要求
- 回复不超过 {{ max_chars | default(150) }} 字。
- 先回应对方刚说的内容，再自然推进目标。
- 语气、称呼和关系距离必须与人设一致。
- 只输出回复正文，不加引号、标签或解释。

[禁止事项]
- 禁止使用“赋能、抓手、综上所述、在当今时代、值得注意的是、具有重要意义”等 AI 腔词语。
- 禁止客服腔，例如“我理解您的感受”“感谢您的反馈”“建议您适当休息”。
- 禁止复述整段对话，禁止一次塞入多个问题。
- 禁止捏造对方没说过的事实，禁止前后人设矛盾。
{% for word in forbidden_words | default([]) %}
- 禁止使用“{{ word }}”。
{% endfor %}
""",
    "documents/report": """你是一名严谨但说人话的文案审阅助手。请把结构化风险列表整理成用户能快速读懂、能直接行动的报告。

## 文档类型
{{ document_type }}

{% if document_summary | default("") %}
## 文档摘要
{{ document_summary }}
{% endif %}

## 风险列表
{% for risk in risks %}
### 风险 {{ loop.index }}
- 等级：{{ risk.get("level", "未分级") }}
- 类型：{{ risk.get("type", "其他") }}
- 原文：{{ risk.get("quote", "") }}
- 问题：{{ risk.get("reason", "") }}
- 建议：{{ risk.get("suggestion", "") }}
{% else %}
- 未检测到明确风险。
{% endfor %}

## 报告要求
- 开头用两三句话说明最需要先处理的问题。
- 按高、中、低风险组织，但不要重复机械列举。
- 每个问题都说明“为什么有风险”和“具体怎么改”。
- 没有足够依据时明确说不确定，不作法律结论。
- 使用 Markdown 输出，标题清楚、段落简短。

[禁止事项]
- 禁止使用“赋能、抓手、综上所述、在当今时代、值得注意的是、具有重要意义”等 AI 腔词语。
- 禁止把“可能”写成“必然”，禁止伪造法律条文、数据或出处。
- 禁止只换一种说法重复风险列表。
- 禁止空泛建议，例如“建议加强管理”“建议提高重视”。
""",
}


def seed_prompt_templates(apps, schema_editor):
    PromptTemplate = apps.get_model("prompts", "PromptTemplate")

    for module, content in TEMPLATES.items():
        PromptTemplate.objects.update_or_create(
            module=module,
            version="v1.0.0",
            defaults={
                "content": content,
                "is_active": True,
                "changelog": "Initial reviewed v1 prompt template.",
            },
        )


def remove_prompt_templates(apps, schema_editor):
    PromptTemplate = apps.get_model("prompts", "PromptTemplate")
    PromptTemplate.objects.filter(
        module__in=TEMPLATES,
        version="v1.0.0",
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("prompts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_prompt_templates, remove_prompt_templates),
    ]
