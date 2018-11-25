# Amara, universalsubtitles.org
#
# Copyright (C) 2014 Participatory Culture Foundation
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

import importlib
import os
import subprocess

from django.conf import settings

try:
    import commit
except ImportError:
    commit = None

def s3_subdirectory():
    """Get the subdirectory to store media in for S3

    We want to have the subdirectory change each time we deploy.  This does a
    couple things:
        - We can upload the media for our next deploy without messing with the
        media for our current one.
        - We can set the HTTP cache headers so that servers cache the content
        forever without worrying about stale media files.
    """
    if commit is None:
        raise AssertionError("No commit module")
    return commit.LAST_COMMIT_GUID

def static_url():
    """Get the base URL for static media

    This is a function rather than just a value in the settings because it's a
    bit complicated to calculate.

    The simple case is when STATIC_MEDIA_USES_S3 is False.  Then we simple
    return the "/media/".  If STATIC_MEDIA_USES_S3 is True, then we return an
    URL pointing to where we upload media to on S3, which includes the git
    checksum as a way to keep the URLs unique between different deployments.
    """
    if not settings.STATIC_MEDIA_USES_S3:
        return "/media/"
    else:
        return "%s%s/" % (settings.STATIC_MEDIA_S3_URL_BASE,
                          s3_subdirectory())

def run_command(commandline, stdin=None):
    """Run a command and return the results.

    An exception will be raised if the command doesn't return 0 or prints to
    stderr.
    """
    p = subprocess.Popen(commandline, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout, stderr = p.communicate(stdin)
    if stderr:
        raise ValueError("Got error from %s: %s" % (commandline, stderr))
    elif p.returncode != 0:
        raise ValueError("Got error code from %s: %s" % (commandline,
                                                         p.returncode))
    else:
        return stdout

def app_static_media_dirs():
    static_media_dirs = []
    for app in settings.INSTALLED_APPS:
        module = importlib.import_module(app)
        static_dir = os.path.join(os.path.dirname(module.__file__), 'static')
        if os.path.exists(static_dir):
            static_media_dirs.append(static_dir)
    return static_media_dirs
