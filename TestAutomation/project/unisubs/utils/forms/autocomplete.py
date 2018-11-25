# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
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

from django import forms

class AutocompleteTextInput(forms.TextInput):
    def __init__(self, *args, **kwargs):
        extra_fields = kwargs.pop('extra_fields', None)
        super(AutocompleteTextInput, self).__init__(*args, **kwargs)
        self.attrs['autocomplete'] = 'off'
        self.attrs['class'] = 'autocomplete-textbox'
        if extra_fields:
            self.attrs['data-autocomplete-extra-fields'] = extra_fields

    def set_autocomplete_url(self, url):
        self.attrs['data-autocomplete-url'] = url
