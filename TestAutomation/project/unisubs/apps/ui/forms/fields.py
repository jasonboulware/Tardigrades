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

import json

from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe, SafeUnicode
from django.utils.translation import ugettext_lazy as _
from django import forms
from django.forms import fields as django_fields
from django.forms import widgets as django_widgets

from utils import translation
from ui.forms import widgets

class HelpTextList(SafeUnicode):
    """
    Help text displayed as a bullet list
    """
    def __new__(cls, *items):
        output = []
        output.append(u'<ul class="helpList">')
        for item in items:
            output.extend([u'<li>', unicode(item), u'</li>'])
        output.append(u'</ul>')
        return SafeUnicode.__new__(cls, u''.join(output))

class AmaraChoiceFieldMixin(object):
    """
    choice_help_text is a dictionary of value:help_text entries
    -- can be used for example if you want all choices of a radio button group
       to have help texts individually

    dynamic_choice_help_text is also a dictionary of value:help_text entries
    -- use this is if you want a selector's help text to change depending on which 
       option is selected
    """
    def __init__(self, allow_search=True, filter=False, max_choices=None,
                 choice_help_text=None, dynamic_choice_help_text=None,
                 *args, **kwargs):
        self.filter = filter
        if choice_help_text:
            self.choice_help_text = dict(choice_help_text)
        else:
            self.choice_help_text = {}

        if dynamic_choice_help_text:
            self.dynamic_choice_help_text = dict(dynamic_choice_help_text)
        else:
            self.dynamic_choice_help_text = {}

        super(AmaraChoiceFieldMixin, self).__init__(*args, **kwargs)
        if not allow_search:
            self.set_select_data('nosearchbox')
        if max_choices:
            self.set_select_data('max-allowed-choices', max_choices)

        if self.dynamic_choice_help_text:
            self.set_select_data('dynamic-choice-help-texts', self.dynamic_choice_help_text)

    def _get_choices(self):
        return self._choices

    def _set_choices(self, value):
        self._choices = list(value)
        self._setup_widget_choices()

    choices = property(_get_choices, _set_choices)

    def _setup_widget_choices(self):
        null_choice = None
        widget_choices = []
        for choice in self.choices:
            if not choice[0]:
                null_choice = choice[1]
        self.widget.choices = [
            self.make_widget_choice(c)
            for c in self.choices
        ]
        if null_choice:
            self.set_select_data('placeholder', null_choice)
            self.set_select_data('clear', 'true')
        else:
            self.unset_select_data('placeholder')
            self.set_select_data('clear', 'false')

    def make_widget_choice(self, choice):
        name, label = choice

        help_text = self.choice_help_text.get(name)
        if help_text:
            label = u''.join([
                force_unicode(label),
                mark_safe(
                    '<div class="helpBlock helpBlock-radio">{}</div>'.format(
                        force_unicode(conditional_escape(help_text))))
            ])
        return (name, label)

    def widget_attrs(self, widget):
        if isinstance(widget, forms.Select):
            widget_class = 'select'
            if self.dynamic_choice_help_text:
                widget_class += ' dynamicHelpText'

            if self.filter:
                widget_class += ' selectFilter'
            
            return { 'class': widget_class }
        else:
            return {}

    def set_select_data(self, name, value=1):
        name = 'data-' + name
        if isinstance(self.widget, forms.Select):
            if isinstance(value, (list, dict)):
                value = json.dumps(value)
            self.widget.attrs[name] = value

    def unset_select_data(self, name):
        name = 'data-' + name
        if isinstance(self.widget, forms.Select):
            self.widget.attrs.pop(name, None)

class AmaraChoiceField(AmaraChoiceFieldMixin, forms.ChoiceField):
    pass

class AmaraMultipleChoiceField(AmaraChoiceFieldMixin,
                               forms.MultipleChoiceField):
    pass

