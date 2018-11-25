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

from django.core.files import File
from django.forms import widgets
from django.forms.utils import flatatt
from django.template.loader import render_to_string
from django.utils.datastructures import MultiValueDict
from django.utils.encoding import force_unicode, force_text
from django.utils.html import (conditional_escape, format_html,
                               format_html_join)
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from utils import datauri
from utils.amazon.fields import S3ImageFieldFile

class AmaraLanguageSelectMixin(object):
    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        if attrs is None:
            attrs = {}
        if isinstance(value, basestring):
            # single-select
            attrs['data-initial'] = value
        else:
            # multi-select
            attrs['data-initial'] = ':'.join(value)
        return super(AmaraLanguageSelectMixin, self).render(
            name, value, attrs)

    def render_options(self, selected_choices):
        # The JS code populates the options
        return ''

class AmaraLanguageSelect(AmaraLanguageSelectMixin, widgets.Select):
    pass

class AmaraLanguageSelectMultiple(AmaraLanguageSelectMixin,
                                  widgets.SelectMultiple):
    pass

class AmaraProjectSelectMultiple(widgets.SelectMultiple):
    pass

class AmaraRadioSelect(widgets.RadioSelect):
    def __init__(self, inline=False, 
                 dynamic_choice_help_text=None, dynamic_choice_help_text_initial=None, 
                 *args, **kwargs):
        super(AmaraRadioSelect, self).__init__(*args, **kwargs)
        self.inline = inline

        try:
            self.widget_classes = kwargs['attrs']['class']
        except KeyError:
            self.widget_classes = ''

        if dynamic_choice_help_text:
            self.dynamic_choice_help_text = dict(dynamic_choice_help_text)
            self.widget_classes += ' dynamicHelpTextRadio'
        else:
            self.dynamic_choice_help_text = {}

        if dynamic_choice_help_text_initial:
            self.dynamic_choice_help_text_initial = dynamic_choice_help_text_initial   

    def render(self, name, value, attrs=None):
        div_class = 'radio'
        li_class = ''
        ul_class = ''
        if self.inline:
            div_class += ' div-radio-inline'
            li_class = 'li-radio-inline'

        if self.dynamic_choice_help_text:
            ul_class = 'radio-dynamic-help-text'        

        if value is None:
            value = ''
        output = [u'<ul class="{}">'.format(ul_class)]
        for i, choice in enumerate(self.choices):
            input_id = '{}_{}'.format(attrs['id'], i)
            output.extend([
                u'<li class="{}"><div class="{}">'.format(li_class, div_class),
                self.render_input(name, value, choice, input_id),
                self.render_label(name, value, choice, input_id),
                u'</div></li>',
            ])
        output.append(u'</ul>')

        if self.dynamic_choice_help_text:
            output.append(u'<div class="helpBlock dynamicHelpTextContainer">')
            if self.dynamic_choice_help_text_initial:
                output.append(self.dynamic_choice_help_text_initial)
            output.append(u'</div>')

        return mark_safe(u''.join(output))

    def render_input(self, name, value, choice, input_id):
        attrs = {
            'id': input_id,
            'type': 'radio',
            'name': name,
            'value': force_unicode(choice[0]),
            'class': self.widget_classes
        }
        if choice[0] == value:
            attrs['checked'] = 'checked'

        if self.dynamic_choice_help_text:
            attrs['data-dynamic-help-text'] = self.dynamic_choice_help_text[choice[0]]

        return u'<input{}>'.format(flatatt(attrs))

    def render_label(self, name, value, choice, input_id):
        return (u'<label for="{}"><span class="radio-icon"></span>'
                '{}</label>'.format(input_id, force_unicode(choice[1])))

class SearchBar(widgets.TextInput):
    def render(self, name, value, attrs=None):
        input = super(SearchBar, self).render(name, value, attrs)
        return mark_safe(u'<div class="searchbar">'
                         '<label class="sr-only">{}</label>'
                         '{}'
                         '</div>'.format(_('Search'), input))

class ContentHeaderSearchBar(widgets.TextInput):
    def render(self, name, value, attrs=None):
        attrs['class'] = 'contentHeader-searchBar'
        input = super(ContentHeaderSearchBar, self).render(name, value, attrs)
        return format_html(
            '<div class="contentHeader-search">'
            '<label class="sr-only">{}</label>' +
            unicode(input) +
            '</div>', _('Search'))

class AmaraFileInput(widgets.FileInput):
    template_name = "widget/file_input.html"
    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, {
            'type': self.input_type,
            'name': name,
        })
        if value != '':
            final_attrs['value'] = force_text(self._format_value(value))
        return mark_safe(render_to_string(self.template_name, final_attrs))

class UploadOrPasteWidget(widgets.TextInput):
    template_name = "future/forms/widgets/upload-or-paste.html"

    def render(self, name, value, attrs=None):
        context = {
            'name': name,
            'initial_text': '',
        }
        if isinstance(value, basestring):
            context['initial_text'] = value
        return mark_safe(render_to_string(self.template_name, context))

    def value_from_datadict(self, data, files, name):
        selector = data.get(name + '-selector')
        if selector == 'upload':
            return files.get(name + '-upload')
        else:
            return data.get(name + '-paste')

