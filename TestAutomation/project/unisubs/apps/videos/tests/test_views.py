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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

from datetime import datetime
import json

from BeautifulSoup import BeautifulSoup

from babelsubs.storage import SubtitleSet, diff
from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from django.db.models import ObjectDoesNotExist
from django.test import TestCase

from auth.models import CustomUser as User
from subtitles import pipeline
from teams.models import Task
from teams.permissions_const import ROLE_ADMIN
from videos.tasks import video_changed_tasks
from videos.templatetags.subtitles_tags import format_sub_time
from videos.tests.videotestutils import (
    WebUseTest, create_langs_and_versions
)
from videos import views
from videos.models import (
    Video, VideoUrl, Action, VIDEO_TYPE_YOUTUBE, SubtitleVersion,
    SubtitleLanguage, Subtitle
)
from videos.tests.data import (
    get_video, make_subtitle_language, make_subtitle_version
)
from widget import video_cache
from utils import test_utils
from utils.factories import *

class TestViews(WebUseTest):
    def setUp(self):
        self._make_objects_with_factories()
        cache.clear()
        mail.outbox = []

    def test_videourl_create_with_team_video(self):
        team_video = TeamVideoFactory()
        video = team_video.video
        self.assertEqual(video.videourl_set.count(), 1)
        # get ready to add another url
        secondary_url = 'http://example.com/video2.ogv'
        data = {
            'url': secondary_url,
            'video': video.pk
        }
        url = reverse('videos:video_url_create')
        # this shouldn't work without logging in
        response = self.client.post(url, data)
        self.assertEqual(video.videourl_set.count(), 1)
        # this shouldn't work without if logged in as a non-team member
        non_team_member = UserFactory()
        self._login(non_team_member)
        response = self.client.post(url, data)
        self.assertEqual(video.videourl_set.count(), 1)
        # this should work when logged in as a team member
        member = UserFactory()
        TeamMemberFactory(user=member, team=team_video.team,
                          role=ROLE_ADMIN)
        self._login(member)
        response = self.client.post(url, data)
        self.assertEqual(video.videourl_set.count(), 2)

    def test_create(self):
        self._login()
        url = reverse('videos:create')

        self._simple_test('videos:create')

        data = {
            'video_url': 'http://www.youtube.com/watch?v=osexbB_hX4g&feature=popular'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        try:
            video = Video.objects.get(videourl__videoid='osexbB_hX4g',
                                      videourl__type=VIDEO_TYPE_YOUTUBE)
        except Video.DoesNotExist:
            self.fail()

        self.assertEqual(response['Location'], video.get_absolute_url())

    def test_video_url_remove(self):
        test_utils.invalidate_widget_video_cache.run_original_for_test()
        self._login()
        secondary_vurl = VideoURLFactory(video=self.video)
        self.assertEqual(self.video.videourl_set.count(), 2)
        # make sure get is not allowed
        url = reverse('videos:video_url_remove')
        data = {'id': secondary_vurl.id}
        response = self.client.get(url, data)
        self.assertEqual(response.status_code, 405)
        # check post
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.video.videourl_set.count(), 1)
        delete_actions = self.video.activity.filter(type='video-url-deleted')
        self.assertEqual(delete_actions.count(), 1)
        # assert cache is invalidated
        cached_video_urls = video_cache.get_video_urls(self.video.video_id)
        self.assertEqual(len(cached_video_urls), 1)

    def test_video_url_deny_remove_primary(self):
        self._login()
        video_url = self.video.get_primary_videourl_obj()
        # make primary
        response = self.client.post(reverse('videos:video_url_remove'),
                                    {'id': video_url.id})
        self.assertEqual(response.status_code, 403)

    def test_video(self):
        self.video.title = 'title'
        self.video.save()
        response = self.client.get(self.video.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)

        self.video.title = ''
        self.video.save()
        response = self.client.get(self.video.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_legacy_history(self):
        # TODO: write tests
        pass

    def test_stop_notification(self):
        # TODO: write tests
        pass

    def test_subscribe_to_updates(self):
        # TODO: write test
        pass

    def test_history(self):
        v = pipeline.add_subtitles(self.video, 'en', None)
        sl = v.subtitle_language
        self._simple_test('videos:translation_history',
            [self.video.video_id, sl.language_code, sl.id])

    def _test_rollback(self):
        #TODO: Seems like roll back is not getting called (on models)
        self._login()

        version = self.video.version(0)
        last_version = self.video.version(public_only=False)

        self._simple_test('videos:rollback', [version.id], status=302)

        new_version = self.video.version()
        self.assertEqual(last_version.version_no+1, new_version.version_no)

    def test_opensubtitles2010_page(self):
        self._simple_test('opensubtitles2010_page')

    def test_faq_page(self):
        self._simple_test('faq_page')

    def test_about_page(self):
        self._simple_test('about_page')

    def test_policy_page(self):
        self._simple_test('policy_page')
