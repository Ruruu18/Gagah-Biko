from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_customerprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_status',
            field=models.CharField(default='unpaid', max_length=50),
        ),
        migrations.AddField(
            model_name='order',
            name='stripe_checkout_session_id',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='order',
            name='stripe_payment_intent_id',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
