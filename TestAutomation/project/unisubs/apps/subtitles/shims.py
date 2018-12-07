# -*- coding: utf-8 -*-
# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program.  If not, see http://www.gnu.org/licenses/agpl-3.0.html.

"""Helper functions to graft the current UI on to the new data model."""

import json

from django.urls import reverse
from django.utils.http import urlquote_plus

def is_dependent(subtitle_language):
    """Return whether the language is "dependent" on another one.

    Basically, whether it's a translation or not.

    """
    return subtitle_language.get_translation_source_language_code() != None

def get_widget_url(subtitle_language, mode=None, task_id=None):
    # duplicates
    # unisubs.widget.SubtitleDialogOpener.prototype.openDialogOrRedirect_
    video = subtitle_language.video
    video_url = video.get_video_url()

    config = {
        "videoID": video.video_id,
        "videoURL": video_url,
        "effectiveVideoURL": video_url,
        "languageCode": subtitle_language.language_code,
        "subLanguagePK": subtitle_language.pk,
        "originalLanguageCode": video.language,
        "mode": mode,
        "task": task_id,
    }

    if is_dependent(subtitle_language):
        config['baseLanguageCode'] = subtitle_language.get_translation_source_language_code()

    return (reverse('onsite_widget') +
            '?config=' + urlquote_plus(json.dumps(config)))
