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

"""externalsites.syncing.kaltura -- Sync subtitles to/from kaltura"""

from xml.dom import minidom

import requests

from externalsites.exceptions import SyncingError
from externalsites.syncing.kaltura_languages import KalturaLanguageMap

KALTURA_API_URL = 'http://www.kaltura.com/api_v3/'
SESSION_TYPE_USER = 0
SESSION_TYPE_ADMIN = 2
CAPTION_TYPE_DFXP = 2
CAPTION_TYPE_SRT = 1
CAPTION_TYPE_WEBVTT = 3
# partnerData value we set for subtitles that we've synced
PARTNER_DATA_TAG = 'synced-from-amara'

def _node_text(node):
    return ''.join(child.nodeValue
                   for child in node.childNodes
                   if child.nodeType == child.TEXT_NODE)

def _find_child(node, tag_name):
    return node.getElementsByTagName(tag_name)[0]

def _has_child(node, tag_name):
    return len(node.getElementsByTagName(tag_name)) > 0

def _check_error(result):
    """Checks if we had an error result."""
    if _has_child(result, 'error'):
        error = _find_child(result, 'error')
        code = _node_text(_find_child(error, 'code'))
        message = _node_text(_find_child(error, 'message'))
        raise SyncingError("%s: %s" % (code, message))

def _make_request(service, action, data):
    params = { 'service': service, 'action': action, }
    response = requests.post(KALTURA_API_URL, params=params, data=data)
    dom = minidom.parseString(response.content)
    try:
        result = _find_child(dom, 'result')
    except IndexError:
        return None
    _check_error(result)
    return result

def _start_session(partner_id, secret):
    result = _make_request('session', 'start', {
        'secret': secret,
        'partnerId': partner_id,
        'type': SESSION_TYPE_ADMIN,
    })
    return _node_text(result)

def _end_session(ks):
    _make_request('session', 'end', { 'ks': ks })

def _find_existing_captionset(ks, video_id, language_code):
    language = KalturaLanguageMap.get_name(language_code)
    result = _make_request('caption_captionasset', 'list', {
        'ks': ks,
        'filter:entryIdEqual': video_id,
    })

    objects = _find_child(result, 'objects')
    for item in objects.getElementsByTagName('item'):
        partner_data = _find_child(item, 'partnerData')
        language_node = _find_child(item, 'language')
        if (_node_text(partner_data) == PARTNER_DATA_TAG and
            _node_text(language_node) == language):
            return _node_text(_find_child(item, 'id'))
    return None

def _add_captions(ks, video_id, language_code):
    language = KalturaLanguageMap.get_name(language_code)
    result = _make_request('caption_captionasset', 'add', {
        'ks': ks,
        'entryId': video_id,
        'captionAsset:language': language,
        'captionAsset:partnerData': PARTNER_DATA_TAG,
        'captionAsset:format': CAPTION_TYPE_SRT,
        'captionAsset:fileExt': 'srt',
    })
    return _node_text(_find_child(result, 'id'))

def _update_caption_content(ks, caption_id, sub_data):
    _make_request('caption_captionasset', 'setcontent', {
        'ks': ks,
        'id': caption_id,
        'contentResource:objectType': 'KalturaStringResource',
        'contentResource:content': sub_data,

    })

def _delete_captions(ks, caption_id):
    _make_request('caption_captionasset', 'delete', {
        'ks': ks,
        'captionAssetId': caption_id,
    })

def update_subtitles(partner_id, secret, video_id, language_code,
                     srt_data):
    ks = _start_session(partner_id, secret)
    try:
        caption_id = _find_existing_captionset(ks, video_id, language_code)
        if caption_id is None:
            caption_id = _add_captions(ks, video_id, language_code)
        _update_caption_content(ks, caption_id, srt_data)
    finally:
        _end_session(ks)

def delete_subtitles(partner_id, secret, video_id, language_code):
    ks = _start_session(partner_id, secret)
    try:
        caption_id = _find_existing_captionset(ks, video_id, language_code)
        if caption_id is not None:
            _delete_captions(ks, caption_id)
    finally:
        _end_session(ks)
