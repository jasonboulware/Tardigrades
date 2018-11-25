# Amara, universalsubtitles.org
#
# Copyright (C) 2013-2015 Participatory Culture Foundation
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

import subprocess, sys
from videos.types.base import VideoType

import logging
logger= logging.getLogger(__name__)

class Mp3VideoType(VideoType):

    abbreviation = 'M'
    name = 'MP3'

    def get_direct_url(self, prefer_audio=False):
        return self.url

    @classmethod
    def matches_video_url(cls, url):
        return cls.url_extension(url) == 'mp3'

    def set_values(self, video, user, team, video_url):
        cmd = """avprobe -v error -show_format -show_streams "{}" | grep duration= | sed 's/^.*=//' | head -n1""".format(self.url)
        try:
            duration = int(float(subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)))
            video.duration = duration
        except subprocess.CalledProcessError as e:
            logger.error("CalledProcessError error({}) when running command {}".format(e.returncode, cmd))
        except:
            logger.error("Unexpected error({}) when running command {}".format(sys.exc_info()[0], cmd))
