# Amara, universalsubtitles.org
#
# Copyright (C) 2014 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program.  If not, see http://www.gnu.org/licenses/agpl-3.0.html.

from __future__ import absolute_import

import functools

from django.test import TestCase
from nose.tools import *
from datetime import datetime, timedelta
import mock

from subtitles import workflows
from subtitles import pipeline
from subtitles.exceptions import ActionError
from subtitles.models import SubtitleNote
from subtitles.signals import subtitles_published, subtitles_completed
from utils.factories import *
from utils import test_utils

class MockAction(workflows.Action):
    def __init__(self, name, complete=None):
        self.name = self.label = name
        self.complete = complete
        self.call_order = []
        self.perform = mock.Mock()
        self.update_language = mock.Mock()
        def on_method_call(method_name, *args, **kwargs):
            self.call_order.append(method_name)
            orig_method = getattr(workflows.Action, method_name)
            return orig_method(self, *args, **kwargs)

        self.perform.side_effect = functools.partial(
            on_method_call, 'perform')
        self.update_language.side_effect = functools.partial(
            on_method_call, 'update_language')

class ActionsTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.video = VideoFactory()
        pipeline.add_subtitles(self.video, 'en',
                               SubtitleSetFactory(num_subs=10))
        self.subtitle_language = self.video.subtitle_language('en')

        self.action1 = MockAction('action1', True)
        self.action2 = MockAction('action2', False)
        self.workflow = workflows.Workflow(self.video)
        self.workflow.get_actions = mock.Mock(return_value=[
            self.action1, self.action2
        ])

    def perform_action(self, action_name):
        self.workflow.perform_action(self.user, 'en', action_name)

    def test_perform_action(self):
        version = pipeline.add_subtitles(self.video, 'en',
                                         SubtitleSetFactory(num_subs=10))
        self.perform_action('action1')
        assert_equal(
            self.action1.update_language.call_args,
            mock.call(self.user, self.video, version.subtitle_language, None))
        assert_equal(
            self.action1.perform.call_args,
            mock.call(self.user, self.video, version.subtitle_language, None))
        assert_equal(self.action1.call_order, ['update_language', 'perform'])

    def test_add_subtitles_with_action(self):
        action = self.workflow.lookup_action(self.user, 'en', 'action1')
        version = pipeline.add_subtitles(self.video, 'en',
                                         SubtitleSetFactory(num_subs=10),
                                         action=None)
        action.perform(self.user, self.video, version.subtitle_language,
                       version)
        self.action1.perform.assert_called_with(
            self.user, self.video, version.subtitle_language, version)

    def test_perform_with_invalid_action(self):
        with assert_raises(LookupError):
            self.perform_action('other-action')

    def test_needs_complete_subtitles(self):
        # With 0 subtitles and complete=True, validate() should raise an
        # error.
        action = self.workflow.lookup_action(self.user, 'en', 'action1')
        version = pipeline.add_subtitles(self.video, 'en',
                                         SubtitleSetFactory(num_subs=0),
                                         action=None)
        with assert_raises(ActionError):
            action.validate(self.user, self.video, version.subtitle_language,
                            version)

class SubtitleNotesTest(TestCase):
    def setUp(self):
        self.video = VideoFactory()
        self.user1 = UserFactory()
        self.user2 = UserFactory()
        SubtitleNote.objects.create(
            video=self.video,
            language_code='en',
            user=self.user1,
            body='note 1',
            created=datetime(2000, 1, 1, 12))
        SubtitleNote.objects.create(
            video=self.video,
            language_code='en',
            user=self.user2,
            body='note 2',
            created=datetime(2000, 1, 1, 13))
        self.editor_notes = workflows.EditorNotes(self.video, 'en')

    def test_heading(self):
        assert_equal(self.editor_notes.heading, 'Notes')

    def test_notes_list(self):
        assert_equal(len(self.editor_notes.notes), 2)
        assert_equal(self.editor_notes.notes[0].body, 'note 1')
        assert_equal(self.editor_notes.notes[1].body, 'note 2')

    def test_post(self):
        self.editor_notes.post(self.user2, 'posted note')
        last_note = SubtitleNote.objects.order_by('-id')[0]
        assert_equal(last_note.body, 'posted note')

    def check_format_created(self, note_created, now, correct_value):
        assert_equal(self.editor_notes.format_created(note_created, now),
                     correct_value)

    def test_format_created_very_recent(self):
        self.check_format_created(datetime(2014, 1, 1, 10, 30),
                                  datetime(2014, 1, 1, 12),
                                  '10:30 AM')

    def test_format_created_somewhat_recent(self):
        self.check_format_created(datetime(2014, 1, 1, 10, 30),
                                  datetime(2014, 1, 5, 12),
                                  'Wed, 10:30 AM')

    def test_format_created_old(self):
        self.check_format_created(datetime(2014, 1, 1, 10, 30),
                                  datetime(2014, 2, 1, 12),
                                  'Jan 1 2014, 10:30 AM')

class CompletePublishLogicTestBase(TestCase):
    @test_utils.mock_handler(subtitles_published)
    @test_utils.mock_handler(subtitles_completed)
    def setUp(self, subtitles_completed_handler, subtitles_published_handler):
        self.video = VideoFactory()
        self.language_code = 'en'
        self.language = self.video.subtitle_language(self.language_code,
                                                     create=True)
        self.subtitles_completed_handler = subtitles_completed_handler
        self.subtitles_published_handler = subtitles_published_handler

    def add_subtitles(self, user, action, **kwargs):
        version = pipeline.add_subtitles(self.video, self.language_code,
                                         SubtitleSetFactory(), author=user,
                                         action=action, **kwargs)
        # reload video/language to avoid issues with caching and calling
        # add_subtitles multiple times
        self.reload_models()
        return version

    def perform_action(self, user, action):
        workflow = self.video.get_workflow()
        workflow.perform_action(user, self.language_code, action)
        self.reload_models()

    def reload_models(self):
        self.video = test_utils.reload_obj(self.video)
        self.language = test_utils.reload_obj(self.language)

    def check_language_state(self, subtitles_complete, public_versions,
                             should_have_emitted_completed,
                             should_have_emitted_published):
        assert_equal(self.language.subtitles_complete, subtitles_complete)
        version_set = self.language.subtitleversion_set
        assert_equal([v.version_number for v in version_set.public()],
                     [v.version_number for v in public_versions])
        assert_equal(self.subtitles_completed_handler.called,
                     should_have_emitted_completed)
        assert_equal(self.subtitles_published_handler.called,
                     should_have_emitted_published)

class CompletePublishLogicTest(CompletePublishLogicTestBase):
    def test_complete_publish_logic(self):
        user = UserFactory()
        v1 = self.add_subtitles(user, 'save-draft')
        self.check_language_state(False, [v1], False, False)
        self.perform_action(user, 'publish')
        self.check_language_state(True, [v1], True, True)

    def test_complete_publish_logic_with_api_complete(self):
        user = UserFactory()
        v1 = self.add_subtitles(user, 'save-draft')
        self.check_language_state(False, [v1], False, False)
        v2 = self.add_subtitles(user, None, complete=True)
        self.check_language_state(True, [v1, v2], True, True)
