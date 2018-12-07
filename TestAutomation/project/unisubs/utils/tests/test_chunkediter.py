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

from utils.chunkediter import chunkediter

class ChunkedIterTest(TestCase):
    def test_iterate(self):
        data = [1, 10, 100, 1000, 10000]

        sum = 0
        for i in chunkediter(data):
            sum += i
        self.assertEqual(sum, 11111)

        sum = 0
        for i in chunkediter(data, 2):
            sum += i
        self.assertEqual(sum, 11111)

        sum = 0
        for i in chunkediter(data, 1):
            sum += i
        self.assertEqual(sum, 11111)

    def test_empty(self):
        data = []

        sum = 0
        for i in chunkediter(data):
            sum += i
        self.assertEqual(sum, 0)

        sum = 0
        for i in chunkediter(data, 1):
            sum += i
        self.assertEqual(sum, 0)
