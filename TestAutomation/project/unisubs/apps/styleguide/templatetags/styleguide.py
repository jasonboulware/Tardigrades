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

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string

register = template.Library()

@register.tag('styleguide-example')
def styleguide_example(parser, token):
    """
    Render a styleguide example

    Note that in order for this tag to work properly, the contents need to be
    wrapped in a {% verbatim %} tag
    """
    nodelist = parser.parse(('end-styleguide-example',))
    parser.delete_first_token()
    return StyleguideExampleNode(nodelist)

class StyleguideExampleNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        content = self.nodelist.render(context)
        return render_to_string('styleguide/example.html', {
            'rendered': template.Template(content).render(context),
            'source': escape(content),
        })
