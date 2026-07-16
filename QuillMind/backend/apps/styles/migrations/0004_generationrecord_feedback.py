from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("styles", "0003_generationrecord_quality"),
    ]

    operations = [
        migrations.AddField(
            model_name="generationrecord",
            name="feedback",
            field=models.CharField(
                blank=True,
                choices=[("up", "有帮助"), ("down", "需改进")],
                max_length=8,
            ),
        ),
    ]
