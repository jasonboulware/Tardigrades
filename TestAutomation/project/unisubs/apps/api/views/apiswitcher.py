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

from functools import update_wrapper
import datetime

from django.conf import settings

class APISwitcherMixin(object):
    """Have a new and deprecated class handle an API View/ViewSet

    To use this:
    - define the View/Viewset as normal, implementing the new API
    - create a subclass APISwitcherMixin added and the following attributes:
        - Deprecated: View/ViewSet to handle the deprecated APi
        - switchover_date: date to switch to the new API by default (int in
          YYYYMMDD form)
    """

    @classmethod
    def as_view(cls, *args, **kwargs):
        old_view = cls.Deprecated.as_view(*args, **kwargs)
        new_view = super(APISwitcherMixin, cls).as_view(
            *args, **kwargs)

        def view(request, *args, **kwargs):
            if cls.should_use_new_api(request):
                return new_view(request, *args, **kwargs)
            else:
                response = old_view(request, *args, **kwargs)
                response['HTTP_X_API_DEPRECATED'] = str(cls.switchover_date)
                return response

        update_wrapper(view, new_view)

        # Give the deprecated class the same name as the new one, so that it
        # appears correct in the API view
        cls.Deprecated.__name__ = cls.__name__

        return view

    def get_view_description(self, html=False):
        func = self.settings.VIEW_DESCRIPTION_FUNCTION
        return func(self.find_view_name_class(), html)

    def get_view_name(self):
        func = self.settings.VIEW_NAME_FUNCTION
        return func(self.find_view_name_class(), getattr(self, 'suffix', None))

    @classmethod
    def find_view_name_class(cls):
        # find the class we should use for get_view_name().  This is the 
        # parent class other than the APISwitcherMixin.
        for klass in cls.__bases__:
            if not issubclass(klass, APISwitcherMixin):
                return klass

    @classmethod
    def should_use_new_api(cls, request):
        if cls.should_always_use_new_view():
            return True
        return cls.api_future_header_value(request) >= cls.switchover_date

    @classmethod
    def api_future_header_value(cls, request):
        try:
            header_val = request.META['HTTP_X_API_FUTURE']
        except KeyError:
            try:
                header_val = request.GET['api-future']
            except KeyError:
                return 0
        # check that the header is in YYYYMMDD format
        if len(header_val) != 8:
            return 0
        try:
            return int(header_val)
        except ValueError:
            return 0

    @classmethod
    def should_always_use_new_view(cls):
        if getattr(settings, 'API_ALWAYS_USE_FUTURE', False):
            return True
        today = datetime.date.today()
        today_val = (today.year * 10000 +
                     today.month * 100 +
                     today.day)
        return today_val >= cls.switchover_date
