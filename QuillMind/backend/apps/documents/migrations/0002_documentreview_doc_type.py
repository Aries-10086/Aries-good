from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="documentreview",
            name="doc_type",
            field=models.CharField(
                choices=[
                    ("contract", "合同"),
                    ("report", "报告"),
                    ("testimony", "口供"),
                    ("general", "通用"),
                ],
                db_index=True,
                default="general",
                max_length=32,
            ),
        ),
    ]
