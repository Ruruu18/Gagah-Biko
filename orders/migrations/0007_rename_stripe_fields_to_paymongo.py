from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0006_order_gcash_reference'),
    ]

    operations = [
        migrations.RenameField(
            model_name='order',
            old_name='stripe_checkout_session_id',
            new_name='paymongo_checkout_session_id',
        ),
        migrations.RenameField(
            model_name='order',
            old_name='stripe_payment_intent_id',
            new_name='paymongo_payment_intent_id',
        ),
    ]
