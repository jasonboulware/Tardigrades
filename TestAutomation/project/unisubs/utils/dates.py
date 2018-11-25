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

import pytz

from datetime import datetime

from django.conf import settings

local_tz = pytz.timezone(settings.TIME_ZONE)

def now():
    """Get the current datetime.

    This function is better to use than datetime.now() because it has support
    for mocking it up in unittests.
    """
    return datetime.now()

def utcnow():
    return now().replace(tzinfo=local_tz).astimezone(pytz.utc)

def this_month_start():
    return month_start(now())

def month_start(dt):
    """Get the first day of a month

    dt can be either datetime or date object, it will be converted to a date.
    """
    if isinstance(dt, datetime):
        dt = dt.date()
    return dt.replace(day=1)

def inc_month(dt):
    if dt.month < 12:
        return dt.replace(month=dt.month+1)
    else:
        return dt.replace(year=dt.year+1, month=1)

def dec_month(dt):
    if dt.month > 1:
        return dt.replace(month=dt.month-1)
    else:
        return dt.replace(year=dt.year-1, month=12)
