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

import datetime
import unittest

from django.test import TestCase

from babelsubs.storage import SubtitleLine, SubtitleSet

from auth.models import CustomUser as User
from nose.tools import assert_raises
from teams.models import Team, TeamVideo
from subtitles import pipeline
from subtitles.models import SubtitleLanguage, SubtitleVersion
from utils.factories import UserFactory
from videos.models import Video, VIDEO_TYPE_BRIGHTCOVE
from videos.types import video_type_registrar, VideoTypeError
from videos.types.base import VideoType, VideoTypeRegistrar
from videos.types.brightcove  import BrightcoveVideoType
from videos.types.dailymotion import DailymotionVideoType
from videos.types.flv import FLVVideoType
from videos.types.htmlfive import HtmlFiveVideoType
from videos.types.kaltura import KalturaVideoType
from videos.types.mp3 import Mp3VideoType
from videos.types.vimeo import VimeoVideoType
from videos.types.youtube import YoutubeVideoType
from utils import test_utils
from externalsites import google

class YoutubeVideoTypeTest(TestCase):
    def setUp(self):
        self.vt = YoutubeVideoType
        self.data = [{
            'url': 'http://www.youtube.com/watch#!v=UOtJUmiUZ08&feature=featured&videos=Qf8YDn9mbGs',
            'video_id': 'UOtJUmiUZ08'
        },{
            'url': 'http://www.youtube.com/v/6Z5msRdai-Q',
            'video_id': '6Z5msRdai-Q'
        },{
            'url': 'http://www.youtube.com/watch?v=woobL2yAxD4',
            'video_id': 'woobL2yAxD4'
        },{
            'url': 'http://www.youtube.com/watch?v=woobL2yAxD4&amp;playnext=1&amp;videos=9ikUhlPnCT0&amp;feature=featured',
            'video_id': 'woobL2yAxD4'
        }]
        self.shorter_url = "http://youtu.be/HaAVZ2yXDBo"

    @test_utils.patch_for_test('externalsites.google.get_video_info')
    def test_video_id(self, mock_get_video_info):
        video_info = google.VideoInfo('test-channel-id', 'title',
                                      'description', 100,
                                      'http://example.com/thumb.png')
        mock_get_video_info.return_value = video_info
        vt = YoutubeVideoType('http://www.youtube.com/watch?v=_ShmidkrcY0')
        self.assertEqual(vt.video_id, '_ShmidkrcY0')
        vt = YoutubeVideoType('http://www.youtube.com/watch?v=_ShmidkrcY0123')
        self.assertEqual(vt.video_id, '_ShmidkrcY0')
        vt = YoutubeVideoType('http://www.youtube.com/watch?v=_Shmid')
        self.assertEqual(vt.video_id, '_Shmid')

    @test_utils.patch_for_test('externalsites.google.get_video_info')
    def test_set_values(self, mock_get_video_info):
        video_info = google.VideoInfo('test-channel-id', 'title',
                                      'description', 100,
                                      'http://example.com/thumb.png')
        mock_get_video_info.return_value = video_info
        vt = YoutubeVideoType('http://www.youtube.com/watch?v=_ShmidkrcY0')
        video = Video()
        vt.set_values(video, None, None, None)
        self.assertEqual(video.title, video_info.title)
        self.assertEqual(video.description, video_info.description)
        self.assertEqual(video.duration, video_info.duration)
        self.assertEqual(video.thumbnail, video_info.thumbnail_url)

    @test_utils.patch_for_test('externalsites.google.get_video_info')
    def test_get_video_info_exception(self, mock_get_video_info):
        video_info = google.VideoInfo('test-channel-id', 'title',
                                      'description', 100,
                                      'http://example.com/thumb.png')
        mock_get_video_info.side_effect = google.APIError()
        vt = YoutubeVideoType('http://www.youtube.com/watch?v=_ShmidkrcY0')
        video = Video()
        vt.set_values(video, None, None, None)

        self.assertEqual(vt.video_id, '_ShmidkrcY0')
        self.assertEqual(video.description, '')
        self.assertEqual(video.duration, None)
        self.assertEqual(video.thumbnail, '')

    def test_matches_video_url(self):
        for item in self.data:
            self.assertTrue(self.vt.matches_video_url(item['url']))
            self.assertFalse(self.vt.matches_video_url('http://some-other-url.com'))
            self.assertFalse(self.vt.matches_video_url(''))
            self.assertFalse(self.vt.matches_video_url('http://youtube.com/'))
            self.assertFalse(self.vt.matches_video_url('http://youtube.com/some-video/'))
            self.assertTrue(self.vt.matches_video_url(self.shorter_url))

    def test_get_video_id(self):
        for item in self.data:
            self.failUnlessEqual(item['video_id'], self.vt._get_video_id(item['url']))

    def test_shorter_format(self):
        vt = self.vt(self.shorter_url)
        self.assertTrue(vt)
        self.assertEqual(vt.video_id , self.shorter_url.split("/")[-1])

    def test_add_youtube_video(self):
        vt = YoutubeVideoType('http://www.youtube.com/watch?v=_ShmidkrcY0')
        vt_2 = YoutubeVideoType('http://www.youtube.com/watch?v=_ShmidkrcY0we')
        vt_3 = YoutubeVideoType('http://www.youtube.com/watch?v=_ShmidkrcY0ewgwe')
        user = UserFactory()
        video, video_url = Video.add(vt, user)
        with assert_raises(Video.DuplicateUrlError):
            video_2, video_url_2 = Video.add(vt_2, user)
        with assert_raises(Video.DuplicateUrlError):
            video_3, video_url_3 = Video.add(vt_3, user)

