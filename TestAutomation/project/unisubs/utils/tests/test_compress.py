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

from string import printable as chars
from random import randint, choice

from django.test import TestCase

from utils.compress import compress, decompress

class CompressTest(TestCase):
    def test_compression(self):
        # Make sure the empty string is handled.
        self.assertEqual('', decompress(compress('')))

        # Make sure a bunch of random ASCII data compresses correctly.
        for _ in xrange(100):
            l = randint(1, 4096)
            data = ''.join(choice(chars) for _ in xrange(l))
            self.assertEqual(data, decompress(compress(data)))

        # Make sure a bunch of random bytes compress correctly.
        for _ in xrange(100):
            l = randint(1, 4096)
            data = ''.join(chr(randint(0, 255)) for _ in xrange(l))
            self.assertEqual(data, decompress(compress(data)))

        # Make sure a bunch of random Unicode data compresses correctly.
        for _ in xrange(100):
            l = randint(1, 1024)
            data = ''.join(choice(u'☃ಠ_ಠ✿☺☻☹♣♠♥♦⌘⌥✔★☆™※±×~≈÷≠π'
                                  u'αßÁáÀàÅåÄäÆæÇçÉéÈèÊêÍíÌìÎîÑñ'
                                  u'ÓóÒòÔôÖöØøÚúÙùÜüŽž')
                           for _ in xrange(l))

            encoded_data = data.encode('utf-8')
            round_tripped = decompress(compress(encoded_data)).decode('utf-8')

            self.assertEqual(data, round_tripped)
