"""
compile_translations -- Compile our gettext message files

This command does basically the same thing as Django's compilemessage command,
but it restricts its work to only the files we want
"""

from django.core.management.base import BaseCommand

from utils.management.commands import update_translations

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        for domain in update_translations.all_domains():
            for locale in update_translations.all_locales():
                self.stdout.write(
                    "compiling {}\n".format(domain.mo_path(locale.name)))
                locale.compile_mo_file(domain)
