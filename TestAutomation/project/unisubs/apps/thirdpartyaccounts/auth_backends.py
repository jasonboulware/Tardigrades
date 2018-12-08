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

import requests
from django.conf import settings
from django.core.files.base import ContentFile

from auth.models import CustomUser as User
from thirdpartyaccounts.models import FacebookAccount, TwitterAccount

TWITTER_CONSUMER_KEY = getattr(settings, 'TWITTER_CONSUMER_KEY', '')
TWITTER_CONSUMER_SECRET = getattr(settings, 'TWITTER_CONSUMER_SECRET', '')
FACEBOOK_API_KEY = getattr(settings, 'FACEBOOK_API_KEY', '')
FACEBOOK_API_SECRET = getattr(settings, 'FACEBOOK_API_SECRET', '')

class TwitterAuthBackend(object):
    def authenticate(self, username):
        try:
            tpa = TwitterAccount.objects.get(username=username)
            user = User.objects.get(pk=tpa.user_id)
        except (TwitterAccount.DoesNotExist, User.DoesNotExist):
            return None
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except:
            return None

class FacebookAuthBackend(object):
    def authenticate(self, facebook=True, user=None):
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except:
            return None
