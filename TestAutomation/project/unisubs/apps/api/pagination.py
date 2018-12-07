# Amara, universalsubtitles.org
#
# Copyright (C) 2015 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program.  If not, see http://www.gnu.org/licenses/agpl-3.0.html.

"""Implement pagination.

This module has a bunch of code to overrides the default paginate_queryset()
method to use offset/limit based pagination instead of page based pagination.

This will get much simpler  once we switch to django-rest-framework 3.1 which
has built-in support for this.
"""

from collections import OrderedDict

from rest_framework import pagination
from rest_framework.response import Response

class AmaraPagination(pagination.LimitOffsetPagination):
    default_limit = 20
    max_limit = 100

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('meta', OrderedDict([
                ('previous', self.get_previous_link()),
                ('next', self.get_next_link()),
                ('offset', self.offset),
                ('limit', self.limit),
                ('total_count', self.count),
            ])),
            ('objects', data),
        ]))
