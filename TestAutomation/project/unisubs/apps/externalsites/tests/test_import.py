# Amara, universalsubtitles.org
#
# Copyright (C) 2015 Participatory Culture Foundation
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

from django.test import TestCase
from nose.tools import *
import mock

from externalsites.models import ExternalAccount, YouTubeAccount
from videos.models import Video, VideoUrl
from utils import test_utils
from utils.factories import *

class YoutubeImportTest(TestCase):
    @test_utils.patch_for_test("externalsites.google.get_uploaded_video_ids")
    @test_utils.patch_for_test("videos.models.Video.add")
    def setUp(self, mock_video_add, mock_get_uploaded_video_ids):
        self.user = UserFactory()
        self.team = TeamFactory()
        self.import_team = TeamFactory()
        self.user_account = YouTubeAccountFactory(user=self.user)
        self.team_account = YouTubeAccountFactory(
            team=self.team, import_team=self.import_team)
        self.mock_get_uploaded_video_ids = mock_get_uploaded_video_ids
        self.mock_video_add = mock_video_add
        self.mock_get_uploaded_video_ids.return_value = [
            'video-1', 'video-2', 'video-3',
        ]
        def make_video(url, user, setup_callback=None, team=None):
            video = VideoFactory(video_url__url=url)
            video_url = video.get_primary_videourl_obj()
            if setup_callback:
                setup_callback(video, video_url)
            return video, video_url
        self.mock_video_add.side_effect = make_video

    def test_accounts_to_import(self):
        # We should select:
        #  - All user accounts
        #  - Team accounts that have import_team set
        team_account_without_import_team = YouTubeAccountFactory(
            team=TeamFactory(), import_team=None)
        assert_items_equal(YouTubeAccount.objects.accounts_to_import(),
                           [self.user_account, self.team_account])
        assert_true(self.user_account.should_import_videos())
        assert_true(self.team_account.should_import_videos())
        assert_false(team_account_without_import_team.should_import_videos())

    def test_user_account_import(self):
        # we should import all videos and set added_by to the user
        self.user_account.import_videos()
        assert_equals(self.mock_video_add.call_args_list, [
            mock.call('http://youtube.com/watch?v=video-1', self.user),
            mock.call('http://youtube.com/watch?v=video-2', self.user),
            mock.call('http://youtube.com/watch?v=video-3', self.user),
        ])

    def test_team_account_import(self):
        # we should import all videos and add them to our team
        self.team_account.import_videos()
        assert_equals(self.mock_video_add.call_args_list, [
            mock.call('http://youtube.com/watch?v=video-1', None, mock.ANY,
                      self.import_team),
            mock.call('http://youtube.com/watch?v=video-2', None, mock.ANY,
                      self.import_team),
            mock.call('http://youtube.com/watch?v=video-3', None, mock.ANY,
                      self.import_team),
        ])
        for i in range(1, 4):
            url = 'http://youtube.com/watch?v=video-{}'.format(i)
            team_video = VideoUrl.objects.get(url=url).video.get_team_video()
            assert_not_equal(team_video, None)
            assert_equal(team_video.team, self.import_team)

    def test_set_last_import_video_id(self):
        self.user_account.import_videos()
        # we should set last_import_video_id to the first video in the list
        assert_equal(
            test_utils.reload_obj(self.user_account).last_import_video_id,
            'video-1')

    def test_dont_reimport(self):
        self.user_account.last_import_video_id = 'video-2'
        self.user_account.import_videos()
        # we should only import videos added after video-2 in the playlist
        assert_equals(self.mock_video_add.call_args_list, [
            mock.call('http://youtube.com/watch?v=video-1', self.user),
        ])
