# Amara, universalsubtitles.org
#
# Copyright (C) 2014 Participatory Culture Foundation
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

import json

from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings
from nose.tools import *

from utils import test_utils
from utils.subtitles import load_subtitles
from externalsites import google, subfetch
from externalsites.syncing.youtube import convert_language_code
import isodate

@override_settings(GOOGLE_API_KEY='test-youtube-api-key')
class YouTubeTestCase(TestCase):
    def test_get_user_info(self):
        mocker = test_utils.RequestsMocker()
        mocker.expect_request(
            'get', 'https://www.googleapis.com/youtube/v3/channels', params={
                'part': 'id,snippet',
                'mine': 'true',
            }, headers={
                'Authorization': 'Bearer test-access-token',
            }, body=json.dumps({
                'items': [
                    {
                        'id': 'test-channel-id',
                        'snippet': {
                            'title': 'test-username',
                        },
                    }
                ]
            })
        )
        google.get_youtube_user_info.run_original_for_test()
        with mocker:
            user_info = google.get_youtube_user_info('test-access-token')
        self.assertEqual(user_info, ('test-channel-id', 'test-username'))

    def make_video_snippet(self, video_id):
        return {
            'snippet': {
                'resourceId': {
                    'kind': u'youtube#video',
                    'videoId': video_id,
                }
            }
        }

    def test_get_uploaded_video_ids(self):
        mocker = test_utils.RequestsMocker()
        mocker.expect_request(
            'get', 'https://www.googleapis.com/youtube/v3/channels', params={
                'part': 'contentDetails',
                'id': 'test-channel-id',
                'key': 'test-youtube-api-key',
            }, body=json.dumps({
                'items': [
                    {
                        'contentDetails': {
                            'relatedPlaylists': {
                                'uploads': 'test-playlist-id',
                            },
                        },
                    },
                ]
            })
        )
        mocker.expect_request(
            'get', 'https://www.googleapis.com/youtube/v3/playlistItems', params={
                'part': 'snippet',
                'maxResults': 50,
                'playlistId': 'test-playlist-id',
                'key': 'test-youtube-api-key',
            }, body=json.dumps({
                'items': [
                    self.make_video_snippet('test-video-id1'),
                    self.make_video_snippet('test-video-id2'),
                    {
                        'snippet': {
                            'resourceId': {
                                'kind': u'youtube#something-else',
                            }
                        }
                    },
                ]
            })
        )
        google.get_uploaded_video_ids.run_original_for_test()
        with mocker:
            video_ids = google.get_uploaded_video_ids('test-channel-id')
        assert_equal(video_ids, [ 'test-video-id1', 'test-video-id2' ])

    def test_get_uploaded_video_ids_multiple_pages(self):
        mocker = test_utils.RequestsMocker()
        mocker.expect_request(
            'get', 'https://www.googleapis.com/youtube/v3/channels', params={
                'part': 'contentDetails',
                'id': 'test-channel-id',
                'key': 'test-youtube-api-key',
            }, body=json.dumps({
                'items': [
                    {
                        'contentDetails': {
                            'relatedPlaylists': {
                                'uploads': 'test-playlist-id',
                            },
                        },
                    },
                ]
            })
        )
        mocker.expect_request(
            'get', 'https://www.googleapis.com/youtube/v3/playlistItems', params={
                'part': 'snippet',
                'maxResults': 50,
                'playlistId': 'test-playlist-id',
                'key': 'test-youtube-api-key',
            }, body=json.dumps({
                'items': [
                    self.make_video_snippet('test-video-id{}'.format(i))
                    for i in range(50)
                ],
                'nextPageToken': 'test-page-token',
            })
        )
        mocker.expect_request(
            'get', 'https://www.googleapis.com/youtube/v3/playlistItems', params={
                'part': 'snippet',
                'maxResults': 50,
                'playlistId': 'test-playlist-id',
                'key': 'test-youtube-api-key',
                'pageToken': 'test-page-token',
            }, body=json.dumps({
                'items': [
                    self.make_video_snippet('test-video-id{}'.format(i))
                    for i in range(50, 75)
                ],
            })
        )
        google.get_uploaded_video_ids.run_original_for_test()
        with mocker:
            video_ids = google.get_uploaded_video_ids('test-channel-id')
        assert_equal(video_ids,
                     [ 'test-video-id{}'.format(i) for i in range(75)])

    def test_get_video_info(self):
        mocker = test_utils.RequestsMocker()
        mocker.expect_request(
            'get', 'https://www.googleapis.com/youtube/v3/videos', params={
                'part': 'snippet,contentDetails',
                'id': 'test-video-id',
                'key': settings.GOOGLE_API_KEY,
            }, body=json.dumps({
                'items': [
                    {
                        'snippet': {
                            'title': 'test-title',
                            'channelId': 'test-channel-id',
                            'description': 'test-description',
                            'thumbnails': {
                                'high': {
                                    'url': 'test-thumbnail-url',
                                }
                            }
                        },
                        'contentDetails': {
                            'duration': 'PT10M10S',
                        }
                    }
                ]
            })
        )
        google.get_video_info.run_original_for_test()
        with mocker:
            video_info = google.get_video_info('test-video-id')
        self.assertEqual(video_info.channel_id, 'test-channel-id')
        self.assertEqual(video_info.title, 'test-title')
        self.assertEqual(video_info.description, 'test-description')
        self.assertEqual(video_info.duration, 610)
        self.assertEqual(video_info.thumbnail_url, 'test-thumbnail-url')

    def test_get_video_invalid_body(self):
        mocker = test_utils.RequestsMocker()
        mocker.expect_request(
            'get', 'https://www.googleapis.com/youtube/v3/videos', params={
                'part': 'snippet,contentDetails',
                'id': 'test-video-id',
                'key': settings.GOOGLE_API_KEY,
            }, body="Invalid body")
        google.get_video_info.run_original_for_test()
        with mocker:
            with assert_raises(google.APIError):
                google.get_video_info('test-video-id')

    def test_get_video_info_no_items(self):
        mocker = test_utils.RequestsMocker()
        mocker.expect_request(
            'get', 'https://www.googleapis.com/youtube/v3/videos', params={
                'part': 'snippet,contentDetails',
                'id': 'test-video-id',
                'key': settings.GOOGLE_API_KEY,
            }, body=json.dumps({
                'items': [
                ]
            })
        )
        google.get_video_info.run_original_for_test()
        with mocker:
            with assert_raises(google.APIError):
                google.get_video_info('test-video-id')

    def test_update_video_description(self):
        mocker = test_utils.RequestsMocker()
        mocker.expect_request(
            'get', 'https://www.googleapis.com/youtube/v3/videos', params={
                'part': 'snippet',
                'id': 'test-video-id',
            }, headers={
                'Authorization': 'Bearer test-access-token',
            }, body=json.dumps({
                'items': [
                    {
                        'snippet': {
                            'title': 'test-title',
                            'channelId': 'test-channel-id',
                            'description': 'test-description',
                            'thumbnails': {
                                'high': {
                                    'url': 'test-thumbnail-url',
                                }
                            }
                        }
                    }
                ]
            })
        )
        mocker.expect_request(
            'put', 'https://www.googleapis.com/youtube/v3/videos', params={
                'part': 'snippet',
            }, headers={
                'Authorization': 'Bearer test-access-token',
                'content-type': 'application/json',
            }, data=json.dumps({
                'id': 'test-video-id',
                'snippet': {
                    'title': 'test-title',
                    'channelId': 'test-channel-id',
                    'description': 'test-updated-description',
                    'thumbnails': {
                        'high': {
                            'url': 'test-thumbnail-url',
                        }
                    }
                }
            })
        )
        google.update_video_description.run_original_for_test()
        with mocker:
            google.update_video_description('test-video-id',
                                                   'test-access-token',
                                                   'test-updated-description')

