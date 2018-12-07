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

from django import forms

from auth.models import get_amara_anonymous_user
from styleguide.models import StyleguideData
from utils import enum
from ui.forms import (
    AmaraImageField, AmaraChoiceField, AmaraMultipleChoiceField, SearchField, SwitchInput,
    ContentHeaderSearchBar, DependentBooleanField, AmaraRadioSelect
)
from ui.utils import SplitCTA

class StyleguideForm(forms.Form):
    def __init__(self, request, **kwargs):
        self.user = request.user
        if self.user.is_anonymous():
            self.user = get_amara_anonymous_user()
        super(StyleguideForm, self).__init__(**kwargs)
        self.setup_form()

    # override these in the subclasses to customize form handling
    def setup_form(self):
        pass

    def save(self):
        pass

    def get_styleguide_data(self):
        try:
            return StyleguideData.objects.get(user=self.user)
        except StyleguideData.DoesNotExist:
            return StyleguideData(user=self.user)

class SwitchForm(StyleguideForm):
    choice = forms.BooleanField(label='Visibility', required=False,
                                widget=SwitchInput('Public', 'Private'))
    inline_choice = forms.BooleanField(
        label='Inline Example', required=False,
        widget=SwitchInput('ON', 'OFF', inline=True))

class MultiFieldForm(StyleguideForm):
    animal_color = AmaraChoiceField(choices=[
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('yellow', 'Yellow'),
    ], label='Color')
    animal_species = AmaraChoiceField(choices=[
        ('dog', 'Dog'),
        ('cat', 'Cat'),
        ('horse', 'Horse'),
    ], label='Species')

    role = DependentBooleanField(
        label='Role', required=True, initial='manager', choices=[
            ('admin', 'Admin'),
            ('manager', 'Manager'),
            ('any', 'Any Team Member'),
        ])


    subtitles_public = forms.BooleanField(
        label='Completed', required=False, initial=True,
        widget=SwitchInput('Public', 'Private'))
    drafts_public = forms.BooleanField(
        label='Drafts', required=False,
        widget=SwitchInput('Public', 'Private'))

    translate_time_limit = forms.CharField(label='Translate', initial=2,
                                           widget=forms.NumberInput)
    review_time_limit = forms.CharField(label='Review', initial=1,
                                        widget=forms.NumberInput)
    approval_time_limit = forms.CharField(label='Approval', initial=1,
                                          widget=forms.NumberInput)

    def clean(self):
        if (self.cleaned_data.get('animal_color') == 'yellow' and
                self.cleaned_data.get('animal_species') == 'dog'):
            self.add_error('animal_species', "Dog's can't be yellow!")

class ImageUpload(StyleguideForm):
    thumbnail = AmaraImageField(label='Image', preview_size=(169, 100),
                                help_text=('upload an image to test'),
                                required=False)
    def setup_form(self):
        styleguide_data = self.get_styleguide_data()
        if styleguide_data.thumbnail:
            self.initial = {
                'thumbnail': styleguide_data.thumbnail
            }

    def save(self):
        styleguide_data = self.get_styleguide_data()
        if self.cleaned_data['thumbnail'] == False:
            styleguide_data.thumbnail = None
        else:
            styleguide_data.thumbnail = self.cleaned_data['thumbnail']
        styleguide_data.save()

class DynamicHelpTextForm(StyleguideForm):
    EnumChoices = enum.Enum('EnumChoices', [
        ('CHOICE1', 'First choice'),
        ('CHOICE2', 'Second choice'),
        ('CHOICE3', 'Third choice'),
    ])

    '''need to match the "keys" of the enum members'''
    EnumChoicesHelpText = enum.Enum('EnumChoicesHelpText', [
        ('CHOICE1', 'First help text'),
        ('CHOICE2', 'Second help text'),
        ('CHOICE3', 'Third help text'),
    ])

    ListChoices = [ 
        ('list1', 'First list'),
        ('list2', 'Second list'),
        ('list3', 'Third list'),
    ]

    ListChoicesHelpText = [
        ('list1', 'First list help text'),
        ('list2', 'Second list help text'),
        ('list3', 'Third list help text'),
    ]

    RadioChoices = [
        ('radio1', 'First radio'),
        ('radio2', 'Second radio'),
        ('radio3', 'Third radio'),
    ]

    RadioChoicesHelpText = [
        ('radio1', 'First radio help text'),
        ('radio2', 'Second radio help text'),
        ('radio3', 'Third radio help text'),
    ]

    field_using_enum = AmaraChoiceField(
        choices=EnumChoices.choices(),
        label=('Field using enum'),
        help_text=('1) There needs to be some initial help text for the JS code to replace'),
        dynamic_choice_help_text=EnumChoicesHelpText.choices())

    field_using_list = AmaraChoiceField(
        choices=ListChoices,
        label=('Field using list'),
        help_text=('2) There needs to be some initial help text for the JS code to replace'),
        dynamic_choice_help_text=ListChoicesHelpText)

    field_using_radio = AmaraChoiceField(
        label=('Field using radio buttons'), 
        choices=RadioChoices,
        widget=AmaraRadioSelect(dynamic_choice_help_text=RadioChoicesHelpText,
            dynamic_choice_help_text_initial='3) Radio button groups also need an initial help text. The initial help text is set in the widget')
    )

class ContentHeader(StyleguideForm):
    search = SearchField(label='Search', required=False,
                         widget=ContentHeaderSearchBar)

class FilterBox(StyleguideForm):
    color = AmaraMultipleChoiceField(
        label="Select color", choices=(
            ('plum', 'Plum'),
            ('amaranth', 'Amaranth'),
            ('lime', 'Lime'),
        ))
    shape = forms.CharField(label="Search for shapes")

class SplitButton(StyleguideForm):
    def setup_form(self):
        self.split_button_with_tooltip = \
            SplitCTA('Split button with tooltip', '#',
            main_tooltip='Main Tooltip 1!',
            dropdown_tooltip='Dropdown Tooltip 1!',
            menu_id='splitbutton1',
            dropdown_items=[('Dropdown Item 1', '#'), ('Dropdown Item 2', '#')])

        self.split_button_no_tooltip = \
            SplitCTA('Split button no tooltip', '#',
            menu_id='splitbutton2',
            dropdown_items=[('Dropdown Item 3', '#'), ('Dropdown Item 4', '#')])

        self.split_button_with_icon = \
            SplitCTA('Split button with icon', '#',
            icon='icon-transcribe',
            menu_id='splitbutton3',
            dropdown_items=[('Dropdown Item 5', '#'), ('Dropdown Item 6', '#')])

        self.split_button_full_width = \
            SplitCTA('Split button full width', '#',
            block=True,
            icon='icon-transcribe',
            menu_id='splitbutton4',
            dropdown_items=[('Dropdown Item 7', '#'), ('Dropdown Item 8', '#')])

        self.split_button_disabled = \
            SplitCTA('Split button disabled', '#',
            block=True,
            disabled=True,
            icon='icon-transcribe',
            menu_id='splitbutton5',
            dropdown_items=[('Dropdown Item 9', '#'), ('Dropdown Item 10', '#')])
