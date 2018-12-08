# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

import binascii
from collections import deque
from datetime import datetime, timedelta
import hashlib
import hmac
import os
import random
import string
import urllib
import uuid

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import UserManager, User as BaseUser
from django.core.cache import cache
from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.urls import reverse
from django.db import IntegrityError
from django.db import models
from django.db import transaction
from django.db.models import Max
from django.db.models.signals import post_save
from django.utils.http import urlquote
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, ugettext

from auth import signals
from auth.validators import PasswordStrengthValidator
from caching import CacheGroup, ModelCacheManager
from utils.amazon import S3EnabledImageField
from utils import dates
from utils import secureid
from utils import translation
from utils.memoize import memoize
from utils.tasks import send_templated_email_async

import logging
logger = logging.getLogger(__name__)

ALL_LANGUAGES = [(val, _(name))for val, name in settings.ALL_LANGUAGES]
EMAIL_CONFIRMATION_DAYS = getattr(settings, 'EMAIL_CONFIRMATION_DAYS', 3)

DEFAULT_AVATAR_URL = ('https://s3.amazonaws.com/'
                      's3.www.universalsubtitles.org/'
                      'gravatar/avatar-default-{size}.png')

def generate_api_key():
        return binascii.b2a_hex(os.urandom(20))

class AnonymousUserCacheGroup(CacheGroup):
    def __init__(self):
        super(AnonymousUserCacheGroup, self).__init__('user:anon',
                                                      cache_pattern='user')

class CustomUserManager(UserManager):
    def create_with_unique_username(self, **kwargs):
        username = kwargs.pop('username')
        for username_try in self._unique_username_iter(username):
            try:
                with transaction.atomic():
                    return self.create(username=username_try, **kwargs)
            except IntegrityError:
                continue
        raise AssertionError("Ran out of username tries")

    def _unique_username_iter(self, username):
        """Yield potential usernames for create_with_unique_username.

        We generate usernames as follows:

            - First try the username unchanged
            - Then try the username with "00", "01", ..., "99" appended to it
            - Then try appending random 6-character strings to the username
            - If there is an "@" symbol in the username, then we insert the
                extra chars before the "@" instead of appending them
        """
        yield username
        if '@' in username:
            at_split = username.split('@', 1)
            part1 = at_split[0]
            part2 = '@' + at_split[1]
        else:
            part1 = username
            part2 = ''

        for i in xrange(100):
            yield '{}{:0>2d}{}'.format(part1, i, part2)
        while True:
            rand_string = ''.join(random.choice(string.ascii_letters +
                                                string.digits)
                                  for i in xrange(6))
            yield '{}{}{}'.format(part1, rand_string, part2)

    def search(self, query):
        qs = self.all()
        valid_term = False
        for term in [term.strip() for term in query.split()]:
            if term:
                valid_term = True
                try:
                    sql = """(LOWER(first_name) LIKE %s
                OR LOWER(last_name) LIKE %s
                OR LOWER(email) LIKE %s
                OR LOWER(username) LIKE %s
                OR LOWER(biography) LIKE %s)"""
                    term = '%' + term.lower() + '%'
                    qs = qs.extra(where=[sql], params=[term, term, term, term, term])
                except Exception as e:
                    logger.error(e)
        if valid_term:
            return qs
        else:
            return self.none()

    '''
    Gets all users except for the amara-bot
    '''
    def real_users(self):
        return self.all().exclude(username=settings.ANONYMOUS_DEFAULT_USERNAME)

def get_amara_anonymous_user():
    user, created = CustomUser.objects.get_or_create(
        pk=settings.ANONYMOUS_USER_ID,
        defaults={'username': settings.ANONYMOUS_DEFAULT_USERNAME})
    return user

