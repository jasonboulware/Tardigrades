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

"""externalsites.subfetch -- Fetch subtitles from external services
"""

import logging, requests

import unilangs
from babelsubs import load_from
from externalsites import google, vimeo
from externalsites.models import YouTubeAccount, VimeoSyncAccount, ExternalAccount
from subtitles.models import ORIGIN_IMPORTED
from subtitles import pipeline
from subtitles.signals import subtitles_imported
from videos.models import VIDEO_TYPE_YOUTUBE, VIDEO_TYPE_VIMEO

logger = logging.getLogger('externalsites.subfetch')

def convert_language_code(lc):
    """
    Convert from a YouTube language code to an Amara one
    """
    try:
        return unilangs.LanguageCode(lc, 'youtube_with_mapping').encode('internal')
    except KeyError:
        # Error looking up the youtube language code.  Return none and we'll
        # skip importing the subtitles.
        return None

def should_fetch_subs(video_url):
    return video_url.type == VIDEO_TYPE_YOUTUBE or \
        video_url.type == VIDEO_TYPE_VIMEO

def fetch_subs(video_url, user=None, team=None):
    if video_url.type == VIDEO_TYPE_YOUTUBE:
        fetch_subs_youtube(video_url, user, team)
    elif video_url.type == VIDEO_TYPE_VIMEO:
        fetch_subs_vimeo(video_url, user, team)
    else:
        logger.warn("fetch_subs() bad video type: %s" % video_url.type)

def lookup_youtube_accounts(video_url, user, team):
    """
    Find the YouTubeAccount objects we should use to try in
    fetch_subs_youtube()
    """
    if team:
        return YouTubeAccount.objects.for_team_or_synced_with_team(team).filter(channel_id=video_url.owner_username,
                                                                                fetch_initial_subtitles=True)
    elif user:
        return YouTubeAccount.objects.filter(type=ExternalAccount.TYPE_USER,
                                             channel_id=video_url.owner_username,
                                             fetch_initial_subtitles=True)
    else:
        return YouTubeAccount.objects.none()

def lookup_vimeo_accounts(video_url, user, team):
    """
    Find the VimeoSyncAccount objects we should use to try in
    fetch_subs_youtube()
    """
    if team:
        return VimeoSyncAccount.objects.for_team_or_synced_with_team(team).filter(username=video_url.owner_username,
                                                                                  fetch_initial_subtitles=True)
    elif user:
        return VimeoSyncAccount.objects.filter(type=ExternalAccount.TYPE_USER,
                                               username=video_url.owner_username,
                                               fetch_initial_subtitles=True)
    else:
        return VimeoSyncAccount.objects.none()

def fetch_subs_vimeo(video_url, user, team):
    video_id = video_url.videoid

    existing_langs = set(
        l.language_code for l in
        video_url.video.newsubtitlelanguage_set.having_versions()
    )
    for vimeo_account in lookup_vimeo_accounts(video_url, user, team):
        tracks = vimeo.get_text_tracks(vimeo_account, video_id)
        versions = []
        if tracks is not None and \
           'data' in tracks:
            for track in tracks['data']:
                language_code = convert_language_code(track['language'])
                if language_code and language_code not in existing_langs:
                    response = requests.get(track['link'])
                    try:
                        subs  = load_from(response.content ,type='vtt').to_internal()
                        version = pipeline.add_subtitles(video_url.video, language_code, subs,
                                                         note="From Vimeo", complete=True,
                                                         origin=ORIGIN_IMPORTED)
                        versions.append(version)
                    except Exception, e:
                        logger.error("Exception while importing subtitles from Vimeo " + str(e))
            if len(versions) > 0:
                subtitles_imported.send(sender=versions[0].subtitle_language, versions=versions)
            break

def fetch_subs_youtube(video_url, user, team):
    video_id = video_url.videoid
    channel_id = video_url.owner_username
    account = find_youtube_account(video_id, lookup_youtube_accounts(video_url, user, team))
    if account is None:
        logger.warn("fetch_subs() no available credentials.")
        return
    existing_langs = set(
        l.language_code for l in
        video_url.video.newsubtitlelanguage_set.having_versions()
    )
    access_token = google.get_new_access_token(account.oauth_refresh_token)
    captions_list = google.captions_list(access_token, video_id)
    versions = []
    for caption_id, language_code, caption_name in captions_list:
        language_code = convert_language_code(language_code)
        if language_code and language_code not in existing_langs:
            dfxp = google.captions_download(access_token, caption_id)
            try:
                version = pipeline.add_subtitles(video_url.video, language_code, dfxp,
                                                 note="From youtube", complete=True,
                                                 origin=ORIGIN_IMPORTED)
                versions.append(version)
            except Exception, e:
                logger.error("Exception while importing subtitles " + str(e))
    if len(versions) > 0:
        subtitles_imported.send(sender=versions[0].subtitle_language, versions=versions)

def find_youtube_account(video_id, possible_accounts):
    try:
        video_info = google.get_video_info(video_id, possible_accounts)
        for account in possible_accounts:
            if account.channel_id == video_info.channel_id:
                return account
        return None
    except google.APIError as e:
        logger.warn("find_youtube_account() error for video id {}: {}".format(video_id, e))
        return None
