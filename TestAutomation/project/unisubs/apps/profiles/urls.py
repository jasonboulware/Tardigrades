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

from profiles import views
import externalsites.views


urlpatterns = [
    url(r'^account/$', views.account, name='account'),
    url(r'^edit/$', views.edit, name='edit'),
    url(r'^dashboard/$', views.dashboard, name='dashboard'),
    url(r'^router/$', views.rpc_router, name='rpc_router'),
    url(r'^router/api/$', views.rpc_router.api, name='rpc_api'),
    url(r'^send_message/$', views.send_message, name='send_message'),
    url(r'^edit_avatar/$', views.edit_avatar, name='edit_avatar'),
    url(r'^remove_avatar/$', views.remove_avatar, name='remove_avatar'),
    url(r'^profile/(?P<user_id>.+)/$', views.profile, name='profile'),
    url(r'^videos/(?P<user_id>.+)/$', views.videos, name='videos'),
    url(r'^generate-api-key/$', views.generate_api_key,
        name='generate-api-key'),
    url(r'^add-third-party/$', views.add_third_party, name='add-third-party'),
    url(r'^remove-third-party/(?P<account_type>\w+)/(?P<account_id>[0-9]+)/$',
        views.remove_third_party, name='remove-third-party'),
]

# settings views that are handled by other apps
urlpatterns += [
    url(r'^sync/$', externalsites.views.user_profile_sync_errors_tab,
        name='profile_sync_externalsites'),
]
