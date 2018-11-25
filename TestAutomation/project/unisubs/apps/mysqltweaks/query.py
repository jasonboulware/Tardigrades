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

"""mysqltweaks.query -- QuerySet subclass that works with our MySQL tweaks."""

from django.db.models import query

class QuerySet(query.QuerySet):
    def __init__(self, *args, **kwargs):
        super(QuerySet, self).__init__(*args, **kwargs)
        self.query.force_index = None

    def force_index(self, index):
        clone = self._clone()
        clone.query.force_index = index
        return clone

    def _clone(self, *args, **kwargs):
        clone = super(QuerySet, self)._clone(*args, **kwargs)
        clone.query.force_index = self.query.force_index
        return clone
