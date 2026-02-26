from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ledger", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="JournalLog",
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
                ("timestamp", models.DateTimeField()),
                ("action", models.CharField(max_length=50)),
                ("journal_id", models.CharField(max_length=100)),
                ("date", models.CharField(blank=True, default="", max_length=20)),
                (
                    "description",
                    models.CharField(blank=True, default="", max_length=500),
                ),
                ("entries", models.JSONField(default=list)),
            ],
            options={
                "db_table": "ledger_journal_log",
                "ordering": ["-timestamp", "-id"],
            },
        ),
    ]
