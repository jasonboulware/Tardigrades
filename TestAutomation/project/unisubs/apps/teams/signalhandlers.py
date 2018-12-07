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

from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete

from auth.models import CustomUser as User
from subtitles.signals import subtitles_published, subtitles_added
from teams import stats
from teams.models import (TeamVideo, TeamMember, MembershipNarrowing,
                          TeamSubtitlesCompleted)
from teams.signals import api_teamvideo_new
from videos.signals import feed_imported

@receiver(feed_imported)
def on_feed_imported(signal, sender, new_videos, **kwargs):
    if sender.team is not None:
        for video in new_videos:
            api_teamvideo_new.send(video.get_team_video())

@receiver(post_save, sender=TeamMember)
@receiver(post_delete, sender=TeamMember)
def on_team_member_change(sender, instance, **kwargs):
    User.cache.invalidate_by_pk(instance.user_id)

@receiver(post_save, sender=MembershipNarrowing)
@receiver(post_delete, sender=MembershipNarrowing)
def on_membership_narrowing_change(sender, instance, **kwargs):
    try:
        User.cache.invalidate_by_pk(instance.member.user_id)
    except TeamMember.DoesNotExist:
        pass

@receiver(subtitles_published)
def on_subtitles_published(sender, **kwargs):
    tv = sender.video.get_team_video()
    if tv:
        stats.increment(tv.team, 'subtitles-published')
        stats.increment(
            tv.team, 'subtitles-published-{}'.format(sender.language_code))

@receiver(subtitles_added)
def on_subtitles_published(sender, version=None, **kwargs):
    tv = sender.video.get_team_video()
    if tv and version.author:
        member = tv.team.get_member(version.author)
        if member:
            TeamSubtitlesCompleted.add(
                member=member,
                video=sender.video,
                language_code=sender.language_code)
