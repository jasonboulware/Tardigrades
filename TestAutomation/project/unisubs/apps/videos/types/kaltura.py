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

from urlparse import urlparse

from videos.types.base import VideoType

def get_kaltura_id(url):
    path_parts = urlparse(url).path.split("/")
    try:
        entry_id_index = path_parts.index('entryId')
    except ValueError:
        return None
    try:
        return path_parts[entry_id_index+1]
    except IndexError:
        return None

class KalturaVideoType(VideoType):

    abbreviation = 'K'
    name = 'Kaltura'   
    
    @classmethod
    def matches_video_url(cls, url):
        url = cls.format_url(url)
        parsed = urlparse(url)
        return parsed.netloc.endswith("kaltura.com") and get_kaltura_id(url)

    # FIXME we should probably just use video_id like all the other video
    # types
    def kaltura_id(self):
        return get_kaltura_id(self.url)
