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
ui.siteheader -- navlinks in the site header
"""
from __future__ import absolute_import

from utils.behaviors import behavior

@behavior
def navlinks():
    """Get a list of navlinks for the site header

    By default, we don't show any links.  An extension app can override this
    and return a custom list of links for the site.

    Returns: List of ui.Tab objects.
    """
    return []
