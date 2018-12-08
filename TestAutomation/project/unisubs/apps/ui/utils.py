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

"""ui.utils -- frontend-related classes

This module contains a few utility classes that's used by the views code.
"""

from __future__ import absolute_import
from copy import copy
from collections import deque
from urllib import urlencode

from collections import namedtuple
from django.urls import reverse
from django.utils.html import format_html, format_html_join, html_safe, mark_safe
from django.utils.translation import ugettext_lazy as _

from ui.templatetags import dropdown
from utils.text import fmt

@html_safe
class Link(object):
    def __init__(self, label, view_name, *args, **kwargs):
        self.label = label
        query = kwargs.pop('query', None)
        self.class_ = kwargs.pop('class_', None)
        if '/' in view_name or view_name == '#':
            # URL path passed in, don't try to reverse it
            self.url = view_name
        else:
            self.url = reverse(view_name, args=args, kwargs=kwargs)
        if query:
            self.url += '?' + urlencode(query)

    def __unicode__(self):
        if self.class_:
            return format_html(u'<a href="{}" class="{}">{}</a>', self.url,
                               self.class_, self.label)
        else:
            return format_html(u'<a href="{}">{}</a>', self.url, self.label)

    def active(self):
        if self.class_:
            class_ = self.class_ + ' active'
        else:
            class_ = 'active'
        return self.clone(class_=class_)

    def clone(self, **new_attrs):
        rv = copy(self)
        rv.__dict__.update(new_attrs)
        return rv

    def __eq__(self, other):
        return (type(self) == type(other) and
                self.label == other.label and
                self.url == other.url)

@html_safe
class AjaxLink(Link):
    def __init__(self, label, **query_params):
        # All of our ajax links hit the current page, adding some query
        # parameters, so this constructor is optimized for that use.
        self.label = label
        self.url = '?' + urlencode(query_params)

    def __unicode__(self):
        return format_html(u'<a class="ajaxLink" data-href="{}">{}</a>', self.url, self.label)

class CTA(Link):
    def __init__(self, label, icon, view_name, block=False,
                 disabled=False, tooltip='', *args, **kwargs):
        super(CTA, self).__init__(label, view_name, *args, **kwargs)
        self.disabled = disabled
        self.icon = icon
        self.block = block
        self.tooltip = tooltip

    def __unicode__(self):
        return self.render()

    def as_block(self):
        return self.render(block=True)

    def render(self, block=False):
        tooltip_element = u'<span data-toggle="tooltip" data-placement="top" title="{}">{}</span>'
        link_element = u'<a href="{}" class="{}"><i class="icon {}"></i> {}</a>'
        css_class = "button"
        if self.disabled:
            css_class += " disabled"
        else:
            css_class += " cta"
        if block:
            css_class += " block"
        link = format_html(link_element, self.url, css_class, self.icon,
                           self.label)
        if len(self.tooltip) > 0:
            link = format_html(tooltip_element, self.tooltip, link)
        return link

    def __eq__(self, other):
        return (isinstance(other, Link) and
                self.label == other.label and
                self.icon == other.icon and
                self.url == other.url)

