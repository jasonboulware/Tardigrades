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

"""Signals for the subtitles app.  """
from django import dispatch

subtitles_deleted = dispatch.Signal()
# Called whenever a new version is added
subtitles_added = dispatch.Signal(providing_args=['version'])
subtitles_imported = dispatch.Signal(providing_args=['versions'])
# Called when when subtitles are "completed".
#   - Most of the time this the publish action occurs.
#   - For tasks, this is when all tasks are complete
#   - Note that this signal may can multiple times for a single
#     SubtitleLanguage
subtitles_completed = dispatch.Signal()
# Called when we have a new public/complete version
subtitles_published = dispatch.Signal(providing_args=['version'])
subtitle_language_changed = dispatch.Signal(providing_args=['old_language'])