class CustomUser(BaseUser, secureid.SecureIDMixin):
    AUTOPLAY_ON_BROWSER = 1
    AUTOPLAY_ON_LANGUAGES = 2
    DONT_AUTOPLAY = 3
    AUTOPLAY_CHOICES = (
        (AUTOPLAY_ON_BROWSER,
         'Autoplay subtitles based on browser preferred languages'),
        (AUTOPLAY_ON_LANGUAGES, 'Autoplay subtitles in languages I know'),
        (DONT_AUTOPLAY, 'Don\'t autoplay subtitles')
    )
    PLAYBACK_MODE_MAGIC = 1
    PLAYBACK_MODE_STANDARD = 2
    PLAYBACK_MODE_BEGINNER = 3
    PLAYBACK_MODE_CHOICES = (
        (PLAYBACK_MODE_MAGIC, 'Magical auto-pause'),
        (PLAYBACK_MODE_STANDARD, 'No automatic pausing'),
        (PLAYBACK_MODE_BEGINNER, 'Play for 4 seconds, then pause')
    )
    homepage = models.URLField(blank=True)
    preferred_language = models.CharField(
        max_length=16, choices=ALL_LANGUAGES, blank=True)
    picture = S3EnabledImageField(blank=True, upload_to='pictures/',
                                  thumb_sizes=[(240, 240), (110, 110), (100, 100), (50, 50), (30, 30)])
    valid_email = models.BooleanField(default=False)

    # if true, items that end on the user activity stream will also be
    # sent as email
    notify_by_email= models.BooleanField(default=True)
    # if true, items that end on the user activity stream will also be
    # sent as a message
    notify_by_message = models.BooleanField(default=True)
    allow_3rd_party_login = models.BooleanField(default=False)
    biography = models.TextField('Bio', blank=True)
    autoplay_preferences = models.IntegerField(
        choices=AUTOPLAY_CHOICES, default=AUTOPLAY_ON_BROWSER)
    award_points = models.IntegerField(default=0)
    last_ip = models.GenericIPAddressField(blank=True, null=True)
    # videos witch are related to user. this is for quicker queries
    videos = models.ManyToManyField('videos.Video', blank=True)
    # for some login backends we end up with a full name but not
    # a first name, last name pair.
    full_name = models.CharField(max_length=63, blank=True, default='')
    partner = models.ForeignKey('teams.Partner', blank=True, null=True)
    is_partner = models.BooleanField(default=False)
    pay_rate_code = models.CharField(max_length=3, blank=True, default='')
    can_send_messages = models.BooleanField(default=True)
    show_tutorial = models.BooleanField(default=True)
    # Whenever a user hides the "You have XX new messages" alert, we record
    # the id of the last message.  We don't show the alert again until the
    # user has a message newer than that message.
    last_hidden_message_id = models.PositiveIntegerField(blank=True,
                                                         default=0)
    playback_mode = models.IntegerField(
        choices=PLAYBACK_MODE_CHOICES, default=PLAYBACK_MODE_STANDARD)
    created_by = models.ForeignKey('self', null=True, blank=True,
                                   related_name='created_users')
    # For storing usernames of deactivated accounts, deleted accounts should not store the old username
    username_old = models.CharField(max_length=30, blank=True, null=True, default='')

    SECURE_ID_KEY = 'User'

    objects = CustomUserManager()

    cache = ModelCacheManager(default_cache_pattern='user')

    # Fields that constitute a user's profile, things like names, bios, etc.
    # When these change we emit the user_profile_changed signal.
    PROFILE_FIELDS = [
        'first_name', 'last_name', 'full_name', 'biography', 'picture',
        'homepage', 'email',
    ]

    class Meta:
        db_table = 'auth_customuser'
        verbose_name = 'User'

    def __init__(self, *args, **kwargs):
        super(CustomUser, self).__init__(*args, **kwargs)
        self.start_tracking_profile_fields()

    def __unicode__(self):
        if self.is_amara_anonymous:
            return settings.ANONYMOUS_FULL_NAME
        elif not self.is_active:
            return ugettext('Retired user')
        elif self.first_name or self.last_name:
            return self.get_full_name()
        elif self.full_name:
            return self.full_name
        else:
            return self.username

    @staticmethod
    def generate_random_username():
        username = str(uuid.uuid4())[0:30]
        try:
            CustomUser.objects.get(username=username)
            return generate_random_username()
        except CustomUser.DoesNotExist:
            return username;

    @property
    def display_username(self):
        if self.is_active:
            return self.username
        else:
            return ugettext('Retired user')

    @property
    def username_with_fullname(self):
        if self.is_active:
            return self.username + ("" if unicode(self) == self.username 
                                       else " ({})".format(unicode(self)))
        else:
            return ugettext('Retired user')

    # Returns a dictionary in the select2 data format
    def get_select2_format(self):
        return { 'id' : self.username,
                 'text': self.username_with_fullname }

    def sent_message(self):
        """
        Should be called each time a user sends a message.
        This is used to control if a user is spamming.
        """
        if hasattr(settings, 'MESSAGES_SENT_WINDOW_MINUTES') and \
           hasattr(settings, 'MESSAGES_SENT_LIMIT'):
            SentMessageDate.objects.sent_message(self)
            self._check_sent_messages()

    def _check_sent_messages(self):
        if hasattr(settings, 'MESSAGES_SENT_WINDOW_MINUTES') and \
           hasattr(settings, 'MESSAGES_SENT_LIMIT'):
            if SentMessageDate.objects.check_too_many_messages(self):
                self.de_activate()

    def de_activate(self):
        if not self.is_superuser:
            self.is_active = False
            self.save()
            import tasks
            tasks.notify_blocked_user.delay(self)

    def deactivate_account(self):
        with transaction.atomic():
            self.unlink_external()
            self.team_members.all().delete()
            self.username_old = self.username
            self.username = CustomUser.generate_random_username()
            self.is_active = False
            self.save()
            signals.user_account_deactivated.send(sender=self)

    def delete_account_data(self):
        # Alternate implementation is to blank all the fields except for some fields
        # indicated in skip_fields
        #
        # for field in self._meta.fields:
        #     if field.name in skip_fields:
        #         continue
        #     if field.default != NOT_PROVIDED:
        #         setattr(self, field.name, field.default)
        #     else:
        #         setattr(self, field.name, None)

        self.username = CustomUser.generate_random_username()
        self.username_old = None
        self.first_name = ""
        self.last_name = ""
        self.picture = None
        self.email= ""
        self.homepage = ""
        self.biography = ""
        self.full_name = ""
        self.save()

    # Deletes videos this user has uploaded and no one else has added subtitles to
    # Also deletes uploaded videos without subtitles
    # Does not delete team videos
    def delete_self_subtitled_videos(self):
        for video in self.videos.all():
            if (video.is_solo_subtitled_by_uploader() 
                and not video.is_team_video()):
                video.delete()

    def has_fullname_set(self):
        return any([self.first_name, self.last_name, self.full_name])

    def display_name(self):
        if self.has_fullname_set():
            return u'{} ({})'.format(unicode(self), self.username)
        else:
            return unicode(self.username)

    def save(self, *args, **kwargs):
        send_confirmation = False

        if not self.email:
            self.valid_email = False
        elif self.pk:
            try:
                before_save = self.__class__._default_manager.get(pk=self.pk)
                send_confirmation = before_save.email != self.email
            except models.ObjectDoesNotExist:
                send_confirmation = True
        elif self.email:
            send_confirmation = True

        if send_confirmation:
            self.valid_email = False

        send_email_confirmation = kwargs.pop('send_email_confirmation', True)
        if self.pk:
            self.check_profile_changed()
        super(CustomUser, self).save(*args, **kwargs)
        self.start_tracking_profile_fields()

        if send_confirmation and send_email_confirmation:
            EmailConfirmation.objects.send_confirmation(self)

    def start_tracking_profile_fields(self):
        self._initial_profile_data = self.calc_profile_data()

    def calc_profile_data(self):
        return {
            name: getattr(self, name)
            for name in CustomUser.PROFILE_FIELDS
        }

    def check_profile_changed(self):
        if self.calc_profile_data() != self._initial_profile_data:
            signals.user_profile_changed.send(self)

    def clean(self):
        if '$' in self.username:
            raise ValidationError("usernames can't contain the '$' character")

    def set_last_hidden_message_id(self, request, message_id):
        if message_id != self.last_hidden_message_id:
            self.last_hidden_message_id = message_id
            self.save()
            # cycle the session key to bust the varnish cache
            request.session.cycle_key()

    def new_messages_count(self):
        """
        Number of messages we should show in the "You have XX new messages
        alert"

        These are messages that:
          - Are unread
          - Have come in after the last time the user hide that message,
            or viewed their inbox

        """
        from messages.models import Message
        qs = (Message.objects.for_user(self)
              .filter(read=False, id__gt=self.last_hidden_message_id))
        return qs.count()

    def last_message_id(self):
        """
        The id of the last message for the user.

        Returns: message id, or 0 if there are no messages
        """
        from messages.models import Message
        qs = Message.objects.for_user(self).order_by('-id')[:1]
        if qs:
            return qs[0].id
        else:
            return 0

    def tutorial_was_shown(self):
        CustomUser.objects.filter(pk=self.id).update(show_tutorial=False)

    def set_playback_mode(self, playback_mode):
        CustomUser.objects.filter(pk=self.id).update(playback_mode=playback_mode)

    @classmethod
    def displayable_users(self, ids):
        return self.objects.filter(pk__in=ids).values_list('pk', 'first_name', 'last_name', 'username')

    @classmethod
    def video_followers_change_handler(cls, sender, instance, action, reverse, model, pk_set, **kwargs):
        from videos.models import SubtitleLanguage

        if reverse and action == 'post_add':
            #instance is User
            for video_pk in pk_set:
                cls.videos.through.objects.get_or_create(video__pk=video_pk, customuser=instance, defaults={'video_id': video_pk})
        elif reverse and action == 'post_remove':
            #instance is User
            for video_pk in pk_set:
                if not SubtitleLanguage.objects.filter(followers=instance, video__pk=video_pk).exists():
                    instance.videos.remove(video_pk)
        elif not reverse and action == 'post_add':
            #instance is Video
            for user_pk in pk_set:
                cls.videos.through.objects.get_or_create(video=instance, customuser__pk=user_pk, defaults={'customuser_id': user_pk})
        elif not reverse and action == 'post_remove':
            #instance is Video
            for user_pk in pk_set:
                if not SubtitleLanguage.objects.filter(followers__pk=user_pk, video=instance).exists():
                    instance.customuser_set.remove(user_pk)
        elif reverse and action == 'post_clear':
            #instance is User
            cls.videos.through.objects.filter(customuser=instance) \
                .exclude(video__subtitlelanguage__followers=instance).delete()
        elif not reverse and action == 'post_clear':
            #instance is Video
            cls.videos.through.objects.filter(video=instance) \
                .exclude(customuser__followed_languages__video=instance).delete()

    @classmethod
    def sl_followers_change_handler(cls, sender, instance, action, reverse, model, pk_set, **kwargs):
        from videos.models import Video, SubtitleLanguage

        if reverse and action == 'post_add':
            #instance is User
            for sl_pk in pk_set:
                sl = SubtitleLanguage.objects.get(pk=sl_pk)
                cls.videos.through.objects.get_or_create(video=sl.video, customuser=instance)
        elif reverse and action == 'post_remove':
            #instance is User
            for sl_pk in pk_set:
                if not Video.objects.filter(followers=instance, subtitlelanguage__pk=sl_pk).exists():
                    sl = SubtitleLanguage.objects.get(pk=sl_pk)
                    instance.videos.remove(sl.video)
        elif not reverse and action == 'post_add':
            #instance is SubtitleLanguage
            for user_pk in pk_set:
                cls.videos.through.objects.get_or_create(video=instance.video, customuser__pk=user_pk, defaults={'customuser_id': user_pk})
        elif not reverse and action == 'post_remove':
            #instance is SubtitleLanguage
            for user_pk in pk_set:
                if not Video.objects.filter(followers__pk=user_pk, subtitlelanguage=instance).exists():
                    instance.video.customuser_set.remove(user_pk)
        elif reverse and action == 'post_clear':
            #instance is User
            cls.videos.through.objects.filter(customuser=instance) \
                .exclude(video__subtitlelanguage__followers=instance).delete()
        elif not reverse and action == 'post_clear':
            #instance is SubtitleLanguage
            cls.videos.through.objects.filter(video=instance) \
                .exclude(customuser__followed_languages__video=instance.video).delete()

    def get_languages(self):
        """Get a list of language codes that the user speaks."""
        return self.cache.get_or_calc("languages", self.calc_languages)

    def calc_languages(self):
        return list(self.userlanguage_set.order_by("priority").values_list('language', flat=True))

    def set_languages(self, languages):
        with transaction.atomic():
            # need to delete all the set languages since there is some funky stuff
            # happening if a user sets the same languages but with different priorities
            self.userlanguage_set.all().delete()
            self.userlanguage_set.set([
                UserLanguage.objects.create(
                    user=self, language=l["language"], priority=l["priority"])
                for l in languages
            ])
        self.cache.invalidate()
        signals.user_profile_changed.send(self)

    def get_language_names(self):
        """Get a list of language names that the user speaks."""
        return [translation.get_language_label(lc)
                for lc in self.get_languages()]

    def get_language_codes_and_names(self):
        """Get a list of language codes/names that the user speaks."""
        return [(lc, translation.get_language_label(lc))
                for lc in self.get_languages()]

    def speaks_language(self, language_code):
        return language_code in [l.language for l in self.get_languages()]

    def is_team_manager(self):
        cached_value = self.cache.get('is-manager')
        if cached_value is not None:
            return cached_value
        is_manager = self.managed_teams().exists()
        self.cache.set('is-manager', is_manager)
        return is_manager

    def managed_teams(self, include_manager=True):
        from teams.models import TeamMember
        possible_roles = [TeamMember.ROLE_OWNER, TeamMember.ROLE_ADMIN]
        if include_manager:
            possible_roles.append(TeamMember.ROLE_MANAGER)
        return self.teams.filter(members__role__in=possible_roles)

    def messageable_teams(self):
        from teams.models import Team
        from teams.permissions import can_message_all_members

        teams = self.teams.all()
        messageable_team_ids = [t.id for t in teams if can_message_all_members(t, self)]

        partners = self.managed_partners.all()
        teams = [list(p.teams.all()) for p in partners]
        partner_teams_ids = [team.id for qs in teams for team in qs]

        messageable_team_ids = messageable_team_ids + partner_teams_ids
        return Team.objects.filter(id__in=messageable_team_ids)

    def open_tasks(self):
        from teams.models import Task
        return Task.objects.incomplete().filter(assignee=self)

    def _get_gravatar(self, size, default='mm'):
        url = "https://www.gravatar.com/avatar/" + hashlib.md5(self.email.lower().encode('utf-8')).hexdigest() + "?"
        url += urllib.urlencode({'d': default, 's':str(size)})
        return url

    # old UI avatars
    def _get_avatar_by_size(self, size):
        if self.picture:
            return self.picture.thumb_url(size, size)
        else:
            return self._get_gravatar(size)

    def avatar(self):
        return self._get_avatar_by_size(100)

    def small_avatar(self):
        return self._get_avatar_by_size(50)

    def large_avatar(self):
        return self._get_avatar_by_size(240)

    # future UI avatar
    def _get_avatar(self, size):
        if self.picture:
            return self.picture.thumb_url(size, size)
        else:
            return self._get_gravatar(
                size, default=DEFAULT_AVATAR_URL.format(size=size))

    def avatar_tag(self):
        avatar = self._get_avatar(30)
        return mark_safe('<span class="avatar"><img src="{}"></span>'.format(avatar))

    def avatar_tag_alert(self):
        avatar = self._get_avatar(30)
        return mark_safe('<span class="avatar avatar-alert"><img src="{}"></span>'.format(avatar))

    def avatar_tag_medium(self):
        avatar = self._get_avatar(50)
        return mark_safe('<span class="avatar avatar-md"><img src="{}"></span>'.format(avatar))

    def avatar_tag_large(self):
        avatar = self._get_avatar(100)
        return mark_safe('<span class="avatar avatar-lg"><img src="{}"></span>'.format(avatar))

    def avatar_tag_extra_large(self):
        avatar = self._get_avatar(110)
        return mark_safe('<span class="avatar avatar-xl"><img src="{}"></span>'.format(avatar))

    def get_absolute_url(self):
        return reverse('profiles:profile', args=(self.username,))

    def send_message_url(self, absolute_url=False):
        url = '{}?user={}'.format(reverse('messages:new'),
                                  urlquote(self.username))
        if absolute_url:
            url = "{}://{}{}".format(settings.DEFAULT_PROTOCOL,
                                     settings.HOSTNAME, url)
        return url

    @property
    def language(self):
        return self.get_preferred_language_display()

    def guess_best_lang(self, request=None):

        if self.preferred_language:
            return self.preferred_language

        user_languages = self.get_languages()
        if user_languages:
            return user_languages[0]

        if request:
            languages = translation.get_user_languages_from_request(request)
            if languages:
                return languages[0]

        return 'en'

    def guess_is_rtl(self, request=None):
        return translation.is_rtl(self.guess_best_lang(request))

    @models.permalink
    def profile_url(self):
        return ('profiles:profile', [self.pk])

    def hash_for_video(self, video_id):
        return hashlib.sha224(settings.SECRET_KEY+str(self.pk)+video_id).hexdigest()

    @classmethod
    def get_amara_anonymous(cls):
        return get_amara_anonymous_user()

    @property
    def is_amara_anonymous(self):
        return self.pk == settings.ANONYMOUS_USER_ID

    @property
    def is_external(self):
        """
        Checks whether accout is external
        It can me an OpeenId link or a token stored as
        a ThirdPartyAccount
        """
        try:
            l = self.openid_connect_link
            return True
        except:
            from thirdpartyaccounts import get_thirdpartyaccount_types
            for thirdpartyaccount_type in get_thirdpartyaccount_types():
                m = apps.get_model(thirdpartyaccount_type[0], thirdpartyaccount_type[1])
                if (m is not None) and (len(m.objects.for_user(self)) > 0):
                    return True
        return False

    def has_valid_password(self):
        # remove this post-1.9 when setting is used
        validator = PasswordStrengthValidator()
        try:
            validator.validate(self.password)
        except ValidationError:
            return False
        return len(self.password) > 0 and self.has_usable_password()

    '''
    Unlinks external authentication accounts (OAuth, Google, Facebook, etc. logins)
    '''
    def unlink_external(self):
        from thirdpartyaccounts import get_thirdpartyaccount_types
        for thirdpartyaccount_type in get_thirdpartyaccount_types():
            m = apps.get_model(thirdpartyaccount_type[0], thirdpartyaccount_type[1])
            if m is not None:
                m.objects.for_user(self).delete()
        try:
            self.openid_connect_link.delete()
        except:
            pass

    def check_api_key(self, key):
        try:
            return self.api_key.key == key
        except AmaraApiKey.DoesNotExist:
            return False

    def get_api_key(self):
        return AmaraApiKey.objects.get_or_create(user=self)[0].key

    def ensure_api_key_created(self):
        AmaraApiKey.objects.get_or_create(user=self)

