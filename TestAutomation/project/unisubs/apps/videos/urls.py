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

from videos import views

urlpatterns = [
    url(r'^watch/$', views.watch_page, name='watch_page'),
    url(r'^watch/featured/$', views.featured_videos, name='featured_videos'),
    url(r'^watch/latest/$', views.latest_videos, name='latest_videos'),
    url(r'^search/', views.search, name='search'),
    url(r'^router/$', views.rpc_router, name='rpc_router'),
    url(r'^router/api/$', views.rpc_router.api, name='rpc_api'),
    url(r'^subscribe_to_updates/$', views.subscribe_to_updates, name='subscribe_to_updates'),
    url(r'^upload_subtitles/$', views.upload_subtitles, name='upload_subtitles'),
    url(r'^create/$', views.create, name='create'),
    url(r'^activities/(?P<video_id>(\w|-)+)/$', views.activity, name='activity'),
    url(r'^stop_notification/(?P<video_id>(\w|-)+)/$', views.stop_notification, name='stop_notification'),
    url(r'^rollback/(?P<pk>\d+)/$', views.rollback, name='rollback'),
    url(r'^diffing/(?P<pk>\d+)/(?P<second_pk>\d+)/$', views.diffing, name='diffing'),
    url(r'^video_url_make_primary/$', views.video_url_make_primary, name='video_url_make_primary'),
    url(r'^video_url_create/$', views.video_url_create, name='video_url_create'),
    url(r'^video_url_remove/$', views.video_url_remove, name='video_url_remove'),
    url(r'^search-urls/$', views.url_search, name='url-search'),
    url(r'^(?P<video_id>(\w|-)+)/debug/$', views.video_debug, name='video_debug'),
    url(r'^(?P<video_id>(\w|-)+)/reset_metadata/$', views.reset_metadata, name='reset_metadata'),
    url(r'^(?P<video_id>(\w|-)+)/set-original-language/$', views.set_original_language, name='set_original_language'),
    url(r'^(?P<video_id>(\w|-)+)/$', views.redirect_to_video),
    url(r'^(?P<video_id>(\w|-)+)/create_subtitles/$', views.create_subtitles, name='create_subtitles'),
    url(r'^(?P<video_id>(\w|-)+)/info/$', views.video, name='video'),
    url(r'^(?P<video_id>(\w|-)+)/info/(?P<title>[^/]+)/$', views.video, name='video_with_title'),
    url(r'^(?P<video_id>(\w|-)+)/url/(?P<video_url>\d+)/$', views.video, name='video_url'),
    url(r'^(?P<video_id>(\w|-)+)/(?P<lang>[\w\-]+)/(?P<lang_id>[\d]+)/$',
        views.subtitles, name='translation_history'),
    url(r'^(?P<video_id>(\w|-)+)/(?P<lang>[\w\-]+)/(?P<lang_id>[\d]+)/(?P<version_id>[\d]+)/$',
        views.subtitles, name='subtitleversion_detail'),
    url(r'^(?P<video_id>(\w|-)+)/(?P<lang>[\w\-]+)/$', views.legacy_history, name='translation_history_legacy'),
    url(r'(?P<video_id>(\w|-)+)/staff/delete/$', views.video_staff_delete, name='video_staff_delete'),
]
