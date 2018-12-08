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

from __future__ import absolute_import

from django.conf import settings
from django.test import TestCase

from externalsites import tasks
from externalsites.credit import (add_credit_to_video_url,
                                         should_add_credit_to_video_url)
from subtitles import pipeline
from videos.models import Video
from videos.templatetags.videos_tags import shortlink_for_video
from utils import test_utils
from utils.factories import *

class ShouldAddCreditTest(TestCase):
    def test_non_youtube_video(self):
        user = UserFactory()
        account = BrightcoveCMSAccountFactory(user=user)
        video_url = BrightcoveVideoFactory().get_primary_videourl_obj()
        self.assertEqual(should_add_credit_to_video_url(video_url, account),
                         False)

    def test_youtube_video(self):
        user = UserFactory()
        account = YouTubeAccountFactory(user=user)
        video_url = YouTubeVideoFactory().get_primary_videourl_obj()
        self.assertEqual(should_add_credit_to_video_url(video_url, account),
                         True)

    def test_youtube_video_team_account(self):
        team = TeamFactory()
        account = YouTubeAccountFactory(team=team)
        video_url = YouTubeVideoFactory().get_primary_videourl_obj()
        self.assertEqual(should_add_credit_to_video_url(video_url, account),
                         False)

    def test_no_account(self):
        user = UserFactory()
        video_url = YouTubeVideoFactory().get_primary_videourl_obj()
        self.assertEqual(should_add_credit_to_video_url(video_url, None),
                         False)

class BaseCreditTest(TestCase):
    @test_utils.patch_for_test('externalsites.google.update_video_description')
    @test_utils.patch_for_test('externalsites.google.get_video_info')
    def setUp(self, mock_get_video_info, mock_update_video_description):
        self.mock_get_video_info = mock_get_video_info
        self.mock_update_video_description = mock_update_video_description
        self.mock_get_video_info.return_value = YouTubeVideoInfoFactory()

class AddCreditTest(BaseCreditTest):
    @test_utils.patch_for_test('externalsites.google.get_new_access_token')
    def setUp(self, mock_get_new_access_token):
        BaseCreditTest.setUp(self)
        self.mock_get_new_access_token = mock_get_new_access_token
        self.mock_get_new_access_token.return_value = 'test-access-token'
        self.user = UserFactory()
        self.video = YouTubeVideoFactory(user=self.user,
                                         channel_id='test-channel-id')
        self.video_url = self.video.get_primary_videourl_obj()
        self.account = YouTubeAccountFactory(
            user=self.user, channel_id=self.video_url.owner_username)
        self.mock_get_video_info.reset_mock()

    def test_add_credit(self):
        # test add_credit_to_video_url
        add_credit_to_video_url(self.video_url, self.account)
        new_description = "\n\n".join([
            'test description',
            "Help us caption & translate this video!",
            shortlink_for_video(self.video)])
        self.mock_get_new_access_token.assert_called_with(
            self.account.oauth_refresh_token)
        self.mock_update_video_description.assert_called_with(
            self.video_url.videoid, 'test-access-token', new_description)

    def test_dont_add_credit_twice(self):
        # test that add_credit_to_video_url only alters the description once
        add_credit_to_video_url(self.video_url, self.account)

        self.mock_get_new_access_token.reset_mock()
        self.mock_update_video_description.reset_mock()
        self.mock_get_video_info.reset_mock()

        add_credit_to_video_url(self.video_url, 'test-access-token')
        self.assertEqual(self.mock_get_new_access_token.call_count, 0)
        self.assertEqual(self.mock_update_video_description.call_count, 0)
        self.assertEqual(self.mock_get_video_info.call_count, 0)

    def test_dont_add_credit_if_description_has_credit_text(self):
        # If the description already has our credit text we shouldn't try to
        # re-add it (this covers the case for descriptions that were altered
        # by the old accountlinker code).
        self.mock_get_video_info.return_value = YouTubeVideoInfoFactory(
            description="\n\n".join([
                'Test description',
                "Help us caption & translate this video!",
                shortlink_for_video(self.video)]))

        add_credit_to_video_url(self.video_url, self.account)
        # in this case we should call get_new_access_token() and
        # get_video_info() to get the description, but avoid the
        # update_video_description() API call.

        self.assertEqual(self.mock_get_new_access_token.call_count, 1)
        self.assertEqual(self.mock_get_video_info.call_count, 1)
        self.assertEqual(self.mock_update_video_description.call_count, 0)

    def test_concurency(self):
        # simulate add_credit_to_video_url() being called by a second thread
        # while it's still running in the first
        self.first_call = True
        def get_video_info(video_id):
            # this gets called inside add_credit_to_video_url().  Try queing
            # up a second call to add_credit_to_video_url()
            if self.first_call:
                self.first_call = False
                add_credit_to_video_url(self.video_url, self.account)
            return self.mock_get_video_info.return_value

        self.mock_get_video_info.side_effect = get_video_info
        add_credit_to_video_url(self.video_url, self.account)

        self.assertEqual(self.mock_update_video_description.call_count, 1)


