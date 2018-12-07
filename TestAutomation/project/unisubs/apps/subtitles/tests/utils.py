# -*- coding: utf-8 -*-
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

from __future__ import absolute_import

from babelsubs.storage import SubtitleSet

from videos.models import Video
from subtitles.models import SubtitleLanguage
from utils.factories import *

VIDEO_URL = 'http://youtu.be/heKK95DAKms'
VIDEO_URL_2 = 'http://youtu.be/e4MSN6IImpI'
VIDEO_URL_3 = 'http://youtu.be/i_0DXxNeaQ0'


def make_video():
    return VideoFactory(video_url__url=VIDEO_URL)

def make_video_2():
    return VideoFactory(video_url__url=VIDEO_URL_2)

def make_video_3():
    return VideoFactory(video_url__url=VIDEO_URL_3)

def make_sl(video, language_code):
    sl = SubtitleLanguage(video=video, language_code=language_code)
    sl.save()
    return sl

def refresh(m):
    return m.__class__.objects.get(id=m.id)

def versionid(version):
    return version.language_code[:1] + str(version.version_number)

def ids(vs):
    return set(versionid(v) for v in vs)

def parent_ids(version):
    return ids(version.parents.full())

def ancestor_ids(version):
    return ids(version.get_ancestors())

def make_subtitle_set(language_code, num_subs=4):
    sset = SubtitleSet(language_code)
    for x in xrange(0, num_subs):
        sset.append_subtitle(x*1000, x*1000 - 1, "Sub %s" % x)
    return sset
