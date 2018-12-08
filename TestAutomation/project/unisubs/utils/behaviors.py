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
Extensible behavior functions

This module allows one app to define a "behavior function", which other apps
can then override to change the behavior.  This is the `Chain of responsibility pattern <http://http://en.wikipedia.org/wiki/Chain-of-responsibility_pattern/>`_ which helps keep modules loosely coupled.

A typical use for this is the subtitle that we display for video cards,
underneath the title.  Normally, we don't show anything there, but for TED we
show the speaker name.  Putting the code that deals with this inside the
videos app is bad practice because:

- It's adding complexity to the videos app.  Handling team requirements is
  outside of its scope.
- It requires importing from the teams app, but the teams app needs to import
  from the videos app.  So we now have a circular dependency.

Instead, videos defines the `get_video_subtitle` behavior, which can then be
overriden by other apps.  This allows us to change the behavior without having
to add complexity/dependencies to the videos app.  The code works something
like this.

Example:
    >>> @behavior
    ... def get_video_subtitle(video)
    ...     return video.title
    >>> @get_video_subtitle.override
    ... def get_video_subtitle_for_team_foo(video):
    ...     team_video = video.get_team_video()
    ...     if team_video and team_video.slug == 'foo'
    ...         return 'My Team: %s' % video.title
    ...     else:
    ...         return DONT_OVERRIDE
"""

from functools import wraps

DONT_OVERRIDE = object()

def behavior(func):
    """Declare a function as an overridable behavior.

    This allows other components to modify the behavior of the function by
    decorating them with func.override.  When invoked, the override function
    will be passed the arguments the original function was called with.

    The override function's return vaule will be used intead of the return
    value of the original.  If DONT_OVERRIDE is returned, then control will
    pass to other override functions, and finally the original function.

    Override functions are themselves behaviors, so they can be overriden
    again forming a chain of responsibility that handles the behaviors.  If
    the same function is overriden twice, then the override functions will be
    called in FIFO order.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if wrapper.override_func:
            rv = wrapper.override_func(*args, **kwargs)
            if rv is not DONT_OVERRIDE:
                return rv
        return func(*args, **kwargs)
    wrapper.override_func = None
    def override(override_func):
        override_func = behavior(override_func)
        # if we already have an override_func, make that function override the
        # second override.  This effectively insert the new function
        # between the original and the old override functions.
        if wrapper.override_func is not None:
            override_func.override(wrapper.override_func)
        wrapper.override_func = override_func
        return override_func
    wrapper.override = override
    return wrapper
