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
from django.urls import reverse
from django.test import TestCase

from auth.models import CustomUser as User
from utils.factories import *

class TestViews(TestCase):
    def setUp(self):
        self.auth = dict(username='admin', password='admin')
        self.user = UserFactory(**self.auth)

    def _simple_test(self, url_name, args=None, kwargs=None, status=200, data={}):
        response = self.client.get(reverse(url_name, args=args, kwargs=kwargs), data)
        self.assertEqual(response.status_code, status)
        return response

    def _login(self):
        self.client.login(**self.auth)

    def test_edit_account(self):
        self._simple_test('profiles:account', status=302)

        self._login()
        self._simple_test('profiles:account')

        data = {
            'editaccount': True,
            'account-username': 'new_username_for_admin',
            'account-email': self.user.email,
            'account-current_password': 'admin',
            'userlanguage_set-TOTAL_FORMS': '0',
            'userlanguage_set-INITIAL_FORMS': '0',
            'userlanguage_set-MAX_NUM_FORMS': ''
        }
        response = self.client.post(reverse('profiles:account'), data=data)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(pk=self.user.pk)
        self.assertEqual(user.username, data['account-username'])

        other_user = UserFactory()
        data['account-username'] = other_user.username
        response = self.client.post(reverse('profiles:account'), data=data)
        self.assertEqual(response.status_code, 200)

    def test_edit_profile(self):
        self._simple_test('profiles:edit', status=302)

        self._login()
        self._simple_test('profiles:edit')

        data = {
            'username': 'new_username_for_admin',
            'email': 'someone@example.com',
            'userlanguage_set-TOTAL_FORMS': '0',
            'userlanguage_set-INITIAL_FORMS': '0',
            'userlanguage_set-MAX_NUM_FORMS': ''
        }
        response = self.client.post(reverse('profiles:edit'), data=data)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(pk=self.user.pk)
        # the view sets this from the user model, make sure are not
        # able to change this
        self.assertNotEqual(user.username, data['username'])
        self.assertNotEqual(user.email, data['email'])
        other_user = UserFactory()
        data['username'] = other_user.username
        response = self.client.post(reverse('profiles:edit'), data=data)
        self.assertRedirects(response, reverse('profiles:edit'))
