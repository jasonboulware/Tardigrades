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

from __future__ import absolute_import
import json

from django import forms
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _

from .autocomplete import AutocompleteTextInput
from teams.models import Team

class TeamAutocompleteField(forms.CharField):
    default_error_messages = {
        'not-found': _(u'Team not found'),
        'invalid': _(u'Invalid team choice'),
    }

    def __init__(self, *args, **kwargs):
        if 'widget' not in kwargs:
            kwargs['widget'] = AutocompleteTextInput
        super(TeamAutocompleteField, self).__init__(*args, **kwargs)
        self.queryset = Team.objects.all()

    def set_autocomplete_url(self, url):
        self.widget.set_autocomplete_url(url)

    def clean(self, value):
        value = super(TeamAutocompleteField, self).clean(value)
        if not value:
            return None
        try:
            return self.queryset.get(slug=value)
        except Team.DoesNotExist:
            if not Team.objects.filter(slug=value).exists():
                raise forms.ValidationError(self.error_messages['not-found'])
            else:
                raise forms.ValidationError(self.error_messages['invalid'])

def autocomplete_team_view(request, queryset=None, limit=10):
    if queryset is None:
        queryset = Team.objects.all()
    query = request.GET.get('query')
    # put exact matches first
    teams = list(queryset.filter(slug=query))
    limit -= len(teams)
    # add non-exact matches next
    teams.extend(queryset.filter(slug__icontains=query))
    data = [
        {
            'value': team.slug,
            'label': unicode(team),
        }
        for team in teams
    ]

    return HttpResponse(json.dumps(data), content_type='application/json')
