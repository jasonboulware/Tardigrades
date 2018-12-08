# Amara, universalsubtitles.org
#
# Copyright (C) 2018 Participatory Culture Foundation
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
jobprogress -- Manage progress of long-running jobs

Use this module to help track the progress of long-running jobs that run in
the worker process.

A typical use would be something like this:

 - The view code calls jobprogress.get() to check if there's any current job
   underway, and if so what's the progress for that job.
 - If the user initiates the job, the view code calls jobprogress.start(),
   before scheduling the background task.  If start() returns False, then that
   means there's already another background task running and we should skip
   scheduling another one.
 - Inside the task, as the job progresses, it calls jobprogress.update().
 - Once the job is complete, it calls jobprogress.complete()
"""

from collections import namedtuple
import json

from django_redis import get_redis_connection

TIMEOUT = 300

ProgressStatus = namedtuple('ProgressStatus', 'current total')

def start(key):
    """
    Call this before starting to run the report

    Returns:
        True if we should start the report job
        False if a job is already running and we shouldn't start a new one
    """
    r = get_redis_connection('storage')
    pipe = r.pipeline()
    pipe.setnx(_make_key(key), _make_value(0, 0))
    r.expire(_make_key(key), TIMEOUT)
    rvs = pipe.execute()
    return bool(rvs[0])

def update(key, current, total):
    """
    Update the progress for a current job
    """
    r = get_redis_connection('storage')
    r.setex(_make_key(key), TIMEOUT, _make_value(current, total))

def complete(key):
    """
    Indicate that the report job is complete
    """
    r = get_redis_connection('storage')
    r.delete(_make_key(key))

def get(key):
    """
    Get the progress of the current report job

    Returns:
        ProgressStatus object or None if no job is running.
    """

    r = get_redis_connection('storage')
    return _parse_value(r.get(_make_key(key)))

def _make_key(key):
    return 'progress-{}'.format(key)

def _make_value(current, total):
    return json.dumps((current, total))

def _parse_value(value):
    if value is None:
        return None
    else:
        return ProgressStatus(*json.loads(value))
