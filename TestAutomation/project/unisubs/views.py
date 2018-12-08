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

import logging

from django.http import Http404, HttpResponse
from django.shortcuts import render

from caching.decorators import cache_page
from utils.decorators import staff_member_required
from utils.one_time_data import get_one_time_data
logger = logging.getLogger(__name__)

@cache_page(minutes=60)
def home(request):
    return render(request, 'home.html')

@staff_member_required
def errortest(request):
    foo = 'bar'
    baz = 12345
    try:
        1/0
    except:
        logging.error("Errortest: handled exception", exc_info=True)

    raise AssertionError("Errortest: unhandled exception")

def one_time_url(request, token):
    """
    This is a view to host one-time, time limited URLs, used
    to deliver non-public data to a third party website.
    """
    data = get_one_time_data(token)
    if data is not None:
        response = HttpResponse(data, content_type="text/plain")
        response['Content-Disposition'] = 'attachment'
        return response
    else:
        raise Http404()
