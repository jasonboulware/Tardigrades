# -*- coding: utf-8 -*-
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
from django.utils.text import slugify
from unidecode import unidecode


def pan_slugify(value):
    """Return a Unicode-translitered slug.

    This is helpful for most inputs containing Unicode. For example:

        cação -> cacao

    """
    return slugify(unidecode(value))

def pan_slugify_username(s):
    """Return a slugified string suitable for a username."""
    return pan_slugify(s).replace('-', '_')
