# Amara, universalsubtitles.org
#
# Copyright (C) 2016 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program.  If not, see http://www.gnu.org/licenses/agpl-3.0.html.

"""
api.extra -- framework for extra fields on API endpoints

This module exist to handle the extra query parameter for API endpoints.
There are a couple features here:

  - API clients can optionally include an extra parameter to ask for extra
    in the response.
  - Clients can specify any number of extra fields using a comma separated list
  - The extra fields can be implemented by components other than the API.  In
    particular, some are implement in amara-enterprise.

To facilitate this, we create a distpach-style system where components can
register to handle the extra fields.  Here's how it works:

- We define an ExtraDispatcher object to be used for an endpoint, or set of
  endpoints.
- Components can register for particular extra parameters with the register()
  method.
- The API code calls the add_data() method to potentially add extra data
  to the response.
- ExtraDispatcher calculates which components should be called based on the
  extra query param and calls them.
"""

class ExtraDispatcher(object):
    """
    Dispatcher for extra paramaters
    """
    def __init__(self):
        self.callbacks = {}

    def register(self, name, callback):
        """
        Register an extra callback function

        If name is present in the extra query param, callback will be called
        to add extra data to the response.

        Args:
            name: name for the extra data.  This is what needs to be present
                  in the extra query param to trigger the callback.  It must
                  be unique.
            callback: callback function to provide the extra data.
        """
        self.callbacks[name] = callback

    def handler(self, name):
        """
        Function decorator to register a callback function

        You can use this decorator like this:

        @handler(name)
        def function():
            pass

        It's a shortcut for defining the function, then calling
        register(name, function).
        """
        def decorator(func):
            self.register(name, func)
            return func
        return decorator

    def add_data(self, request, data, **kwargs):
        """
        Add extra data to an API response.

        This method figures out if any functions registered with register()
        should be called and calls them.  The arguments are:
            - request.user
            - data
            - Any additional kwargs
        """
        extra = request.query_params.get('extra')
        if extra:
            for name in extra.split(','):
                callback = self.callbacks.get(name)
                if callback:
                    callback(request.user, data, **kwargs)

video = ExtraDispatcher()
video_language = ExtraDispatcher()
user = ExtraDispatcher()
