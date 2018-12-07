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

from django.test import TestCase
from nose.tools import *

from subtitles import workflows
from teams.models import TeamSubtitleNote, Task
from teams.workflows.notes import TeamEditorNotes
from teams.workflows.old.subtitleworkflows import TaskTeamEditorNotes
from utils import test_utils
from utils.factories import *

class TestTeamNotes(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.team = TeamFactory(admin=self.user)
        self.team_video = TeamVideoFactory(team=self.team)
        self.video = self.team_video.video

    def test_workflow_returns_team_editor_notes(self):
        workflow = workflows.get_workflow(self.video)
        editor_notes = workflow.get_editor_notes(self.user, 'en')
        assert_is_instance(editor_notes, TeamEditorNotes)

    def test_post_adds_team_subtitle_note(self):
        assert_equal(TeamSubtitleNote.objects.count(), 0)
        editor_notes = TeamEditorNotes(self.team, self.video, 'en')
        editor_notes.post(self.user, 'note')
        assert_equal(TeamSubtitleNote.objects.count(), 1)

class TestTaskTeamNotes(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.team = TeamFactory(admin=self.user,
                                workflow_enabled=True)
        WorkflowFactory(team=self.team)
        self.team_video = TeamVideoFactory(team=self.team)
        self.video = self.team_video.video

    def test_workflow_returns_task_team_editor_notes(self):
        workflow = workflows.get_workflow(self.video)
        editor_notes = workflow.get_editor_notes(self.user, 'en')
        assert_is_instance(editor_notes, TaskTeamEditorNotes)

    def check_send_messages(self, mock_send_messages, note, recipients):
        assert_equals(mock_send_messages.call_count, 1)
        args, kwargs = mock_send_messages.call_args
        assert_equals(args[0], note)
        assert_items_equal(args[1], recipients)
        assert_equals(len(args), 2)
        assert_equals(len(kwargs), 0)
        mock_send_messages.reset_mock()

    @test_utils.patch_for_test('teams.workflows.old.subtitleworkflows'
                               '.TaskTeamEditorNotes.send_messages')
    def test_emails(self, mock_send_messages):
        subtitler = UserFactory()
        reviewer = UserFactory()
        approver = UserFactory()
        task = TaskFactory.create_approve(self.team_video, 'en',
                                          subtitler=subtitler,
                                          reviewer=reviewer)
        task.assignee = approver
        task.approved = Task.APPROVED_IDS['Rejected']
        task.complete()
        # At this point: subtitler is assigned a completed task; reviewer is
        # assigned an incomplete task; and approver is assigned a task that
        # was complete but rejected.  When a user posts a note, all the other
        # users should be sent emails.
        editor_notes = TaskTeamEditorNotes(self.team_video, 'en')
        note = editor_notes.post(subtitler, 'note')
        self.check_send_messages(mock_send_messages, note, [reviewer, approver])

        note2 = editor_notes.post(reviewer, 'note')
        self.check_send_messages(mock_send_messages, note2, [subtitler, approver])

        note3 = editor_notes.post(approver, 'note')
        self.check_send_messages(mock_send_messages, note3, [subtitler, reviewer])
