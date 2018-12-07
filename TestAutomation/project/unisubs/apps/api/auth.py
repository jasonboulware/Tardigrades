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

from rest_framework import authentication
from rest_framework import exceptions
from auth.models import AmaraApiKey
from auth.models import CustomUser as User

class TokenAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        username = request.META.get('HTTP_X_API_USERNAME')
        api_key = request.META.get('HTTP_X_API_KEY')
        if api_key is None:
            # fall back on the old header name
            api_key = request.META.get('HTTP_X_APIKEY')

        if not username:
            return None

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('No such user')

        if not user.is_active:
            raise exceptions.AuthenticationFailed('User disabled')

        if not AmaraApiKey.objects.filter(user=user, key=api_key).exists():
            raise exceptions.AuthenticationFailed('Invalid API Key')

        return (user, None)
