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
import re
import logging
from urlparse import urlparse

from base import VideoType
from externalsites import google
from utils.taskqueue import job
import externalsites
logger = logging.getLogger(__name__)

class YoutubeVideoType(VideoType):

    _url_patterns = [re.compile(x) for x in [
        r'youtube.com/.*?v[/=](?P<video_id>[\w-]+)',
        r'youtu.be/(?P<video_id>[\w-]+)',
    ]]

    HOSTNAMES = ( "youtube.com", "youtu.be", "www.youtube.com",)

    abbreviation = 'Y'
    name = 'Youtube'
    site = 'youtube.com'

    # changing this will cause havock, let's talks about this first
    URL_TEMPLATE = 'http://www.youtube.com/watch?v=%s'

    CAN_IMPORT_SUBTITLES = True

    VIDEOID_MAX_LENGTH = 11
    MAX_ACCOUNTS_TO_TRY = 10

    def __init__(self, url):
        self.url = url
        self.videoid = self._get_video_id(self.url)

    @property
    def video_id(self):
        return self.videoid

    def convert_to_video_url(self):
        return 'http://www.youtube.com/watch?v=%s' % self.video_id

    @classmethod
    def matches_video_url(cls, url):
        hostname = urlparse(url).netloc
        return (hostname in YoutubeVideoType.HOSTNAMES and
                any(pattern.search(url) for pattern in cls._url_patterns))

    def get_direct_url(self, prefer_audio=False):
        if prefer_audio:
            return google.get_direct_url_to_audio(self.video_id)
        else:
            return google.get_direct_url_to_video(self.video_id)

    def get_video_info(self, video, user, team, video_url):
        incomplete = False
        if not hasattr(self, '_video_info'):
            if team:
                accounts = externalsites.models.YouTubeAccount.objects.for_team_or_synced_with_team(team)
            elif user:
                accounts = externalsites.models.YouTubeAccount.objects.for_owner(user)
            else:
                accounts = externalsites.models.YouTubeAccount.objects.none()
            try:
                self._video_info = google.get_video_info(self.video_id, accounts[:YoutubeVideoType.MAX_ACCOUNTS_TO_TRY])
            except google.APIError:
                if len(accounts) > YoutubeVideoType.MAX_ACCOUNTS_TO_TRY:
                    accounts_pks = map(lambda x: x.pk, accounts[YoutubeVideoType.MAX_ACCOUNTS_TO_TRY:])
                    get_set_values_background.enqueue_in(
                        2, self.video_id, accounts_pks, video.pk,
                        video_url.pk)
                    incomplete = True
                    self._video_info = None
                else:
                    raise
        return self._video_info, incomplete

    @classmethod
    def complete_set_values(cls, video, video_url, video_info):
        if not video.title:
            video.title = video_info.title
        if not video.description:
            video.description = video_info.description
        video.duration = video_info.duration
        if not video.thumbnail:
            video.thumbnail = video_info.thumbnail_url
        if video_url is not None:
            cls.set_owner_username(video, video_url, video_info)

    def set_values(self, video, user, team, video_url):
        try:
            video_info, incomplete = self.get_video_info(video, user, team, video_url)
        except google.APIError:
            return
        if not incomplete:
            self.complete_set_values(video, video_url, video_info)
        return incomplete

    @classmethod
    def set_owner_username(cls, video, video_url, video_info):
        if video_url.owner_username is None and video_info.channel_id is not None:
            video_url.owner_username = video_info.channel_id
            video_url.save()

    @classmethod
    def url_from_id(cls, video_id):
        return YoutubeVideoType.URL_TEMPLATE % video_id

    @classmethod
    def _get_video_id(cls, video_url):
        for pattern in cls._url_patterns:
            match = pattern.search(video_url)
            video_id = match and match.group('video_id')
            if bool(video_id):
                return video_id[:YoutubeVideoType.VIDEOID_MAX_LENGTH]
        raise ValueError("Unknown video id")

@job
def get_set_values_background(video_id, accounts_pks, video_pk, video_url_pk):
    from django.db import models
    from videos.models import Video, VideoUrl
    from externalsites.models import YouTubeAccount
    try:
        video = Video.objects.get(id=video_pk)
        video_url = VideoUrl.objects.get(id=video_url_pk)
        accounts = list(YouTubeAccount.objects.filter(id__in=accounts_pks))
        video_info = google.get_video_info(video_id, accounts)
        YoutubeVideoType.complete_set_values(video,
                                             video_url,
                                             video_info)
    except models.ObjectDoesNotExist, e:
        return
    except Exception, e:
        logger.error("No values available for video " + video_id)
    video.update_search_index()
    video.save()
