# Amara, universalsubtitles.org
#
# Copyright (C) 2015 Participatory Culture Foundation
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

"""utils.forms.languages -- form fields for selecting languages."""

from django import forms
from django.forms.utils import flatatt
from django.utils.safestring import mark_safe

from utils import translation
from .widgets import Dropdown

class LanguageDropdown(Dropdown):
    """Widget that renders a language dropdown

    Attrs:
        options: space separate string containing language options.  Each one
            of these corresponds to a section on the dropdown.  If present,
            that section will be enabled.  Possible values are "null", "my",
            "popular" and "all".
    """

    def render(self, name, value, attrs, choices=()):
        final_attrs = self.build_attrs(attrs)
        final_attrs['name'] = name
        if value:
            final_attrs['data-initial'] = value
        return mark_safe(u'<select{}></select>'.format(flatatt(final_attrs)))

class MultipleLanguageDropdown(forms.SelectMultiple):
    """Widget that renders a language dropdown

    Attrs:
        options: space separate string containing language options.  Each one
            of these corresponds to a section on the dropdown.  If present,
            that section will be enabled.  Possible values are "null", "my",
            "popular" and "all".
    """

    def render(self, name, value, attrs, choices=()):
        final_attrs = self.build_attrs(attrs)
        final_attrs['name'] = name
        final_attrs['style'] = "width: 100%"
        if 'class' in final_attrs:
            final_attrs['class'] += ' select'
        else:
            final_attrs['class'] = 'select'
        if value:
            final_attrs['data-initial'] = value
        return mark_safe(u'<select multiple{}></select>'.format(
            flatatt(final_attrs)))

class WidgetAttrDescriptor(object):
    """Field attribute that gets/sets a widget attribute."""
    def __init__(self, attr_name):
        self.attr_name = attr_name

    def __get__(self, field, cls=None):
        return field.widget.attrs.get(self.attr_name)

    def __set__(self, field, value):
        if value is True:
            field.widget.attrs[self.attr_name] = '1'
        else:
            field.widget.attrs[self.attr_name] = value

class LanguageFieldMixin(object):
    def __init__(self, *args, **kwargs):
        options = kwargs.pop('options', "null my popular all")
        null_label = kwargs.pop('null_label', None)
        placeholder = kwargs.pop('placeholder', False)
        allow_clear = kwargs.pop('allow_clear', False)
        kwargs['choices'] = translation.get_language_choices()
        super(LanguageFieldMixin, self).__init__(*args, **kwargs)
        if options:
            self.options = options
        if null_label:
            self.null_label = null_label
        if placeholder:
            self.placeholder = placeholder
        if allow_clear:
            self.allow_clear = allow_clear

    options = WidgetAttrDescriptor('data-language-options')
    null_label = WidgetAttrDescriptor('data-language-null-label')
    placeholder = WidgetAttrDescriptor('data-placeholder')
    allow_clear = WidgetAttrDescriptor('data-allow-clear')

    def exclude(self, languages):
        self.widget.attrs['data-language-exclude'] = languages
        self.choices = [
            c for c in self.choices if c[0] not in languages
        ]

    def limit_to(self, languages):
        self.widget.attrs['data-language-limit-to'] = languages
        self.choices = [
            c for c in self.choices if c[0] in languages
        ]

class LanguageField(LanguageFieldMixin, forms.ChoiceField):
    widget = LanguageDropdown

    def clean(self, value):
        return value if value != 'X' else None

class MultipleLanguageField(LanguageFieldMixin, forms.MultipleChoiceField):
    widget = MultipleLanguageDropdown
    def clean(self, value):
        if value:
            return [
                code if code != 'X' else None
                for code in value
            ]
        else:
            return value
