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

from django.core.cache import cache

TIMEOUT = 60 * 60 * 24 * 5 # 5 days


def _lang_is_synced_id(language, public):
    if public:
        return u"language-%s-timing-complete-public" % (language.pk,)
    else:
        return u"language-%s-timing-complete-private" % (language.pk,)

def invalidate_language_cache(language):
    cache.delete(_lang_is_synced_id(language, True))
    cache.delete(_lang_is_synced_id(language, False))

def get_is_synced(language, public):
    cache_key = _lang_is_synced_id(language, public)
    return cache.get(cache_key)

def set_is_synced(language, public, value):
    cache_key = _lang_is_synced_id(language, public)
    cache.set(cache_key, value, TIMEOUT)
