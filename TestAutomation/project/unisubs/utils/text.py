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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

from collections import defaultdict

class fmtdict(defaultdict):
    def __init__(self, variables):
        defaultdict.__init__(self)
        self.update(variables)

    def __missing__(self, key):
        return key

def fmt(text, **variables):
    """Format a string of text by interpolating variables.

    fmt works like the % operator used with a dict, but doesn't throw an
    exception if a variable is missing.  Instead the variable name will be
    used as the value.

    This function should used for translated strings instead of other methods
    (the % operator, str.format, string.Template) because it's better for
    translators for a few reasons:
        - Using named variables is better than positional args because the
          translator might change their other.
        - If a translator mistakenly translates a variable name, the page
          doesn't break.
        - It uses the % operator syntax because that's how translators see the
          text inside a blocktrans tag.  Using the same syntax is good because
          it's less for translators to have to learn.

    See #1376 for more info.
    """
    return text % fmtdict(variables)
