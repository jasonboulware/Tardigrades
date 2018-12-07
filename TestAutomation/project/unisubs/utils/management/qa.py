import itertools
import logging
import mock
import string
import random

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.defaultfilters import slugify

from auth.models import CustomUser as User
from externalsites.google import VideoInfo
from utils.factories import *

class QASetupCommand(BaseCommand):
    """Base class for setting up data for QA testing """
    def handle(self, *args, **kwargs):
        settings.EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'
        self.video_counter = itertools.count(1)
        self.set_log_level()
        self.setup()

    def set_log_level(self):
        logging.getLogger().setLevel(logging.WARN)

    def printout(self, string):
        self.stdout.write(string + "\n")

    def print_header(self, text):
        middle = " {} ".format(text)
        total_length = 60
        leading = (total_length - len(middle)) // 2
        trailing = total_length - len(middle) - leading
        self.printout("-" * leading + text + "-" * trailing)

    def print_all_done(self):
        self.printout("")
        self.print_header("All Done")
        self.printout("")

    def input_string(self, prompt, help_text=None):
        if help_text is None:
            self.stdout.write("{}: ".format(prompt))
        else:
            self.stdout.write("{}\n({})\n".format(prompt, help_text))
        return raw_input().strip()

    def input_boolean(self, prompt, help_text=None):
        prompt = prompt + " (y/n)"
        while True:
            response = self.input_string(prompt, help_text)
            if response in ('y', 'yes'):
                return True
            elif response in ('n', 'no'):
                return False
            self.printout('Please type "y" or "n"')

    def input_integer(self, prompt, help_text=None):
        while True:
            response = self.input_string(prompt, help_text)
            try:
                return int(response)
            except ValueError:
                pass
            self.printout('Please enter a valid integer')

    def input_user(self, prompt, help_text=None):
        return self.create_user(self.input_string(prompt, help_text))

    def input_superuser(self, prompt, help_text=None):
        return self.create_superuser(self.input_string(prompt, help_text))

    def create_user(self, username, **create_data):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return UserFactory(username=username, **create_data)

    def create_superuser(self, username, **create_data):
        try:
            user = User.objects.get(username=username)
            if not (user.is_superuser and user.is_staff):
                user.is_superuser = user.is_staff = True
                user.save()
            return user
        except User.DoesNotExist:
            return UserFactory(username=username, is_staff=True,
                               is_superuser=True, **create_data)

    def create_video(self, team=None):
        url = ('https://www.youtube.com/watch?v=dQw4w9WgXcQ&foo=' +
               ''.join(random.choice(string.letters) for i in range(10)))
        # use mock.patch to skip the API query to youtube
        with mock.patch('externalsites.google.get_video_info') as mocker:
            mocker.return_value = VideoInfo(
                channel_id=u'UC38IQsAvIsxxjztdMZQtwHA',
                title=u'Test video #{}'.format(self.video_counter.next()),
                description=u'Created for QA Testing',
                duration=213,
                thumbnail_url=u'https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg')
            video = YouTubeVideoFactory(video_url__url=url)
        if team is not None:
            TeamVideoFactory(video=video, team=team)
        return video

    def slugify(self, name):
        return slugify(name)
