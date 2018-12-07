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

from django.test import TestCase

from caching.tests.utils import assert_invalidates_model_cache
from teams.models import MembershipNarrowing
from utils.factories import *

class TeamCacheInvalidationTest(TestCase):
    def setUp(self):
        self.team = TeamFactory()

    def test_change_team(self):
        with assert_invalidates_model_cache(self.team):
            self.team.save()

    def test_change_team_member(self):
        with assert_invalidates_model_cache(self.team):
            member = TeamMemberFactory(team=self.team)
        with assert_invalidates_model_cache(self.team):
            member.save()
        with assert_invalidates_model_cache(self.team):
            member.delete()

    def test_change_membership_narrowing(self):
        admin = TeamMemberFactory(team=self.team)
        member = TeamMemberFactory(team=self.team)
        with assert_invalidates_model_cache(self.team):
            narrowing = MembershipNarrowing.objects.create(
                member=member, language='en', added_by=admin)
        with assert_invalidates_model_cache(self.team):
            narrowing.save()
        with assert_invalidates_model_cache(self.team):
            narrowing.delete()
