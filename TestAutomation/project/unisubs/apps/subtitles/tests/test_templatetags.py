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

from __future__ import absolute_import

from django.test import TestCase
from subtitles.pipeline import  add_subtitles
from subtitles.templatetags.new_subtitles_tags import visibility_display

from utils.factories import *

class TestVisibilityDisplay(TestCase):

    def setUp(self):
        video = TeamVideoFactory().video
        sset = SubtitleSetFactory(num_subs=10)
        self.sv = add_subtitles(video, 'en', subtitles=sset)

    def test_public(self):
        self.assertEqual(visibility_display(self.sv), 'Public')

    def test_private(self):
        self.sv.unpublish()
        self.sv.save()
        self.assertEqual(visibility_display(self.sv), 'Private')

    def test_deleted(self):
        self.sv.unpublish(delete=True)
        self.sv.save()
        self.assertEqual(visibility_display(self.sv), 'Deleted')
