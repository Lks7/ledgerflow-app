from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lists", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="shoppingitem",
            name="platform",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
    ]
