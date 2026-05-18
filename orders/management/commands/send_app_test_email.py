from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Send a test email using the configured Django SMTP settings.'

    def add_arguments(self, parser):
        parser.add_argument('recipient', help='Email address that should receive the test message.')

    def handle(self, *args, **options):
        recipient = options['recipient']

        missing = [
            name
            for name in ('EMAIL_HOST', 'EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD')
            if not getattr(settings, name, None)
        ]
        if missing:
            joined = ', '.join(missing)
            raise CommandError(f'Missing email setting(s): {joined}. Check eugeneproject/.env.')

        sent = send_mail(
            'Gagah Home Made-Biko test email',
            'Your Django email settings are working.',
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )

        if sent != 1:
            raise CommandError('Django did not report a delivered test email.')

        self.stdout.write(self.style.SUCCESS(f'Test email sent to {recipient}.'))
