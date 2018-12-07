# Amara, universalsubtitles.org
#
# Copyright (C) 2018 Participatory Culture Foundation
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

def fix_attrs(attrs):
    """
    Fixup a set of HTML attrs pass in to a templatetag

    This method fixes an issue when passing in HTML attributes to a django
    template tag:

      - '_' is replaced with '-'.  This is because '-' is an invalid when
        passing in the attribute from the template code.
      - The values True and False are replaced with 'true'/'false', which jquery can parse
    """
    for key, value in attrs.items():
        if value is True:
            attrs[key] = 'true'
        elif value is False:
            attrs[key] = 'false'

        if '_' in key:
            new_key = key.replace('_', '-')
            attrs[new_key] = attrs.pop(key)
    return attrs
