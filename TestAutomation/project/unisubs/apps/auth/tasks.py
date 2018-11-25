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

import logging

from django.conf import settings

from auth.models import LoginToken
from utils import send_templated_email
from utils.taskqueue import job

logger = logging.getLogger(__name__)

BLOCKED_USER_NOTIFICATION_TEMPLATE = "auth/blocked_user_notification.html"

@job
def expire_login_tokens():
    LoginToken.objects.get_expired().delete()

@job
def notify_blocked_user(user):
    if hasattr(settings, 'BLOCKED_USER_NOTIFICATION_ADDRESS'):
        subject = "Attacking user detected and de-activated"
        logger.error("A user was deactivated because he was sending too many messages: {}".format(user.username))
        return send_templated_email(settings.BLOCKED_USER_NOTIFICATION_ADDRESS, subject, \
                                    BLOCKED_USER_NOTIFICATION_TEMPLATE, {'username': user.username}, \
                                    from_email=None, ct="html", fail_silently=not settings.DEBUG)
