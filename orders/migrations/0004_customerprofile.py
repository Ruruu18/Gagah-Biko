# Generated manually for customer profile persistence.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_customer_profiles(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    CustomerProfile = apps.get_model('orders', 'CustomerProfile')

    for user in User.objects.all():
        full_name = user.get_full_name().strip() or user.email or user.username
        CustomerProfile.objects.get_or_create(
            user=user,
            defaults={'full_name': full_name},
        )


def backfill_order_users(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Order = apps.get_model('orders', 'Order')

    users_by_email = {
        user.email.lower(): user
        for user in User.objects.exclude(email='')
    }

    for order in Order.objects.filter(user__isnull=True).exclude(email=''):
        user = users_by_email.get(order.email.lower())
        if user:
            order.user = user
            order.save(update_fields=['user'])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('orders', '0003_emailotp_delete_phoneotp'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=255)),
                ('marketing_opt_in', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='customer_profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='order',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(backfill_customer_profiles, migrations.RunPython.noop),
        migrations.RunPython(backfill_order_users, migrations.RunPython.noop),
    ]
