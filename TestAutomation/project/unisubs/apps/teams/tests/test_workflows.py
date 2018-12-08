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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

from django.test import TestCase

from subtitles import pipeline
from subtitles.tests.test_workflows import CompletePublishLogicTestBase
from utils.factories import *
from utils.test_utils import *

class TeamCompletePublishLogicTest(CompletePublishLogicTestBase):
    def setUp(self):
        super(TeamCompletePublishLogicTest, self).setUp()
        self.team = TeamFactory(workflow_type='O')
        TeamVideoFactory(video=self.video, team=self.team)

    def test_non_tasks(self):
        user = UserFactory(team=self.team)
        v1 = self.add_subtitles(user, 'save-draft')
        self.check_language_state(False, [v1], False, False)
        self.perform_action(user, 'publish')
        self.check_language_state(True, [v1], True, True)

    def test_simple(self):
        self.team.workflow_type = 'S'
        self.team.save()
        user = UserFactory(team=self.team)
        v1 = self.add_subtitles(user, 'save-draft')
        self.check_language_state(False, [v1], False, False)
        self.perform_action(user, 'publish')
        self.check_language_state(True, [v1], True, True)

    def assign_current_task(self, user):
        t = self.team.task_set.incomplete().get()
        t.assignee = user
        t.save()

    def test_tasks(self):
        WorkflowFactory(team=self.team)
        self.team.workflow_enabled = True
        self.team.save()
        subtitler = UserFactory(team=self.team)
        reviewer = UserFactory(team=self.team)
        approver = UserFactory(team=self.team)
        TaskFactory(team=self.team,
                    team_video=self.video.get_team_video(),
                    language=self.language_code,
                    assignee=subtitler, type=10)

        # move the subtitles through the tasks system, the logic around
        # subtitles_complete doesn't make a whole lot of sense, but I don't
        # really want to risk changing it

        v1 = self.add_subtitles(subtitler, 'save-draft')
        self.check_language_state(False, [], False, False)

        v2 = self.add_subtitles(subtitler, 'complete')
        self.check_language_state(True, [], False, False)

        self.assign_current_task(reviewer)
        v3 = self.add_subtitles(reviewer, 'approve')
        self.check_language_state(True, [], False, False)

        self.assign_current_task(approver)
        self.perform_action(approver, 'send-back')
        self.check_language_state(False, [], False, False)

        self.assign_current_task(reviewer)
        v4 = self.add_subtitles(reviewer, 'approve')
        self.check_language_state(True, [], False, False)

        self.assign_current_task(approver)
        self.perform_action(approver, 'approve')
        self.check_language_state(True, [v4], True, True)
