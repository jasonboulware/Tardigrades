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

"""app.videos.permissions -- Video permissions checks."""

import teams.permissions as teams_permissions

def can_user_edit_video_urls(video, user):
    """Check if a user has permission to add a URL to a video."""
    team_video = video.get_team_video()
    if not team_video:
        # for non-team videos, the allow_video_urls_edit attribute
        # controls access.  This should be True for all videos
        return video.allow_video_urls_edit
    else:
        # for team videos, check if the user can edit the video
        return teams_permissions.can_edit_video(team_video, user)

def can_user_resync(video, user):
    """Check if a user has permission to resync the video's subtitles."""
    if user.is_staff:
        return True
    team_video = video.get_team_video()
    if team_video:
        # for team videos, check if the user can resync the video
        return teams_permissions.can_resync(team_video.team, user)
    # For now this is limited to team videos
    # as we'd need to know if a user actually own the youtube channel
    return False

def can_user_resync_own_video(video, user):
    """Check if a user has permission to resync the video's subtitles."""
    if user.is_staff or (video.user == user):
        return True
    return False

def can_view_activity(video, user):
    return video.get_workflow().user_can_view_video(user)
