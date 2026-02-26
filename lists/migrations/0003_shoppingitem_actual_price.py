from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lists", "0002_shoppingitem_platform"),
    ]

    operations = [
        migrations.AddField(
            model_name="shoppingitem",
            name="actual_price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
    ]
