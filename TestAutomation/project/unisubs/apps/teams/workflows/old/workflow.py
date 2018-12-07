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
TeamWorkflow classes for old-style teams
"""

from __future__ import absolute_import
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from teams import views
from teams.workflows import TeamWorkflow
from .subtitleworkflows import (TaskTeamSubtitlesWorkflow,
                                NonTaskTeamSubtitlesWorkflow)
from utils.behaviors import DONT_OVERRIDE
from videos.behaviors import VideoPageCustomization

class OldTeamWorkflow(TeamWorkflow):
    """Workflow for old-style teams

    We have tried to tackle the issue of team workflows in several ways.  The
    most infamous has to be the tasks sytem.  This class acts the glue between
    the new workflow components and the old systems.

    The plan is to migrate all our teams from OldTeamWorkflow to newer
    workflow styles.  At that point we can get rid of OldTeamWorkflow and also
    probably a bunch of other things like the tasks code, the Workflow table,
    several Team model fields, etc.
    """

    type_code = 'O'
    label = _('Old Style')
    api_slug = 'default'
    dashboard_view = staticmethod(views.old_dashboard)
    workflow_settings_view = staticmethod(views.old_team_settings_workflows)

    def activity_type_filter_options(self):
        """
        Get possible activity type filter values

        This is used on the activity page to populate the type dropdown.
        """
        options = super(OldTeamWorkflow, self).activity_type_filter_options()
        if self.team.is_tasks_team():
            options.extend([
                'version-approved',
                'version-rejected',
                'version-accepted',
                'version-declined',
            ])
        return options

    def video_page_customize(self, request, video):
        if not (self.team.is_tasks_team() and
                self.team.user_is_member(request.user)):
            return DONT_OVERRIDE
        sidebar = render_to_string('future/teams/tasks/video-sidebar.html', {
            'video': video,
            'team': self.team,
            'team_video': video.get_team_video(),
        }, request)
        return VideoPageCustomization(sidebar, None, self.team)

    def get_subtitle_workflow(self, team_video):
        """Get the SubtitleWorkflow for a video with this workflow.  """
        if self.team.is_tasks_team():
            return TaskTeamSubtitlesWorkflow(team_video)
        else:
            return NonTaskTeamSubtitlesWorkflow(team_video)

    def extra_pages(self, user):
        pages = [ ]
        if self.team.is_tasks_team():
            pages.append(self.team_page('tasks', _('Tasks'),
                                        'teams:team_tasks'))
        return pages

    def extra_settings_pages(self, user):
        return [
            self.team_page('languages', _('Languages'),
                            'teams:settings_languages')
        ]
