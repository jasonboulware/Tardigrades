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

from utils import send_templated_email
from utils.taskqueue import job

logger = logging.getLogger(__name__)

@job
def send_templated_email_async(to, subject, body_template, body_dict,
                               from_email=None, ct="html", fail_silently=False,
                               check_user_preference=True):
    return send_templated_email(
        to,subject, body_template, body_dict, from_email=None, ct="html",
        fail_silently=False, check_user_preference=check_user_preference)

@job
def test():
    logger.info('in test task')
