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

"""
caching.decorators -- caching decorators
"""
from django.views.decorators.cache import cache_control
from django.views.decorators.vary import vary_on_headers

def cache_page(minutes=0, seconds=0):
    max_age = minutes * 60 + seconds
    def decorator(func):
        func = vary_on_headers('Accept-Language', 'Cookie')(func)
        func = cache_control(max_age=max_age)(func)
        return func
    return decorator