class LanguageFieldMixin(AmaraChoiceFieldMixin):
    """
    Used to create a language selector

    This is implemented as a mixin class so it can be used for both single and
    multiple selects.

    Args:
        options: whitespace separated list of different option types.  The
            following types are supported:
            - null: allow no choice
            - my: "My languages" optgroup
            - popular: "Popular languages" optgroup
            - all: "All languages" optgroup
            - dont-set: The "Don't set" option.  Use this when you want to
              allow users to leave the value unset, but only if they actually
              select that option rather than just leaving the initial value
              unchanged.
            - unset: The "Unset" option.  Work's the same as "Don't set", but
              with a different label.
    """

    def __init__(self, options="null my popular all",
                 placeholder=_("Select language"), *args, **kwargs):
        super(LanguageFieldMixin, self).__init__(*args, **kwargs)
        self.set_options(options)
        if "null" in options:
            self.set_placeholder(placeholder)

    def set_options(self, options):
        self.set_select_data('language-options', options)
        choices = translation.get_language_choices(flat=True)
        option_list = options.split()
        if 'dont-set' in option_list:
            choices.append(('null', _('Don\'t set')))
        elif 'unset' in option_list:
            choices.append(('null', _('Unset')))
        self.choices = choices

    def exclude(self, languages):
        self.set_select_data('exclude', json.dumps(languages))
        self.choices = [
            c for c in self.choices if c[0] not in languages
        ]

    def limit_to(self, languages):
        self.set_select_data('limit-to', json.dumps(languages))
        self.choices = [
            c for c in self.choices if c[0] in languages
        ]

    def set_flat(self, enabled):
        if enabled:
            self.set_select_data('flat', 1)
        else:
            self.unset_select_data('flat')

    def set_placeholder(self, placeholder):
        self.set_select_data('placeholder', placeholder)

    def _setup_widget_choices(self):
        pass

    def clean(self, value):
        value = super(LanguageFieldMixin, self).clean(value)
        if value == 'null':
            value = ''
        return value

class LanguageField(LanguageFieldMixin, forms.ChoiceField):
    widget = widgets.AmaraLanguageSelect

class MultipleLanguageField(LanguageFieldMixin, forms.MultipleChoiceField):
    widget = widgets.AmaraLanguageSelectMultiple

class SearchField(forms.CharField):
    widget = widgets.SearchBar

    def __init__(self, label=_('Search for videos'), **kwargs):
        kwargs['label'] = ''
        super(SearchField, self).__init__(**kwargs)
        if label:
            self.widget.attrs['placeholder'] = label

class UploadOrPasteField(forms.Field):
    widget = widgets.UploadOrPasteWidget

'''
By default, when validation of this field fails, the selected options are not retained.
This can be remedied by retrieving the POST data from the form and using it with 
_set_initial_selections() method to set pre-selected values
'''
class MultipleAutoCompleteField(AmaraMultipleChoiceField):
    widget = django_widgets.SelectMultiple

    def __init__(self, *args, **kwargs):
        super(MultipleAutoCompleteField, self).__init__(*args, **kwargs)

        # We set the classname for the JS script that's responsible for handling the initial data
        widget_classes = self.widget.attrs['class']
        self.widget.attrs['class'] = widget_classes + " multipleAutoCompleteSelect"
        
        self.valid_queryset = None

    def set_valid_queryset(self, queryset):
        self.valid_queryset = queryset

    def set_ajax_autocomplete_url(self, url):
        self.set_select_data('ajax', url)

    '''
    <selections> must be a list of JSON objects in the format select2 library expects:
        'id' - the value of the selected option
        'text' - the display text of the selected option

    Use this method if you want the form to have pre-loaded selections
    -- useful if you want to retain the value of this field after a failed validation
       (see teams.forms:InviteForm::usernames field for an example)
    '''
    def _set_initial_selections(self, selections):
        self.set_select_data('initial-selections', selections)

    '''
    This is not really a useful validation approach, override this to 
    be more specific on what is actually being validated
    '''
    def clean(self, values):
        if self.valid_queryset is not None:
            qs = self.valid_queryset.filter(username__in=values)
            if len(qs) != len(values):
                raise forms.validationError(_('Not all users are part of the valid search space!'))
        
        return values

class AmaraImageField(forms.ImageField):
    widget = widgets.AmaraImageInput

    def __init__(self, preview_size=None, **kwargs):
        self.preview_size = preview_size
        super(AmaraImageField, self).__init__(**kwargs)
        self.widget.preview_size = preview_size

class DependentBooleanField(forms.MultiValueField):
    """
    Displays a several checkboxes, each one depending on the previous.

    See the multiField styleguide entry for how we use this
    """

    def __init__(self, choices, **kwargs):
        self.choices = choices
        fields = [
            django_fields.BooleanField(required=False)
            for c in choices
        ]
        widget = widgets.DependentCheckboxes(choices)
        super(DependentBooleanField, self).__init__(
            widget=widget, fields=fields, require_all_fields=False, **kwargs)

    def compress(self, data_list):
        for choice, checked in reversed(zip(self.choices, data_list)):
            if checked:
                return choice[0]
        if self.required:
            # required fields make the first choice always checked and
            # disabled.  That means we won't see it in the POST data, but
            # we should return it here.
            return self.choices[0][0]
        return None

__all__ = [
    'AmaraChoiceField', 'AmaraMultipleChoiceField', 'LanguageField',
    'MultipleLanguageField', 'SearchField', 'HelpTextList',
    'UploadOrPasteField', 'AmaraImageField', 'MultipleAutoCompleteField',
    'DependentBooleanField',
]

