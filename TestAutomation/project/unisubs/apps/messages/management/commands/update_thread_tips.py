from django.core.management.base import BaseCommand
from django.db.models import Q
import logging
from messages.models import Message

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--days',
                    action='store_true',
                    dest='days',
                    default=None,
                    help='Days of history of threads to process, by default all messages in history')

    def handle(self, *args, **kwargs):
        threads = Message.objects.filter(thread__isnull=False)
        if kwargs['days'] is not None:
            threads = threads.filter(created__gt=datetime.datetime.now() - datetime.timedelta(days=kwargs['days']))
        threads = set(threads.values_list('thread', flat=True))
        num_threads = len(threads)
        self.stdout.write("Adding thread tips, found {} threads to process\n".format(num_threads))
        processed = 0
        for thread in threads:
            messages = Message.objects.filter(Q(thread=thread) | Q(id=thread), deleted_for_user=False).order_by('-created')
            if messages.count() > 0:
                messages.update(has_reply_for_user = True)
                last_message = messages[0]
                last_message.has_reply_for_user = False
                last_message.save()
            messages = Message.objects.filter(Q(thread=thread) | Q(id=thread), deleted_for_author=False).order_by('-created')
            if messages.count() > 0:
                messages.update(has_reply_for_author = True)
                last_message = messages[0]
                last_message.has_reply_for_author = False
                last_message.save()
            processed += 1
            self.stdout.write("\rProcessed {}/{} threads".format(processed, num_threads))
            self.stdout.flush()
        self.stdout.write('\nSuccessfully processed all threads\n')
