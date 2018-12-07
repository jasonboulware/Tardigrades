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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

from django.test import TestCase

from caching.tests.utils import assert_invalidates_model_cache
from subtitles import pipeline
from subtitles.models import SubtitleLanguage
from utils.factories import *

class VideoCacheInvalidationTest(TestCase):
    # test a bunch of actions that should invalidate the video cache
    def setUp(self):
        self.video = VideoFactory()
        self.version = pipeline.add_subtitles(self.video, 'en',
                                              SubtitleSetFactory())
        self.language = self.version.subtitle_language

    def test_new_version(self):
        with assert_invalidates_model_cache(self.video):
            pipeline.add_subtitles(self.video, 'en', SubtitleSetFactory())

    def test_rollback(self):
        pipeline.add_subtitles(self.video, 'en', SubtitleSetFactory())
        with assert_invalidates_model_cache(self.video):
            pipeline.rollback_to(self.video, 'en', 1)

    def test_delete_language(self):
        with assert_invalidates_model_cache(self.video):
            self.language.nuke_language()

    def test_new_language(self):
        with assert_invalidates_model_cache(self.video):
            SubtitleLanguage.objects.create(video=self.video,
                                            language_code='fr')

    def test_add_video_url(self):
        with assert_invalidates_model_cache(self.video):
            self.video.add_url('http://example.com/video4.mp4', UserFactory())

    def test_remove_video_url(self):
        video_url = VideoURLFactory(video=self.video)
        with assert_invalidates_model_cache(self.video):
            video_url.delete()

    def test_update_video(self):
        with assert_invalidates_model_cache(self.video):
            self.video.title = 'new title'
            self.video.save()

    def test_update_language(self):
        with assert_invalidates_model_cache(self.video):
            self.language.subtitles_complete = True
            self.language.save()

    def test_update_version(self):
        pipeline.add_subtitles(self.video, 'en', SubtitleSetFactory())
        with assert_invalidates_model_cache(self.video):
            self.version.unpublish()

    def test_add_follower(self):
        user = UserFactory()
        with assert_invalidates_model_cache(self.video):
            self.video.followers.add(user)

    def test_remove_follower(self):
        user = UserFactory()
        self.video.followers.add(user)
        with assert_invalidates_model_cache(self.video):
            self.video.followers.remove(user)