class HtmlFiveVideoTypeTest(TestCase):
    def setUp(self):
        self.vt = HtmlFiveVideoType

    def test_matches_video_url(self):
        self.assertTrue(self.vt.matches_video_url(
            'http://someurl.com/video.ogv'))
        self.assertTrue(self.vt.matches_video_url(
            'http://someurl.com/video.OGV'))
        self.assertTrue(self.vt.matches_video_url('http://someurl.com/video.ogg'))
        self.assertTrue(self.vt.matches_video_url('http://someurl.com/video.mp4'))
        self.assertTrue(self.vt.matches_video_url('http://someurl.com/video.m4v'))
        self.assertTrue(self.vt.matches_video_url('http://someurl.com/video.webm'))

        self.assertFalse(self.vt.matches_video_url('http://someurl.ogv'))
        self.assertFalse(self.vt.matches_video_url('http://someurl.com/ogv'))
        self.assertFalse(self.vt.matches_video_url(''))
        #for this is other type
        self.assertFalse(self.vt.matches_video_url('http://someurl.com/video.flv'))
        self.assertFalse(self.vt.matches_video_url('http://someurl.com/ogv.video'))

class Mp3VideoTypeTest(TestCase):
    def setUp(self):
        self.vt = Mp3VideoType

    def test_matches_video_url(self):
        self.assertTrue(self.vt.matches_video_url(
            'http://someurl.com/audio.mp3'))
        self.assertTrue(self.vt.matches_video_url(
            'http://someurl.com/audio.MP3'))
        self.assertFalse(self.vt.matches_video_url(
            'http://someurl.com/mp3.audio'))

class DailymotionVideoTypeTest(TestCase):
    def test_matches_video_url(self):
        url = ('http://www.dailymotion.com/video/'
               'x7u2ww_juliette-drums_lifestyle#hp-b-l')

        self.assertTrue(DailymotionVideoType.matches_video_url(url))
        self.assertFalse(DailymotionVideoType.matches_video_url(''))
        self.assertFalse(DailymotionVideoType.matches_video_url(
            'http://www.dailymotion.com'))

    def test_video_id(self):
        url = ('http://www.dailymotion.com/video/'
               'x7u2ww_juliette-drums_lifestyle#hp-b-l')
        vt = DailymotionVideoType(url)
        self.assertEqual(vt.video_id, 'x7u2ww')

    @unittest.skip('Need mock dailymotion API')
    def test_set_values(self):
        # TODO: implement this without doing a direct request to dailymotion
        pass

class FLVVideoTypeTest(TestCase):
    def setUp(self):
        self.vt = FLVVideoType

    def test_matches_video_url(self):
        self.assertTrue(self.vt.matches_video_url(
            'http://someurl.com/video.flv'))
        self.assertFalse(self.vt.matches_video_url(
            'http://someurl.flv'))
        self.assertFalse(self.vt.matches_video_url(
            ''))
        self.assertFalse(self.vt.matches_video_url(
            'http://someurl.com/flv.video'))

class VimeoVideoTypeTest(TestCase):
    def test_video_id(self):
        vt = VimeoVideoType('http://vimeo.com/15786066?some_param=111')
        self.assertEqual(vt.video_id, '15786066')

    def test_matches_video_url(self):
        url = 'http://vimeo.com/15786066?some_param=111'
        self.assertTrue(VimeoVideoType.matches_video_url(url))
        self.assertFalse(VimeoVideoType.matches_video_url('http://vimeo.com'))
        self.assertFalse(VimeoVideoType.matches_video_url(''))

    @unittest.skip('Need Mock Vimeo APi')
    def test_set_values(self):
        # We should re-empliment this one once we have a way to mock out the
        # vimeo API.
        url = u'http://vimeo.com/22070806'
        vt = VimeoVideoType(url)
        video = Video()
        vt.set_values(video, None, None)

        self.assertNotEqual(video.title, '')
        self.assertNotEqual(video.description, '')

