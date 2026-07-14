from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("styles", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="styleprofile",
            name="description",
            field=models.TextField(blank=True),
        ),
    ]