class AmaraClearableFileInput(widgets.ClearableFileInput):
    template_name = "widget/clearable_file_input.html"
    def render(self, name, value, attrs=None):
        context = {
                'initial_text': self.initial_text,
                'input_text': self.input_text,
                'clear_checkbox_label': self.clear_checkbox_label,
        }
        if value is None:
            value = ''
        context.update(self.build_attrs(attrs, {
            'type': self.input_type,
            'name': name,
        }))
        if value != '':
            context['value'] = force_text(self._format_value(value))

        # if is_initial
        if bool(value and hasattr(value, 'url')):
            # context.update(self.get_template_substitution_values(value))
            if not self.is_required:
                checkbox_name = self.clear_checkbox_name(name)
                checkbox_id = self.clear_checkbox_id(checkbox_name)
                context['checkbox_name'] = conditional_escape(checkbox_name)
                context['checkbox_id'] = conditional_escape(checkbox_id)

        return mark_safe(render_to_string(self.template_name, context))

class AmaraImageInput(widgets.ClearableFileInput):
    def __init__(self):
        super(AmaraImageInput, self).__init__()
        # default size, overwritten by AmaraImageField
        self.preview_size = (100, 100)

    def render(self, name, value, attrs=None):
        if isinstance(value, S3ImageFieldFile):
            thumb_url = value.thumb_url(*self.preview_size)
        elif isinstance(value, File):
            thumb_url = datauri.from_django_file(value)
        else:
            thumb_url = None
        return mark_safe(render_to_string('future/forms/widgets/image-input.html', {
            'thumb_url': thumb_url,
            'name': name,
            'clear_name': self.clear_checkbox_name(name),
            'preview_width': self.preview_size[0],
            'preview_height': self.preview_size[1],
        }))

class SwitchInput(widgets.CheckboxInput):
    def __init__(self, on_label, off_label, inline=False, **kwargs):
        self.on_label = on_label
        self.off_label = off_label
        self.inline = inline
        super(SwitchInput, self).__init__(**kwargs)

    def render(self, name, value, attrs=None):
        if attrs is None:
            attrs = {}
        if 'class' not in attrs:
            attrs['class'] = 'switch inline' if self.inline else 'switch'
        return mark_safe(render_to_string('future/forms/widgets/switch.html', {
            'name': name,
            'value': value,
            'off_label': self.off_label,
            'on_label': self.on_label,
            'inline': self.inline,
            'attrs': flatatt(attrs),
        }))

# mainly used to hack the ordered multi field in the collab workflow settings page
class ReadOnlySpan(widgets.Widget):
    def __init__(self, inner_text='', attrs=None):
        super(ReadOnlySpan, self).__init__(attrs)
        self.inner_text = inner_text

    def render(self, name, value, attrs=None):
        span_class = ''
        if 'class' in self.attrs:
            span_class = self.attrs['class']
        return mark_safe(u'<span class="{}">{}</span>'.format(span_class, self.inner_text))

class DependentCheckboxes(widgets.MultiWidget):
    # TODO Make this work with switches as well as checkboxes
    template_name = 'ui/dependent-choices.html'

    def __init__(self, choices):
        self.choices = choices
        super(DependentCheckboxes, self).__init__(
            [widgets.CheckboxInput() for choice in choices])

    def decompress(self, value):
        saw_value = False

        rv = []

        for choice_value, choice_label in reversed(self.choices):
            if choice_value == value or saw_value:
                rv.append(True)
                saw_value = True
            else:
                rv.append(False)
        rv.reverse()
        return rv

    def get_context(self, name, value, attrs):
        # We handle the required attribute specially.  Don't make the
        # checkboxes required.  Instead make the first checkbox checked and
        # disabled.
        required = attrs['required']
        attrs['required'] = False

        context = super(DependentCheckboxes, self).get_context(
            name, value, attrs)

        self.add_checked_to_subwidgets(context['widget']['subwidgets'], value)
        if required:
            context['widget']['subwidgets'][0]['attrs'].update({
                'disabled': 'disabled',
                'checked': 'checked'
            })


        context['widget']['subwidgets_and_labels'] = [
            (choice[1], subwidget)
            for choice, subwidget in zip(self.choices, context['widget']['subwidgets'])
        ]
        return context

    def add_checked_to_subwidgets(self, subwidgets, value):
        saw_value = False
        for choice, widget in reversed(zip(self.choices, subwidgets)):
            if choice[0] == value or saw_value:
                widget['attrs']['checked'] = 'checked'
                saw_value = True

__all__ = [
    'AmaraRadioSelect', 'SearchBar', 'ContentHeaderSearchBar',
    'AmaraFileInput', 'AmaraClearableFileInput', 'UploadOrPasteWidget',
    'AmaraImageInput', 'SwitchInput', 'ReadOnlySpan', 'DependentCheckboxes'
]
