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

from __future__ import absolute_import

from django import template
from django.forms.utils import flatatt
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from utils.text import fmt

from ui.templatetags.utils import fix_attrs
import ui.siteheader
import ui.dates

register = template.Library()

@register.filter
def date(dt):
    return ui.dates.date(dt)

@register.filter
def elapsed_time(dt):
    return ui.dates.elapsed_time(dt)

@register.filter
def datetime(dt):
    return ui.dates.datetime(dt)

@register.simple_tag(takes_context=True)
def header_links(context):
    nav = context.get('nav')
    parts = []
    parts.append(mark_safe(u'<ul>'))
    for tab in ui.siteheader.navlinks():
        if tab.name == nav:
            parts.append(
                format_html(u'<li class="active">{}</li>',
                            mark_safe(unicode(tab))))
        else:
            parts.append(format_html(u'<li>{}</li>', tab))
    parts.append(mark_safe(u'</ul>'))
    return format_html_join(u'\n', u'{}', [(p,) for p in parts])

@register.simple_tag()
def checkbox(id_, id_prefix=None, **attrs):
    """
    Use this to create a checkbox not attached to any form

    A good example of this is the checkboxes in listView
    """
    if id_prefix:
        id_ = '{}{}'.format(id_prefix, id_)
    fix_attrs(attrs).update({
        'type': 'checkbox',
        'id': id_,
    })
    return format_html(
        '<div class="checkbox"><input{}>'
        '<label for="{}"><span class="checkbox-icon"></span></label></div>',
        flatatt(attrs), id_)

@register.simple_tag(name='progress-bar')
def progress_bar(label, current, total, css_class='teal'):
    if total > 0:
        percent = '{}%'.format(100.0 * float(current) / float(total))
    else:
        percent = '0%'
    percent_label = fmt(_(u'%(percent)s complete'), percent=percent)

    return format_html(
        '<div class="progressBar teal">'
        '<div class="progressBar-progress" role="progressbar" style="width: {};">'
        '<span class="sr-only">{}</span></div></div>'
        '<p class="progressBar-label teal">{} '
        '<span class="progressBar-percentage">{}</span></p>',
        percent, percent_label, unicode(label), percent_label)
