# Amara, universalsubtitles.org
#
# Copyright (C) 2014 Participatory Culture Foundation
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

"""externalsites.google -- Google API handling."""

from collections import namedtuple
from email.mime.multipart import MIMEMultipart, MIMEBase
from lxml import etree
import json
import logging
import urllib
import urlparse
import re
import time

from django.conf import settings
from django.utils.translation import ugettext as _
import jwt
import requests
import pafy, isodate

from utils.subtitles import load_subtitles
from utils.text import fmt

class APIError(StandardError):
    """Error communicating with YouTube's API."""
    pass

class OAuthError(APIError):
    """Error handling YouTube's OAuth."""
    pass

OAuthCallbackData = namedtuple(
    'OAuthCallbackData', 'refresh_token access_token openid_id sub state')
YoutubeUserInfo = namedtuple('YoutubeUserInfo', 'channel_id username')
VideoInfo = namedtuple('VideoInfo',
                       'channel_id title description duration thumbnail_url')
DriveFileInfo = namedtuple(
    'DriveFileInfo',
    'title description mime_type duration content_url embed_url thumbnail_url')
OpenIDProfile = namedtuple('OpenIDProfile',
                           'sub email full_name first_name last_name')

DRIVE_URL_PATTERN = re.compile(r'/d/(.*?)/')

YOUTUBE_TITLE_MAX_LENGTH = 100

logger = logging.getLogger(__name__)

def youtube_scopes():
    return [
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/youtube.force-ssl",
    ]

def request_token_url(redirect_uri, access_type, state, extra_scopes=()):
    """Get the URL to for the request token

    We should redirect the user's browser to this URL when trying to initiate
    OAuth authentication.

    The basic flow is that we send the user's browser to request_token_url,
    then youtube does it's OAuth stuff and sends the browser back to
    redirect_uri.  Then the calling code calls handle_callback() to process
    the OAuth data sent with the request to redirect_uri.

    :param redirect_uri: URI to redirect the user to after youtube
    authentication is complete
    :param state: dict of state info.  This will get returned back from
    handle_callback()
    """
    scopes = ['openid']
    scopes.extend(extra_scopes)
    redirect_uri_parsed = urlparse.urlparse(redirect_uri)

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": ' '.join(scopes),
        "state": json.dumps(state),
        "response_type": "code",
        "access_type": access_type,
        'openid.realm': "{}://{}/".format(redirect_uri_parsed.scheme,
                                          redirect_uri_parsed.netloc),
    }
    if access_type == 'offline':
        params["approval_prompt"] = "force"

    return ("https://accounts.google.com/o/oauth2/auth?" + 
            urllib.urlencode(params))

def _oauth_token_post(**params):
    params["client_id"] = settings.GOOGLE_CLIENT_ID
    params["client_secret"] = settings.GOOGLE_CLIENT_SECRET

    response = requests.post("https://accounts.google.com/o/oauth2/token",
                             data=params, headers={
        "Content-Type": "application/x-www-form-urlencoded"
                             })

    if response.status_code != 200:
        logger.error("Error requesting Youtube OAuth token", extra={
                    "data": {
                        "sent_data": params,
                        "response": response.content
                    },
                })
        raise OAuthError('Authentication error')

    response_data = response.json()
    if response_data.get('error', None):
        logger.error("Error on requesting Youtube OAuth token", extra={
                    "data": {
                        "sent_data": params,
                        "response": response.content
                    },
                })
        raise OAuthError(response_data['error'])

    return response

def handle_callback(request, redirect_uri):
    """Handle the youtube oauth callback.

    :param request: djongo Request object
    :redirect_uri: same URI as as passed to request_token_url()

    :returns: OAuthCallbackData object
    """

    code = request.GET.get('code')
    error = request.GET.get('error')
    state = request.GET.get('state')

    if error is not None:
        raise OAuthError(fmt(_('Youtube error: %(error)s'), error=error))

    if code is None:
        logger.warn("handle_callback: no authorization code (%s)" %
                    request.GET)
        raise OAuthError(_('Error while linking.  Please try again.'))

    if state is not None:
        state = json.loads(state)

    # exchange the auth code for refresh/access tokens
    response = _oauth_token_post(code=code, grant_type='authorization_code',
                                 redirect_uri=redirect_uri)
    # decode the id_token.  We can skip verification since we used HTTPS to
    # connect to google
    response_data = response.json()
    token_data = jwt.decode(response_data['id_token'], verify=False)
    return OAuthCallbackData(
        response_data.get('refresh_token'),
        response_data['access_token'],
        "",
        token_data['sub'],
        state,
    )

def get_new_access_token(refresh_token):
    response = _oauth_token_post(grant_type='refresh_token',
                                 refresh_token=refresh_token)
    return response.json()['access_token']

