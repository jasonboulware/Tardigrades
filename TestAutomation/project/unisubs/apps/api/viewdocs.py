# Amara, universalsubtitles.org
#
# Copyright (C) 2015 Participatory Culture Foundation
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

import re

from django.utils.encoding import smart_text
from django.utils.safestring import mark_safe
from rest_framework.views import get_view_name, get_view_description
from rest_framework.utils import formatting
import markdown

markdown_formatter = markdown.Markdown(safe_mode=False, extensions=[
    'headerid(level=2)',
    'tables',
])

def amara_get_view_name(view_cls, suffix=None):
    if hasattr(view_cls, 'DOC_NAME'):
        return view_cls.DOC_NAME
    return get_view_name(view_cls, suffix)

tab_markup = re.compile("^#\s*([\w\s/]+)\s+#$", re.M)

def amara_get_view_description(view_cls, html=False):
    description = view_cls.__doc__ or ''
    description = formatting.dedent(smart_text(description))
    if not html:
        return description
    return mark_safe('<div class="api-description">{}</div>'.format(
        markup_description(description)))

def markup_description(description):
    split_into_tabs = tab_markup.split(description)
    if len(split_into_tabs) == 1:
        # no tabs just return straight markup
        return markdown_formatter.convert(description)
    tab_content = split_into_tabs[0:None:2]
    tab_labels = ['About'] + split_into_tabs[1:None:2]
    chunks = []
    chunks.append('<ul class="nav nav-tabs">')
    for i, label in enumerate(tab_labels):
        chunks.append(make_tab_item(i+1, label))
    chunks.append('</ul><div class="well tab-content">')
    for i, content in enumerate(tab_content):
        chunks.append(make_tab_pane(i+1, markdown_formatter.convert(content)))
    chunks.append('</div>')
    return ''.join(chunks)

def make_tab_item(index, label):
    if index == 1:
        attrs = ' class="active"'
    else:
        attrs = ''
    return '<li{}><a href="#tab-{}" data-toggle="tab">{}</a></li>'.format(
        attrs, index, label)

def make_tab_pane(index, content):
    if index == 1:
        classes = 'tab-pane active'
    else:
        classes = 'tab-pane'
    return '<div class="{}" id="tab-{}">{}</div>'.format(classes, index,
                                                         content)
