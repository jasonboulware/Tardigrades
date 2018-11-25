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

from django.test import TestCase
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django.http import HttpResponseRedirect
import mock
from nose.tools import *

from subtitles import pipeline
from videos.forms import (AddFromFeedForm, VideoForm, CreateSubtitlesForm,
                          MultiVideoCreateSubtitlesForm,)
from videos.models import Video, VideoFeed
from videos.types import video_type_registrar
from utils import test_utils
from utils.factories import *
from utils.translation import get_language_choices

class TestVideoForm(TestCase):
    def setUp(self):
        self.vimeo_urls = ("http://vimeo.com/17853047",)
        self.youtube_urls = ("http://youtu.be/HaAVZ2yXDBo",
                             "http://www.youtube.com/watch?v=HaAVZ2yXDBo")
        self.html5_urls = ("http://www.jplayer.org/video/m4v/Big_Buck_Bunny_Trailer.m4v",)
        self.daily_motion_urls = ("http://www.dailymotion.com/video/xb0hsu_qu-est-ce-que-l-apache-software-fou_tech",)

    def _test_urls(self, urls):
        for url in urls:
            form = VideoForm(data={"video_url":url})
            self.assertTrue(form.is_valid(), msg=form.errors.as_text())
            video = form.video
            video_type = video_type_registrar.video_type_for_url(url)
            # double check we never confuse video_id with video.id with videoid, sigh
            model_url = video.get_video_url()
            if hasattr(video_type, "videoid"):
                self.assertTrue(video_type.videoid  in model_url)
            # check the pk is never on any of the urls parts
            for part in model_url.split("/"):
                self.assertTrue(str(video.pk)  != part)
            self.assertTrue(video.video_id  not in model_url)

            self.assertTrue(Video.objects.filter(videourl__url=model_url).exists())

    def test_youtube_urls(self):
        self._test_urls(self.youtube_urls)

    def test_vimeo_urls(self):
        self._test_urls(self.vimeo_urls)

    def test_html5_urls(self):
        self._test_urls(self.html5_urls)

    def test_dailymotion_urls(self):
        self._test_urls(self.daily_motion_urls)

class AddFromFeedFormTestCase(TestCase):
    @test_utils.patch_for_test('videos.forms.FeedParser')
    def setUp(self, MockFeedParserClass):
        TestCase.setUp(self)
        self.user = UserFactory()
        mock_feed_parser = mock.Mock()
        mock_feed_parser.version = 1.0
        MockFeedParserClass.return_value = mock_feed_parser

    def make_form(self, **data):
        return AddFromFeedForm(self.user, data=data)

    def make_feed(self, url):
        return VideoFeed.objects.create(user=self.user, url=url)

    def test_success(self):
        form = self.make_form(feed_url='http://example.com/feed.rss')
        self.assertEquals(form.errors, {})
        form.save()
        self.assertEquals(set(f.url for f in VideoFeed.objects.all()),
                          set(['http://example.com/feed.rss']))


    def test_duplicate_feeds(self):
        # test trying to add feed that already exists
        url = 'http://example.com/feed.rss'
        self.make_feed(url)
        form = self.make_form(feed_url=url)
        self.assertNotEquals(form.errors, {})

class CreateSubtitlesFormTestBase(TestCase):
    @test_utils.patch_for_test('videos.forms.get_user_languages_from_request')
    def setUp(self, mock_get_user_languages_from_request):
        self.video = VideoFactory()
        self.user = UserFactory()
        self.mock_get_user_languages_from_request = \
                mock_get_user_languages_from_request

    def make_mock_request(self):
        mock_request = mock.Mock()
        mock_request.user = self.user
        return mock_request

