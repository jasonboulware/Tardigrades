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
from django.db import models

from auth.models import CustomUser as User
from subtitles.models import SubtitleLanguage, SubtitleVersion


class SubtitlingSession(models.Model):
    language = models.ForeignKey(
        SubtitleLanguage, related_name='subtitling_sessions')
    # fix me: write this migration to base_language_code
    base_language = models.ForeignKey(
        SubtitleLanguage, null=True, related_name='based_subtitling_sessions')
    parent_version = models.ForeignKey(SubtitleVersion, null=True)
    user = models.ForeignKey(User, null=True)
    browser_id = models.CharField(max_length=128, blank=True)
    datetime_started = models.DateTimeField(auto_now_add=True)

    @property
    def video(self):
        return self.language.video

    def matches_request(self, request):
        if request.user.is_authenticated() and self.user:
            return self.user == request.user