def create_custom_user(sender, instance, created, **kwargs):
    if created:
        values = {}
        for field in sender._meta.local_fields:
            values[field.attname] = getattr(instance, field.attname)
        user = CustomUser(**values)
        user.save()

post_save.connect(create_custom_user, BaseUser)


class Awards(models.Model):
    COMMENT = 1
    START_SUBTITLES = 2
    START_TRANSLATION = 3
    EDIT_SUBTITLES = 4
    EDIT_TRANSLATION = 5
    RATING = 6
    TYPE_CHOICES = (
        (COMMENT, _(u'Add comment')),
        (START_SUBTITLES, _(u'Start subtitles')),
        (START_TRANSLATION, _(u'Start translation')),
        (EDIT_SUBTITLES, _(u'Edit subtitles')),
        (EDIT_TRANSLATION, _(u'Edit translation'))
    )
    points = models.IntegerField()
    type = models.IntegerField(choices=TYPE_CHOICES)
    user = models.ForeignKey(CustomUser, null=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'auth_awards'

    def _set_points(self):
        if self.type == self.COMMENT:
            self.points = 10
        elif self.type == self.START_SUBTITLES:
            self.points = 100
        elif self.type == self.START_TRANSLATION:
            self.points = 100
        elif self.type == self.EDIT_SUBTITLES:
            self.points = 50
        elif self.type == self.EDIT_TRANSLATION:
            self.points = 50
        else:
            self.points = 0

    def save(self, *args, **kwrags):
        self.points or self._set_points()
        if not self.pk:
            CustomUser.objects.filter(pk=self.user.pk).update(award_points=models.F('award_points')+self.points)
        return super(Awards, self).save(*args, **kwrags)

    @classmethod
    def on_comment_save(cls, sender, instance, created, **kwargs):
        if created:
            try:
                cls.objects.get_or_create(user=instance.user, type = cls.COMMENT)
            except MultipleObjectsReturned:
                pass

    @classmethod
    def on_subtitle_version_save(cls, sender, instance, created, timestamp=None, **kwargs):
        if not instance.user:
            return

        if created and instance.version_no == 0:
            if instance.language.is_original:
                type = cls.START_SUBTITLES
            else:
                type = cls.START_TRANSLATION
        else:
            if instance.language.is_original:
                type = cls.EDIT_SUBTITLES
            else:
                type = cls.EDIT_TRANSLATION
        try:
            cls.objects.get_or_create(user=instance.user, type=type)
        except MultipleObjectsReturned:
            pass

class UserLanguage(models.Model):
    PROFICIENCY_CHOICES = (
        (1, _('understand enough')),
        (2, _('understand 99%')),
        (3, _('write like a native')),
    )
    user = models.ForeignKey(CustomUser)
    language = models.CharField(max_length=16, choices=ALL_LANGUAGES, verbose_name='languages')
    proficiency = models.IntegerField(choices=PROFICIENCY_CHOICES, default=1)
    priority = models.IntegerField(null=True)
    follow_requests = models.BooleanField(
        default=False,
        verbose_name=_('follow requests in language'))

    class Meta:
        db_table = 'auth_userlanguage'
        unique_together = ['user', 'language']

    def save(self, *args, **kwargs):
        super(UserLanguage, self).save(*args, **kwargs)
        CustomUser.cache.invalidate_by_pk(self.user_id)

    def delete(self, *args, **kwargs):
        super(UserLanguage, self).delete(*args, **kwargs)
        CustomUser.cache.invalidate_by_pk(self.user_id)

class Announcement(models.Model):
    content = models.CharField(max_length=500)
    created = models.DateTimeField(help_text=_(u'This is date when start to display announcement. And only the last will be displayed.'))
    hidden = models.BooleanField(default=False)

    cache_key = 'last_accouncement'
    hide_cookie_name = 'hide_accouncement'
    cookie_date_format = '%d/%m/%Y %H:%M:%S'

    class Meta:
        db_table = 'auth_announcement'
        ordering = ['-created']

    @classmethod
    def clear_cache(cls):
        cache.delete(cls.cache_key)

    def save(self, *args, **kwargs):
        super(Announcement, self).save(*args, **kwargs)
        self.clear_cache()

    def delete(self, *args, **kwargs):
        self.clear_cache()
        return super(Announcement, self).delete(*args, **kwargs)

    @classmethod
    def last(cls, hidden_date=None):
        last = cache.get(cls.cache_key)
        if last == 0:
            return None

        if last is None:
            try:
                qs = cls.objects.filter(created__lte=datetime.today()) \
                    .filter(hidden=False)
                last = qs[0:1].get()
            except cls.DoesNotExist:
                last = 0
            cache.set(cls.cache_key, last, 60*60)

        if hidden_date and last and last.created < hidden_date:
            return None

        return last

class EmailConfirmationManager(models.Manager):

    def confirm_email(self, confirmation_key):
        try:
            confirmation = self.get(confirmation_key=confirmation_key)
        except self.model.DoesNotExist:
            return None
        if not confirmation.key_expired():
            from messages import tasks as notifier
            user = confirmation.user
            user.valid_email = True
            user.save()
            notifier.email_confirmed.delay(user.pk)
            return user

    def send_confirmation(self, user):
        assert user.email
        from messages.models import Message

        self.filter(user=user).delete()

        salt = hashlib.sha1(str(random.random())+settings.SECRET_KEY).hexdigest()[:5]
        confirmation_key = hashlib.sha1(salt + user.email.encode('utf-8')).hexdigest()
        path = reverse("auth:confirm_email", args=[confirmation_key])
        activate_url = u"{}://{}{}".format(settings.DEFAULT_PROTOCOL,
                                           settings.HOSTNAME, path)
        context = {
            "user": user,
            "activate_url": activate_url,
            "confirmation_key": confirmation_key,
            'HOSTNAME': settings.HOSTNAME,
            'BASE_URL': "%s://%s"  % (settings.DEFAULT_PROTOCOL,
                                      settings.HOSTNAME)
        }
        subject = u'Please confirm your email address for Amara'
        send_templated_email_async.delay(user, subject, "messages/email/email-confirmation.html", context)
        return self.create(
            user=user,
            sent=datetime.now(),
            confirmation_key=confirmation_key)

    def delete_expired_confirmations(self):
        d = datetime.now() - timedelta(days=EMAIL_CONFIRMATION_DAYS)
        self.filter(sent__lt=d).delete()

class EmailConfirmation(models.Model):

    user = models.ForeignKey(CustomUser)
    sent = models.DateTimeField()
    confirmation_key = models.CharField(max_length=40)

    objects = EmailConfirmationManager()

    def __unicode__(self):
        return u"confirmation for %s" % self.user.email

    class Meta:
        db_table = 'auth_emailconfirmation'
        verbose_name = _("e-mail confirmation")
        verbose_name_plural = _("e-mail confirmations")

    def key_expired(self):
        expiration_date = self.sent + timedelta(days=EMAIL_CONFIRMATION_DAYS)
        return expiration_date <= datetime.now()
    key_expired.boolean = True

class LoginTokenManager(models.Manager):
    def get_expired(self):
        expires_in = datetime.now() - LoginToken.EXPIRES_IN
        return self.filter(created__lt=expires_in)

    def generate_token(self, user):
        new_uuid = uuid.uuid4()
        return hmac.new("%s%s" % (user.pk, str(new_uuid)), digestmod=hashlib.sha1).hexdigest()

    def for_user(self, user, updates=True):
        try:
           lt = self.get(user=user)
           if updates:
               lt.token = self.generate_token(user)
               lt.created = datetime.now()
               lt.save()
        except LoginToken.DoesNotExist:
            lt = self.create(user=user, token=self.generate_token(user))
        return lt

class LoginToken(models.Model):
    """
    Links a user account to a secret, this allows a user to be logged in
    just by clicking on a URL. Mostly 3rd parties need this when creating
    content on a user's behalf and then redirecting them to our website.
    The url should expire, just to avoid the security hazard of having those
    lying around indefinitely.

    When creating new instances, client code should use
    LoginToken.objects.get_for_user(user)
    This avoids breaking unique constrainst and badly formed tokens.
    """

    EXPIRES_IN = timedelta(minutes=120) # minutes
    user = models.OneToOneField(CustomUser, related_name="login_token")
    token = models.CharField(max_length=40, unique=True)
    created = models.DateTimeField(auto_now_add=True)

    objects = LoginTokenManager()

    class Meta:
        db_table = 'auth_logintoken'

    @property
    def is_expired(self):
        return self.created + LoginToken.EXPIRES_IN <  datetime.now()

    def is_valid(self):
        if self.is_expired:
            return False
        # be paranoid, these users should never be login / staff members
        if self.user.is_staff or self.user.is_superuser:
            return False
        return True

    def __unicode__(self):
        return u"LoginToken for %s" %(self.user)

class AmaraApiKey(models.Model):
    user = models.OneToOneField(CustomUser, related_name="api_key")
    created = models.DateTimeField(auto_now_add=True)
    key = models.CharField(max_length=256, blank=True, default=generate_api_key)

    class Meta:
        db_table = 'auth_amaraapikey'

    def __unicode__(self):
        return u"Api key for {}: {}".format(self.user, self.key)

    def generate_new_key(self, commit=True):
        self.key = generate_api_key()
        if commit:
            self.save()
        return self.key

class SentMessageDateManager(models.Manager):
    def sent_message(self, user):
        self.create(user=user, created=dates.now())

    def check_too_many_messages(self, user):
        now = dates.now()
        self.get_queryset().filter(created__lt=now - timedelta(minutes=settings.MESSAGES_SENT_WINDOW_MINUTES)).delete()
        return self.get_queryset().filter(user=user,
                                    created__gt=now - timedelta(minutes=settings.MESSAGES_SENT_WINDOW_MINUTES)).count() > settings.MESSAGES_SENT_LIMIT

class SentMessageDate(models.Model):
    user = models.ForeignKey(CustomUser)
    created = models.DateTimeField()
    objects = SentMessageDateManager()

    class Meta:
        db_table = 'auth_sentmessagedate'
