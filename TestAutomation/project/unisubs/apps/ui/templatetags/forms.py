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

import itertools

from django import forms
from django import template
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.translation import ugettext as _

from ui.forms import HelpTextList, SwitchInput
from utils.text import fmt

register = template.Library()

@register.simple_tag
def render_field(field, reverse_required=False):
    return render_to_string('future/forms/field.html', {
        'field': field,
        'field_id': field.auto_id,
        'widget_type': calc_widget_type(field),
        'label': field.label,
        'help_text': field.help_text,
        'errors': field.errors,
        'no_help_block': isinstance(field.help_text, HelpTextList),
        'label': calc_label(field, reverse_required),
    })

@register.simple_tag
def render_filter_field(field):
    """
    Template tag version of render_filter_field.

    This is the current version and is used with the filterBox element
    """
    return render_field(field, reverse_required=True)

# Deprecated ways to render form fields
@register.filter('render_field')
def render_field_filter_version(field):
    return render_field(field)

@register.filter('render_filter_field')
def render_filter_field_filter_version(field):
    """
    Template tag version of render_filter_field.

    This is the deprecated version and works with the old-style filters
    """
    return render_to_string('future/forms/filter-field.html', {
        'field': field,
        'label': field.label,
        'help_text': field.help_text,
        'errors': field.errors,
        'widget_type': calc_widget_type(field),
        'label': field.label,
    })

@register.inclusion_tag('future/forms/button-field.html')
def button_field(field, button_label, button_class="cta"):
    return {
        'field': field,
        'widget_type': calc_widget_type(field),
        'no_help_block': isinstance(field.help_text, HelpTextList),
        'button_label': button_label,
        'button_class': button_class,
    }

@register.filter
def is_checkbox(bound_field):
    widget = bound_field.field.widget
    return (isinstance(widget, forms.CheckboxInput) and
            not isinstance(widget, SwitchInput))

def calc_widget_type(field):
    if field.is_hidden:
        return 'hidden'
    try:
        widget = field.field.widget
    except StandardError:
        return 'default'
    if isinstance(widget, forms.RadioSelect):
        return 'radio'
    elif isinstance(widget, forms.SelectMultiple):
        return 'select-multiple'
    elif isinstance(widget, forms.Select):
        return 'select'
    elif isinstance(widget, SwitchInput):
        return 'switch'
    elif isinstance(widget, forms.CheckboxInput):
        return 'checkbox'
    elif isinstance(widget, forms.Textarea):
        return 'default'
    else:
        return 'default'

def calc_label(field, reverse_required=False):
    if not field.label:
        return ''
    elif is_checkbox(field):
        return field.label
    elif not field.field.required and not reverse_required:
        return label_with_optional(field.label)
    elif field.field.required and reverse_required:
        return label_with_required(field.label)
    else:
        return field.label

def label_with_required(label):
    return format_html(
        u'{} <span class="fieldOptional">{}</span>',
        unicode(label), _(u'(required)'))

def label_with_optional(label):
    return format_html(
        u'{} <span class="fieldOptional">{}</span>',
        unicode(label), _(u'(optional)'))

@register.inclusion_tag('future/forms/field.html')
def multi_field(label, *fields, **kwargs):
    help_text = kwargs.get('help_text')
    reverse_required = kwargs.get('reverse_required')
    required = kwargs.get('required')
    optional = kwargs.get('optional')
    dependent = kwargs.get('dependent')
    ordered = kwargs.get('ordered')

    fields_and_labels = [
        (field, field.label if not is_checkbox(field) else None)
        for field in fields
    ]

    field = render_to_string('future/forms/multi-field.html', {
        'fields_and_labels': fields_and_labels,
        'dependent': dependent,
        'ordered': ordered,
        'checkbox_mode': is_checkbox(fields[0]),
    })
    errors = []
    for f in fields:
        errors.extend(f.errors)
    field_id = 'id_' + '_'.join(field.name for field in fields)

    if required:
        label = label_with_required(label)
    elif optional:
        label = label_with_optional(label)

    return {
        'field': field,
        'field_id': field_id,
        'widget_type': 'multi-field',
        'label': label,
        'help_text': help_text,
        'errors': errors,
        'no_help_block': False,
    }