class AddCreditScheduleTest(BaseCreditTest):
    # Test that we schedule add_credit_to_video_url to be called after certain
    # events
    @test_utils.patch_for_test('externalsites.tasks.add_amara_credit')
    def setUp(self, mock_add_amara_credit):
        BaseCreditTest.setUp(self)
        self.mock_add_amara_credit = mock_add_amara_credit
        self.user = UserFactory()
        self.channel_id = self.mock_get_video_info.return_value.channel_id
        self.account = YouTubeAccountFactory(user=self.user,
                                             channel_id=self.channel_id)

    def test_add_credit_on_new_video(self):
        video, video_url = Video.add('http://youtube.com/watch?v=abcdef',
                                     self.user)
        self.mock_add_amara_credit.delay.assert_called_with(video_url.id)

    def test_add_credit_on_new_public_tip(self):
        video = YouTubeVideoFactory(user=self.user,
                                    channel_id=self.channel_id)
        self.mock_add_amara_credit.delay.reset_mock()
        pipeline.add_subtitles(video, 'en', SubtitleSetFactory(),
                               action='publish')
        self.mock_add_amara_credit.delay.assert_called_with(
            video.get_primary_videourl_obj().id)

    def test_dont_add_credit_without_account(self):
        # test a video for our user, but not from our youtube account
        self.mock_get_video_info.return_value = YouTubeVideoInfoFactory(
            channel_id='other-channel')
        video = YouTubeVideoFactory(user=self.user, channel_id='test-channel')
        self.assertEqual(self.mock_add_amara_credit.delay.call_count, 0)
        # adding a public tip shouldn't result in a call either
        pipeline.add_subtitles(video, 'en', SubtitleSetFactory(),
                               action='publish')
        self.assertEqual(self.mock_add_amara_credit.delay.call_count, 0)

    def test_dont_add_credit_to_non_youtube_videos(self):
        team = TeamFactory()
        account = BrightcoveCMSAccountFactory(team=team)
        video = BrightcoveVideoFactory()
        TeamVideoFactory(team=team, video=video)
        self.assertEqual(self.mock_add_amara_credit.delay.call_count, 0)

        pipeline.add_subtitles(video, 'en', None)
        self.assertEqual(self.mock_add_amara_credit.delay.call_count, 0)

class AddCreditTaskTest(TestCase):
    @test_utils.patch_for_test('externalsites.credit.add_credit_to_video_url')
    def setUp(self, mock_add_credit_to_video_url):
        self.mock_add_credit_to_video_url = mock_add_credit_to_video_url

    def test_add_amara_credit_task(self):
        # test the add_amara_credit task
        user = UserFactory()
        video = YouTubeVideoFactory(
            user=user, channel_id=test_utils.test_video_info.channel_id)
        video_url = video.get_primary_videourl_obj()
        account = YouTubeAccountFactory(
            user=user, channel_id=test_utils.test_video_info.channel_id)
        tasks.add_amara_credit(video_url.id)
        # add_amara_credit should get a new access token, then call
        # add_credit_to_video_url()
        self.mock_add_credit_to_video_url.assert_called_with(
            video_url, account)

    def test_task_called_with_no_account(self):
        # test what happens when the task is executed but no account exists
        # (maybe it was deleted after it was scheduled)
        video = YouTubeVideoFactory()
        video_url = video.get_primary_videourl_obj()
        tasks.add_amara_credit(video_url.id)
        # add_amara_credit should get a new access token, then call
        # add_credit_to_video_url()
        self.assertEqual(self.mock_add_credit_to_video_url.call_count, 0)
