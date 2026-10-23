from decimal import Decimal
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("chat", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="item",
            name="price",
            field=models.DecimalField(
                max_digits=10, decimal_places=2, null=True, blank=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                help_text="Unit price before VAT; leave blank if unknown.",
            ),
        ),
    ]
