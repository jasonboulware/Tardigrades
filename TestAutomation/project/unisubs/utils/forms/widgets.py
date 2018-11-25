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

from itertools import chain

from django.forms import widgets
from django.forms.utils import flatatt
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe

class Dropdown(widgets.Select):
    def build_attrs(self, *args, **kwargs):
        attrs = super(Dropdown, self).build_attrs(*args, **kwargs)
        attrs['style'] = "width: 100%"
        if 'class' in attrs:
            attrs['class'] += ' select'
        else:
            attrs['class'] = 'select'
        return attrs
