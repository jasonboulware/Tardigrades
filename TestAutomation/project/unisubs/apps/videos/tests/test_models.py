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

import functools

from django.db import IntegrityError
from django.test import TestCase, TransactionTestCase
from django.utils.encoding import iri_to_uri
from nose.tools import *
import babelsubs
import mock

from auth.models import CustomUser as User
from subtitles import pipeline
from subtitles.models import SubtitleLanguage
from videos import signals
from videos.models import Video, VideoUrl, VideoTypeUrlPattern
from videos.tasks import video_changed_tasks
from videos.tests.data import (
    get_video, make_subtitle_language, make_subtitle_version, make_rollback_to
)
from widget import video_cache
from utils.subtitles import dfxp_merge
from utils import test_utils
from utils.factories import *
from utils.test_utils import MockVideoType

def refresh(m):
    return m.__class__._default_manager.get(pk=m.pk)

class TestVideoUrl(TestCase):
    def setUp(self):
        self.video = VideoFactory()
        self.primary_url = self.video.get_primary_videourl_obj()
        self.url = VideoURLFactory(video=self.video)
        self.user = UserFactory()

    def test_remove(self):
        self.url.remove(self.user)
        assert_equal(self.video.videourl_set.count(), 1)

    def test_remove_primary(self):
        with assert_raises(IntegrityError):
            self.primary_url.remove(self.user)

    def test_unicode_url(self):
        unicode_url = u"http://\u2014.com"
        self.primary_url.url = unicode_url
        self.primary_url.save()
        self.assertEqual(iri_to_uri(unicode_url), self.primary_url.url)

    def test_unique_error_message(self):
        self.assertEqual(self.url.unique_error_message(None, ['url']),
                         ('This URL already <a href="{}">exists</a> as its own video in our system. ' +
                         'You can\'t add it as a secondary URL.').format(self.url.get_absolute_url()))
