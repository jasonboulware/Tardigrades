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

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.reverse import reverse
import pytz

from utils.factories import *

def format_datetime_field(datetime):
    if datetime is None:
        return None
    tz = timezone.get_default_timezone()
    isoformat = tz.localize(datetime).astimezone(pytz.utc).isoformat()
    return isoformat.replace('+00:00', 'Z')

def format_datetime_field_as_date(datetime):
    if datetime is None:
        return None
    return datetime.date().isoformat()

def user_field_data(user):
    if user:
        return {
            'username': user.username,
            'id': user.secure_id(),
            'uri': reverse('api:users-detail', kwargs={
                'identifier': 'id$' + user.secure_id(),
            }, request=APIRequestFactory().get('/')),
        }
    else:
        return None

class EndpointClient(object):
    """
    Like django rest framework's API client, but for a single endpoint
    """
    def __init__(self, url):
        self.url = url
        self.user = UserFactory(is_superuser=True)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def get(self, expected_response=status.HTTP_200_OK):
        return self.check_response(
            expected_response, self.client.get(self.url))

    def post(self, data, expected_response=status.HTTP_201_CREATED):
        return self.check_response(
            expected_response,
            self.client.post(self.url, data, format='json'))

    def put(self, data, expected_response=status.HTTP_200_OK):
        return self.check_response(
            expected_response,
            self.client.put(self.url, data, format='json'))

    def check_response(self, code, response):
        assert response.status_code == code, response.content
        return response
