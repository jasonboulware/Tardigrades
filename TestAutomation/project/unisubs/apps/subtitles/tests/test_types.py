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

import datetime
import json

from babelsubs import ParserList, GeneratorList
from django.core.exceptions import ValidationError
from django.test import TestCase
from subtitles.types import SubtitleFormatListClass

class SubtitleTypesTest(TestCase):
    def setUp(self):
        pass
    def test_subtitle_list(self):
        l = SubtitleFormatListClass(ParserList, GeneratorList)
        self.assertEqual(len(l), 13)