class CreateSubtitlesFormTest(CreateSubtitlesFormTestBase):
    def make_form(self, data=None):
        return CreateSubtitlesForm(self.make_mock_request(), self.video,
                                   data=data)

    def test_needs_primary_audio_language(self):
        self.video.primary_audio_language_code = ''
        self.assertEquals(self.make_form().needs_primary_audio_language, True)

        self.video.primary_audio_language_code = 'en'
        self.assertEquals(self.make_form().needs_primary_audio_language, False)

    def check_language_choices(self, correct_choices):
        choices = self.make_form()['subtitle_language_code'].field.choices
        for optgroup, correct_optgroup in zip(choices, correct_choices):
            assert_equal(unicode(optgroup[0]), unicode(correct_optgroup[0]))
            assert_equal(optgroup[1], correct_optgroup[1])

    def test_subtitle_language_filter_top_section(self):
        # We should use the user's languages as our top section (if set)
        self.user.set_languages([
            dict(language='en', priority=0),
            dict(language='fr', priority=1),
        ])

        self.check_language_choices(get_language_choices(top_section=(
            ('Your Languages', [
                (u'en', 'English'),
                (u'fr', 'French'),
            ])
        )))

    def test_subtitle_language_filter_top_section_no_languages_set(self):
        self.user.set_languages([])
        self.check_language_choices(get_language_choices())

    def test_subtitle_language_filter_excludes_languages(self):
        # test that we don't allow languages that already have subtitles
        pipeline.add_subtitles(self.video, 'en', None)
        pipeline.add_subtitles(self.video, 'fr', None)
        self.check_language_choices(get_language_choices(exclude=['en', 'fr']))

    def check_redirect(self, response, language_code):
        self.assertEquals(response.__class__, HttpResponseRedirect)
        correct_url = reverse('subtitles:subtitle-editor', kwargs={
            'video_id': self.video.video_id,
            'language_code': language_code,
        })
        self.assertEquals(response['Location'], correct_url)

    def test_submit_video_has_no_primary_audio_language(self):
        # test submitting when the primary audio language code is needed
        self.video.primary_audio_language_code = ''
        form = self.make_form({
            'primary_audio_language_code': 'en',
            'subtitle_language_code': 'fr',
        })
        self.assertEquals(form.is_valid(), True)
        # handle_post should set the primary_audio_language_code, then
        # redirect to the editor
        response = form.handle_post()
        self.video = test_utils.reload_obj(self.video)
        self.assertEquals(self.video.primary_audio_language_code, 'en')
        self.check_redirect(response, 'fr')

        # try the same thing without primary_audio_language_code being
        # present.
        self.video.primary_audio_language_code = ''
        form = self.make_form({
            'subtitle_language_code': 'fr',
        })
        self.assertEquals(form.is_valid(), False)

    def test_submit_video_has_primary_audio_language_set(self):
        self.video.primary_audio_language_code = 'en'
        form = self.make_form({
            'subtitle_language_code': 'fr',
        })
        self.assertEquals(form.is_valid(), True)
        # handle_post should set the primary_audio_language_code, then
        # redirect to the editor
        response = form.handle_post()
        self.assertEquals(self.video.primary_audio_language_code, 'en')
        self.check_redirect(response, 'fr')

        # try the same thing without subtitle_language_code being present.
        form = self.make_form({})
        self.assertEquals(form.is_valid(), False)

    def test_user_permissions_check(self):
        team = TeamFactory(subtitle_policy=40)
        TeamVideoFactory(team=team, video=self.video)
        form = self.make_form({
            'primary_audio_language_code': 'en',
            'subtitle_language_code': 'fr',
        })
        # The form should be invalid, because our user doesn't have
        # permissions to subtitle the video.
        self.assertEquals(form.is_valid(), False)

class MultiVideoCreateSubtitlesFormTest(CreateSubtitlesFormTestBase):
    def make_form(self, data=None):
        return MultiVideoCreateSubtitlesForm(self.make_mock_request(),
                                             Video.objects.all(), data=data)

    def test_submit_with_existing_language(self):
        # test that submiting a subtitle language that's already created for
        # our video fails
        pipeline.add_subtitles(self.video, 'fr', None)
        form = self.make_form({
            'video': self.video.id,
            'primary_audio_language_code': 'en',
            'subtitle_language_code': 'fr',
        })
        self.assertEquals(form.is_valid(), False)
        self.assertEquals(form.errors.keys(), ['subtitle_language_code'])
