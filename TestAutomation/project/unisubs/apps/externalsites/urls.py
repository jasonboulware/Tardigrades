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

from externalsites import views

urlpatterns = [
    url(r'^resync/(?P<video_url_id>\d+)/(?P<language_code>[\w-]+)/$', views.resync, name='resync'),
    url(r'^youtube-add-account/', views.youtube_add_account,
        name='youtube-add-account'),
    url(r'^vimeo-add-account/', views.vimeo_add_account,
        name='vimeo-add-account'),
    url(r'^vimeo-login-done/', views.vimeo_login_done, name='vimeo-login-done'),
    url(r'^google-callback/', views.google_callback, name='google-callback'),
    url(r'^google-login/', views.google_login, name='google-login'),
    url(r'^google-login-confirm/', views.google_login, {'confirmed': False}, name='google-login-confirm'),

    url(r'^export-subtitles/', views.export_subtitles, name='export-subtitles'),

    url(r'^team-add-external-account/(?P<slug>[-\w]+)', views.team_add_external_account, name='team-add-external-account'),
    url(r'^team-edit-external-account/(?P<slug>[-\w]+)', views.team_edit_external_account, name='team-edit-external-account'),
]