class TestTimeParsing(TestCase):
    def test_with_minutes(self):
        self.assertEqual(isodate.parse_duration('PT10M10S').total_seconds(), 610)

    def test_without_minutes(self):
        self.assertEqual(isodate.parse_duration('PT10S').total_seconds(), 10)

    def test_invalid(self):
        self.assertRaises(Exception, isodate.parse_duration, 'foo')

class TestYoutubeMapping(TestCase):
    def test_mapping_from_youtube(self):
        self.assertEqual(subfetch.convert_language_code('en'), 'en')
        self.assertEqual(subfetch.convert_language_code('fr-CA'), 'fr-ca')
        self.assertEqual(subfetch.convert_language_code('pt-PT'), 'pt')
        self.assertEqual(subfetch.convert_language_code('zh-Hant'), 'zh-tw')
        self.assertEqual(subfetch.convert_language_code('fr-ca'), None)
        self.assertEqual(subfetch.convert_language_code('zz'), None)
        self.assertEqual(subfetch.convert_language_code('zz-zz'), None)
        self.assertEqual(subfetch.convert_language_code('es-419'), 'es-419')
        self.assertEqual(subfetch.convert_language_code('en-IN'), 'en-in')
        self.assertEqual(subfetch.convert_language_code('en-AU'), 'en-au')

    def test_mapping_to_youtube(self):
        self.assertEqual(convert_language_code('en', True), 'en')
        self.assertEqual(convert_language_code('fr-ca', True), 'fr-CA')
        self.assertEqual(convert_language_code('pt', True), 'pt-PT')
        self.assertEqual(convert_language_code('zh-tw', True), 'zh-Hant')
        self.assertEqual(convert_language_code('es-419', True), 'es-419')
        self.assertEqual(convert_language_code('en-in', True), 'en-IN')
        self.assertEqual(convert_language_code('en-au', True), 'en-AU')
        self.assertEqual(convert_language_code('en', False), 'en')
        self.assertEqual(convert_language_code('fr-ca', False), 'fr-CA')
        self.assertEqual(convert_language_code('pt', False), 'pt')
        self.assertEqual(convert_language_code('zh-tw', False), 'zh-TW')
        self.assertEqual(convert_language_code('es-419', False), 'es-419')
        self.assertEqual(convert_language_code('en-in', False), 'en-IN')
        self.assertEqual(convert_language_code('en-au', False), 'en-AU')

