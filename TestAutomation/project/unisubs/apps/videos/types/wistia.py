# Amara, universalsubtitles.org
# 
# Copyright (C) 2012 Participatory Culture Foundation
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

from vidscraper.sites import wistia
from vidscraper.errors import Error as VidscraperError
from base import VideoType, VideoTypeError
from django.conf import settings
from django.utils.html import strip_tags

# wistia.WISTIA_API_KEY = getattr(settings, 'WISTIA_API_KEY')
# wistia.WISTIA_API_SECRET = getattr(settings, 'WISTIA_API_SECRET')

class WistiaVideoType(VideoType):

    abbreviation = 'W'
    name = 'Wistia.com'   
    site = 'wistia.com'
    linkurl = None

    def __init__(self, url):
        self.url = url
        self.videoid = self._get_wistia_id(url)
        # not sure why this is being done, it breaks external URL
        self.linkurl = url.replace('/embed/', '/medias/')
        try:
            self.shortmem = wistia.get_shortmem(url)
        except VidscraperError, e:
            # we're not raising an error here because it 
            # disallows us from adding private Wistia videos.
            pass
        
    @property
    def video_id(self):
        return self.videoid
    
    def convert_to_video_url(self):
        return "https://fast.wistia.net/embed/iframe/%s" % self.videoid

    @classmethod
    def matches_video_url(cls, url):
        return bool(wistia.WISTIA_REGEX.match(url))

    def set_values(self, video_obj, user, team, video_url):
        try:
            video_obj.thumbnail = wistia.get_thumbnail_url(self.url, self.shortmem) or ''
            video_obj.small_thumbnail = wistia.get_small_thumbnail_url(self.url, self.shortmem) or ''
            video_obj.title = wistia.scrape_title(self.url, self.shortmem)
            video_obj.description = strip_tags(wistia.scrape_description(self.url, self.shortmem))
        except Exception:
            # in case the Wistia video is private.
            pass
    
    def _get_wistia_id(self, video_url):
        return wistia.WISTIA_REGEX.match(video_url).groupdict().get('video_id') 
