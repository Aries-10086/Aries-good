from django.db import migrations


STRATEGY_SECTION = """{% if strategy_instruction | default("") %}
## 本次回复策略
{{ strategy_instruction }}
{% endif %}

"""


def update_prompt(apps, schema_editor):
    PromptTemplate = apps.get_model("prompts", "PromptTemplate")
    template = PromptTemplate.objects.filter(
        module="chat/reply",
        version="v1.0.0",
    ).first()
    if template and "## 本次回复策略" not in template.content:
        template.content = template.content.replace(
            "## 回复要求",
            f"{STRATEGY_SECTION}## 回复要求",
        )
        template.save(update_fields=("content", "updated_at"))


class Migration(migrations.Migration):
    dependencies = [
        ("prompts", "0003_add_style_examples_to_generate_prompt"),
    ]

    operations = [
        migrations.RunPython(update_prompt, migrations.RunPython.noop),
    ]
