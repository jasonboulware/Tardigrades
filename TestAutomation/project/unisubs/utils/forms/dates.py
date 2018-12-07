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

"""utils.forms.dates -- Date-related form code."""

from datetime import datetime, date

from django import forms
from django.utils.translation import ugettext_lazy as _

from utils import dates

class MonthChoiceField(forms.ChoiceField):
    DATE_FORMAT = '%Y-%m'
    DATE_LABEL_FORMAT = '%B %Y'

    def __init__(self, start=None, count=12, empty_label=_('Select a month'),
                 *args, **kwargs):
        choices = self.make_choices(start, count, empty_label)
        super(MonthChoiceField, self).__init__(choices=choices, *args, **kwargs)

    def make_choices(self, start, count, empty_label):
        rv = []
        if empty_label:
            rv.append(('', empty_label))
        if start is None:
            start = date.today()
        d = dates.month_start(start)
        for i in xrange(count):
            rv.append((d.strftime(self.DATE_FORMAT),
                       d.strftime(self.DATE_LABEL_FORMAT)))
            d = dates.dec_month(d)
        return rv

    def clean(self, value):
        value = super(MonthChoiceField, self).clean(value)
        if value:
            try:
                return datetime.strptime(value, self.DATE_FORMAT).date()
            except ValueError:
                raise forms.ValidationError(_('Invalid date format'))
        else:
            return None
