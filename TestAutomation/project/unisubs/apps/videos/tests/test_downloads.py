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

import urllib
import urlparse

from babelsubs.parsers.dfxp import DFXPParser
from django.urls import reverse
from django.test import TestCase

from subtitles.templatetags import new_subtitles_tags
from utils.test_utils import reload_obj
from videos.models import Video
from videos.tests.data import (
    get_video, make_subtitle_language, make_subtitle_version
)

class DownloadFilenameTest(TestCase):
    def check_get_download_filename(self, title, correct_filename):
        v = Video()
        v.title = title
        self.assertEquals(v.get_download_filename(), correct_filename)

    def test_newline(self):
        self.check_get_download_filename(u"my\ntitle", u'my title')

    def test_period(self):
        self.check_get_download_filename(u"my.title", u'mytitle')

    def test_hash(self):
        self.check_get_download_filename(u"my#title", u'mytitle')

    def test_question_mark(self):
        self.check_get_download_filename(u"my?title", u'mytitle')

    def test_space(self):
        # spaces should be left alone
        self.check_get_download_filename(u"my title", u'my title')

    def test_long_title(self):
        title = (u"This is a really long title used to "
                 u"make sure we are not truncating file names")
        self.check_get_download_filename(title, title)

class DFXPTest(TestCase):
    def _download_subs(self, subtitle_language, format):
        url = new_subtitles_tags.subtitle_download_url(
            subtitle_language.get_tip(), format)
        url_filename = urlparse.urlparse(url).path.split('/')[-1]
        expected_filename = ("%s.%s.%s" % (
            subtitle_language.version().title.replace('.', '_'),
            subtitle_language.language_code,
            format))
        self.assertEquals(urllib.unquote(url_filename), expected_filename)

        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        return res.content

    def test_dfxp_serializer(self):
        video = get_video()
        sl_en = make_subtitle_language(video, 'en')
        video.primary_audio_language_code = 'en'
        video.save()
        make_subtitle_version(sl_en, [(100, 200, 'Here we go!')],
                              title='title')
        sl_en = reload_obj(sl_en)

        content = self._download_subs(sl_en, 'dfxp')
        serialized = DFXPParser(content)
        subtitle_set = serialized.to_internal()

        self.assertEqual(len(subtitle_set), 1)

        start, end, content, meta = list(subtitle_set)[0]

        self.assertEqual(start, 100)
        self.assertEqual(end, 200)
        self.assertEqual(content, 'Here we go!')

