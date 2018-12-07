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

from django.conf.urls import url

from thirdpartyaccounts import views

urlpatterns = [
    url(r'^facebook_login/(?P<email>[^/]+)/$', views.facebook_login, name='facebook_login'),
    url(r'^facebook_login_confirm/(?P<email>[^/]+)/$', views.facebook_login, {'confirmed': False}, name='facebook_login_confirm_email'),
    url(r'^facebook_login_confirm/$', views.facebook_login, {'confirmed': False, 'email': None}, name='facebook_login_confirm'),
    url(r'^twitter_login/$', views.twitter_login, name='twitter_login'),
    url(r'^twitter_login_done/$', views.twitter_login_done, name='twitter_login_done'),
    url(r'^twitter_login_confirm/$', views.twitter_login, {'confirmed': False}, name='twitter_login_confirm'),
    url(r'^twitter_login_done_confirm/$', views.twitter_login_done, {'confirmed': False}, name='twitter_login_done_confirm'),
]

