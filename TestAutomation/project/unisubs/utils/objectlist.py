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

"""Wrapper for the deprecated object_list() function

This should not be used for new code, or even old code really.  The new
ListView class is much better.  But in the meantime this function should keep
the existing views working.
"""

from django.core.paginator import Paginator, InvalidPage
from django.http import Http404
from django.shortcuts import render

def object_list(request, queryset, paginate_by=None, allow_empty=True,
                template_name=None, extra_context=None,
                template_object_name='object'):

    paginator = Paginator(queryset, paginate_by,
                          allow_empty_first_page=allow_empty)
    page = request.GET.get('page', 1)
    try:
        page_number = int(page)
    except ValueError:
        if page == 'last':
            page_number = paginator.num_pages
        else:
            # Page is not 'last', nor can it be converted to an int.
            raise Http404
    try:
        page_obj = paginator.page(page_number)
    except InvalidPage:
        raise Http404

    context = {
            '%s_list' % template_object_name: page_obj.object_list,
            'paginator': paginator,
            'page_obj': page_obj,
            'is_paginated': page_obj.has_other_pages(),
    }
    context.update(extra_context)
    return render(request, template_name, context)

