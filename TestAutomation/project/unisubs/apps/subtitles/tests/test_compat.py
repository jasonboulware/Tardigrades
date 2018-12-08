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

"""Testing the backwards-compatibility shims."""

from django.test import TestCase

from subtitles.compat import (
    subtitlelanguage_is_translation, subtitlelanguage_original_language_code
)
from subtitles.tests.utils import make_video, make_sl


class TestTranslationShims(TestCase):
    def setUp(self):
        self.video = make_video()
        self.sl_en = make_sl(self.video, 'en')
        self.sl_fr = make_sl(self.video, 'fr')
        self.sl_de = make_sl(self.video, 'de')


    def test_subtitlelanguage_is_translation(self):
        # en fr
        #  2  
        #  | 1
        #  |/
        #  1
        e1 = self.sl_en.add_version()
        f1 = self.sl_fr.add_version(parents=[e1])
        e2 = self.sl_en.add_version()

        self.assertFalse(subtitlelanguage_is_translation(self.sl_en))
        self.assertTrue(subtitlelanguage_is_translation(self.sl_fr))
        self.assertFalse(subtitlelanguage_is_translation(self.sl_de))

        # en fr
        #    2
        #  2 |
        #  | 1
        #  |/
        #  1 
        f2 = self.sl_fr.add_version()

        self.assertFalse(subtitlelanguage_is_translation(self.sl_en))
        self.assertTrue(subtitlelanguage_is_translation(self.sl_fr))
        self.assertFalse(subtitlelanguage_is_translation(self.sl_de))

        # en fr de
        #       1
        #    2
        #  2 |
        #  | 1
        #  |/
        #  1 
        d1 = self.sl_de.add_version()

        self.sl_de.clear_tip_cache()
        self.assertFalse(subtitlelanguage_is_translation(self.sl_de))

        # en fr de
        #       2
        #      /|
        #     / 1
        #    2
        #  2 |
        #  | 1
        #  |/
        #  1 
        d2 = self.sl_de.add_version(parents=[f2])

        self.sl_de.clear_tip_cache()
        self.assertTrue(subtitlelanguage_is_translation(self.sl_de))

        # Deleting the *source* of a translation shouldn't change the fact that
        # a language is a translation.

        # en fr de
        #       2
        #      /|
        #     / 1
        #    X
        #  2 |
        #  | 1
        #  |/
        #  1 
        f2.visibility_override = 'deleted'
        f2.save()

        self.sl_de.clear_tip_cache()
        self.assertTrue(subtitlelanguage_is_translation(self.sl_de))

        # But deleting the version that makes a language a translation should.
        # I think.  This is really hard.
        d2.visibility_override = 'deleted'
        d2.save()

        self.sl_de.clear_tip_cache()
        self.assertFalse(subtitlelanguage_is_translation(self.sl_de))

        # Shut up, Pyflakes.
        assert e1 and f1 and e2 and f2 and d1 and d2

    def test_subtitlelanguage_original_language_code(self):
        # en fr
        #  2  
        #  | 1
        #  |/
        #  1
        e1 = self.sl_en.add_version()
        f1 = self.sl_fr.add_version(parents=[e1])
        e2 = self.sl_en.add_version()

        self.assertEqual(subtitlelanguage_original_language_code(self.sl_en), None)
        self.assertEqual(subtitlelanguage_original_language_code(self.sl_fr), 'en')
        self.assertEqual(subtitlelanguage_original_language_code(self.sl_de), None)

        # en fr
        #    2
        #  2 |
        #  | 1
        #  |/
        #  1 
        f2 = self.sl_fr.add_version()

        self.assertEqual(subtitlelanguage_original_language_code(self.sl_en), None)
        self.assertEqual(subtitlelanguage_original_language_code(self.sl_fr), 'en')
        self.assertEqual(subtitlelanguage_original_language_code(self.sl_de), None)

        # en fr de
        #       1
        #    2
        #  2 |
        #  | 1
        #  |/
        #  1 
        d1 = self.sl_de.add_version()

        self.assertEqual(subtitlelanguage_original_language_code(self.sl_en), None)
        self.assertEqual(subtitlelanguage_original_language_code(self.sl_fr), 'en')
        self.assertEqual(subtitlelanguage_original_language_code(self.sl_de), None)

        # en fr de
        #       2
        #      /|
        #     / 1
        #    2
        #  2 |
        #  | 1
        #  |/
        #  1 
        d2 = self.sl_de.add_version(parents=[f2])

        self.assertEqual(subtitlelanguage_original_language_code(self.sl_en), None)
        self.assertEqual(subtitlelanguage_original_language_code(self.sl_fr), 'en')

        # Since the new data model doesn't have the concept of one to one
        # translations, we have to fudge things here.  It's possible that we
        # might need to clean this up and do something more DB-intensive to
        # really get the right answer here.
        self.assertTrue(subtitlelanguage_original_language_code(self.sl_de)
                        in ['en', 'fr'])

        # Shut up, Pyflakes.
        assert e1 and f1 and e2 and f2 and d1 and d2

