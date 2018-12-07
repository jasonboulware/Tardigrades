# -*- coding: utf-8 -*-
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
from datetime import datetime, timedelta
from urlparse import urlparse
from nose.tools import *
import mock
import re


from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.core import mail
from django.test import TestCase

from auth import signals
from auth.models import CustomUser as User, UserLanguage
from auth.models import LoginToken, AmaraApiKey
from caching.tests.utils import assert_invalidates_model_cache
from externalsites.models import YouTubeAccount, VimeoSyncAccount
from subtitles.tests.utils import make_sl
from utils.factories import *
from utils import test_utils
from videos.models import Video


class UserSpammingTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
    def test_de_activate_users(self):
        self.assertEqual(self.user.is_active, True)
        self.user.de_activate()
        self.assertEqual(self.user.is_active, False)
        self.user.is_superuser = True
        self.user.is_active = True
        self.user.de_activate()
        self.assertEqual(self.user.is_active, True)

    @test_utils.patch_for_test('utils.dates.now')
    def test_spamming_user_deactivated(self, mock_now):
        mock_now.return_value = datetime(2017, 1, 1)
        self.assertEqual(self.user.is_active, True)
        for message in range(settings.MESSAGES_SENT_LIMIT):
            self.user.sent_message()
        self.assertEqual(self.user.is_active, True)
        self.user.sent_message()
        self.assertEqual(self.user.is_active, False)
        self.user.is_active = True
        mock_now.return_value += timedelta(minutes=settings.MESSAGES_SENT_WINDOW_MINUTES, seconds=1)
        self.user.sent_message()
        self.assertEqual(self.user.is_active, True)

class VideosFieldTest(TestCase):
    def setUp(self):
        self.user = UserFactory()

    def check_user_videos(self, videos):
        self.assertEqual(set(self.user.videos.all()), set(videos))

    def test_with_video_followers(self):
        video = VideoFactory(title='video1')
        video2 = VideoFactory(title='video2')
        self.check_user_videos([])
        # add
        video.followers.add(self.user)
        self.check_user_videos([video])
        # add with reverse relation
        self.user.followed_videos.add(video2)
        self.check_user_videos([video, video2])
        # remove
        video.followers.remove(self.user)
        self.check_user_videos([video2])
        # remove with reverse relation
        self.user.followed_videos.remove(video2)
        self.check_user_videos([])
        # clear
        video.followers.add(self.user)
        self.check_user_videos([video])
        video.followers = []
        self.check_user_videos([])
        # clear with reverse relation
        video.followers.add(self.user)
        self.check_user_videos([video])
        self.user.followed_videos = []
        self.check_user_videos([])

class UserCreationTest(TestCase):
    def test_notfications(self):
        self.assertEqual(len(mail.outbox), 0)
        user = User(email='la@example.com', username='someone')
        user.set_password("secret")
        user.save()
        self.assertEqual(len(mail.outbox), 1)

    def test_notifications_unicode(self):
        self.assertEqual(len(mail.outbox), 0)
        user = User(email=u'Leandro Andrés@example.com', username='unicodesomeone')
        user.set_password("secret")
        user.save()
        self.assertEqual(len(mail.outbox), 1)

    def test_username_cant_have_dollar_sign(self):
        with assert_raises(ValidationError):
            User(username="user$name").full_clean()

class UserProfileChangedTest(TestCase):
    def test_create(self):
        # We shouldn't emit the signal when we initially create a user
        with test_utils.mock_handler(signals.user_profile_changed) as handler:
            u = User()
            u.first_name = 'ben'
            u.save()
            assert_false(handler.called)

    def test_update(self):
        u = User.objects.create()
        with test_utils.mock_handler(signals.user_profile_changed) as handler:
            u.first_name = 'ben'
            u.save()
            assert_true(handler.called)
            assert_equal(handler.call_args,
                         mock.call(signal=mock.ANY, sender=u))

    def test_update_non_profile_fields(self):
        # Updated non-profile fields shouldn't result in the signal
        u = User()
        with test_utils.mock_handler(signals.user_profile_changed) as handler:
            u.show_tutorial = False
            u.save()
            assert_false(handler.called)

class UniqueUsernameTest(TestCase):
    def test_username_already_unique(self):
        # if the username is unique to begin with, we should use that
        user = User.objects.create_with_unique_username(username='test')
        assert_equal(user.username, 'test')

    def test_strategy1(self):
        # If the username is not unique, we should try to append "00", "01",
        # "02", ... until "99" to the username
        UserFactory(username='test')
        for i in xrange(5):
            UserFactory(username='test0{}'.format(i))
        user = User.objects.create_with_unique_username(username='test')
        assert_equal(user.username, 'test05')

    def test_strategy2(self):
        # If strategy1 doesn't produce a unique username, then we should
        # append random strings until we find one
        UserFactory(username='test')
        for i in xrange(100):
            UserFactory(username='test{:0>2d}'.format(i))
        user = User.objects.create_with_unique_username(username='test')
        assert_true(re.match(r'test[a-zA-Z0-9]{6}', user.username),
                    user.username)

    def test_at_symbol(self):
        # if there is an "@" symbol in the username, we should insert our
        # extra chars before it.
        UserFactory(username='test@example.com')
        for i in xrange(5):
            UserFactory(username='test0{}@example.com'.format(i))
        user = User.objects.create_with_unique_username(
            username='test@example.com')
        assert_equal(user.username, 'test05@example.com')

    def test_at_symbol_strategy2(self):
        UserFactory(username='test@example.com')
        for i in xrange(100):
            UserFactory(username='test{:0>2d}@example.com'.format(i))
        user = User.objects.create_with_unique_username(
            username='test@example.com')
        assert_true(re.match(r'test[a-zA-Z0-9]{6}@example.com', user.username),
                    user.username)


