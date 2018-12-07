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

"""userlookup -- handle looking up users in the API using various methods

We want to allow users to be looked up in different ways.  At a minimum, we
want to support looking up users by either username or ID.  Also, some of our
partners want special ways to lookup users on their teams.

This module allows for a dynamic system to lookup users using string
identifiers using the following system:
  - If the string begins with "id$" then we do a secure ID lookup
  - We allow other modules to register other prefixes to handle partner
    customizations
  - As a default, we do a username lookup
"""

from __future__ import absolute_import

import functools

from auth.models import CustomUser as User

_lookup_functions = {}

def register(prefix):
    """Decorator to register a customized lookup

    Args:
        prefix: unique key to identify the lookup.  When using the API, the
            user can then be specified with "prefix$id".


    This should be used to decorate a lookup function.  That function will
    be passed the parsed id value and should return a User or raise
    User.DoesNotExist.
    """
    def wrapper(lookup_func):
        _lookup_functions[prefix] = lookup_func
        return lookup_func
    return wrapper

def lookup_user(identifier):
    parts = identifier.split('$', 1)
    if len(parts) > 1:
        if parts[0] in _lookup_functions:
            return _lookup_functions[parts[0]](parts[1])
    return User.objects.get(username=identifier)

@register('id')
def secure_id_lookup(secure_id):
    return User.lookup_by_secure_id(secure_id)