def revoke_auth_token(refresh_token):
    requests.get('https://accounts.google.com/o/oauth2/revoke',
                 params={'token': refresh_token})

def multipart_format(parts):
    """Make a multipart message

    Args:
        parts: list of (content_type, data) tuples

    Returns:
        (headers, data) tuple
    """
    multi_message = MIMEMultipart('related')
    for content_type, data in parts:
        msg = MIMEBase(*content_type.split('/', 1))
        msg.set_payload(data)
        multi_message.attach(msg)

    body_lines = []
    in_headers = True
    last_key = None
    headers = {}
    for line in multi_message.as_string().splitlines(True):
        if in_headers:
            if line == '\n':
                in_headers = False
            elif line.startswith(' ') and last_key:
                headers[last_key] += line.rstrip()
            else:
                key, value = line[:-1].split(':')
                headers[key] = value.strip()
                last_key = key
        else:
            body_lines.append(line)
    return headers, ''.join(body_lines)

def _make_api_request(method, access_token, url, **kwargs):
    """Make a youtube API request

    Args:
        method: HTTP method to use
        access_token: access token to use, or None for APIs that don't need
            authentication
        **kwargs: args to send to requests.request()
    """
    if access_token is not None:
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        kwargs['headers']['Authorization'] = 'Bearer %s' % access_token
    else:
        if 'params' not in kwargs:
            kwargs['params'] = {}
        kwargs['params']['key'] = settings.GOOGLE_API_KEY
    response = requests.request(method, url, **kwargs)
    if method == 'delete':
        expected_status_code = 204
    else:
        expected_status_code = 200
    if response.status_code != expected_status_code:
        try:
            errors = response.json()['error']['errors']
            message = ' '.join(e['reason'] for e in errors)
        except StandardError, e:
            logger.error("%s parsing youtube response (%s): %s" % (
                e, response.status_code, response.content))
            message = 'Unkown error'
        raise APIError(message)
    return response

def _make_youtube_api_request(method, access_token, url_path, **kwargs):
    url = 'https://www.googleapis.com/youtube/v3/' + url_path
    return _make_api_request(method, access_token, url, **kwargs)

def _make_youtube_upload_api_request(method, access_token, url_path, **kwargs):
    url = 'https://www.googleapis.com/upload/youtube/v3/' + url_path
    return _make_api_request(method, access_token, url, **kwargs)

def channel_get(access_token, part, channel_id=None):
    params = { 'part': ','.join(part) }
    if channel_id is None:
        params['mine'] = 'true'
    else:
        params['id'] = channel_id
    return _make_youtube_api_request('get', access_token, 'channels',
                                     params=params)

def video_get(access_token, video_id, part):
    return _make_youtube_api_request('get', access_token, 'videos', params={
        'id': video_id,
        'part': ','.join(part),
    })

def get_uploads_playlist_id(channel_id):
    response = channel_get(None, ['contentDetails'], channel_id)
    try:
        content_details = response.json()['items'][0]['contentDetails']
    except IndexError:
        return None
    return content_details['relatedPlaylists']['uploads']

def get_uploaded_video_ids(channel_id):
    MAX_ITEMS = 1000

    playlist_id = get_uploads_playlist_id(channel_id)
    if playlist_id is None:
        return []
    results, next_page_token = _get_uploaded_video_ids(playlist_id, None)
    while next_page_token and len(results) < MAX_ITEMS:
        more_results, next_page_token = _get_uploaded_video_ids(
            playlist_id, next_page_token)
        results.extend(more_results)
    return results

def _get_uploaded_video_ids(playlist_id, page_token):
    """Fetches one page of results for get_uploaded_video_ids()."""
    params = {
        'part': 'snippet',
        'playlistId': playlist_id,
        'maxResults': 50,
    }
    if page_token:
        params['pageToken'] = page_token
    response = _make_youtube_api_request('get', None, 'playlistItems',
                                         params=params)
    response_data = response.json()
    rv = []
    for item in response_data['items']:
        resource_id = item['snippet']['resourceId']
        if resource_id['kind'] == 'youtube#video':
            rv.append(resource_id['videoId'])
    return rv, response_data.get('nextPageToken')

def captions_list(access_token, video_id):
    """Fetch info on all non-ASR captions for a video

    Returns:
        List of (caption_id, language_code, name) tuples
    """
    response = _make_youtube_api_request(
        'get', access_token, 'captions', params={
            'videoId': video_id,
            'part': 'id,snippet',
        })
    return [
        (caption['id'], caption['snippet']['language'],
         caption['snippet']['name'])
        for caption in response.json()['items']
        if caption['snippet']['trackKind'] != 'ASR'
    ]

