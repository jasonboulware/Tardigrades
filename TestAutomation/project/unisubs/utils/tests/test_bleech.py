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

from django.test import TestCase
import bleach

class BleachSanityTest(TestCase):

    def test_weird_input(self):
        html = "<b>hello</b>"
        value = bleach.clean(html, strip=True, tags=[], attributes=[])
        self.assertEquals(u"hello", value)

        html = "<b></b>"
        value = bleach.clean(html, strip=True, tags=[], attributes=[])
        self.assertEquals(u"", value)

        html = '<p><iframe frameborder="0" height="315" src="http://www.youtube.com/embed/6ydeY0tTtF4" width="560"></iframe></p>'
        value = bleach.clean(html, strip=True, tags=[], attributes=[])
        self.assertEquals(u"", value)
