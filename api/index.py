import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

app = get_wsgi_application()

if os.getenv("VERCEL"):
    call_command("migrate", interactive=False, verbosity=0)
    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    if admin_email and admin_password:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        admin_user, created = User.objects.get_or_create(
            username=admin_email,
            defaults={
                "email": admin_email,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        changed = False
        if not admin_user.email:
            admin_user.email = admin_email
            changed = True
        if not admin_user.is_staff:
            admin_user.is_staff = True
            changed = True
        if not admin_user.is_superuser:
            admin_user.is_superuser = True
            changed = True
        if created or not admin_user.has_usable_password():
            admin_user.set_password(admin_password)
            changed = True
        if changed:
            admin_user.save()