def captions_download(access_token, caption_id, format='ttml'):
    """Download a caption file."""
    response = _make_youtube_api_request('get', access_token,
                                         'captions/{}'.format(caption_id),
                                         params={'tfmt': format})
    return response.content

def captions_insert(access_token, video_id, language_code,
                    sub_content_type, sub_data):
    """Download a caption file."""
    caption_data = json.dumps({
        'snippet': {
            'videoId': video_id,
            'language': language_code,
            'name': '',
        }
    })

    headers, data = multipart_format([
        ('application/json', caption_data),
        (sub_content_type, sub_data)
    ])

    params = {
        'uploadType': 'multipart',
        'part': 'snippet',
    }
    response = _make_youtube_upload_api_request(
        'post', access_token, 'captions', params=params,
        headers=headers, data=data)
    return response.content

def captions_update(access_token, caption_id, sub_content_type, sub_data):
    """Download a caption file."""
    caption_data = json.dumps({
        'id': caption_id,
    })

    headers, data = multipart_format([
        ('application/json', caption_data),
        (sub_content_type, sub_data)
    ])

    params = {
        'uploadType': 'multipart',
        'part': 'id',
    }
    response = _make_youtube_upload_api_request(
        'put', access_token, 'captions', params=params,
        headers=headers, data=data)
    return response.content

def captions_delete(access_token, caption_id):
    response = _make_youtube_api_request(
        'delete', access_token, 'captions', params={'id': caption_id})
    return response.content

def video_put(access_token, video_id, **data):
    part = '.'.join(data.keys())
    data['id'] = video_id
    return _make_youtube_api_request('put', access_token, 'videos', params={
        'part': part,
    }, data=json.dumps(data), headers={
        'content-type': 'application/json'
    })

def get_youtube_user_info(access_token):
    """Get info about a user logged in with access_token

    google/youtube have this concept of "channel IDs" which uniquely identify
    users across youtube, google+, and presumably new services that get added.
    Alongside the channel ID is the channel title, which is a human-friendly
    name to display to the user.

    :returns: (channel_id, display_name) tuple
    """
    response = channel_get(access_token, part=['id','snippet'])
    channel = response.json()['items'][0]
    return YoutubeUserInfo(channel['id'], channel['snippet']['title'])

def get_openid_profile(access_token):
    """Get OpenID info from an access token

    :returns: OpenIDProfile
    """
    url = 'https://www.googleapis.com/plus/v1/people/me/openIdConnect'
    response = _make_api_request('get', access_token, url)
    response_data = response.json()
    return OpenIDProfile(
        response_data['sub'],
        response_data['email'],
        response_data.get('name', ''),
        response_data.get('given_name', ''),
        response_data.get('family_name', ''),
    )

def get_video_info(video_id, accounts=[]):
    for account in accounts:
        try:
            access_token = get_new_access_token(account.oauth_refresh_token)
            return _get_video_info(video_id, access_token)
        except Exception, e:
            pass
    try:
        logger.info("youtube.get_video_info()", extra={
            'stack': True,
        })
        return _get_video_info(video_id)
    except APIError as e:
        logger.error("Youtube API Error: %s, falling back", e)
        try:
            p = pafy.new(video_id)
            return VideoInfo(None, p.title, "", p.length, p.thumb)
        except:
            raise e

def _get_video_info(video_id, access_token=None):
    response = video_get(access_token, video_id, ['snippet', 'contentDetails'])
    try:
        response_data = response.json()
        snippet = response_data['items'][0]['snippet']
        content_details = response_data['items'][0]['contentDetails']
        return VideoInfo(snippet['channelId'],
                         snippet['title'],
                         snippet['description'],
                         isodate.parse_duration(content_details['duration']).total_seconds(),
                         snippet['thumbnails']['high']['url'])
    except StandardError, e:
        raise APIError("get_video_info: Unexpected content: %s" % e)


def get_direct_url_to_audio(video_id):
    """
    It does a request to google to retrieve the URL
    So that should be done in a backgound task
    """
    return pafy.new(video_id).getbestaudio().url

def get_direct_url_to_video(video_id):
    """
    It does a request to google to retrieve the URL
    So that should be done in a backgound task
    """
    return pafy.new(video_id).getbest(preftype="mp4").url

def update_video_description(video_id, access_token, description):
    # get the current snippet for the video
    response = video_get(access_token, video_id, ['snippet'])
    snippet = response.json()['items'][0]['snippet']
    # send back the snippet with the new description
    snippet['description'] = description
    video_put(access_token, video_id, snippet=snippet)

