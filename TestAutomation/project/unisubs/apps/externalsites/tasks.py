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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

import logging

from django.core.exceptions import ObjectDoesNotExist

from externalsites import credit
from externalsites import google
from externalsites import subfetch
from externalsites.models import (get_account, get_sync_account, SyncHistory,
                                  YouTubeAccount, VimeoSyncAccount)
from subtitles.models import SubtitleLanguage, SubtitleVersion
from videos.models import VideoUrl
from auth.models import CustomUser as User
from teams.models import Team
from utils.taskqueue import job
logger = logging.getLogger(__name__)

@job
def update_subtitles(account_type, account_id, video_url_id, lang_id):
    """Update a subtitles for a language"""
    logger.info("externalsites.tasks.update_subtitles(%s, %s, %s, %s)",
                account_type, account_id, video_url_id, lang_id)
    try:
        account = get_account(account_type, account_id)
        language = SubtitleLanguage.objects.get(id=lang_id)
        video_url = VideoUrl.objects.get(id=video_url_id)
    except ObjectDoesNotExist, e:
        logger.error(
            'Lookup error in update_subtitles(): %s' % e,
            exc_info=True,
            extra={
                'data': {
                    'account_type': account_type,
                    'account_id': account_id,
                    'video_url_id': video_url_id,
                    'lang_id': lang_id,
                }
            }
        )
        return
    else:
        account.update_subtitles(video_url, language)

@job
def delete_subtitles(account_type, account_id, video_url_id, lang_id):
    """Delete a subtitles for a language"""
    logger.info("externalsites.tasks.delete_subtitles(%s, %s, %s, %s)",
                account_type, account_id, video_url_id, lang_id)

    try:
        account = get_account(account_type, account_id)
        video_url = VideoUrl.objects.get(id=video_url_id)
        language = SubtitleLanguage.objects.get(id=lang_id)
    except ObjectDoesNotExist, e:
        logger.error(
            'Lookup error in delete_subtitles(): %s' % e,
            exc_info=True,
            extra={
                'data': {
                    'account_type': account_type,
                    'account_id': account_id,
                    'video_url_id': video_url_id,
                    'lang_id': lang_id,
                    'version_id': version_id,
                }
            }
        )
        return

    account.delete_subtitles(video_url, language)

@job
def update_all_subtitles(account_type, account_id):
    """Update all subtitles for a given account."""
    logger.info("externalsites.tasks.update_all_subtitles(%s, %s)",
                account_type, account_id)
    try:
        account = get_account(account_type, account_id)
    except ObjectDoesNotExist, e:
        logger.error(
            'Lookup error in update_all_subtitles(): %s' % e,
            exc_info=True,
            extra={
                'data': {
                    'account_type': account_type,
                    'account_id': account_id,
                    'video_url_id': video_url_id,
                    'lang_id': lang_id,
                    'version_id': version_id,
                }
            }
        )
        return
    if account.team:
        videos = account.team.videos
    else:
        videos = account.user.video_set

    for video in videos.all():
        for video_url in video.get_video_urls():
            if not account.should_sync_video_url(video, video_url):
                continue
            language_qs = (video.newsubtitlelanguage_set
                           .having_public_versions())
            for language in language_qs:
                update_subtitles.delay(account_type, account_id,
                                       video_url.id, language.id)

@job
def add_amara_credit(video_url_id):
    video_url = VideoUrl.objects.get(id=video_url_id)
    account = get_sync_account(video_url.video, video_url)
    if credit.should_add_credit_to_video_url(video_url, account):
        try:
            credit.add_credit_to_video_url(video_url, account)
        except google.OAuthError:
            logger.exception("Error adding youtube credit")

@job
def fetch_subs(video_url_id, user_id=None,  team_id=None):
    if team_id is None:
        team = None
    else:
        team = Team.objects.get(id=team_id)
    if user_id is None:
        user = None
    else:
        user = User.objects.get(id=user_id)
    try:
        subfetch.fetch_subs(VideoUrl.objects.get(id=video_url_id), user, team)
    except google.OAuthError:
        logger.exception("Error fetching sutitles")

@job
def retry_failed_sync():
    sh = SyncHistory.objects.get_attempt_to_resync()
    if sh is None:
        return
    account = sh.get_account()
    try:
        account.update_subtitles(sh.video_url, sh.language)
    except google.OAuthError:
        logger.exception("Error retrying failed sync")

@job
def import_video_from_youtube_account(account_id):
    try:
        account = YouTubeAccount.objects.get(id=account_id)
        account.import_videos()
    except YouTubeAccount.DoesNotExist:
        logger.warn("import_video_from_youtube_account: "
                    "YouTubeAccount.DoesNotExist ({})".format(account_id))

@job
def unlink_external_sync_accounts(owner):
    YouTubeAccount.objects.for_owner(owner).delete()
    VimeoSyncAccount.objects.for_owner(owner).delete()
