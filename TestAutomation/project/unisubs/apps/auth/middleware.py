# Amara, universalsubtitles.org
#
# Copyright (C) 2014 Participatory Culture Foundation
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

import functools

from django.contrib import auth
from django.contrib.auth.models import AnonymousUser
from django.utils.functional import SimpleLazyObject

from utils import requestdata

def get_user(request):
    user = auth.get_user(request)
    return user if user.is_active else AnonymousUser()

from auth.models import CustomUser as User

class AmaraAuthenticationMiddleware(object):
    def use_cached_user(self, request):
        try:
            user_id = request.session[auth.SESSION_KEY]
        except KeyError:
            request.user = auth.get_user(request)
            request.session[auth.SESSION_KEY] = request.user.id
        else:
            request.user = self._get_cached_user(user_id)

    def _get_cached_user(self, user_id):
        if user_id is None:
            return AnonymousUser()
        try:
            return User.cache.get_instance(user_id)
        except User.DoesNotExist:
            return AnonymousUser()

    def process_request(self, request):
        # FIXME: this should probably be the default behavior, but that would
        # prevent the user from being modified during the request.  We should
        # take a survey of our view functions and see which ones need to do
        # that.
        request.use_cached_user = functools.partial(self.use_cached_user,
                                                    request)
        request.user = get_user(request)
        requestdata.log('user', request.user.username)
