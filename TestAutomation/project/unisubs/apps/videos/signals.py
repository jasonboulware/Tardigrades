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

from django import dispatch

feed_imported = dispatch.Signal(providing_args=['new_videos'])
# emitted any time a video title changes
title_changed = dispatch.Signal(providing_args=['old_title'])
# emitted when a video title changes from the edit video dialog
video_title_edited = dispatch.Signal(providing_args=['user', 'old_title'])
duration_changed = dispatch.Signal(providing_args=['old_duration'])
language_changed = dispatch.Signal(
    providing_args=['old_primary_audio_language_code'])
video_added = dispatch.Signal(providing_args=['video_url'])
video_url_added = dispatch.Signal(providing_args=['video', 'new_video', 'user', 'team'])
video_url_made_primary = dispatch.Signal(providing_args=['old_url', 'user'])
video_url_deleted = dispatch.Signal(providing_args=['user'])
video_deleted = dispatch.Signal(providing_args=['user'])
