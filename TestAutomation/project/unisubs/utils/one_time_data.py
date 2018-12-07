# Amara, universalsubtitles.org
#
# Copyright (C) 2017 Participatory Culture Foundation
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

import uuid
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse

def _mk_key(token):
    return "one-time-data-" + token

def set_one_time_data(data):
    token = str(uuid.uuid4())
    key = _mk_key(token)
    cache.set(key, data, 60)
    return '{}://{}{}'.format(settings.DEFAULT_PROTOCOL,
                                 settings.HOSTNAME,
                                 reverse("one_time_url", kwargs={"token": token}))

def get_one_time_data(token):
    key = _mk_key(token)
    data = cache.get(key)
    # It seems like Brightcove wants to hit it twice
    # cache.delete(key)
    return data
