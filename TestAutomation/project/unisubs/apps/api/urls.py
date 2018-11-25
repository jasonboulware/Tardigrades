# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
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

from __future__ import absolute_import

from django.conf.urls import url
from rest_framework import routers

from . import views

router = routers.SimpleRouter()
router.register(r'videos', views.videos.VideoViewSet)
router.register(r'videos/(?P<video_id>[\w\d]+)/languages',
                views.subtitles.SubtitleLanguageViewSet,
                base_name='subtitle-language')
router.register(r'videos/(?P<video_id>[\w\d]+)/urls',
                views.videos.VideoURLViewSet, base_name='video-url')
router.register(r'teams', views.teams.TeamViewSet, base_name='teams')
router.register(r'teams/(?P<team_slug>[\w\d\-]+)/members',
                views.teams.TeamMemberViewSet, base_name='team-members')
router.register(r'teams/(?P<team_slug>[\w\d\-]+)/projects',
                views.teams.ProjectViewSet, base_name='projects')
router.register(r'teams/(?P<team_slug>[\w\d\-]+)/tasks',
                views.teams.TaskViewSet, base_name='tasks')
router.register(r'teams/(?P<team_slug>[\w\d\-]+)/applications',
                views.teams.TeamApplicationViewSet,
                base_name='team-application')
router.register(r'teams/(?P<team_slug>[\w\d\-]+)/notifications',
                views.teams.TeamNotificationViewSet,
                base_name='team-notifications')
router.register(r'users', views.users.UserViewSet, base_name='users')
router.register(r'activity', views.activity.ActivityViewSet,
                base_name='activity')

urlpatterns = router.urls + [
    url(r'^$', views.index.index, name='index'),
    url(r'videos/(?P<video_id>[\w\d]+)/activity/$',
        views.activity.VideoActivityView.as_view(), name='video-activity'),
    url(r'^videos/(?P<video_id>[\w\d]+)'
        '/languages/(?P<language_code>[\w-]+)/subtitles/$',
        views.subtitles.SubtitlesView.as_view(), name='subtitles'),
    url(r'^videos/(?P<video_id>[\w\d]+)'
        '/languages/(?P<language_code>[\w-]+)/subtitles/actions/$',
        views.subtitles.Actions.as_view(), name='subtitle-actions'),
    url(r'^videos/(?P<video_id>[\w\d]+)'
        '/languages/(?P<language_code>[\w-]+)/subtitles/notes/$',
        views.subtitles.NotesList.as_view(), name='subtitle-notes'),
    url(r'videos/(?P<video_id>[\w\d]+)/duration',
        views.videos.VideoDurationView.as_view(), name='video-duration'),
    url(r'videos/(?P<video_id>[\w\d]+)/follow',
        views.videos.VideoFollowerView.as_view(), name='video-follow'),
    url(r'^videos/(?P<video_id>[\w\d]+)'
        '/languages/(?P<language_code>[\w-]+)/follow$',
        views.subtitles.LanguageFollowerView.as_view(), name='language-follow'),
    url(r'^teams/(?P<team_slug>[\w\d\-]+)/languages/$',
        views.teams.team_languages, name='team-languages'),
     url(r'teams/(?P<team_slug>[\w\d\-]+)/languages/preferred/',
         views.teams.TeamPreferredLanguagesView.as_view(),
         name='team-languages-preferred'),
     url(r'teams/(?P<team_slug>[\w\d\-]+)/languages/blacklisted/',
         views.teams.TeamBlacklistedLanguagesView.as_view(),
         name='team-languages-blacklisted'),
    url(r'^languages/$', views.languages.languages, name='languages'),
    url(r'^message/$', views.messages.Messages.as_view(), name='messages'),
    url(r'users/(?P<identifier>[^/]+)/activity/$',
        views.activity.UserActivityView.as_view(), name='user-activity'),
    url(r'teams/(?P<slug>[\w\d-]+)/activity/$',
        views.activity.TeamActivityView.as_view(), name='team-activity'),
]
