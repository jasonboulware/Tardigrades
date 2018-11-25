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

"""
Team workflow startup code
"""

from utils.behaviors import DONT_OVERRIDE
import subtitles.workflows
import videos.behaviors
from teams.models import Team
from teams.workflows import TeamWorkflow
from teams.workflows.old import OldTeamWorkflow
from teams.workflows.simple import SimpleTeamWorkflow

@subtitles.workflows.get_workflow.override
def get_workflow_override(video):
    team_video = video.get_team_video()
    if team_video is None:
        return DONT_OVERRIDE
    if video.cache.cache_pattern is not None:
        # If we have have a video from cache also get the team from cache
        team = Team.cache.get_instance(team_video.team_id,
                                       video.cache.cache_pattern)
        team_video.team = team
        team_workflow = TeamWorkflow.get_workflow(team)
    else:
        team_workflow = TeamWorkflow.get_workflow(team_video.team)
    return team_workflow.get_subtitle_workflow(video.get_team_video())

@videos.behaviors.video_page_customize.override
def video_page_customize(request, video):
    team_video = video.get_team_video()
    if team_video:
        team_workflow = TeamWorkflow.get_workflow(team_video.team)
        return team_workflow.video_page_customize(request, video)
    else:
        return DONT_OVERRIDE

@videos.behaviors.subtitles_page_customize.override
def subtitles_page_customize(request, video, subtitle_language):
    team_video = video.get_team_video()
    if team_video:
        team_workflow = TeamWorkflow.get_workflow(team_video.team)
        return team_workflow.subtitles_page_customize(request, video,
                                                      subtitle_language)
    else:
        return DONT_OVERRIDE

# register default team workflows
OldTeamWorkflow.register('O', 'default')
SimpleTeamWorkflow.register('S', 'simple')
