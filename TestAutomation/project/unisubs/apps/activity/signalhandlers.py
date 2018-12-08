# Amara, universalsubtitles.org
#
# Copyright (C) 2016 Participatory Culture Foundation
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
from django.db.models.signals import post_save

from activity.models import ActivityRecord
from comments.models import Comment
from subtitles.models import SubtitleLanguage, SubtitleVersion
from teams.models import TeamVideo, TeamMember
from videos.models import Video
import teams.signals
import videos.signals

@receiver(videos.signals.video_added)
def on_video_added(sender, **kwargs):
    ActivityRecord.objects.create_for_video_added(sender)

@receiver(videos.signals.language_changed)
def on_language_changed(sender, **wargs):
    ActivityRecord.objects.filter(video=sender).update(
        video_language_code=sender.primary_audio_language_code)

@receiver(videos.signals.video_url_added)
def on_video_url_added(sender, new_video, **kwargs):
    if not new_video:
        ActivityRecord.objects.create_for_video_url_added(sender)

@receiver(videos.signals.video_deleted)
def on_video_deleted(sender, user, **kwargs):
    ActivityRecord.objects.create_for_video_deleted(sender, user)

@receiver(videos.signals.video_url_made_primary)
def on_video_url_made_primary(sender, old_url, user, **kwargs):
    ActivityRecord.objects.create_for_video_url_made_primary(sender, old_url,
                                                             user)

@receiver(videos.signals.video_url_deleted)
def on_video_url_deleted(sender, user, **kwargs):
    ActivityRecord.objects.create_for_video_url_deleted(sender, user)

@receiver(videos.signals.video_title_edited)
def on_video_title_edited(sender, user, **kwargs):
    ActivityRecord.objects.create_for_video_title_edited(sender, user)

@receiver(post_save, sender=Comment)
def on_comment_save(instance, created, **kwargs):
    if not created:
        return
    if isinstance(instance.content_object, Video):
        ActivityRecord.objects.create_for_comment(instance.content_object,
                                                  instance)
    elif isinstance(instance.content_object, SubtitleLanguage):
        ActivityRecord.objects.create_for_comment(instance.content_object.video,
                                          instance,
                                          instance.content_object.language_code)

@receiver(post_save, sender=SubtitleVersion)
def on_subtitle_version_save(instance, created, **kwargs):
    if created:
        ActivityRecord.objects.create_for_subtitle_version(instance)

@receiver(post_save, sender=TeamVideo)
def on_team_video_save(instance, created, **kwargs):
    if created:
        ActivityRecord.objects.create_for_video_moved(instance.video, instance.added_by, to_team=instance.team)
        ActivityRecord.objects.move_video_records_to_team(instance.video,
                                                          instance.team)

@receiver(teams.signals.video_removed_from_team)
def on_team_video_delete(sender, team, user, **kwargs):
    ActivityRecord.objects.create_for_video_moved(sender, user, from_team=team)
    ActivityRecord.objects.move_video_records_to_team(sender, None)

@receiver(post_save, sender=TeamMember)
def on_team_member_save(instance, created, **kwargs):
    if created:
        ActivityRecord.objects.create_for_new_member(instance)

@receiver(teams.signals.member_leave)
def on_team_member_deleted(sender, **kwargs):
    ActivityRecord.objects.create_for_member_deleted(sender)

@receiver(teams.signals.video_moved_from_team_to_team)
def on_video_moved_from_team_to_team(user, destination_team, old_team, video, **kwargs):
    ActivityRecord.objects.create_for_video_moved(video, user, from_team=old_team, to_team=destination_team)
    ActivityRecord.objects.move_video_records_to_team(video, destination_team)

@receiver(teams.signals.team_settings_changed)
def on_team_settings_changed(sender, user, changed_settings, **kwargs):
    ActivityRecord.objects.create_for_team_settings_changed(sender, user,
                                                            changed_settings)
