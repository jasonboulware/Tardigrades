# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
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
from django.http import HttpRequest
from nose.tools import *
from rest_framework.exceptions import AuthenticationFailed

from api.auth import TokenAuthentication
from utils.factories import *

class TestAPIAuth(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.api_key = self.user.get_api_key()
        self.auth = TokenAuthentication()

    def make_request(self, username, key):
        request = HttpRequest()
        request.META['HTTP_X_API_USERNAME'] = username
        request.META['HTTP_X_APIKEY'] = key
        return request

    def test_correct_token(self):
        request = self.make_request(self.user.username, self.api_key)
        assert_equal(self.auth.authenticate(request), (self.user, None))

    def test_incorrect_token(self):
        request = self.make_request(self.user.username, "foo")
        with assert_raises(AuthenticationFailed):
            self.auth.authenticate(request)

    def test_no_token(self):
        request = self.make_request(None, None)
        assert_equal(self.auth.authenticate(request), None)
