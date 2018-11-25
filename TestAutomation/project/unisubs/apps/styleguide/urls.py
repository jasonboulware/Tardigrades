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

from __future__ import absolute_import

from django.conf.urls import url

from styleguide import views

urlpatterns = [
    url(r'^$', views.home, name='styleguide'),
    url(r'^member-search$', views.member_search, name='member_search'),
    url(r'^filter-box$', views.filter_box, name='filter-box'),
    url(r'^(?P<section_id>[\w-]+)$', views.section, name='section'),
]
