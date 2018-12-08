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

import htmllib, formatter
import bleach

CLEAN_DEFAULTS = {
        'tags': ['a', 'b', 'strong', 'i', 'em', 'u', 'li', 'ol', 'ul'],
        'attributes': {'a': 'href'},
        'protocols': ['http', 'https']}

def unescape(s):
    p = htmllib.HTMLParser(formatter.NullFormatter() )
    # we need to preserve line breaks, nofill makes sure we don't
    # loose them
    p.nofill = True
    p.save_bgn()
    p.feed(s)
    return p.save_end().strip()

def clean_html(source, tags=CLEAN_DEFAULTS['tags'],
               attributes=CLEAN_DEFAULTS['attributes'],
               protocols=CLEAN_DEFAULTS['protocols']):
    return bleach.clean(source, tags=tags, attributes=attributes, protocols=protocols)
