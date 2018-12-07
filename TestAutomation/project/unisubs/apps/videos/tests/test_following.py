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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

from teams.models import Task
from videos.tests.data import (
    get_user, get_video, get_team, get_team_member, get_team_video,
    make_subtitle_language, make_subtitle_version
)
from videos.tests.videotestutils import WebUseTest

class TestFollowingVideos(WebUseTest):
    def _assertFollowers(self, item, users):
        self.assertEqual(set(item.followers.values_list('id', flat=True)),
                         set([user.id for user in users]))

    def test_create_video(self):
        # Videos without authors should not have any followers.
        video = get_video(1)
        self._assertFollowers(video, [])

        # But submitters automatically follow their videos.
        user = get_user()
        video = get_video(2, user=user)
        self._assertFollowers(video, [user])

    def test_create_edit_subs(self):
        video = get_video(1)
        sl_en = make_subtitle_language(video, 'en')

        # Start off with zero followers.
        self._assertFollowers(video, [])
        self._assertFollowers(sl_en, [])

        # Transcriber/translator should follow only the language, not the video.
        en_author = get_user(1)
        make_subtitle_version(sl_en, author=en_author)
        self._assertFollowers(video, [])
        self._assertFollowers(sl_en, [en_author])

        # Create a "translation".
        sl_ru = make_subtitle_language(video, 'ru')
        self.assertEqual(sl_ru.followers.count(), 0)

        ru_author = get_user(2)
        make_subtitle_version(sl_ru, author=ru_author, parents=[('en', 1)])

        # Translation editors should follow only the language, not the video.
        self.assertEqual(sl_ru.get_translation_source_language_code(), 'en')
        self._assertFollowers(video, [])
        self._assertFollowers(sl_en, [en_author])
        self._assertFollowers(sl_ru, [ru_author])

        # Editors should also follow only the language, not the video.
        editor = get_user(3)

        make_subtitle_version(sl_en, author=editor)
        self._assertFollowers(video, [])
        self._assertFollowers(sl_en, [en_author, editor])
        self._assertFollowers(sl_ru, [ru_author])

        make_subtitle_version(sl_ru, author=editor)
        self._assertFollowers(video, [])
        self._assertFollowers(sl_en, [en_author, editor])
        self._assertFollowers(sl_ru, [ru_author, editor])
