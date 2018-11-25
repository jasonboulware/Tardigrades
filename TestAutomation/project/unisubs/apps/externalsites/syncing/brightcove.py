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

"""externalsites.syncing.brightcove -- Sync subtitles to/from brightcove"""

import json
import requests

from externalsites import brightcove
from externalsites.exceptions import SyncingError
from utils.one_time_data import set_one_time_data

import logging
logger = logging.getLogger(__name__)

MEDIA_READ_URL = 'https://api.brightcove.com/services/library'
MEDIA_WRITE_URL = 'https://api.brightcove.com/services/post'

def update_subtitles_cms(account_id, client_id, client_secret, bc_video_id, subtitle_version):
    try:
        brightcove._make_subtitle_cms_request(account_id, client_id, client_secret, bc_video_id, subtitle_version.language_code, subtitle_version)
    except brightcove.BrightcoveAPIError, e:
        raise SyncingError(unicode(e))

def delete_subtitles_cms(account_id, client_id, client_secret, bc_video_id, subtitle_language):
    try:
        brightcove._make_subtitle_cms_request(account_id, client_id, client_secret, bc_video_id, subtitle_language.language_code)
    except brightcove.BrightcoveAPIError, e:
        raise SyncingError(unicode(e))

def _make_write_request(write_token, method, **params):
    file_content = params.pop('file_content', None)
    data = {
        'method': method,
        'params': params,
    }
    data['params']['token'] = write_token

    if file_content is None:
        response = requests.post(MEDIA_WRITE_URL,
                                 data={'json': json.dumps(data) })
    else:
        response = requests.post(MEDIA_WRITE_URL,
                                 data={ 'JSONRPC': json.dumps(data) },
                                 files={ 'file': file_content})

    if not hasattr(response, 'json'):
        raise SyncingError("Invalid response data: %s" % response.content)

    response_data = response.json()
    if response_data.get('error') is not None:
        error = response_data['error']
        try:
            code = error['code']
            msg = error['message']
        except StandardError:
            raise SyncingError("Unknown error")
        else:
            raise SyncingError("%s: %s" % (code, msg))

def update_subtitles(write_token, video_id, video):
    _make_write_request(write_token, 'add_captioning', video_id=video_id,
                        caption_source={ 'displayName': 'Amara Captions', },
                        file_content=video.get_merged_dfxp())

def delete_subtitles(write_token, video_id):
    _make_write_request(write_token, 'delete_captioning', video_id=video_id)
