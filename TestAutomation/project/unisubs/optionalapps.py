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

"""
.. _optional-apps:

Optional Apps
=============
Amara.org uses several apps/packages that are stored in private github
repositories that add extra functionality for paid partnerships.  These apps
are optional -- the amara codebase runs fine without them.

This module handles adding functionality from those repositories, but only if
they're present.

.. autofunction:: setup_path
.. autofunction:: get_repository_paths
.. autofunction:: get_apps
.. autofunction:: get_urlpatterns
.. autofunction:: exec_repository_scripts

"""

import os
import sys

from django import apps
from django.conf.urls import include, url

project_root = os.path.abspath(os.path.dirname(__file__))

# These are git submodules that can extend the amara code
AMARA_EXTENSIONS = [
    'amara-assets',
    'amara-enterprise',
]

def _extensions_present():
    """Get the amara extensions that are present."""
    for name in AMARA_EXTENSIONS:
        repo_path = os.path.join(project_root, name)
        if os.path.exists(repo_path) and os.listdir(repo_path):
            yield name

def setup_path():
    """
    Add optional repositories to the python path
    """
    sys.path.extend(get_repository_paths())

def get_repository_paths():
    """Get paths to optional repositories that are present

    Returns:
        list of paths to our optional repositories.  We should add these to
        sys.path so that we can import the apps.
    """
    return [os.path.join(project_root, repo)
            for repo in _extensions_present()]

def get_apps():
    """Get a list of optional apps

    Returns:
        list of app names from our optional repositories to add to
        INSTALLED_APPS.
    """
    app_names = []
    repo_paths = [os.path.abspath(p) for p in get_repository_paths()]
    for app_config in apps.apps.get_app_configs():
        app_path = os.path.abspath(app_config.path)
        for repo_path in repo_paths:
            if app_path.startswith(repo_path):
                app_names.append(app_config.name)
    return tuple(app_names)

def get_urlpatterns():
    """Get Django urlpatterns for URLs from our optional apps.

    This function finds urlpatterns inside the urls module for each optional
    app.  In addition a module variable can define a variable called PREFIX to
    add a prefix to the urlpatterns.

    Returns:
        url patterns containing urls for our optional apps to add to our root
        urlpatterns
    """
    urlpatterns = []

    for app_name in get_apps():
        try:
            app_module = __import__('{0}.urls'.format(app_name))
            url_module = app_module.urls
        except ImportError:
            continue
        try:
            prefix = url_module.PREFIX
        except AttributeError:
            prefix = ''
        urls_module = '{0}.urls'.format(app_name)
        urlpatterns.append(
            url(prefix, include(urls_module, namespace=app_name)))

    return urlpatterns

def exec_repository_scripts(filename, globals, locals):
    """Add extra values to the settings module.

    This function looks for files named filename in each optional
    repository.  If that exists, then we call execfile() to run the code using
    the settings globals/locals.  This simulates that code being inside the
    current scope.
    """
    for directory in get_repository_paths():
        script_path = os.path.join(directory, filename)
        if os.path.exists(script_path):
            execfile(script_path, globals, locals)