class TestVideo(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.youtube_video = 'http://www.youtube.com/watch?v=pQ9qX8lcaBQ'
        self.html5_video = 'http://mirrorblender.top-ix.org/peach/bigbuckbunny_movies/big_buck_bunny_1080p_stereo.ogg'

    def test_url_cache(self):
        test_utils.invalidate_widget_video_cache.run_original_for_test()
        video = get_video(1)
        video_url = video.get_video_url()

        # After adding the video, we should be able to look up its ID in the
        # cache, given just the URL.
        cache_id_1 = video_cache.get_video_id(video_url)
        self.assertIsNotNone(cache_id_1)
        self.assertTrue(Video.objects.filter(video_id=cache_id_1).exists())

        # Remove the video (and make sure it's gone).
        video.delete()
        self.assertFalse(Video.objects.filter(videourl__url=video_url).exists())

        # Trying to get the video ID out of the cache now actually *creates* the
        # video!
        cache_id_2 = video_cache.get_video_id(video_url)
        self.assertTrue(Video.objects.filter(videourl__url=video_url).exists())

        # The video_id will be different than before (since this is a new Video
        # record) and the cache should have been updated properly.
        self.assertNotEqual(cache_id_1, cache_id_2)
        self.assertTrue(Video.objects.filter(video_id=cache_id_2).exists())

    def test_video_title(self):
        video = get_video(url='http://www.youtube.com/watch?v=pQ9qX8lcaBQ')

        def _assert_title(correct_title):
            self.assertEquals(refresh(video).title, correct_title)

        # Test title before any subtitles are added.
        _assert_title(test_utils.test_video_info.title)

        # Make a subtitle language in the primary language.
        video.primary_audio_language_code = 'en'
        video.save()
        sl_en = make_subtitle_language(video, 'en')

        # Just adding languages shouldn't affect the title.
        _assert_title(test_utils.test_video_info.title)

        # Add subtitles with a custom title.  The title should be updated to
        # reflect this.
        make_subtitle_version(sl_en, [], title="New Title")
        _assert_title("New Title")

        # New versions should continue update the title properly.
        make_subtitle_version(sl_en, [], title="New Title 2")
        _assert_title("New Title 2")

        # Versions in a non-primary-audio-language should not affect the video
        # title.
        sl_ru = make_subtitle_language(video, 'ru')
        make_subtitle_version(sl_ru, [], title="New Title 3")
        _assert_title("New Title 2")

        # Rollbacks (of the primary audio language) should affect the title just
        # like a new version.
        make_rollback_to(sl_en, 1)
        _assert_title("New Title")

class TestChangedSignals(TestCase):
    def test_title_changed_signal(self):
        video = VideoFactory(title='old_title')
        with test_utils.mock_handler(signals.title_changed) as mock_handler:
            # normal saves shouldn't cause the signal to emit
            video.save()
            assert_equal(mock_handler.call_count, 0)
            # saves that change the title should
            video.title = 'new_title'
            video.save()
            assert_equal(mock_handler.call_count, 1)
            assert_equal(mock_handler.call_args,
                         mock.call(signal=signals.title_changed,
                                   sender=video, old_title='old_title'))
            # test that 1 more save doesn't cause a second signal
            video.save()
            assert_equal(mock_handler.call_count, 1)

    def test_duration_changed_signal(self):
        video = VideoFactory(duration=100)
        with test_utils.mock_handler(signals.duration_changed) as mock_handler:
            # normal saves shouldn't cause the signal to emit
            video.save()
            assert_equal(mock_handler.call_count, 0)
            # saves that change the duration should
            video.duration = 200
            video.save()
            assert_equal(mock_handler.call_count, 1)
            assert_equal(mock_handler.call_args,
                         mock.call(signal=signals.duration_changed,
                                   sender=video, old_duration=100))
            # test that 1 more save doesn't cause a second signal
            video.save()
            assert_equal(mock_handler.call_count, 1)

    def test_language_changed_signal(self):
        video = VideoFactory(primary_audio_language_code='')
        with test_utils.mock_handler(signals.language_changed) as mock_handler:
            # normal saves shouldn't cause the signal to emit
            video.save()
            assert_equal(mock_handler.call_count, 0)
            # saves that change the language should
            video.primary_audio_language_code = 'en'
            video.save()
            assert_equal(mock_handler.call_count, 1)
            assert_equal(mock_handler.call_args,
                         mock.call(signal=signals.language_changed,
                                   sender=video,
                                   old_primary_audio_language_code=''))
            # test that 1 more save doesn't cause a second signal
            video.save()
            assert_equal(mock_handler.call_count, 1)

    def test_no_changed_signals_on_initial_created(self):
        cm1 = test_utils.mock_handler(signals.title_changed)
        cm2 = test_utils.mock_handler(signals.duration_changed)
        cm3 = test_utils.mock_handler(signals.language_changed)
        with cm1 as handler1, cm2 as handler2, cm3 as handler3:
            video = Video()
            video.primary_audio_language_code = 'en'
            video.title = 'foo'
            video.duration = 123
            video.save()
        assert_equal(handler1.call_count, 0)
        assert_equal(handler2.call_count, 0)
        assert_equal(handler3.call_count, 0)

class TestModelsSaving(TestCase):
    def test_video_languages_count(self):
        # TODO: Merge this into the metadata tests file?
        video = get_video()

        # Start with no languages.
        self.assertEqual(video.languages_count, 0)
        self.assertEqual(video.newsubtitlelanguage_set.having_nonempty_tip()
                                                      .count(),
                         0)

        # Create one.
        sl_en = make_subtitle_language(video, 'en')
        make_subtitle_version(sl_en, [(100, 200, "foo")])

        # The query should immediately show it.
        self.assertEqual(video.newsubtitlelanguage_set.having_nonempty_tip()
                                                      .count(),
                         1)

        # But the model object will not.
        self.assertEqual(video.languages_count, 0)

        # Even if we refresh it, the model still doesn't show it.
        video = Video.objects.get(pk=video.pk)
        self.assertEqual(video.languages_count, 0)

        # Until we run the proper tasks.
        video_changed_tasks.delay(video.pk)
        test_utils.video_changed_tasks.run_original()

        # But we still need to refresh it to see the change.
        self.assertEqual(video.languages_count, 0)
        video = Video.objects.get(pk=video.pk)
        self.assertEqual(video.languages_count, 1)

    def test_subtitle_language_save(self):
        def _refresh(video):
            video_changed_tasks.delay(video.pk)
            test_utils.video_changed_tasks.run_original()
            return Video.objects.get(pk=video.pk)

        # Start out with a video with one language.
        # By default languages are not complete, so the video should not be
        # complete either.
        video = get_video()
        sl_en = make_subtitle_language(video, 'en')
        self.assertIsNone(video.complete_date)
        self.assertEqual(video.newsubtitlelanguage_set.count(), 1)

        # Marking the language as complete doesn't complete the video on its own
        # -- we need at least one version!
        sl_en.subtitles_complete = True
        sl_en.save()
        video = _refresh(video)
        self.assertIsNone(video.complete_date)

        # But an unsynced version can't be complete either!
        # TODO: uncomment once babelsubs supports unsynced subs...
        # make_subtitle_version(sl_en, [(100, None, "foo")])
        # video = _refresh(video)
        # self.assertIsNone(video.complete_date)

        # A synced version (plus the previously set flag on the language) should
        # result in a completed video.
        make_subtitle_version(sl_en, [(100, 200, "foo")])
        video = _refresh(video)
        self.assertIsNotNone(video.complete_date)

        # Unmarking the language as complete should uncomplete the video.
        sl_en.subtitles_complete = False
        sl_en.save()
        video = _refresh(video)
        self.assertIsNone(video.complete_date)

        # Any completed language is enough to complete the video.
        sl_ru = make_subtitle_language(video, 'ru')
        make_subtitle_version(sl_ru, [(100, 200, "bar")])
        sl_ru.subtitles_complete = True
        sl_ru.save()

        video = _refresh(video)
        self.assertIsNotNone(video.complete_date)

class TestSubtitleLanguageCaching(TestCase):
    def setUp(self):
        self.videos, self.langs, self.versions = bulk_subs({
            'video': {
                'en': [
                    {},
                    {},
                    {}
                ],
                'es': [
                    {},
                ],
                'fr': [
                    {},
                    {'visibility': 'private'},
                ],
            },
        })
        self.video = self.videos['video']

    def test_fetch_one_language(self):
        self.assertEquals(self.video.subtitle_language('en').id,
                          self.langs['video', 'en'].id)

    def test_fetch_all_languages(self):
        self.assertEquals(
            set(l.id for l in self.video.all_subtitle_languages()),
            set(l.id for l in self.langs.values()))

    def test_cache_one_language(self):
        # the first call should result in a query
        with self.assertNumQueries(1):
            lang = self.video.subtitle_language('en')
        # subsequent calls shouldn't
        with self.assertNumQueries(0):
            self.assertEquals(self.video.subtitle_language('en'), lang)
            # the language video should be cached as well
            lang.video
        # but they should once we clear the cache
        self.video.clear_language_cache()
        with self.assertNumQueries(1):
            self.video.subtitle_language('en')

    def test_cache_all_languages(self):
        with self.assertNumQueries(1):
            languages = self.video.all_subtitle_languages()

        lang_map = dict((l.language_code, l) for l in languages)
        with self.assertNumQueries(0):
            self.assertEquals(set(languages),
                              set(self.video.all_subtitle_languages()))
            # the videos should be cached
            for lang in languages:
                lang.video
            # fetching one video should use the cache as well
            self.assertEquals(self.video.subtitle_language('en'),
                              lang_map['en'])
        self.video.clear_language_cache()
        with self.assertNumQueries(1):
            self.video.all_subtitle_languages()

    def test_non_existant_language(self):
        # subtitle_language() should return None for non-existant languages
        self.assertEquals(self.video.subtitle_language('pt-br'), None)
        # we should cache that result
        with self.assertNumQueries(0):
            self.assertEquals(self.video.subtitle_language('pt-br'), None)
        # just because None is in the cache, we shouldn't return it from
        # all_subtitle_languages()
        for lang in self.video.all_subtitle_languages():
            self.assertNotEquals(lang, None)
        # try that again now that all the languages are cached
        for lang in self.video.all_subtitle_languages():
            self.assertNotEquals(lang, None)

    def test_prefetch(self):
        self.video.prefetch_languages()
        with self.assertNumQueries(0):
            self.video.all_subtitle_languages()
            lang = self.video.subtitle_language('en')
            # fetching the video should be cached
            lang.video

    def test_prefetch_some_languages(self):
        self.video.prefetch_languages(languages=['en', 'es'])
        with self.assertNumQueries(0):
            self.video.subtitle_language('en')
            self.video.subtitle_language('es')
        with self.assertNumQueries(1):
            self.video.subtitle_language('fr')

    def test_prefetch_with_tips(self):
        self.video.prefetch_languages(with_public_tips=True,
                                      with_private_tips=True)
        with self.assertNumQueries(0):
            for lang in self.video.all_subtitle_languages():
                # fetching the tips should be cached
                lang.get_tip(public=True)
                lang.get_tip(public=False)
                # fetching the version video should be cached
                lang.get_tip(public=True).video
                lang.get_tip(public=False).video

class TestSelectHasPublicVersion(TestCase):
    def setUp(self):
        self.video = VideoFactory()

    def check_has_public_version(self, correct_value):
        qs = Video.objects.filter(pk=self.video.pk).select_has_public_version()
        assert_equal(bool(qs[0]._has_public_version), correct_value)

    def test_no_versions(self):
        self.check_has_public_version(False)

    def test_visibility_public(self):
        pipeline.add_subtitles(self.video, 'en', None, visibility='public')
        self.check_has_public_version(True)

    def test_visibility_private(self):
        pipeline.add_subtitles(self.video, 'en', None, visibility='private')
        self.check_has_public_version(False)

    def test_visibility_override_public(self):
        pipeline.add_subtitles(self.video, 'en', None, visibility='private',
                               visibility_override='public')
        self.check_has_public_version(True)

    def test_visibility_override_private(self):
        pipeline.add_subtitles(self.video, 'en', None, visibility='public',
                               visibility_override='private')
        self.check_has_public_version(False)

    def test_visibility_override_deleted(self):
        pipeline.add_subtitles(self.video, 'en', None, visibility='public',
                               visibility_override='deleted')
        self.check_has_public_version(False)

    def test_one_version_public(self):
        pipeline.add_subtitles(self.video, 'en', None, visibility='public')
        pipeline.add_subtitles(self.video, 'en', None, visibility='private')
        self.check_has_public_version(True)

    def test_has_public_version_is_optimized(self):
        # test that calling has_public_version() doesn't result in any db
        # queries
        other_video = VideoFactory()
        pipeline.add_subtitles(self.video, 'en', None, visibility='public')
        pipeline.add_subtitles(other_video, 'en', None, visibility='private')
        videos = list(Video.objects.all().select_has_public_version()
                      .order_by('id'))
        with self.assertNumQueries(0):
            assert_true(videos[0].has_public_version())
            assert_false(videos[1].has_public_version())

class TestGetMergedDFXP(TestCase):
    def test_get_merged_dfxp(self):
        video = VideoFactory(primary_audio_language_code='en')
        pipeline.add_subtitles(video, 'en', [
            (100, 200, 'text'),
        ])
        pipeline.add_subtitles(video, 'fr', [
            (100, 200, 'french text'),
        ])
        pipeline.add_subtitles(video, 'es', [
            (100, 200, 'spanish text'),
        ])
        pipeline.add_subtitles(video, 'de', [
            (100, 200, 'spanish text'),
        ], visibility='private')

        video.clear_language_cache()

        subtitles = [
            video.subtitle_language(lang).get_public_tip().get_subtitles()
            for lang in ('en', 'fr', 'es')
        ]

        self.assertEquals(video.get_merged_dfxp(), dfxp_merge(subtitles))

class TestTypeUrlPatterns(TestCase):
    def setUp(self):
        pattern = VideoTypeUrlPattern()
        self.url = "http://example.com/"
        self.type = "YT"
        pattern.url_pattern = self.url
        pattern.type = self.type
        pattern.save()
    def get_patterns_for_type(self):
        patterns = VideoTypeUrlPattern.objects.patterns_for_type("YT")
        self.assertEquals(len(patterns), 1)
        for p in patterns:
            self.assertEquals(p.type, self.type)
            self.assertEquals(p.url_pattern, self.url)

class AddVideoTest(TestCase):
    def setUp(self):
        self.url = 'http://example.com/video.mp4'
        self.user = UserFactory()

    def test_add_video(self):
        # test the simple case of creating a new video
        video, video_url = Video.add(MockVideoType(self.url), self.user)
        assert_equal(video.get_video_url(), self.url)
        assert_equal(video_url.primary, True)
        assert_equal(video_url.added_by, self.user)
        assert_equal(video_url.type, MockVideoType.abbreviation)
        assert_equal(video.user, self.user)

    @test_utils.with_mock_video_type_registrar
    def test_string_url(self, mock_registrar):
        video, video_url = Video.add(self.url, self.user)
        assert_equal(mock_registrar.video_type_for_url.call_args,
                     mock.call(self.url))
        assert_equal(video_url.type, MockVideoType.abbreviation)

    def test_attributes_from_video_url(self):
        # Video.add() should set attributes on the video from the VideoType
        mock_video_type = MockVideoType(self.url, title='vurl title',
                                        duration=100)
        mock_video_type.owner_username.return_value = 'test-user'
        video, video_url = Video.add(mock_video_type, self.user)
        assert_equal(video.title, 'vurl title')
        assert_equal(video.duration, 100)
        assert_equal(video_url.videoid, mock_video_type.video_id)

    def test_null_videoid(self):
        # Test VideoType.video_id being None
        mock_video_type = MockVideoType(self.url)
        mock_video_type.video_id = None
        video, video_url = Video.add(mock_video_type, self.user)
        assert_equal(video_url.videoid, '')

    def test_setup_callback(self):
        # Test the setup_callback param
        def setup_callback(video, video_url):
            video.title = 'setup_callback title'
        video, video_url = Video.add(MockVideoType(self.url), self.user,
                                     setup_callback)
        assert_equal(video.title, 'setup_callback title')
        # check that we saved the data to the DB
        assert_equal(test_utils.reload_obj(video).title,
                     'setup_callback title')

    def test_convert_video_url(self):
        # We should allow the VideoType to alter the URL using the
        # convert_to_video_url() method.
        new_url = 'http://example.com/new_url.mp4'
        video, video_url = Video.add(MockVideoType(new_url), self.user)
        assert_equal(video_url.url, new_url)

    def test_title_from_url(self):
        # As a fallback, we should use the video URL to set the title
        video, video_url = Video.add(MockVideoType(self.url), self.user)
        assert_equal(video.title, 'example.com/.../video.mp4')
        # but not if title is set manually
        video.delete()
        def setup_callback(video, video_url):
            video.title = 'test title'
        video, video_url = Video.add(MockVideoType(self.url), self.user,
                                     setup_callback)
        assert_equal(video.title, 'test title')

    def test_notify_by_message(self):
        self.user.notify_by_message = True
        video, video_url = Video.add(MockVideoType(self.url), self.user)
        assert_true(video.followers.filter(id=self.user.id).exists())

    def test_notify_by_message_false(self):
        self.user.notify_by_message = False
        video, video_url = Video.add(MockVideoType(self.url), self.user)
        assert_false(video.followers.filter(id=self.user.id).exists())

    @test_utils.mock_handler(signals.video_added)
    @test_utils.mock_handler(signals.video_url_added)
    def test_signals(self, on_video_url_added, on_video_added):
        def setup_callback(video, video_url):
            assert_equal(on_video_added.call_count, 0)
            assert_equal(on_video_url_added.call_count, 0)
        video, video_url = Video.add(MockVideoType(self.url), self.user,
                                     setup_callback)
        assert_equal(on_video_added.call_count, 1)
        assert_equal(on_video_added.call_args,
                     mock.call(signal=signals.video_added,
                               sender=video, video_url=video_url))
        assert_equal(on_video_url_added.call_count, 1)
        assert_equal(on_video_url_added.call_args,
                     mock.call(signal=signals.video_url_added,
                               sender=video_url, video=video, new_video=True, team=None, user=self.user))

def check_duplicate_url_error(url, existing_video, team=None,
                              from_prevent_duplicate_public_videos=False):
    num_videos_before_call = Video.objects.count()
    with assert_raises(Video.DuplicateUrlError) as cm:
        v, vurl = Video.add(url, UserFactory(), team=team)
    assert_equal(cm.exception.video, existing_video)
    assert_equal(cm.exception.video_url, existing_video.get_primary_videourl_obj())
    assert_equal(cm.exception.from_prevent_duplicate_public_videos,
                 from_prevent_duplicate_public_videos)
    # test that we didn't create any extra videos as a result of the call
    assert_equal(Video.objects.count(), num_videos_before_call)


class AddVideoTestWithTransactions(TransactionTestCase):
    # These tests is split off from the others because it needs to be inside a
    # TransactionTestCase.  TransactionTestCase is not needed for the other
    # tests and it slows things down a lot.

    def test_duplicate_video_url_public_video(self):
        # test calling Video.add() with a URL already in the system on a
        # public video.
        url = 'http://example.com/video.mp4'
        # This should be an exception if the video is being added without a
        # team
        video = VideoFactory(video_url__url=url)
        check_duplicate_url_error(url, video)
        # Adding with to a team should be okay though
        Video.add(url, UserFactory(), team=TeamFactory())

    def test_duplicate_video_url_but_other_team(self):
        # test calling Video.add() with a URL already in the system on a
        # team video
        url = 'http://example.com/video.mp4'
        team = TeamFactory()
        other_team = TeamFactory()
        video = VideoFactory(video_url__url=url, team=team)
        # Adding a video to the same team should be an exception
        check_duplicate_url_error(url, video, team=team)
        # Adding to a different team should be okay though
        Video.add(url, UserFactory(), team=other_team)
        # Adding a public video should also be okay
        Video.add(url, UserFactory(), team=None)

    def test_exception_in_setup_callback(self):
        # If setup_callback throws an exception, we shouldn't create any
        # video/video_url objects
        num_videos_before_call = Video.objects.count()
        num_video_urls_before_call = VideoUrl.objects.count()
        url = 'http://example.com/video.mp4'
        with assert_raises(ValueError):
            Video.add(MockVideoType(url), UserFactory(),
                      mock.Mock(side_effect=ValueError()))

        assert_equal(Video.objects.count(), num_videos_before_call)
        assert_equal(VideoUrl.objects.count(), num_video_urls_before_call)

class PreventDuplicatePublicVideoFlagTest(TestCase):
    # Test adding videos when a team has prevent_duplicate_public_videos set
    def setUp(self):
        self.user = UserFactory()
        self.team = TeamFactory(prevent_duplicate_public_videos=True,
                                admin=self.user)
        self.project = ProjectFactory(team=self.team, slug='test-project')
        self.url = 'http://example.com/video.mp4'

    def test_add_to_team_moves_public_video(self):
        # Test adding a video URL to a team, when it's already on a video in
        # the public area.  We should move the existing video rather than
        # create a new one
        video1, video_url1 = Video.add(self.url, self.user)
        video2, video_url2 = self.team.add_video(self.url, self.user)
        assert_equal(video1.id, video2.id)
        assert_equal(video2.get_team_video().team, self.team)
        video_url = VideoUrl.objects.get(url=self.url)
        assert_equal(video_url.team_id, self.team.id)

    def test_move_into_project(self):
        # Test moving a video from the public area and also into a project
        video1, video_url1 = Video.add(self.url, self.user)
        video2, video_url2 = self.team.add_video(self.url, self.user,
                                        project=self.project)
        assert_equal(video2.get_team_video().project, self.project)

    def test_add_to_public(self):
        # Test adding a video URL to the public area when it's already on a
        # video in the team.  We should throw a DuplicateUrlError.
        video, video_url = self.team.add_video(self.url, self.user)
        check_duplicate_url_error(self.url, video,
                                  from_prevent_duplicate_public_videos=True)

    def test_remove_from_team(self):
        # Test removing a video from a different team, when one of it's video
        # URLs is on the team.  This should result in a DuplicateUrlError,
        # since the video would go to the public area otherwise.
        video1, video_url1 = self.team.add_video(self.url, self.user)
        other_team = TeamFactory(admin=self.user)
        video2, video_url2 = other_team.add_video(self.url, self.user)

        with assert_raises(Video.DuplicateUrlError) as cm:
            video2.get_team_video().remove(self.user)
        assert_equal(cm.exception.video, video1)
        assert_equal(cm.exception.video_url, video_url1)
        assert_equal(cm.exception.from_prevent_duplicate_public_videos, True)

    def test_move_to_team(self):
        # Test moving a video from a team without
        # prevent_duplicate_public_videos to a team with it set.  It should
        # result in a DuplicateUrlError if there is a public video with the
        # same URL
        public_video, public_video_url = Video.add(self.url, self.user)
        other_team = TeamFactory(admin=self.user)
        video, video_url = other_team.add_video(self.url, self.user)
        with assert_raises(Video.DuplicateUrlError) as cm:
            video.get_team_video().move_to(self.team)
        assert_equal(cm.exception.video, public_video)
        assert_equal(cm.exception.video_url, public_video_url)
        assert_equal(cm.exception.from_prevent_duplicate_public_videos, True)

    def test_add_video_url_to_public(self):
        # Test trying to add a video URL to a public video, when that video URL
        # is already on a team video.  This should result in a
        # DuplicateUrlError.
        video1, video_url1 = self.team.add_video(self.url, self.user)
        video2, video_url2 = Video.add('http://otherurl.com/video.mp4', self.user)
        with assert_raises(Video.DuplicateUrlError) as cm:
            video2.add_url(self.url, self.user)
        assert_equal(cm.exception.video, video1)
        assert_equal(cm.exception.video_url, video_url1)
        assert_equal(cm.exception.from_prevent_duplicate_public_videos, True)

    def test_add_video_url_to_team_video(self):
        # Test trying to add a video URL to a team video, when that video URL
        # is already in the public area.  There's no clear way to handle this,
        # for now just let it happen
        video1, video_url1 = Video.add(self.url, self.user)
        video2, video_url2 = self.team.add_video(
            'http://otherurl.com/video.mp4', self.user)
        with assert_raises(Video.DuplicateUrlError) as cm:
            video2.add_url(self.url, self.user)
        assert_equal(cm.exception.video, video1)
        assert_equal(cm.exception.video_url, video_url1)
        assert_equal(cm.exception.from_prevent_duplicate_public_videos, True)

class AddVideoUrlTest(TestCase):
    def setUp(self):
        self.url = 'http://example.com/video.mp4'
        self.new_url = 'http://example.com/video2.mp4'
        self.video = VideoFactory(video_url__url=self.url)
        self.video_url = self.video.get_primary_videourl_obj()
        self.user = UserFactory()

    def test_add_url(self):
        video_url = self.video.add_url(MockVideoType(self.new_url), self.user)
        assert_equal(video_url.url, self.new_url)
        assert_equal(video_url.video, self.video)
        assert_equal(video_url.primary, False)

    @test_utils.with_mock_video_type_registrar
    def test_string_url(self, mock_registrar):
        video_url = self.video.add_url(self.new_url, self.user)
        assert_equal(mock_registrar.video_type_for_url.call_args,
                     mock.call(self.new_url))
        assert_equal(video_url.type, MockVideoType.abbreviation)

    def test_already_added(self):
        video_url = self.video.add_url(MockVideoType(self.new_url), self.user)
        num_video_urls_before_call = VideoUrl.objects.count()
        with assert_raises(Video.DuplicateUrlError) as cm:
            video_url = self.video.add_url(MockVideoType(self.new_url),
                                           self.user)
        assert_equal(cm.exception.video, self.video)
        assert_equal(cm.exception.video_url, video_url)
        assert_equal(VideoUrl.objects.count(), num_video_urls_before_call)

    def test_convert_video_url(self):
        converted_url = 'http://example.com/video2-converted.mp4'
        video_url = self.video.add_url(MockVideoType(converted_url), self.user)
        assert_equal(video_url.url, converted_url)

    def test_set_values_not_called(self):
        # since this is not the first VideoURL being added, we don't want to
        # call VideoType.set_values() and override the video attributes.
        video_url = self.video.add_url(
            MockVideoType(self.new_url, title='new title'), self.user)
        assert_not_equal(self.video.title, 'new title')

    @test_utils.mock_handler(signals.video_url_added)
    def test_signal(self, on_video_url_added):
        video_url = self.video.add_url(MockVideoType(self.new_url), self.user)
        assert_equal(on_video_url_added.call_count, 1)
        assert_equal(on_video_url_added.call_args, mock.call(
            signal=signals.video_url_added, sender=video_url,
            video=self.video, new_video=False))
