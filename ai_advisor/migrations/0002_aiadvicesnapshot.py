from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai_advisor", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AIAdviceSnapshot",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("month", models.CharField(max_length=7, unique=True)),
                ("payload", models.JSONField(default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "ai_advisor_snapshot",
                "ordering": ["-month"],
            },
        ),
    ]
