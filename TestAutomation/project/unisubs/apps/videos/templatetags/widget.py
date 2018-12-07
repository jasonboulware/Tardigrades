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

from django import template
from django.conf import settings

register = template.Library()

@register.inclusion_tag('videos/_widget.html')
def widget(widget_params, div_id='widget_div'):
    return {
        'div_id': div_id,
        'widget_params': widget_params
    }

@register.inclusion_tag('videos/_get_counter.html')
def get_counter():
    domain = settings.HOSTNAME
    return {
        'domain': domain
    }
