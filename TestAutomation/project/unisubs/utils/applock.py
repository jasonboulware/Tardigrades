# -*- coding: utf-8 -*-
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

"""utils.applock -- manage application-level locks

This module handle creating app-wide locks.  We currently implement them using
the MySQL GET_LOCK() statement.
"""

import contextlib
import time

from django.db import connection

class LockBusy(StandardError):
    pass

def _lock_name(name):
    return "amara.%s" % name

def acquire_lock(cursor, name, timeout=None):
    start_time = time.time()
    while True:
        cursor.execute("SELECT GET_LOCK(%s, 0)", (_lock_name(name),))
        rv = cursor.fetchone()[0]
        if rv != 0:
            break
        if timeout is None or time.time() >= start_time + timeout:
            raise LockBusy()
        time.sleep(0.1)

def release_lock(cursor, name):
    cursor.execute("SELECT RELEASE_LOCK(%s)", (_lock_name(name),))

@contextlib.contextmanager
def lock(name, timeout=None):
    """Context manager that manages an app-wide lock."""
    cursor = connection.cursor()
    acquire_lock(cursor, name, timeout=timeout)
    yield
    release_lock(cursor, name)
