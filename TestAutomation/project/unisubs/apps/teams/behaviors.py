# Amara, universalsubtitles.org
#
# Copyright (C) 2015 Participatory Culture Foundation
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
from utils.behaviors import behavior

@behavior
def get_main_project(team):
    """Get the main project for a team

    This is the project that will be selected by default on the videos page.

    The default is to return None, which causes "All Projects".  This can be
    overrided for specific teams though (e.g. TED).
    """
    return None

@behavior
def get_team_join_mode(team, user):
    """
    Get the appropriate join mode for the team - mainly used for the non-member landing page
    """
    if not user.is_authenticated():
        return 'login'
    else:
        return None

@behavior
def get_team_login_url(team):
    """
    Get the appropriate login url for the team
    """
    return reverse('auth:login')
