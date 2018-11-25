# Amara, universalsubtitles.org
#
# Copyright (C) 2016 Participatory Culture Foundation
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

import json
import logging

from requests.auth import HTTPBasicAuth
import requests

from notifications.models import TeamNotificationSettings, TeamNotification
from utils.taskqueue import job

logger = logging.getLogger(__name__)

class NotificationHandlerBase(object):
    """Handle notifications for a team.

    We use NotificationHandlerBase subclasses to send HTTP notifications to
    teams for certain events on amara.  The basic system is:

    - Create a NotificationHandlerBase subclass
        - Implement some of the on_* methods
        - Inside the method send an HTTP notification using
          send_notification().
        - Call the register() class method.
    - Create a TeamNotificationSettings instance using the django admin
       - Set the type to the same type passed to register()
       - Set the URL to the url we should post to.
    """


    def __init__(self, notification_settings):
        self.notification_settings = notification_settings
        self.team = notification_settings.team
        self.extra_teams = notification_settings.extra_teams.all()
        self.url = notification_settings.url
        self.headers = notification_settings.get_headers()
        self.auth_username = notification_settings.auth_username
        self.auth_password = notification_settings.auth_password

    def send_notification(self, data):
        """Send an HTTP notification

        This method queues up a HTTP POST request in the do_http_post() task.

        Args:
            data -- array of primative data to be encoded as json.
              do_http_post() will add the number field which corresponds to
              the TeamNotification.number
        """
        do_http_post.delay(self.team.id, self.url, data, self.headers,
                           self.auth_username, self.auth_password)

    def on_video_added(self, video, old_team):
        pass

    def on_video_removed(self, video, new_team):
        pass

    def on_video_moved_project(self, video, old_project, new_project):
        pass

    def on_video_url_made_primary(self, video, video_url, user):
        pass

    def on_subtitles_added(self, video, subtitle_version):
        pass

    def on_subtitles_imported(self, video, subtitle_versions):
        pass

    def on_subtitles_published(self, video, subtitle_language):
        pass

    def on_subtitles_deleted(self, video, subtitle_language):
        pass

    def on_user_added(self, user, team):
        pass

    def on_user_removed(self, user, team):
        pass

    def on_user_info_updated(self, user, team):
        pass

    def on_status_changed(self, video, user, team,
                          subtitles_language_code, status, extra):
        pass

@job
def do_http_post(team_id, url, data, headers, auth_username, auth_password):
    """Handle the HTTP POST for a notifaction

    This function also handles creating the TeamNotification object associated
    with the request.  It operates inside a task so that the network call
    doesn't block the web app process.

    Args:
        team_id: PK of the Team this notification is for
        url: URL to POST to
        data: array of primitive data to JSON-encode and send.  We will also
            add the number field, which will store the number of the
            associated TeamNotification.
        headers: extra headers to add to the request
        auth_username: authentication to send with the request
        auth_password: authentication to send with the request
    """
    if auth_username:
        auth = HTTPBasicAuth(auth_username, auth_password)
    else:
        auth = None
    notification = TeamNotification.create_new(team_id, url, data)
    post_data = data.copy()
    post_data['number'] = notification.number
    headers.update({
        'Content-type': 'application/json',
    })
    status_code = None
    error_message = None
    try:
        response = requests.post(url, data=json.dumps(post_data),
                                 headers=headers, auth=auth)
    except requests.ConnectionError:
        notification.error_message = "Connection error"
    except requests.Timeout:
        notification.error_message = "Request timeout"
    except requests.TooManyRedirects:
        notification.error_message = "Too many redirects"
    else:
        notification.response_status = response.status_code
        if response.status_code != 200:
            notification.error_message = 'Response status: {}'.format(
                response.status_code)
    notification.save()

# maps type strings to NotificationHandlerBase subclasses
_registry = {}

def register(type_slug, cls):
    """Register a notification handler class

    Args:
        type_slug: unique slug to identify the handler class
    """
    _registry[type_slug] = cls

def get_type_choices():
    return [(key, key) for key in sorted(_registry.keys())]

def call_event_handler(team, name, *args, **kwargs):
    """Call an event handler method

    This method looks up the NotificationHandlerBase subclass for a team,
    then calls on of it's event handler methods.
    """
    notification_setting = TeamNotificationSettings.lookup(team)
    if not notification_setting:
        return
    handler_class = _registry[notification_setting.type]
    handler = handler_class(notification_setting)
    method = getattr(handler, name)
    try:
        method(*args, **kwargs)
    except Exception:
        msg = "Error calling notification {} for {}".format(name, team)
        logger.error(msg, exc_info=True)

def call_event_handler_for_video(video, name, *args, **kwargs):
    team_video = video.get_team_video()
    if team_video:
        call_event_handler(team_video.team, name, *args, **kwargs)

def call_event_handler_for_team(team, name, *args, **kwargs):
    call_event_handler(team, name, *args, **kwargs)