class VideoTypeRegistrarTest(TestCase):
    def test_base(self):
        registrar = VideoTypeRegistrar()

        class MockupVideoType(VideoType):
            abbreviation = 'mockup'
            name = 'MockUp'

        registrar.register(MockupVideoType)
        self.assertEqual(registrar[MockupVideoType.abbreviation], MockupVideoType)
        self.assertEqual(registrar.choices[-1], (MockupVideoType.abbreviation, MockupVideoType.name))

    def test_video_type_for_url(self):
        type = video_type_registrar.video_type_for_url('some url')
        self.assertEqual(type, None)
        type = video_type_registrar.video_type_for_url('http://youtube.com/v=UOtJUmiUZ08')
        self.assertTrue(isinstance(type, YoutubeVideoType))
        return
        self.assertRaises(VideoTypeError, video_type_registrar.video_type_for_url,
                          'http://youtube.com/v=100500')

class BrightcoveVideoTypeTest(TestCase):
    player_id = '1234'
    video_id = '5678'

    @test_utils.patch_for_test('videos.types.brightcove.BrightcoveVideoType._resolve_url_redirects')
    def setUp(self, resolve_url_redirects):
        TestCase.setUp(self)
        self.resolve_url_redirects = resolve_url_redirects
        resolve_url_redirects.side_effect = lambda url: url

    def check_url(self):
            self.assertEquals(vu.type, 'R')
            self.assertEquals(vu.brightcove_id(), self.video_id)

    def test_type(self):
        self.assertEqual(BrightcoveVideoType.abbreviation,
                         VIDEO_TYPE_BRIGHTCOVE)

    def make_url(self, url):
        return url.format(video_id=self.video_id, player_id=self.player_id)

    def check_url(self, url):
        self.assertTrue(BrightcoveVideoType.matches_video_url(url))
        vt = BrightcoveVideoType(url)
        self.assertEquals(vt.video_id, self.video_id)

    def check_no_match(self, url):
        self.assertFalse(BrightcoveVideoType.matches_video_url(url))

    def test_old_style_urls(self):
        # test URLs with the video_id in the path
        self.check_url(self.make_url(
            'http://link.brightcove.com'
            '/services/link/bcpid{player_id}/bctid{video_id}'))
        self.check_url(self.make_url(
            'http://bcove.me'
            '/services/link/bcpid{player_id}/bctid{video_id}'))
        # test URLs with the video_id in the query
        self.check_url(self.make_url(
            'http://link.brightcove.com'
            '/services/link/bcpid{player_id}'
            '?bckey=foo&bctid={video_id}'))

    def test_mp4_urls(self):
        self.check_url(self.make_url(
            'https://foo-a.akamaihd.net/123/132_456_789.mp4'
            '?pubId=123&videoId={video_id}'))
        # Don't match if the host is different
        self.check_no_match(self.make_url(
            'https://foo-a.example.com/123/132_456_789.mp4'
            '?pubId=123&videoId={video_id}'))
        # Don't match if the query parameters are different
        self.check_no_match(self.make_url(
            'https://foo-a.akamaihd.net/123/132_456_789.mp4'
            '?pubId=123&videoId={video_id}&foo=bar'))
        self.check_no_match(self.make_url(
            'https://foo-a.akamaihd.net/123/132_456_789.mp4'
            '?videoId={video_id}'))

    def test_redirection(self):
        # test URLs in bcove.me that redirect to another brightcove URL
        self.resolve_url_redirects.side_effect = lambda url: self.make_url(
            'http://link.brightcove.com/'
            'services/link/bcpid{player_id}/bctid{video_id}')
        self.check_url('http://bcove.me/shortpath')

class KalturaVideoTypeTest(TestCase):
    def test_video_id(self):
        url = ('http://cdnbakmi.kaltura.com/p/1492321/sp/149232100/serveFlavor/'
               'entryId/1_zr7niumr/flavorId/1_djpnqf7y/name/a.mp4')

        vt = KalturaVideoType(url)
        self.assertEquals(vt.abbreviation, 'K')
        self.assertEquals(vt.kaltura_id(), '1_zr7niumr')

