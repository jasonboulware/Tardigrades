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

"""Test signal emmission."""

from __future__ import absolute_import

from django.test import TestCase
from nose.tools import *
import mock

from babelsubs.storage import SubtitleSet
from utils.factories import *
from utils.test_utils import patch_for_test, mock_handler
from subtitles import signals
from subtitles import pipeline
from subtitles import workflows

class DeleteLanguageTest(TestCase):
    def setUp(self):
        self.video = TeamVideoFactory().video
        self.subtitles_deleted_handler = mock.Mock()
        signals.subtitles_deleted.connect(self.subtitles_deleted_handler,
                                         weak=False)
        self.addCleanup(signals.subtitles_deleted.disconnect,
                        self.subtitles_deleted_handler)

    def test_subtitles_deleted(self):
        v1 = pipeline.add_subtitles(self.video, 'en', None)
        language = v1.subtitle_language
        language.nuke_language()
        self.assertEquals(self.subtitles_deleted_handler.call_count, 1)
        self.subtitles_deleted_handler.assert_called_with(signal=mock.ANY,
                                                         sender=language)

class NewVersionTest(TestCase):
    def test_add_subtitles(self):
        video = VideoFactory()
        with mock_handler(signals.subtitles_added) as handler:
            version = pipeline.add_subtitles(video, 'en',
                                             SubtitleSetFactory())
        assert_true(handler.called)
        assert_equal(handler.call_args,
                     mock.call(signal=mock.ANY,
                               sender=version.subtitle_language,
                               version=version))

    def test_rollback(self):
        video = VideoFactory()
        v1 = pipeline.add_subtitles(video, 'en', SubtitleSetFactory())
        v2 = pipeline.add_subtitles(video, 'en', SubtitleSetFactory())
        with mock_handler(signals.subtitles_added) as handler:
            v3 = pipeline.rollback_to(video, 'en', v1.version_number)
        assert_true(handler.called)
        assert_equal(handler.call_args,
                     mock.call(signal=mock.ANY,
                               sender=v3.subtitle_language,
                               version=v3))

class SubtitlesPublishedTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.video = VideoFactory()
        self.subtitles_published_handler = mock.Mock()
        signals.subtitles_published.connect(self.subtitles_published_handler,
                                            weak=False)
        self.addCleanup(signals.subtitles_published.disconnect,
                        self.subtitles_published_handler)

    def test_publish_action(self):
        # test the publish action by itself
        pipeline.add_subtitles(self.video, 'en', SubtitleSetFactory())
        self.subtitles_published_handler.reset_mock()
        workflow = workflows.get_workflow(self.video)
        workflow.perform_action(self.user, 'en', 'publish')
        self.subtitles_published_handler.assert_called_with(
            signal=mock.ANY, sender=self.video.subtitle_language('en'),
            version=None)

    def test_add_subtitles_with_publish(self):
        # test adding subtitles with the publish action
        v = pipeline.add_subtitles(self.video, 'en', SubtitleSetFactory(),
                                   action='publish')
        self.subtitles_published_handler.assert_called_with(
            signal=mock.ANY, sender=v.subtitle_language, version=v)

    def test_add_subtitles_without_publish(self):
        # test adding subtitles without the publish action
        pipeline.add_subtitles(self.video, 'en', SubtitleSetFactory(),
                               action=None)
        assert_equal(self.subtitles_published_handler.call_count, 0)

    def test_add_subtitles_with_complete_true(self):
        # test adding subtitles with complete=True
        v = pipeline.add_subtitles(self.video, 'en', SubtitleSetFactory(),
                                   complete=True)
        self.subtitles_published_handler.assert_called_with(
            signal=mock.ANY, sender=v.subtitle_language, version=v)

    def test_add_subtitles_with_complete_true_but_unsynced_subs(self):
        # test adding subtitles with complete=True, but the subtitles
        # themseleves aren't complete.  For this corner case, we should not
        # emit subtitles_published.
        subs = SubtitleSet(language_code='en')
        subs.append_subtitle(None, None, 'content')
        pipeline.add_subtitles(self.video, 'en', subs, complete=True)
        assert_equal(self.subtitles_published_handler.call_count, 0)
