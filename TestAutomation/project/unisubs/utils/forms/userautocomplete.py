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
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from .autocomplete import AutocompleteTextInput
from auth.models import CustomUser as User
from utils.text import fmt

class UserAutocompleteField(forms.CharField):
    default_error_messages = {
        'not-found': _(u'User not found'),
        'invalid': _(u'Invalid user choice'),
    }

    def __init__(self, *args, **kwargs):
        if 'widget' not in kwargs:
            kwargs['widget'] = AutocompleteTextInput
        super(UserAutocompleteField, self).__init__(*args, **kwargs)
        self.queryset = User.objects.all()

    def set_autocomplete_url(self, url):
        self.widget.set_autocomplete_url(url)

    def clean(self, value):
        value = super(UserAutocompleteField, self).clean(value)
        if not value:
            return None
        try:
            return self.queryset.get(username=value)
        except User.DoesNotExist:
            if not User.objects.filter(username=value).exists():
                raise forms.ValidationError(self.error_messages['not-found'])
            else:
                raise forms.ValidationError(self.error_messages['invalid'])

def autocomplete_user_view(request, queryset, limit=10):
    query = request.GET.get('query')
    # put exact matches first
    users = list(queryset.filter(username=query))
    limit -= len(users)
    # add non-exact matches next
    users.extend(
        queryset.filter(Q(username__icontains=query)|
                        Q(first_name__icontains=query)|
                        Q(last_name__icontains=query)|
                        Q(full_name__icontains=query))
        .exclude(username=query)[:limit]
    )
    data = [
        {
            'value': user.username,
            'label': fmt(_('%(username)s (%(full_name)s)'),
                         username=user.username,
                         full_name=unicode(user)),
        }
        for user in users
    ]

    return HttpResponse(json.dumps(data), content_type='application/json')
