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

from __future__ import absolute_import

import json

from django import template
from django.urls import reverse
from django.forms.utils import flatatt
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from utils.bunch import Bunch
from ui.templatetags.utils import fix_attrs

register = template.Library()

@register.simple_tag(name='dropdown-button-icon')
def dropdown_button_icon(menu_id, css_class=None, **attrs):
    fix_attrs(attrs)
    attrs.update({
        'data-target': menu_id,
        'role': 'button',
        'aria-haspopup': 'true',
        'aria-expanded': 'false',
        'class': 'dropdownMenu-button',
    })
    if css_class:
        attrs['class'] += ' {}'.format(css_class)

    return format_html(
        u'<button{}><span class="fa fa-ellipsis-v"></span></button>',
        flatatt(attrs))

@register.simple_tag(name='dropdown-button')
def dropdown_button(menu_id, css_class, **attrs):
    fix_attrs(attrs)
    return format_html(
        u'<button data-target="{}" class="dropdownMenu-button {}" role="button" aria-haspopup="true" '
        'aria-expanded="false"{}>', menu_id, css_class, flatatt(attrs))

@register.simple_tag(name='end-dropdown-button')
def end_dropdown_button():
    return mark_safe(u'</button>')

@register.simple_tag(name='filterbox-dropdown-button')
def filter_box_dropdown_button(menu_id, label):
    return format_html(
        '{}'
        '<span class="filterBox-buttonIcon fa fa-filter"></span> '
        '<span class="filterBox-buttonText">{}</span>'
        '{}',
        dropdown_button(menu_id, 'filterBox-button'), label,
        end_dropdown_button())

@register.simple_tag
def dropdown(menu_id, css_class=None, labelled_by=None):
    attrs = {
        'class': 'dropdownMenu',
        'role': 'menu',
        'id': menu_id
    }
    if css_class:
        attrs['class'] += ' {}'.format(css_class)
    if labelled_by:
        attrs['aria-labelledby'] = labelled_by

    return format_html(u'<ul{}>', flatatt(attrs))

@register.simple_tag(name='dropdown-item')
def dropdown_item(label, view_name, *args, **kwargs):
    options = extra_dropdown_item_options(kwargs)

    if options.raw_url:
        url = view_name
    else:
        url = reverse(view_name, args=args, kwargs=kwargs)

    return make_dropdown_item(label, options, {
        'href': url
    })

@register.simple_tag(name='dropdown-js-item')
def dropdown_js_item(label, *data, **kwargs):
    options = extra_dropdown_item_options(kwargs)

    return make_dropdown_item(label, options, {
        'href': '#',
        'data-activate-args': json.dumps(data),
    }, link_tag='button')

@register.simple_tag(name='dropdown-header-item')
def dropdown_header_item(label, **kwargs):
    options = extra_dropdown_item_options(kwargs)

    return make_dropdown_item(label, options, {
        'href': '#',
        'class': 'header',
    }, link_tag='button')

@register.simple_tag(name='dropdown-update-filter-items')
def dropdown_update_filter_items(bound_field, header=True):
    field_name = bound_field.name
    field = bound_field.field
    parts = []
    for choice in field.choices:
        args = [ choice[1], "update-filter", field_name, choice[0] ]
        if choice[0] == field.initial:
            args.append('default')
        parts.append(dropdown_js_item(*args))
    return mark_safe('\n'.join(parts))

def make_dropdown_item(label, options, link_attrs, link_tag='a'):
    link_attrs.update({
        'tabindex': -1,
        'role': 'menuitem',
    })
    if 'class' in link_attrs:
        link_attrs['class'] += ' dropdownMenu-link'
    else:
        link_attrs['class'] = 'dropdownMenu-link'

    classes = ['dropdownMenu-item']
    if options.separator:
        classes.append('separator')
    if options.extra_class:
        classes.append(options.extra_class)

    if options.icon:
        if options.icon.startswith('fa-'):
            icon_class="fa {}".format(options.icon)
        else:
            icon_class="icon icon-{}".format(options.icon)

        label_html = format_html(
            u'<span class="{} dropdownMenu-icon"></span>'
            u'<span class="dropdownMenu-text">{}</span> ',
            icon_class, unicode(label))
    elif options.count:
        label_html = format_html(u'<span class="dropdownMenu-text">{}</span> <span class="dropdownMenu-extra">{}</span>',
                                 unicode(label), options.count)
    else:
        label_html = format_html(u'<span class="dropdownMenu-text">{}</span>',
                                 unicode(label))
    if options.disabled:
        link_html = format_html(
            u'<span class="dropdownMenu-link disabled">{}</span>', label_html)
    else:
        link_html = format_html(u'<{0}{1}>{2}</{0}>', link_tag, flatatt(link_attrs), label_html)

    return format_html(u'<li role="none" class="{}">{}</li>',
                       u' '.join(classes), link_html)

def extra_dropdown_item_options(kwargs):
    """
    Extract dropdown-item arguments from kwargs, leaving the rest to use for
    the reverse() call.

    This is basically a workaround for the fact that you can't have named args
    after *args, in python2.
    """
    return Bunch(separator=kwargs.pop('separator', None),
                 extra_class=kwargs.pop('class', None),
                 disabled=kwargs.pop('disabled', None),
                 icon=kwargs.pop('icon', None),
                 count=kwargs.pop('count', None),
                 raw_url=kwargs.pop('raw_url', None))

@register.simple_tag
def enddropdown():
    return format_html(u'</ul>')
