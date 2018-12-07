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

"""externalsites.signalhandlers -- Signal handler functions."""

from django.dispatch import receiver
from django.db.models.signals import post_save

from externalsites import credit
from externalsites import subfetch
from externalsites import tasks
from externalsites.models import (KalturaAccount,
                                  get_sync_accounts, get_sync_account)
from subtitles.models import (SubtitleLanguage, SubtitleVersion, ORIGIN_IMPORTED)
from videos.models import Video, VideoUrl
import subtitles.signals
import videos.signals
import auth.signals

import logging
logger = logging.getLogger(__name__)

def _update_subtitles_for_language(language):
    for account, video_url in get_sync_accounts(language.video):
        tasks.update_subtitles.delay(account.account_type, account.id,
                                     video_url.id, language.id)
        if credit.should_add_credit_to_video_url(video_url, account):
            tasks.add_amara_credit.delay(video_url.id)

@receiver(subtitles.signals.subtitles_published)
def on_subtitles_published(signal, sender, version=None, **kwargs):
    if not isinstance(sender, SubtitleLanguage):
        raise ValueError("sender must be a SubtitleLanguage: %s" % sender)
    if not (version is not None and version.origin == ORIGIN_IMPORTED):
        _update_subtitles_for_language(sender)

@receiver(subtitles.signals.subtitles_deleted)
def on_subtitles_deleted(signal, sender, **kwargs):
    if not isinstance(sender, SubtitleLanguage):
        raise ValueError("sender must be a SubtitleLanguage: %s" % sender)
    language = sender
    for account, video_url in get_sync_accounts(language.video):
        tasks.delete_subtitles.delay(account.account_type, account.id,
                                     video_url.id, language.id)

@receiver(post_save, sender=KalturaAccount)
def on_account_save(signal, sender, instance, **kwargs):
    tasks.update_all_subtitles.delay(instance.account_type, instance.id)

@receiver(videos.signals.video_url_added)
def on_video_url_added(sender, video, **kwargs):
    video_url = sender
    account = get_sync_account(video, video_url)
    if credit.should_add_credit_to_video_url(video_url, account):
        tasks.add_amara_credit.delay(video_url.pk)
    if subfetch.should_fetch_subs(video_url):
        team = kwargs.pop('team', None)
        if team is not None:
            team = team.pk
        user = kwargs.pop('user', None)
        if user is not None:
            user = user.pk
        try:
            tasks.fetch_subs.delay(video_url.pk, user, team)
        except Exception, e:
            logger.error("Exception")
            logger.error(e)

@receiver(auth.signals.user_account_deactivated)
def on_user_account_deactivated(sender, **kwargs):
    tasks.unlink_external_sync_accounts.delay(sender)