class SplitCTA(CTA):
    '''
    args:
    menu_id - id of the dropdown menu container. If there are multiple SplitCTA's in a page, each one must have a unique menu_id
    dropdown_items - an iterable of (label, url) tuples
    '''
    def __init__(self, label, view_name, icon=None, block=False,
                    disabled=False, main_tooltip=None, menu_id='splitCTADropdownMenu',
                    dropdown_tooltip=None, dropdown_items=[], 
                    *args, **kwargs):
        super(SplitCTA, self).__init__(label, icon, view_name, block, disabled, main_tooltip)
        self.dropdown_tooltip = dropdown_tooltip
        self.dropdown_items = dropdown_items
        self.menu_id = menu_id

    def _create_main_button(self):
        # mark-up variables
        tooltip_mu = u'<span class="{}" data-toggle="tooltip" data-placement="top" title="{}">{}</span>'
        cta_mu = u'<a href="{}" class="{}">{}{}</a>'
        icon_mu = ""

        tooltip_css_class = ""
        cta_css_class = "button split-button"

        if self.icon:
            icon_mu = format_html(u'<i class="icon {}"></i>', self.icon)

        if self.disabled:
            cta_css_class += " disabled"
        else:
            cta_css_class += " cta"

        if self.tooltip:
            if self.block:
                tooltip_css_class += "width-100"

            # just the cta element
            cta = format_html(cta_mu, self.url, cta_css_class, icon_mu, self.label)

            # the cta element wrapped in the tooltip span
            cta = format_html(tooltip_mu, tooltip_css_class, self.tooltip, cta)
        else:
            if self.block:
                cta_css_class += " block"
            # no need to wrap the cta element in the tooltip span if there's no tooltip
            cta = format_html(cta_mu, self.url, cta_css_class, icon_mu, self.label)

        return cta

    def _create_dropdown_toggle(self):        
        tooltip_mu = u'<span data-toggle="tooltip" data-placement="top" title="{}">{}</span>'
        caret_mu = u'<span class="caret"></span>'

        css_class = "button split-button split-button-dropdown-toggle"

        if self.disabled:
            css_class += " disabled"
        else:
            css_class += " cta"

        dropdown_toggle = (dropdown.dropdown_button(self.menu_id, css_class)
                           + mark_safe(caret_mu)
                           + dropdown.end_dropdown_button())

        # wrap the dropdown toggle mark-up around the tooltip mark-up
        if self.dropdown_tooltip:
            dropdown_toggle = format_html(tooltip_mu, self.dropdown_tooltip, dropdown_toggle)

        return dropdown_toggle

    def _create_dropdown_menu(self):
        dropdown_menu = dropdown.dropdown(self.menu_id, css_class='dropdownMenuLeft')
        dropdown_items = [dropdown.dropdown_item(i[0], i[1], raw_url=True) for i in self.dropdown_items]
        dropdown_items = mark_safe(''.join(dropdown_items))

        return dropdown_menu + dropdown_items + dropdown.enddropdown()

    def render(self, block=False):
        container = u'<div class="{}">{}{}{}</div>'

        if self.block:
            css_class = " split-button-container-full-width"
        else:
            css_class = " split-button-container"

        main_cta = self._create_main_button()
        dropdown_toggle = self._create_dropdown_toggle()
        dropdown_menu = self._create_dropdown_menu()

        return format_html(container, css_class, main_cta, dropdown_toggle, dropdown_menu)

    def __eq__(self, other):
        return (super(SplitCTA, self).__eq__(other) and
                self.dropdown_tooltip == other.dropdown_tooltip and
                self.dropdown_items == other.dropdown_items)

class Tab(Link):
    def __init__(self, name, label, view_name, *args, **kwargs):
        self.name = name
        super(Tab, self).__init__(label, view_name, *args, **kwargs)

    def __eq__(self, other):
        return (isinstance(other, Tab) and
                self.name == other.name and
                self.label == other.label and
                self.url == other.url)

class SectionWithCount(list):
    """Section that contains a list of things with a count in the header
    """
    header_template = u'{} <span class="count">({})</span>'
    def __init__(self, header_text):
        self.header_text = header_text

    def header(self):
        return format_html(self.header_template, self.header_text,
                           len(self))

@html_safe
class ContextMenu(object):
    """Context menu

    Each child of ContextMenu should be a Link or MenuSeparator item
    """
    def __init__(self, initial_items=None):
        self.items = deque()
        if initial_items:
            self.extend(initial_items)

    def append(self, item):
        self.items.append(item)

    def extend(self, items):
        self.items.extend(items)

    def prepend(self, item):
        self.items.appendleft(item)

    def prepend_list(self, items):
        self.items.extendleft(reversed(items))

    def __unicode__(self):
        output = []
        output.append(u'<div class="context-menu">')
        output.append(u'<a href="#" class="dropdown-toggle" data-toggle="dropdown" role="button" aria-haspopup="true" aria-expanded="false"><span class="caret"></span></a>')
        output.append(u'<ul class="dropdown-menu">')
        for item in self.items:
            if isinstance(item, MenuSeparator):
                output.append(u'<li class="divider"></li>')
            else:
                output.append(u'<li>{}<li>'.format(unicode(item)))
        output.append(u'</ul></div>')
        return u'\n'.join(output)

class MenuSeparator(object):
    """Display a line to separate items in a ContextMenu."""

__all__ = [
    'Link', 'AjaxLink', 'CTA', 'Tab', 'SectionWithCount', 'ContextMenu',
    'MenuSeparator', 'SplitCTA'
]
