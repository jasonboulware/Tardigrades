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

"""Extends the django Paginator class to work with amara """

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

class AmaraPaginator(Paginator):
    def get_page(self, request):
        page = request.GET.get('page')
        try:
            page = self.page(page)
        except PageNotAnInteger:
            page = self.page(1)
        except EmptyPage:
            page = self.page(self.num_pages)
        self.add_links_to_page(page, request)
        return page

    def add_links_to_page(self, page, request):
        query = request.GET.copy()
        page.first_page_link = self.make_page_link(1, query)
        page.last_page_link = self.make_page_link(self.num_pages, query)
        if page.has_previous():
            page.previous_page_link = self.make_page_link(
                page.previous_page_number(), query)
        else:
            page.previous_page_link = None
        if page.has_next():
            page.next_page_link = self.make_page_link(page.next_page_number(),
                                                      query)
        else:
            page.next_page_link = None

    def make_page_link(self, page_number, query):
        query['page'] = page_number
        return '?' + query.urlencode()

class AmaraPaginatorFuture(Paginator):
    """Version of the amara paginator for the future API.  Once we switch
    over, this can replace the current one
    """
    def get_page(self, request):
        page = request.GET.get('page')
        try:
            page = self.page(page)
        except PageNotAnInteger:
            page = self.page(1)
        except EmptyPage:
            page = self.page(self.num_pages)
        self.add_links_to_page(page, request)
        return page

    def add_links_to_page(self, page, request):
        query = request.GET.copy()

        start_page = max(1, min(page.number - 2, self.num_pages - 4))
        end_page = min(start_page + 5, self.num_pages)

        page.nearest_page_links = [
            (i, self.make_page_link(i, query))
            for i in range(start_page, end_page + 1)
        ]
        page.first_page_link = self.make_page_link(1, query)
        page.last_page_link = self.make_page_link(self.num_pages, query)

    def make_page_link(self, page_number, query):
        query['page'] = page_number
        return '?' + query.urlencode()

    def make_next_previous_page_links(self, page, request):
        query = request.GET.copy()
        next_url = self.make_page_link(page.number+1, query) if page.number < self.num_pages else ''
        prev_url = self.make_page_link(page.number-1, query) if page.number > 1 else ''
        return (next_url, prev_url)

    def get_context(self, request):
        page = self.get_page(request)
        next_page, prev_page = self.make_next_previous_page_links(page, request)
        return {
            'paginator': self,
            'page': page,
            'next': next_page,
            'prev': prev_page,
        }
