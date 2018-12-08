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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

import contextlib

from nose.tools import *

@contextlib.contextmanager
def assert_invalidates_model_cache(instance):
    key = 'assert-invalidates-video-cache'
    # delete the current CacheGroup to make sure we get a clean one
    Model = instance.__class__
    cache_group = Model.cache.get_cache_group(instance.pk)
    cache_group.set(key, 'value')
    yield
    cache_group = Model.cache.get_cache_group(instance.pk)
    assert_equal(cache_group.get(key), None, 'cache not invalidated')
