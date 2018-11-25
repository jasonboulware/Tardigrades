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

from __future__ import absolute_import

from datetime import datetime

from django.test import TestCase
import mock
from nose.tools import *

from caching.tests.utils import assert_invalidates_model_cache
from teams.models import Project, TeamVideoMigration
from utils import test_utils
from utils.factories import *

class TeamVideoCacheTest(TestCase):
    def setUp(self):
        self.video = VideoFactory()

    def test_add_to_team(self):
        with assert_invalidates_model_cache(self.video):
            TeamVideoFactory(video=self.video)

    def test_move_team(self):
        team_video = TeamVideoFactory(video=self.video)
        other_team = TeamFactory()
        with assert_invalidates_model_cache(self.video):
            team_video.move_to(other_team)

    def test_remove_from_team(self):
        team_video = TeamVideoFactory(video=self.video)
        with assert_invalidates_model_cache(self.video):
            team_video.delete()

class TeamMoveTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.team = TeamFactory()
        self.project = Project.objects.create(team=self.team, name='project1')
        self.team2 = TeamFactory()
        self.project2 = Project.objects.create(team=self.team2,
                                               name='project2')
        self.video = VideoFactory()
        self.team_video = TeamVideoFactory(team=self.team, video=self.video)

    def check_migration(self, migration, datetime, from_team, to_team,
                        to_project):
        self.assertEquals(migration.datetime, datetime)
        self.assertEquals(migration.from_team, from_team)
        self.assertEquals(migration.to_team, to_team)
        self.assertEquals(migration.to_project, to_project)

    @test_utils.patch_for_test('teams.models.TeamVideoMigration.now')
    def test_move(self, mock_now):
        mock_now.return_value = datetime(2013, 01, 01)
        self.team_video.move_to(self.team2, self.project2)
        mock_now.return_value = datetime(2013, 01, 02)
        self.team_video.move_to(self.team, project=self.project)
        mock_now.return_value = datetime(2013, 01, 03)
        self.team_video.move_to(self.team2, project=self.project2)

        migrations = list(TeamVideoMigration.objects.all())
        self.assertEquals(len(migrations), 3)
        self.check_migration(migrations[0], datetime(2013, 01, 01), self.team,
                             self.team2, self.project2)
        self.check_migration(migrations[1], datetime(2013, 01, 02),
                             self.team2, self.team, self.project)
        self.check_migration(migrations[2], datetime(2013, 01, 03),
                             self.team, self.team2, self.project2)

class AddPublicVideoTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.team = TeamFactory(admin=self.user)
        self.video = VideoFactory()

    def test_add(self):
        self.team.add_existing_video(self.video, self.user)
        team_video = self.video.get_team_video()
        assert_equal(team_video.team, self.team)
        assert_equal(team_video.added_by, self.user)
        assert_equal(team_video.project, self.team.default_project)

    def test_add_to_project(self):
        project = ProjectFactory(team=self.team)
        self.team.add_existing_video(self.video, self.user, project)
        assert_equal(self.video.get_team_video().project, project)

    def test_prevent_duplicate_public_videos_flag(self):
        self.team.prevent_duplicate_public_videos = True
        self.team.save()
        self.team.add_existing_video(self.video, self.user)
        assert_equal(self.video.get_team_video().team, self.team)
