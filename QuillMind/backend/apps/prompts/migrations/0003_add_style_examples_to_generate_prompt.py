from django.db import migrations


UPDATED_CONTENT = """你是一名中文写作搭档。请按照给定风格完成内容，让成稿像同一个人自然写出，而不是机械模仿词语。

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

{% if style_samples | default([]) %}
## 原文风格参考
只学习以下样本的表达节奏、措辞和标点习惯，不要照抄其中的事实或句子。
{% for sample in style_samples %}
### 样本 {{ loop.index }}
{{ sample }}
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
"""


def update_prompt(apps, schema_editor):
    PromptTemplate = apps.get_model("prompts", "PromptTemplate")
    PromptTemplate.objects.filter(
        module="styles/generate",
        version="v1.0.0",
    ).update(content=UPDATED_CONTENT)


class Migration(migrations.Migration):
    dependencies = [
        ("prompts", "0002_seed_prompt_templates_v1"),
    ]

    operations = [
        migrations.RunPython(update_prompt, migrations.RunPython.noop),
    ]
