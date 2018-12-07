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
import subprocess, sys, uuid, os
import requests
import logging

from django.core.exceptions import ValidationError
from django.conf import settings

from utils.url_escape import url_escape

logger = logging.getLogger(__name__)

class VideoType(object):

    abbreviation = None
    name = None    

    CAN_IMPORT_SUBTITLES = False

    def __init__(self, url):
        self.url = url_escape(url)

    @property
    def video_id(self):
        return

    def player_url(self):
        """Get the URL to play the video.

        By default this is just the normal url attribute.  But for some video
        types we want to use a different URL to play the video than the main
        url.
        """
        return self.url

    def get_audio_file(self):
        """
        Should return path to a mono audio track
        of the video. this should be a local file.
        Takes time to complete as file must be
        downloaded, encoded, etc.
        """
        # File is read from its URL, then converted to mono, in was
        # so that we do not lose quality with another encoding
        # will raise an exception if there is no diretc URL for
        # type
        def clean(file_name, file_handle=None):
            if file_handle:
                file_handle.close()
            try:
                os.remove(file_name)
            except Exception, e:
                logger.error(repr(e))
        url = self.get_direct_url(prefer_audio=True)
        download_file = os.path.join(settings.TMP_FOLDER, str(uuid.uuid4()))
        with open(download_file, 'wb') as handle:
            try:
                response = requests.get(url, stream=True, timeout=5, verify=False)
            except requests.ConnectionError as e:
                logger.error("""Request to download raw audio/video file was not successful, raised ConnectionError error {}""".format(repr(e)))
                clean(download_file, handle)
                return None
            except requests.Timeout as e:
                logger.error("""Request to download raw audio/video file was not successful, raised Timeout error {}""".format(repr(e)))
                clean(download_file, handle)
                return None
            except Exception as e:
                logger.error("""Request to download raw audio/video file was not successful, raised exception {}""".format(repr(e)))
                clean(download_file, handle)
                return None
            if not response.ok:
                logger.error("""Request to download raw audio/video file was not successful, returned error {}""".format(response.status_code))
                clean(download_file, handle)
                return None
            for block in response.iter_content(1024):
                handle.write(block)
        output = os.path.join(settings.TMP_FOLDER, str(uuid.uuid4()) + ".wav")
        cmd = """avconv -i "{}" -ar 16000 -ac 1 {}""".format(download_file, output)
        logger.error("CMD " + cmd)
        try:
            subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError as e:
            logger.error("CalledProcessError error({}) when running command {}".format(e.returncode, cmd))
            clean(download_file)
            clean(output)
            return None
        except:
            logger.error("Unexpected error({}) when running command {}".format(sys.exc_info()[0], cmd))
            clean(download_file)
            clean(output)
            return None
        clean(download_file)
        return output

    def get_direct_url(self, prefer_audio=False):
        return None
    
    def convert_to_video_url(self):
        return self.format_url(self.url)
    
    @classmethod
    def matches_video_url(cls, url):
        raise Exception('Not implemented')

    @staticmethod
    def url_extension(url):
        """Get the extension of an URL's path.

        Returns the extension as a lowercase string (without the "." part).
        If the path for url doesn't have an extension, None is returned.
        """

        parsed = urlparse(url)
        components = parsed.path.split('.')
        if len(components) == 1:
            # no extension at all
            return None
        return components[-1].lower()

    @property
    def defaults(self):
        return {
            'allow_community_edits': True
        }

    def set_values(self, video, user, team, video_url):
        pass
    
    @classmethod
    def format_url(cls, url):
        return url.strip()
    
class VideoTypeRegistrar(dict):
    
    domains = []
    
    def __init__(self, *args, **kwargs):
        super(VideoTypeRegistrar, self).__init__(*args, **kwargs)
        self.choices = []
        self.type_list = []
        
    def register(self, video_type):
        self[video_type.abbreviation] = video_type
        self.type_list.append(video_type)
        self.choices.append((video_type.abbreviation, video_type.name))
        domain = getattr(video_type, 'site', None)
        domain and self.domains.append(domain)
        
    def video_type_for_url(self, url):
        for video_type in self.type_list:
            if video_type.matches_video_url(url):
                return video_type(url)
            
class VideoTypeError(Exception):
    pass
