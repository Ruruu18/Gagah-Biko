from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CustomerProfile


@receiver(post_save, sender=get_user_model())
def ensure_customer_profile(sender, instance, created, **kwargs):
    if not created:
        return

    full_name = instance.get_full_name().strip() or instance.email or instance.username
    CustomerProfile.objects.get_or_create(
        user=instance,
        defaults={'full_name': full_name},
    )
