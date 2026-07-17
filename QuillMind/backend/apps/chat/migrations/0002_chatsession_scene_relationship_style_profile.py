from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("styles", "0004_generationrecord_feedback"),
        ("chat", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatsession",
            name="relationship",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="chatsession",
            name="scene",
            field=models.CharField(
                choices=[
                    ("invite_dinner", "邀请聚餐"),
                    ("persuade_game", "说服朋友打游戏"),
                    ("comfort", "安慰"),
                    ("urge", "催促"),
                    ("custom", "自定义"),
                ],
                db_index=True,
                default="custom",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="chatsession",
            name="style_profile",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="chat_sessions",
                to="styles.styleprofile",
            ),
        ),
    ]
