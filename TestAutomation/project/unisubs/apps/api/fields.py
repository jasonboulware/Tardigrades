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
from rest_framework import serializers
from rest_framework.fields import CharField
from rest_framework.reverse import reverse
import pytz

from api import userlookup
from auth.models import CustomUser as User
from teams.models import Team
from utils.enum import EnumMember

class LanguageCodeField(CharField):
    def to_internal_value(self, language_code):
        return language_code.lower()

class UserField(serializers.CharField):
    """Serialize user data inside other serializers

    For example: SubtitleVersion.author and TeamMember.user
    """
    default_error_messages = {
        'invalid-user': "Invalid User"
    }

    def to_representation(self, user):
        if user:
            identifier = 'id$' + user.secure_id()
            return {
                'id': user.secure_id(),
                'username': user.username,
                'uri': reverse('api:users-detail', args=[identifier],
                               request=self.context['request']),
            }
        else:
            return None

    def to_internal_value(self, identifier):
        if identifier:
            try:
                return userlookup.lookup_user(identifier)
            except User.DoesNotExist:
                self.fail('invalid-user')
        else:
            return None

class TeamSlugField(CharField):
    default_error_messages = {
        'invalid-team': "Invalid Team"
    }

    def to_representation(self, team):
        if team:
            return team.slug
        else:
            return None

    def to_internal_value(self, slug):
        if slug:
            try:
                return Team.objects.get(slug=slug)
            except Team.DoesNotExist:
                self.fail('invalid-team')
        else:
            return None

class TimezoneAwareDateTimeField(serializers.DateTimeField):
    def __init__(self, *args, **kwargs):
        super(TimezoneAwareDateTimeField, self).__init__(*args, **kwargs)
        self.tz = timezone.get_default_timezone()

    def to_representation(self, value):
        return super(TimezoneAwareDateTimeField, self).to_representation(
            self.tz.localize(value).astimezone(pytz.utc))

class EnumField(CharField):
    def __init__(self, enum, *args, **kwargs):
        self.enum = enum
        super(EnumField, self).__init__(*args, **kwargs)

    def to_internal_value(self, slug):
        try:
            return self.enum.lookup_slug(slug)
        except KeyError:
            raise serializers.ValidationError("invalid slug: {}".format(slug))

    def to_representation(self, value):
        if isinstance(value, EnumMember):
            return value.slug
        else:
            return value
