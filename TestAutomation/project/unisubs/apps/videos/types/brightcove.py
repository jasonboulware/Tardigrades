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
import urlparse

import requests

from vidscraper.errors import Error as VidscraperError
from base import VideoType, VideoTypeError
from django.conf import settings
from django.utils.html import strip_tags

from externalsites import brightcove
import externalsites

BRIGHTCOVE_API_KEY = getattr(settings, 'BRIGHTCOVE_API_KEY', None)
BRIGHTCOVE_API_SECRET = getattr(settings, 'BRIGHTCOVE_API_SECRET' , None)

# We need to support 2 different schemes for brightcove URLs:
#
#  - The original style where we would embed a brightcove player URL, and look
#    for the bctid param
#  - The newer style where it's an akamaihd link, with a videoId query param
#
# We create 2 different classes to handle this, each one handles one style of
# URL

class OldStyleBrightcoveVideoMatcher(object):
    """
    Match legacy brightcove URLs,

    These were links to one of the brightcove players.
    """

    REGEXES = [
        r'http://[\w_-]+.brightcove.com/',
        r'http://bcove.me/[\w_-]+',
    ]
    REGEXES = [re.compile(x) for x in REGEXES]

    def matches_video_url(self, url):
        for r in self.REGEXES:
            if bool(r.match(url)):
                return True
        from videos.models import VideoTypeUrlPattern
        for pattern in VideoTypeUrlPattern.objects.patterns_for_type('C'):
            if url.find(pattern.url_pattern) == 0 and url.find('bctid') > 0:
                return True
        return False

    def extract_brightcove_id(self, url):
        parsed = urlparse.urlparse(url)
        query = urlparse.parse_qs(parsed.query)
        path_parts = parsed.path.split("/")
        return self._find_brightcode_id(url, 'bctid', query, path_parts)

    def _find_brightcode_id(self, url, name, query, path_parts):
        if name in query:
            return query[name][0]
        for part in path_parts:
            if part.startswith(name):
                return part[len(name):]
        raise ValueError("cant find %s in %s" % (name, url))

class MP4BrightcoveVideoMatcher(object):
    """
    Match brightcove MP4 links
    """

    def matches_video_url(self, url):
        # There isn't a fool-proof way to identify brightcove videos, since
        # they're essentially just links to MP4 files.  Hopfully, using a
        # combination of the domain name and which query params are present
        # will work okay in practice
        parsed = urlparse.urlparse(url)
        query = urlparse.parse_qs(parsed.query)
        return (
            parsed.netloc.endswith('.akamaihd.net') and
            set(query.keys()) == set(['videoId', 'pubId']))

    def extract_brightcove_id(self, url):
        parsed = urlparse.urlparse(url)
        query = urlparse.parse_qs(parsed.query)
        return query['videoId'][0]

def get_brightcove_publisher_id(url):
    parsed = urlparse.urlparse(url)
    query = urlparse.parse_qs(parsed.query)
    try:
        return query['pubId'][0]
    except KeyError, IndexError:
        return None

ALL_MATCHERS = [
    OldStyleBrightcoveVideoMatcher(),
    MP4BrightcoveVideoMatcher(),
]

class BrightcoveVideoType(VideoType):

    abbreviation = 'C'
    name = 'Brightcove'
    site = 'brightcove.com'

    def __init__(self, url):
        self.url = self._resolve_url_redirects(url)
        for matcher in ALL_MATCHERS:
            if matcher.matches_video_url(self.url):
                self.brightcove_id = matcher.extract_brightcove_id(self.url)
                break
        else:
            raise ValueError("No brightcove matcher for {}".format(self.url))

    def _resolve_url_redirects(self, url):
        return requests.head(url, allow_redirects=True).url

    def get_direct_url(self, prefer_audio=False):
        return self.url

    @property
    def video_id(self):
        return self.brightcove_id

    @classmethod
    def matches_video_url(cls, url):
        return any(matcher.matches_video_url(url) for matcher in ALL_MATCHERS)

    def set_values(self, video, user, team, video_url):
        publisher_id = get_brightcove_publisher_id(video_url.url)
        if team and publisher_id:
            try:
                account = (
                    externalsites.models.BrightcoveCMSAccount.objects
                    .for_owner(team)
                    .filter(publisher_id=publisher_id)
                    .get())
                self.set_values_from_account(video, account)
            except externalsites.models.BrightcoveAccount.DoesNotExist:
                pass

    def set_values_from_account(self, video, account):
        try:
            video_info = brightcove.get_video_info(
                account.publisher_id, account.client_id,
                account.client_secret, self.brightcove_id)
        except brightcove.BrightcoveAPIError, e:
            return
        if not video.title:
            video.title = video_info["title"]
        if not video.description:
            video.description = video_info["description"]
        if not video.thumbnail:
            video.thumbnail = video_info["thumbnail"]
        if not video.duration:
            video.duration = int(video_info["duration_ms"]) / 1000    # convert from ms to s