def update_video_metadata(video_id, access_token, primary_audio_language_code, language_code, title, description):
    response = video_get(access_token, video_id, ['snippet','localizations'])
    item = response.json()['items'][0]
    snippet = item['snippet']
    if 'defaultLanguage' not in snippet:
        snippet['defaultLanguage'] = primary_audio_language_code
        result = video_put(access_token, video_id, snippet=snippet)
        response = video_get(access_token, video_id, ['snippet','localizations'])
        item = response.json()['items'][0]
        snippet = item['snippet']
    if 'localizations' in item:
        localizations = response.json()['items'][0]['localizations']
        localizations[language_code] = {"title": title[:YOUTUBE_TITLE_MAX_LENGTH], "description": description}
        result = video_put(access_token, video_id, localizations=localizations)

def get_service_account_access_token(scope):
    """Get an access token for our service account

    The service account is what we use to perform requests where the "user" is
    the amara server.  It's controlled by the following settings:

    - GOOGLE_SERVICE_ACCOUNT: email address for the service account
    - GOOGLE_SERVICE_ACCOUNT_SECRET: RSA private key for the service account
    """
    if (settings.GOOGLE_SERVICE_ACCOUNT is None or
            settings.GOOGLE_SERVICE_ACCOUNT_SECRET is None):
        raise APIError('Google service account not setup')
    url = 'https://www.googleapis.com/oauth2/v4/token'
    now = int(time.time())
    claim = {
        'iss': settings.GOOGLE_SERVICE_ACCOUNT,
        'scope': scope,
        'aud': 'https://www.googleapis.com/oauth2/v4/token',
        'iat': now,
        'exp': now + 3600,
    }
    data = {
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'assertion': jwt.encode(
        claim, settings.GOOGLE_SERVICE_ACCOUNT_SECRET, 'RS256'),
    }
    response = requests.post(url, data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded"
    })
    try:
        response_data = response.json()
        if 'error' in response_data:
            raise OAuthError(response_data['error'])
        else:
            return response_data['access_token']
    except ValueError, KeyError:
        raise OAuthError(
            "Error parsing response: {}".format(response.content))

def _make_drive_api_request(method, access_token, url_path, **kwargs):
    url = 'https://www.googleapis.com/drive/v3/' + url_path
    return _make_api_request(method, access_token, url, **kwargs)

def drive_file_get(access_token, drive_file_id, fields):
    params = {}
    if fields is not None:
        params['fields'] = ','.join(fields)
    return _make_drive_api_request('get', access_token,
                                   'files/{}'.format(drive_file_id),
                                   params=params)

def get_drive_file_id(url):
        parsed_url = urlparse.urlparse(url)
        if parsed_url.scheme == 'drive':
            # Handle drive:///[file_id] schemes (see convert_to_video_url)
            return parsed_url.path[1:]
        match = DRIVE_URL_PATTERN.search(parsed_url.path)
        if match:
            return match.group(1)
        else:
            raise ValueError("Unknown video id")
def matches_drive_url(url):
        parsed_url = urlparse.urlparse(url)
        return (parsed_url.scheme == 'drive' or
                parsed_url.netloc == 'drive.google.com')

def get_drive_file(drive_file_id, fields=None):
    access_token = get_service_account_access_token(
        'https://www.googleapis.com/auth/drive.readonly')
    return drive_file_get(access_token, drive_file_id, fields)

def get_drive_file_content(drive_file_id):
    response = get_drive_file(drive_file_id, ['size'])
    try:
        size = int(response.json()['size'])
    except StandardError, e:
        raise APIError("get_drive_file_content size: {} ({})".format(
            e, response.content))
    if size > 2000000:
        raise APIError("File above the 2MB limit")
    return get_drive_file(drive_file_id+"?alt=media").text

def get_drive_file_info(drive_file_id):
    """Get info on a drive file

    Notes:
       - The thumbnailLink is only valid "on the order of hours".  This is
           okay for our purposes though, since we copy it to S3
       - The embed link is no longer supported with the V3 API.  So for now,
         we just construct it ourselves.
   """
    fields = [
        'name', 'description', 'mimeType', 'webContentLink', 'thumbnailLink',
        'videoMediaMetadata',
    ]
    response = get_drive_file(drive_file_id, fields)
    embed_url = 'https://drive.google.com/file/d/{}/preview'.format(
        drive_file_id)
    try:
        response_data = response.json()
        try:
            duration = response_data['videoMediaMetadata']['durationMillis']
            duration = int(round(float(duration) / 1000.0))
        except (ValueError, KeyError):
            duration = None
        return DriveFileInfo(response_data.get('name'),
                             response_data.get('description'),
                             response_data.get('mimeType'),
                             duration,
                             response_data.get('webContentLink'),
                             embed_url,
                             response_data.get('thumbnailLink'))
    except StandardError, e:
        raise APIError("get_drive_file_info: {} ({})".format(
            e, response.content))
