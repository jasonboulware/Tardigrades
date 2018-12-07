# Amara, universalsubtitles.org
#
# Copyright (C) 2015 Participatory Culture Foundation
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

from django.test import TestCase
from nose.tools import *
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
import mock

from messages.models import Message
from utils.test_utils.monkeypatch import patch_for_test
from utils.factories import *

class ActivityTestCase(TestCase):
    def setUp(self):
        self.user = UserFactory(username='test-user')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.team = TeamFactory(admin=self.user)
        self.team_members = [
            TeamMemberFactory(team=self.team).user
            for i in xrange(3)
        ]
        self.url = reverse('api:messages')

    def check_messages(self, recipients, correct_subject, correct_content):
        all_messages = list(Message.objects.all())
        assert_items_equal([m.user for m in all_messages], recipients)
        for m in all_messages:
            assert_equal(m.subject, correct_subject)
            assert_equal(m.content, correct_content)
            assert_equal(m.author, self.user)

    def check_validation_error(self, data):
        response = self.client.post(self.url, data)
        assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_user_message(self):
        response = self.client.post(self.url, {
            'user': self.team_members[0].username,
            'subject': 'test-subject',
            'content': 'test-content',
        })
        assert_equal(response.status_code, status.HTTP_201_CREATED)
        self.check_messages([self.team_members[0]], 'test-subject',
                            'test-content')

    def test_send_team_message(self):
        response = self.client.post(self.url, {
            'team': self.team.slug,
            'subject': 'test-subject',
            'content': 'test-content',
        })
        assert_equal(response.status_code, status.HTTP_201_CREATED)
        # note that self.user is also a team member, but we shouldn't send a
        # message to that user since they were the one who created the
        # message.
        self.check_messages(self.team_members, 'test-subject', 'test-content')

    def test_invalid_user(self):
        self.check_validation_error({
            'user': 'invalid-user',
            'subject': 'test-subject',
            'content': 'test-content',
        })

    def test_invalid_team(self):
        self.check_validation_error({
            'team': 'invalid-team',
            'subject': 'test-subject',
            'content': 'test-content',
        })

    def test_user_or_team_required(self):
        self.check_validation_error({
            'subject': 'test-subject',
            'content': 'test-content',
        })

    def test_check_can_send_messages(self):
        self.user.can_send_messages = False
        self.user.save()
        response = self.client.post(self.url, {
            'team': self.team.slug,
            'subject': 'test-subject',
            'content': 'test-content',
        })
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)


    @patch_for_test('teams.permissions.can_message_all_members')
    def test_check_can_message_team_permission(self,
                                               mock_can_message_all_members):
        mock_can_message_all_members.return_value = False
        response = self.client.post(self.url, {
            'team': self.team.slug,
            'subject': 'test-subject',
            'content': 'test-content',
        })
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)
        assert_equal(mock_can_message_all_members.call_args,
                     mock.call(self.team, self.user))
