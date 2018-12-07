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

from subtitles import views

urlpatterns = [
    url(r'^old-editor/(?P<video_id>[\w]+)/(?P<language_code>[\w-]+)/$', views.old_editor, name='old-editor'),
    url(r'^editor/(?P<video_id>[\w]+)/(?P<language_code>[\w-]+)/$', views.SubtitleEditor.as_view(), name='subtitle-editor'),
    url(r'^editor/(?P<video_id>[\w]+)/(?P<language_code>[\w-]+)/regain',
        views.regain_lock, name='regain_lock'),
    url(r'^editor/(?P<video_id>[\w]+)/(?P<language_code>[\w-]+)/release',
        views.release_lock, name='release_lock'),
    url(r'^editor/tutorial_shown', views.tutorial_shown, name='tutorial_shown'),
    url(r'^editor/set_playback_mode', views.set_playback_mode, name='set_playback_mode'),
    url(r'^(?P<video_id>[\w]+)/(?P<language_code>[\w-]+)(?:/(?P<version_number>[\d]+))?/download/(?P<filename>.+)\.(?P<format>[\w]+)',
        views.download, name='download'),
    url(r'^(?P<video_id>[\w]+)/download/(?P<filename>.+)\.dfxp', views.download_all, name='download_all'),
]