class UserCacheTest(TestCase):
    def test_user_language_change_invalidates_cache(self):
        user = UserFactory()
        with assert_invalidates_model_cache(user):
            user_lang = UserLanguage.objects.create(user=user, language='en')
        with assert_invalidates_model_cache(user):
            user_lang.delete()

class LoginTokenModelTest(TestCase):
    def test_creation(self):
        user = UserFactory()
        lt1 = LoginToken.objects.for_user(user)
        lt2 = LoginToken.objects.for_user(user, updates=False)
        self.assertEqual(lt1.token, lt2.token)
        self.assertEqual(len(lt1.token), 40)
        # assesrt updates does what it says
        lt3 = LoginToken.objects.for_user(user, updates=True)
        self.assertNotEqual(lt3.token, lt2.token)
        self.assertEqual(len(lt3.token), 40)

    def test_expire(self):
        user = UserFactory()

        lt1 = LoginToken.objects.for_user(user)
        self.assertFalse(lt1.is_expired)
        self.assertFalse(LoginToken.objects.get_expired().filter(pk=lt1.pk).exists())
        older_date = datetime.now() - timedelta(minutes=1) - LoginToken.EXPIRES_IN
        lt1.created = older_date
        lt1.save()
        self.assertTrue(lt1.is_expired)
        self.assertTrue(LoginToken.objects.get_expired().filter(pk=lt1.pk).exists())


class LoginTokenViewsTest(TestCase):
    def test_valid_login(self):
        user = UserFactory()
        lt1 = LoginToken.objects.for_user(user)
        redirect_url = '/en/videos/watch'
        url = reverse("auth:token-login", args=(lt1.token,)) + "?next=%s" % redirect_url
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        location = response._headers['location'][1]
        redirect_path = urlparse(location).path
        self.assertEqual(redirect_path, redirect_url)

    def test_invalid_login(self):
        user = UserFactory()
        lt1 = LoginToken.objects.for_user(user)
        redirect_url = '/en/videos/watch'
        url = reverse("auth:token-login", args=(lt1.token,)) + "?next=%s" % redirect_url
        lt1.delete()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_staff_is_offlimit(self):
        user = UserFactory()
        lt1 = LoginToken.objects.for_user(user)
        user.is_staff  = True
        user.save()
        redirect_url = '/en/videos/watch'
        url = reverse("auth:token-login", args=(lt1.token,)) + "?next=%s" % redirect_url
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_superuser_is_offlimit(self):
        user = UserFactory()
        lt1 = LoginToken.objects.for_user(user)
        user.is_superuser  = True
        user.save()
        redirect_url = '/en/videos/watch'
        url = reverse("auth:token-login", args=(lt1.token,)) + "?next=%s" % redirect_url
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)


class ApiKeysTest(TestCase):
    def setUp(self):
        self.user = UserFactory()

    def test_get_api_key(self):
        self.assertEqual(len(self.user.get_api_key()), 40)


class UserDeactivateTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.youtube_account = YouTubeAccountFactory(user=self.user)
        self.vimeo_account = VimeoSyncAccountFactory(user=self.user)

    def test_deactivate_user(self):
        old_username = self.user.username

        self.user.deactivate_account()

        self.assertFalse(self.user.team_members.all().exists())
        self.assertNotEqual(self.user.username, old_username)
        self.assertFalse(self.user.is_active)
        self.assertFalse(YouTubeAccount.objects.for_owner(self.user).exists())
        self.assertFalse(VimeoSyncAccount.objects.for_owner(self.user).exists())

    def test_delete_account_data(self):
        old_username = self.user.username

        self.user.delete_account_data()

        self.assertNotEqual(self.user.username, old_username)
        self.assertFalse(self.user.username_old)
        self.assertFalse(self.user.first_name)
        self.assertFalse(self.user.last_name)
        self.assertFalse(self.user.picture)
        self.assertFalse(self.user.email)
        self.assertFalse(self.user.homepage)
        self.assertFalse(self.user.biography)
        self.assertFalse(self.user.full_name)

    def test_delete_videos(self):
        self.user2 = UserFactory()
        self.team = TeamFactory()
        self.video = VideoFactory(user=self.user)
        self.video2 = VideoFactory(user=self.user)
        self.video3 = VideoFactory(user=self.user)
        self.team.add_existing_video(self.video3, self.user)
        self.sl = make_sl(self.video, 'en')
        self.sl2 = make_sl(self.video2, 'en')

        self.sl.add_version(title='title a',
                            description='desc a',
                            subtitles=[],
                            author=self.user)
        self.sl2.add_version(title='title a',
                            description='desc a',
                            subtitles=[],
                            author=self.user2)

        video_pk = self.video.pk
        video2_pk = self.video2.pk
        video3_pk = self.video3.pk

        self.user.delete_self_subtitled_videos()

        self.assertFalse(Video.objects.filter(pk=video_pk).exists())
        self.assertTrue(Video.objects.filter(pk=video2_pk).exists())
        self.assertTrue(Video.objects.filter(pk=video3_pk).exists())

