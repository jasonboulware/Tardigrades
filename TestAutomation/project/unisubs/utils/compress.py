# -*- coding: utf-8 -*-
# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
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

"""Django-ORM-friendly data compression."""

import base64, zlib

def compress(data):
    """Compress a bytestring and return it in a form Django can store.

    If you want to store a Unicode string, you need to encode it to a bytestring
    yourself!

    Django prefers to receive Unicode strings to store in a text field, which
    will mangle normal zip data.  We base64 it to avoid the problem.

    """
    return base64.encodestring(zlib.compress(data))

def decompress(data):
    """Decompress data created with compress."""
    return zlib.decompress(base64.decodestring(data))
