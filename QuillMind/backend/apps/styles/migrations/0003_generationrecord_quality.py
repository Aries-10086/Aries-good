from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("styles", "0002_styleprofile_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="generationrecord",
            name="quality",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
