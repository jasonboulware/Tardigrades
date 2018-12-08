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

from datetime import datetime

def update_metadata(video_pk):
    from videos.models import Video
    video = Video.objects.get(pk=video_pk)
    video.edited = datetime.now()
    video.save()
    _update_is_public(video)
    _update_is_was_subtitled(video)
    _update_languages_count(video)
    _update_complete_date(video)
    _invalidate_cache(video)

def _update_is_was_subtitled(video):
    from subtitles.models import SubtitleLanguage
    language_code = video.primary_audio_language_code
    has_version = (SubtitleLanguage.objects.having_nonempty_tip()
                                           .filter(video=video, 
                                                   language_code=language_code)
                                           .exists())

    if not has_version:
        if video.is_subtitled:
            video.is_subtitled = False
            video.save()
    else:
        if not video.is_subtitled or not video.was_subtitled:
            video.is_subtitled = True
            video.was_subtitled = True
            video.save()

def _update_languages_count(video):
    video.languages_count = video.newsubtitlelanguage_set.having_nonempty_tip().count()
    video.save()

def _update_complete_date(video):
    is_complete = video.is_complete
    if is_complete and video.complete_date is None:
        video.complete_date = datetime.now()
        video.save()
    elif not is_complete and video.complete_date is not None:
        video.complete_date = None
        video.save()

def _invalidate_cache(video):
    from widget import video_cache
    video_cache.invalidate_cache(video.video_id)

def _update_is_public(video):
    team_video = video.get_team_video()
    if team_video:
        video.is_public = team_video.team.videos_public()
    else:
        video.is_public = True
    video.save()
