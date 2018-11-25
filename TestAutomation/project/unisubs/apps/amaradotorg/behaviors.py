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

import logging

from django.utils.translation import gettext as _

from teams.behaviors import get_main_project
from teams.models import Project
from utils.behaviors import DONT_OVERRIDE
from utils.text import fmt

logger = logging.getLogger(__name__)

def is_ted_team(team):
    return team.slug.startswith('ted')

@get_main_project.override
def amara_get_main_project(team):
    if is_ted_team(team):
        try:
            return team.project_set.get(slug='tedtalks')
        except Project.DoesNotExist:
            pass
    return DONT_OVERRIDE
