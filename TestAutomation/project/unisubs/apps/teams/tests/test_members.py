from __future__ import absolute_import

from django.test import TestCase
from nose.tools import *

from auth.models import CustomUser as User
from teams.models import Team, TeamMember
from teams.forms import CreateTeamForm
from utils.factories import *

class MembershipTests(TestCase):
    def test_new_team_has_owner(self):
        user = UserFactory()
        f = CreateTeamForm(
            user,
            dict(
            name="arthur",
            slug="arthur",
            workflow_type='O',
            membership_policy=1,
            video_policy=1,
        ))
        assert_true(f.is_valid(), f.errors.as_text())
        t = f.save(user)
        self.assertEqual(
            t.members.get(user=user).role,
            TeamMember.ROLE_OWNER,
            "New teams should always be created by their owner")
