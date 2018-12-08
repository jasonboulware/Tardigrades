from django.conf import settings
from django.core.management.base import BaseCommand

from auth.models import CustomUser

class Command(BaseCommand):
    def handle(self, *args, **options):
        CustomUser.objects.get_or_create(
            pk=settings.ANONYMOUS_USER_ID,
            defaults={'username': settings.ANONYMOUS_DEFAULT_USERNAME})
