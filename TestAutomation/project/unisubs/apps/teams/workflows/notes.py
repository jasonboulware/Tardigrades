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

"""
EditorNote subclass for teams
"""

from django.utils.translation import ugettext as _

from subtitles.workflows import EditorNotes
from teams.models import TeamSubtitleNote

class TeamEditorNotes(EditorNotes):
    def __init__(self, team, video, language_code):
        self.team = team
        self.video = video
        self.language_code = language_code
        self.heading = _('Team Notes')
        self.notes = self.fetch_notes()

    def fetch_notes(self):
        return list(TeamSubtitleNote.objects
                    .filter(video=self.video, team=self.team,
                            language_code=self.language_code)
                    .order_by('created')
                    .select_related('user'))

    def post(self, user, body):
        return TeamSubtitleNote.objects.create(
            team=self.team, video=self.video,
            language_code=self.language_code,
            user=user, body=body)

