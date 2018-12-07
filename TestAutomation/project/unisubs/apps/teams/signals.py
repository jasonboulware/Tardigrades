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

from django import dispatch

logger = logging.getLogger(__name__)

member_leave = dispatch.Signal()
member_remove = dispatch.Signal()
video_removed_from_team = dispatch.Signal(providing_args=["team", "user"])
video_moved_from_team_to_team = dispatch.Signal(
        providing_args=["destination_team", "old_team", "video"])
video_moved_from_project_to_project = dispatch.Signal(
        providing_args=["old_project", "new_project", "video"])
team_settings_changed = dispatch.Signal(
        providing_args=["user", "changed_settings", "old_settings"])
# Called when we're creating forms for the team manage videos page.  The
# sender will be the team.  Append new forms to the form_list parameter
build_video_management_forms = dispatch.Signal(providing_args=['form_list'])

# Notification-related signals

# There is quite a bit of indirection here, but the goal is to make
# dispatching these events as simple as possible, since it might occur
# in multiple places.
#
# 1) Client codes dispatches a signal listed in this module:
#    ex: signals.api_on_subtitles_edited.send(subtitle_version)
# 2) The signal calls that handler, which chooses the right event name
#    for the signal and calls the matching sub method (for videos, languages, etc)
# 3) The submethod finds all teams that should be notified (since a video)
#    can belong to more than on team). For each team:
# 3a) Puts the right task on queue, if the teams has a TeamNotificationsSettings
# 3b) The taks querys the TeamNotificationSettings models to fire notifications
# 3c) The TNS checks if there is available data (e.g. which url to post to)
# 3d) Instantiates the right notification class (since specific partners must
#     have their notification data massaged to their needs - e.g. changing the video
#     ids to their own, or the api links to their own endpoints)
# 3e) The notification class fires the notification

def _teams_to_notify(video):
    """
    Returns a list of teams to be notified of events releated to this
    video.
    """
    from teams.models import Team
    from django.db.models import Q
    return list(Team.objects.filter(
        Q(notification_settings__isnull=False) |
        Q(partner__notification_settings__isnull=False),
        teamvideo__video=video))
    
def _execute_video_task(video, event_name):
    from teams import tasks as team_tasks
    from teams.models import  TeamVideo
    from django.db.models import Q
    logger.info("notification: %s (video: %s)", event_name, video)
    tvs =  list(TeamVideo.objects.filter(
        Q(team__notification_settings__isnull=False) |
        Q(team__partner__notification_settings__isnull=False),
        video=video))
    for tv in tvs:
        team_tasks.api_notify_on_video_activity.delay(
            tv.team.pk,
            event_name,
            tv.video.video_id)
    
def _execute_language_task(language, event_name):
    from teams import tasks as team_tasks
    logger.info("notification: %s (language: %s)", event_name, language)
    video = language.video
    teams = _teams_to_notify(video)
    for team in teams:
        team_tasks.api_notify_on_language_activity.delay(
            team.pk,
            event_name,
            language.pk)
 
def _execute_version_task(version, event_name):
    from teams import tasks as team_tasks
    logger.info("notification: %s (version: %s)", event_name, version)
    video = version.video
    teams = _teams_to_notify(video)
    for team in teams:
        team_tasks.api_notify_on_subtitles_activity.delay(
            team.pk,
            event_name,
            version.pk)

def _execute_application_task(application, event_name):
    from teams.tasks import api_notify_on_application_activity
    api_notify_on_application_activity.delay(
        application.team.pk,
        event_name,
        application.pk,
    )
    
def api_on_subtitles_edited(sender, **kwargs):
    from teams.models import TeamNotificationSetting
    _execute_version_task(sender, TeamNotificationSetting.EVENT_SUBTITLE_NEW)
   

def api_on_subtitles_approved(sender, **kwargs):
    from teams.models import TeamNotificationSetting
    _execute_version_task(sender, TeamNotificationSetting.EVENT_SUBTITLE_APPROVED)

def api_on_subtitles_rejected(sender, **kwargs):
    from teams.models import TeamNotificationSetting
    _execute_version_task(sender, TeamNotificationSetting.EVENT_SUBTITLE_REJECTED)
   

def api_on_language_edited(sender, **kwargs):
    from teams.models import TeamNotificationSetting
    _execute_language_task(sender, TeamNotificationSetting.EVENT_LANGUAGE_EDITED)
    

def api_on_language_new(sender, **kwargs):
    from teams.models import TeamNotificationSetting
    _execute_language_task(sender, TeamNotificationSetting.EVENT_LANGUAGE_NEW)


def api_on_video_edited(sender, **kwargs):
    from teams.models import TeamNotificationSetting
    _execute_video_task(sender, TeamNotificationSetting.EVENT_VIDEO_EDITED)
    

def api_on_teamvideo_new(sender, **kwargs):
    from teams import tasks as team_tasks
    from teams.models import TeamNotificationSetting
    
    return team_tasks.api_notify_on_video_activity.delay(
            sender.team.pk,
            TeamNotificationSetting.EVENT_VIDEO_NEW,
            sender.video.video_id )

def api_on_application_new(sender, **kwargs):
    from teams.models import TeamNotificationSetting
    return _execute_application_task(sender, TeamNotificationSetting.EVENT_APPLICATION_NEW)

def api_on_language_deleted(sender, **kwargs):
    from teams.models import TeamNotificationSetting
    return _execute_language_task(
        sender, TeamNotificationSetting.EVENT_LANGUAGE_DELETED)

#: Actual available signals
api_subtitles_edited = dispatch.Signal(providing_args=["version"])
api_subtitles_approved = dispatch.Signal(providing_args=["version"])
api_subtitles_rejected = dispatch.Signal(providing_args=["version"])
api_language_edited = dispatch.Signal(providing_args=["language"])
api_language_deleted = dispatch.Signal()
api_video_edited = dispatch.Signal(providing_args=["video"])
api_language_new = dispatch.Signal(providing_args=["language"])
api_teamvideo_new = dispatch.Signal(providing_args=["video"])
api_application_new = dispatch.Signal(providing_args=["application"])
# connect handlers
api_subtitles_edited.connect(api_on_subtitles_edited)
api_subtitles_approved.connect(api_on_subtitles_approved)
api_subtitles_rejected.connect(api_on_subtitles_rejected)
api_language_edited.connect(api_on_language_edited)
api_language_new.connect(api_on_language_new)
api_language_deleted.connect(api_on_language_deleted)
api_video_edited.connect(api_on_video_edited)
api_teamvideo_new.connect(api_on_teamvideo_new)
api_application_new.connect(api_on_application_new)
