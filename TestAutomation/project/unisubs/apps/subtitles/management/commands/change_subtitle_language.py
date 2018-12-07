from optparse import make_option

from django.core.management.base import BaseCommand

from subtitles.models import SubtitleLanguage

class Command(BaseCommand):
    help = "Change a SubtitleLanguage's language code."

    def handle(self, *args, **options):
        if len(args) < 2:
            self.stderr.write("Usage: change_subtitle_language [id] [new_language_code]")
        subtitle_language = SubtitleLanguage.objects.get(id=args[0])
        subtitle_language.change_language_code(args[1])
