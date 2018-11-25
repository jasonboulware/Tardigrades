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

"""Basic sanity tests to make sure the subtitle models aren't completely broken."""

from __future__ import absolute_import 

from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.test import TestCase
from nose.tools import *

from babelsubs.storage import SubtitleSet

from auth.models import CustomUser as User
from subtitles import pipeline
from subtitles.models import SubtitleLanguage, SubtitleVersion
from subtitles.tests.utils import (
    make_video, make_video_2, make_video_3, make_sl, refresh, ids, parent_ids,
    ancestor_ids
)
from teams.models import Team, TeamMember, TeamVideo
from utils.factories import *

class TestSubtitleLanguage(TestCase):
    def setUp(self):
        self.video = make_video()
        self.video2 = make_video_2()


    def test_create_subtitle_language(self):
        """Basic sanity checks when creating a subtitlelanguage."""
        l = SubtitleLanguage(video=self.video, language_code='en')
        l.save()

        l = refresh(l)
        self.assertEqual(l.language_code, 'en')

    def test_subtitle_language_unique_constraints(self):
        """Test the unique constraints of subtitlelanguages."""

        # The first subtitle language has no restrictions.
        l1 = SubtitleLanguage(video=self.video, language_code='en')
        l1.save()

        # Cannot have more that one SL for the same video+language.
        l2 = SubtitleLanguage(video=self.video, language_code='en')
        def save_l2():
            # Need to put this inside transaction.atomic since we want to do
            # more DB work
            with transaction.atomic():
                l2.save()
        self.assertRaises(IntegrityError, save_l2)

        # But other videos and other languages are fine.
        l3 = SubtitleLanguage(video=self.video2, language_code='en')
        l3.save()

        l4 = SubtitleLanguage(video=self.video, language_code='fr')
        l4.save()

    def test_primary_audio_language(self):
        en = SubtitleLanguage(video=self.video, language_code='en')
        fr = SubtitleLanguage(video=self.video, language_code='fr')
        en.save()
        fr.save()

        en = refresh(en)
        fr = refresh(fr)
        self.assertFalse(en.is_primary_audio_language())
        self.assertFalse(fr.is_primary_audio_language())

        self.video.primary_audio_language_code = 'en'
        self.video.save()

        en = refresh(en)
        fr = refresh(fr)
        self.assertTrue(en.is_primary_audio_language())
        self.assertFalse(fr.is_primary_audio_language())

        self.video.primary_audio_language_code = 'fr'
        self.video.save()

        en = refresh(en)
        fr = refresh(fr)
        self.assertFalse(en.is_primary_audio_language())
        self.assertTrue(fr.is_primary_audio_language())

        self.video.primary_audio_language_code = 'cy'
        self.video.save()

        en = refresh(en)
        fr = refresh(fr)
        self.assertFalse(en.is_primary_audio_language())
        self.assertFalse(fr.is_primary_audio_language())

    def test_get_translation_source(self):
        # Try a language with no versions.
        source_lang = make_sl(self.video, 'en')
        self.assertIsNone(source_lang.get_translation_source_language())

        # Try a non translated language with one version.
        source_lang.add_version()
        source_lang = refresh(source_lang)
        self.assertIsNone(source_lang.get_translation_source_language())

        # Try a non translated language with two versions.  This is different
        # because the lineage map now contains a reference to itself instead of
        # simply being empty.  It still should not be a translation though.
        sv = source_lang.add_version()
        source_lang = refresh(source_lang)
        self.assertIsNone(source_lang.get_translation_source_language())

        # Try a translation.
        translated = make_sl(self.video, 'fr')
        translated.add_version(parents=[sv])
        translated = refresh(translated)
        self.assertEqual(translated.get_translation_source_language(), source_lang)
        self.assertEqual(translated.get_translation_source_language_code(), source_lang.language_code)

        # now a translation off a translation
        chained_translation = make_sl(self.video, 'pt')
        chained_translation.add_version(parents=[translated.get_tip()])
        self.assertEqual(chained_translation.get_translation_source_language(), translated)
        self.assertEqual(chained_translation.get_translation_source_language_code(), translated.language_code)

        # now fork the translated one
        translated.is_forked = True
        translated.save()
        translated = refresh(translated)
        self.assertIsNone(translated.get_translation_source_language())
        self.assertIsNone(translated.get_translation_source_language_code())
        self.assertEqual(
            translated.get_translation_source_language(ignore_forking=True),
            source_lang
        )
        self.assertEqual(
            translated.get_translation_source_language_code(ignore_forking=True),
            source_lang.language_code
        )

    def test_get_tip(self):
        sl = make_sl(self.video, 'en')
        versions = []

        def _assert_tip(public, version_number):
            if version_number is None:
                self.assertEqual(sl.get_tip(public=public), None)
                return

            tip = sl.get_tip(public=public)
            self.assertEqual(tip.version_number, version_number)
            self.assertEqual(tip.is_tip(public=public), True)

            for other_version in sl.subtitleversion_set.exclude(pk=tip.pk):
                self.assertEqual(other_version.is_tip(public=public), False)

        def add_version(**kwargs):
            versions.append(sl.add_version(**kwargs))

        _assert_tip(False, None)
        _assert_tip(True, None)

        add_version(visibility='private')
        _assert_tip(False, 1)
        _assert_tip(True, None)

        add_version()
        _assert_tip(False, 2)
        _assert_tip(True, 2)

        add_version(visibility='public', visibility_override='private')
        _assert_tip(False, 3)
        _assert_tip(True, 2)

        add_version(visibility='private', visibility_override='private')
        _assert_tip(False, 4)
        _assert_tip(True, 2)

        add_version(visibility='private', visibility_override='public')
        _assert_tip(False, 5)
        _assert_tip(True, 5)

        add_version(visibility='public', visibility_override='public')
        _assert_tip(False, 6)
        _assert_tip(True, 6)

    def test_get_version(self):
        # Actually tests the .version() method whose name we should update at
        # some point to fit with the rest.
        sl_1_en = make_sl(self.video, 'en')
        sl_2_en = make_sl(self.video2, 'en')
        sl_1_fr = make_sl(self.video, 'fr')

        def _assert_version(sl, result, **kwargs):
            version = sl.version(**kwargs)
            if not version:
                actual = None
            else:
                actual = (version.language_code, version.version_number)
            self.assertEqual(result, actual)

        # version() always returns None if there are no versions at all
        _assert_version(sl_1_en, None)
        _assert_version(sl_2_en, None)
        _assert_version(sl_1_fr, None)

        _assert_version(sl_1_en, None, public_only=True)
        _assert_version(sl_1_en, None, public_only=False)
        _assert_version(sl_1_en, None, version_number=1)

        # unless you ask for a specific version you get the latest one
        sl_1_en.add_version(visibility='public')
        sl_1_en.add_version(visibility='public')
        sl_2_en.add_version(visibility='public')
        _assert_version(sl_1_en, ('en', 2))
        _assert_version(sl_2_en, ('en', 1))
        _assert_version(sl_1_fr, None)

        # public_only is on by default
        sl_1_en.add_version(visibility='private')
        sl_2_en.add_version(visibility='private', visibility_override='public')
        sl_1_fr.add_version(visibility='public', visibility_override='private')
        _assert_version(sl_1_en, ('en', 2))
        _assert_version(sl_2_en, ('en', 2))
        _assert_version(sl_1_fr, None)

        # but can be turned off
        _assert_version(sl_1_en, ('en', 3), public_only=False)
        _assert_version(sl_2_en, ('en', 2), public_only=False)
        _assert_version(sl_1_fr, ('fr', 1), public_only=False)

        # you can ask for specific versions
        _assert_version(sl_1_en, ('en', 3), public_only=False, version_number=3)
        _assert_version(sl_1_en, ('en', 2), public_only=False, version_number=2)
        _assert_version(sl_1_en, ('en', 1), public_only=False, version_number=1)

        # but they may not be found if they're invalid, or private and you don't
        # override public_only
        _assert_version(sl_1_en, None, version_number=0)
        _assert_version(sl_1_en, None, version_number=3)
        _assert_version(sl_1_en, None, version_number=2023)

    def test_is_imported_from_youtube_and_not_worked_on(self):
        from subtitles.pipeline import add_subtitles
        sl_en = make_sl(self.video, 'en')

        subtitles_1 = [
            (0, 1000, 'Hello there'),
        ]
        subtitles_2 = [
            (0, 1000, 'Hello there'),
            (1000, 2000, 'Hello there'),
        ]

        add_subtitles(self.video, 'en', subtitles_1, note='From youtube')
        self.assertTrue(sl_en.is_imported_from_youtube_and_not_worked_on)

        add_subtitles(self.video, 'en', subtitles_2)
        self.assertFalse(sl_en.is_imported_from_youtube_and_not_worked_on)


class TestSubtitleVersion(TestCase):
    def setUp(self):
        self.video = make_video()
        self.video2 = make_video_2()
        self.sl_en = make_sl(self.video, 'en')
        self.sl_is = make_sl(self.video, 'is')


    def test_create_subtitle_version(self):
        """Basic sanity checks when creating a version."""

        sv = self.sl_en.add_version(title='title a', description='desc a',
                                    subtitles=[])

        sv = refresh(sv)

        self.assertEqual(sv.language_code, 'en')
        self.assertEqual(sv.video.id, self.video.id)
        self.assertEqual(sv.subtitle_language.id, self.sl_en.id)
        self.assertEqual(sv.title, 'title a')
        self.assertEqual(sv.description, 'desc a')
        self.assertEqual(list(sv.get_subtitles().subtitle_items()), [])
        self.assertEqual(sv.visibility, 'public')

    def test_subtitle_serialization(self):
        """Test basic subtitle serialization."""

        # Empty SubtitleSets
        # We explicitly test before and after refreshing to make sure the
        # serialization happens properly in both cases.
        sv = self.sl_en.add_version(subtitles=SubtitleSet('en'))
        self.assertEqual(sv.get_subtitles(), SubtitleSet('en'))
        sv = refresh(sv)
        self.assertEqual(sv.get_subtitles(), SubtitleSet('en'))

        sv = self.sl_en.add_version(subtitles=None)
        self.assertEqual(sv.get_subtitles(), SubtitleSet('en'))
        sv = refresh(sv)
        self.assertEqual(sv.get_subtitles(), SubtitleSet('en'))

        sv = self.sl_en.add_version(subtitles=[])
        self.assertEqual(sv.get_subtitles(), SubtitleSet('en'))
        sv = refresh(sv)
        self.assertEqual(sv.get_subtitles(), SubtitleSet('en'))

        # Non-empty SubtitleSets
        # Again we test pre- and post-refresh.  Note that this is also checking
        # the equality handling for Subtitle and SubtitleSets.
        s0 = (100, 200, "a")
        s1 = (300, 400, "b")

        sv = self.sl_en.add_version(subtitles=SubtitleSet.from_list('en', [s0, s1]))
        self.assertEqual(sv.get_subtitles(), SubtitleSet.from_list('en', [s0, s1]))
        sv = refresh(sv)
        self.assertEqual(sv.get_subtitles(), SubtitleSet.from_list('en', [s0, s1]))

        sv = self.sl_en.add_version(subtitles=[s0, s1])
        self.assertEqual(sv.get_subtitles(), SubtitleSet.from_list('en', [s0, s1]))
        sv = refresh(sv)
        self.assertEqual(sv.get_subtitles(), SubtitleSet.from_list('en', [s0, s1]))

    def test_denormalization_sanity_checks(self):
        """Test the sanity checks for data denormalized into the version model."""

        # Version videos must match their subtitlelanguage's videos.
        sv = self.sl_en.add_version()
        sv.video = self.video2
        self.assertRaises(AssertionError, lambda: sv.save())

        # Version language codes must match their subtitlelanguage's language
        # codes.
        sv = self.sl_en.add_version()
        sv.language_code = 'fr'
        self.assertRaises(AssertionError, lambda: sv.save())

    def test_visibility(self):
        """Test the (non-overrided) visibility filtering of versions."""

        sv1 = self.sl_en.add_version()
        sv2 = self.sl_en.add_version()
        sv3 = self.sl_en.add_version()

        def _count_public():
            return self.sl_en.subtitleversion_set.public().count()

        self.assertEqual(3, _count_public())
        self.assertTrue(sv1.is_public())
        self.assertFalse(sv1.is_private())
        self.assertTrue(sv2.is_public())
        self.assertFalse(sv2.is_private())
        self.assertTrue(sv3.is_public())
        self.assertFalse(sv3.is_private())

        sv1.visibility = 'private'
        sv1.save()
        self.assertEqual(2, _count_public())
        self.assertFalse(sv1.is_public())
        self.assertTrue(sv1.is_private())

        sv3.visibility = 'private'
        sv3.save()
        self.assertEqual(1, _count_public())
        self.assertFalse(sv3.is_public())
        self.assertTrue(sv3.is_private())

        sv2.visibility = 'private'
        sv2.save()
        self.assertEqual(0, _count_public())
        self.assertFalse(sv2.is_public())
        self.assertTrue(sv2.is_private())

    def test_visibility_override(self):
        """Test the overrided visibility filtering of versions."""

        sv = self.sl_en.add_version()

        def _set_vis(vis, vis_over):
            sv.visibility = vis or ''
            sv.visibility_override = vis_over or ''
            sv.save()

        def _count_public():
            return self.sl_en.subtitleversion_set.public().count()

        def _count_extant():
            return self.sl_en.subtitleversion_set.extant().count()

        def _count_full():
            return self.sl_en.subtitleversion_set.full().count()

        def _assert_counts(public, extant, full):
            self.assertEqual(public, _count_public())
            self.assertEqual(extant, _count_extant())
            self.assertEqual(full, _count_full())


        _set_vis('public', None)
        _assert_counts(1, 1, 1)
        self.assertTrue(sv.is_public())
        self.assertFalse(sv.is_private())
        self.assertFalse(sv.is_deleted())

        _set_vis('private', None)
        _assert_counts(0, 1, 1)
        self.assertFalse(sv.is_public())
        self.assertTrue(sv.is_private())
        self.assertFalse(sv.is_deleted())

        _set_vis('private', 'public')
        _assert_counts(1, 1, 1)
        self.assertTrue(sv.is_public())
        self.assertFalse(sv.is_private())
        self.assertFalse(sv.is_deleted())

        _set_vis('public', 'public')
        _assert_counts(1, 1, 1)
        self.assertTrue(sv.is_public())
        self.assertFalse(sv.is_private())
        self.assertFalse(sv.is_deleted())

        _set_vis('public', 'private')
        _assert_counts(0, 1, 1)
        self.assertFalse(sv.is_public())
        self.assertTrue(sv.is_private())
        self.assertFalse(sv.is_deleted())

        _set_vis('private', 'private')
        _assert_counts(0, 1, 1)
        self.assertFalse(sv.is_public())
        self.assertTrue(sv.is_private())
        self.assertFalse(sv.is_deleted())

        _set_vis('public', 'deleted')
        _assert_counts(0, 0, 1)
        self.assertFalse(sv.is_public())
        self.assertFalse(sv.is_private())
        self.assertTrue(sv.is_deleted())

        _set_vis('private', 'deleted')
        _assert_counts(0, 0, 1)
        self.assertFalse(sv.is_public())
        self.assertFalse(sv.is_private())
        self.assertTrue(sv.is_deleted())

    def test_text_time_change(self):
        from subtitles.pipeline import add_subtitles

        SubtitleVersion.objects.full().delete()
        SubtitleLanguage.objects.all().delete()

        subtitles_1 = [
            (0, 1000, 'Hello there'),
        ]
        subtitles_2 = [
            (0, 1000, 'Hello there'),
            (2000, 3000, 'How are you?'),
        ]
        subtitles_3 = [
            (0, 1000, 'Hello there.'),
            (2000, 3000, 'How are you?'),
        ]
        subtitles_4 = [
            (0, 1000, 'Hello there.'),
            (2000, 4000, 'How are you?'),
        ]

        sv1 = add_subtitles(self.video, 'en', subtitles_1)
        sv2 = add_subtitles(self.video, 'en', subtitles_2)
        sv3 = add_subtitles(self.video, 'en', subtitles_3)
        sv4 = add_subtitles(self.video, 'en', subtitles_4)

        self.assertEquals((1.0, 1.0), sv1.get_changes())
        # 33% of text and 33% of timing is new
        self.assertAlmostEqual(1/3.0, sv2.get_changes()[0])
        self.assertAlmostEqual(1/3.0, sv2.get_changes()[1])
        # timing is the same, but 50% of the text is new
        self.assertEquals((0.0, 0.5), sv3.get_changes())
        # text is the same, but 50% of the timing is new
        self.assertEquals((0.5, 0.0), sv4.get_changes())

        # Deleting versions should make their children diff against the
        # still-remaining ones instead of the deleted ones.
        sv2.visibility_override = 'deleted'
        sv2.save()
        sv3 = refresh(sv3)
        self.assertAlmostEqual(1/3.0, sv3.get_changes()[0])
        self.assertEquals(1.0, sv3.get_changes()[1])

    def test_subtitle_count(self):
        s0 = (100, 200, "a")
        s1 = (300, 400, "b")

        sv1 = self.sl_en.add_version(subtitles=[])
        sv2 = self.sl_en.add_version(subtitles=[s0])
        sv3 = self.sl_en.add_version(subtitles=[s0, s1])

        self.assertEqual(0, sv1.subtitle_count)
        self.assertEqual(1, sv2.subtitle_count)
        self.assertEqual(2, sv3.subtitle_count)

        sv1 = refresh(sv1)
        sv2 = refresh(sv2)
        sv3 = refresh(sv3)

        self.assertEqual(0, sv1.subtitle_count)
        self.assertEqual(1, sv2.subtitle_count)
        self.assertEqual(2, sv3.subtitle_count)

        sv4 = self.sl_en.add_version(subtitles=[(None, None, str(i))
                                                for i in xrange(200)])
        self.assertEqual(200, sv4.subtitle_count)
        sv4 = refresh(sv4)
        self.assertEqual(200, sv4.subtitle_count)

    def test_sibling_set(self):
        def _assert_siblings(sv, *vns):
            siblings = sv.sibling_set.full().order_by('version_number')

            for v in siblings:
                self.assertEqual(sv.subtitle_language_id, v.subtitle_language_id)

            self.assertEqual([v.version_number for v in siblings], list(vns))

        v = self.sl_en.add_version()
        _assert_siblings(v, 1)

        v = self.sl_en.add_version()
        _assert_siblings(v, 1, 2)

        v = self.sl_en.add_version()
        _assert_siblings(v, 1, 2, 3)

        v = self.sl_is.add_version()
        _assert_siblings(v, 1)

        v = self.sl_en.add_version()
        _assert_siblings(v, 1, 2, 3, 4)

    def test_rollback_data(self):
        def _assert_rollback_info(v, rollback_of_version_number, is_rollback,
                                  get_rollback_source):
            self.assertEqual(v.rollback_of_version_number,
                             rollback_of_version_number)

            self.assertEqual(v.is_rollback(), is_rollback)

            if get_rollback_source:
                self.assertEqual(v.get_rollback_source(full=True).id,
                                 get_rollback_source.id)
            else:
                self.assertIsNone(v.get_rollback_source(full=True))

        # Two normal versions.
        v1 = self.sl_en.add_version(subtitles=[])
        _assert_rollback_info(v1, None, False, None)

        v2 = self.sl_en.add_version(subtitles=[])
        _assert_rollback_info(v2, None, False, None)

        # Simulate a legacy rollback.
        v3 = self.sl_en.add_version(subtitles=[], rollback_of_version_number=0)
        _assert_rollback_info(v3, 0, True, None)

        # Add a normal one on top.
        v4 = self.sl_en.add_version(subtitles=[])
        _assert_rollback_info(v4, None, False, None)

        # Now add a new-style rollback.
        v5 = self.sl_en.add_version(subtitles=[], rollback_of_version_number=2)
        _assert_rollback_info(v5, 2, True, v2)

        # Add another normal one on top.
        v6 = self.sl_en.add_version(subtitles=[])
        _assert_rollback_info(v6, None, False, None)

        # Rollbacks to rollbacks are cool I guess.
        v7 = self.sl_en.add_version(subtitles=[], rollback_of_version_number=5)
        _assert_rollback_info(v7, 5, True, v5)

        # Make sure the sanity checks work.
        crazy = SubtitleVersion(version_number=4, rollback_of_version_number=4)
        self.assertRaises(ValidationError, lambda: crazy.full_clean())

        crazy = SubtitleVersion(version_number=4, rollback_of_version_number=200)
        self.assertRaises(ValidationError, lambda: crazy.full_clean())


class TestHistory(TestCase):
    def setUp(self):
        self.video = make_video()

        self.sl_en = make_sl(self.video, 'en')
        self.sl_fr = make_sl(self.video, 'fr')
        self.sl_de = make_sl(self.video, 'de')
        self.sl_cy = make_sl(self.video, 'cy')


    def test_linear_parents(self):
        """Test the ancestry, parentage, and lineage for a simple linear history."""

        sv1 = self.sl_en.add_version()
        sv2 = self.sl_en.add_version()
        sv3 = self.sl_en.add_version()

        sv1 = refresh(sv1)
        sv2 = refresh(sv2)
        sv3 = refresh(sv3)

        self.assertEqual(parent_ids(sv1), ids([]))
        self.assertEqual(parent_ids(sv2), ids([sv1]))
        self.assertEqual(parent_ids(sv3), ids([sv2]))

        self.assertEqual(ids(sv1.get_ancestors()), ids([]))
        self.assertEqual(ids(sv2.get_ancestors()), ids([sv1]))
        self.assertEqual(ids(sv3.get_ancestors()), ids([sv1, sv2]))

        self.assertEqual(sv1.lineage, {})
        self.assertEqual(sv2.lineage, {'en': 1})
        self.assertEqual(sv3.lineage, {'en': 2})

    def test_multiple_parents(self):
        """Test the ancestry, parentage, and lineage for a merged history."""

        # en fr
        #    4
        #    |
        #    3
        #   /|
        #  3 |
        #  | 2
        #  2 |
        #  | 1
        #  |/
        #  1
        e1 = self.sl_en.add_version()
        f1 = self.sl_fr.add_version(parents=[e1])
        e2 = self.sl_en.add_version()
        f2 = self.sl_fr.add_version()
        e3 = self.sl_en.add_version()
        f3 = self.sl_fr.add_version(parents=[e3])
        f4 = self.sl_fr.add_version()

        e1 = refresh(e1)
        e2 = refresh(e2)
        e3 = refresh(e3)
        f1 = refresh(f1)
        f2 = refresh(f2)
        f3 = refresh(f3)
        f4 = refresh(f4)

        # Parents
        self.assertEqual(parent_ids(e1), ids([]))
        self.assertEqual(parent_ids(f1), ids([e1]))

        self.assertEqual(parent_ids(e2), ids([e1]))
        self.assertEqual(parent_ids(f2), ids([f1]))

        self.assertEqual(parent_ids(e3), ids([e2]))
        self.assertEqual(parent_ids(f3), ids([f2, e3]))

        self.assertEqual(parent_ids(f4), ids([f3]))

        # Ancestors
        self.assertEqual(ancestor_ids(e1), ids([]))
        self.assertEqual(ancestor_ids(e2), ids([e1]))
        self.assertEqual(ancestor_ids(e3), ids([e1, e2]))

        self.assertEqual(ancestor_ids(f1), ids([e1]))
        self.assertEqual(ancestor_ids(f2), ids([e1, f1]))
        self.assertEqual(ancestor_ids(f3), ids([e1, f1, e2, f2, e3]))
        self.assertEqual(ancestor_ids(f4), ids([e1, f1, e2, f2, e3, f3]))

        # Lineage
        self.assertEqual(e1.lineage, {})
        self.assertEqual(e2.lineage, {'en': 1})
        self.assertEqual(e3.lineage, {'en': 2})

        self.assertEqual(f1.lineage, {'en': 1})
        self.assertEqual(f2.lineage, {'en': 1, 'fr': 1})
        self.assertEqual(f3.lineage, {'en': 3, 'fr': 2})
        self.assertEqual(f4.lineage, {'en': 3, 'fr': 3})

    def test_tangled_history(self):
        """Test the ancestry, parentage, and lineage for a terrifying history."""

        # en fr de cy
        #
        #    3
        #    |
        #    |     5
        #    |    /|
        #    |   / |
        #    |  7  |
        #    |  |\ |
        #    |  | \|
        # +--|--|--4
        # |  |  |  |
        # 3  |  |  |
        # |  |  |  |
        # |  |  6  |
        # |  |  |\ |
        # |  |  | \|
        # |  |  |  3
        # |  |  | /|
        # |  |  |/ |
        # |  |  5  |
        # |  |  |  2
        # |  |  4  |
        # |  | /|\ |
        # |  |/ | \|
        # |  |  |  1
        # |  |  | /
        # |  |  |/
        # |  |  3
        # |  |  |
        # |  2  |
        # |  |  |
        # +--|--2
        # |  | /|
        # 2  |/ |
        # |  1  |
        # |     |
        # +-----1
        # |
        # 1

        e1 = self.sl_en.add_version(parents=[])
        d1 = self.sl_de.add_version(parents=[e1])
        f1 = self.sl_fr.add_version(parents=[])
        e2 = self.sl_en.add_version(parents=[])
        d2 = self.sl_de.add_version(parents=[f1, e2])
        f2 = self.sl_fr.add_version(parents=[])
        d3 = self.sl_de.add_version(parents=[])
        c1 = self.sl_cy.add_version(parents=[d3])
        d4 = self.sl_de.add_version(parents=[f2, c1])
        c2 = self.sl_cy.add_version(parents=[])
        d5 = self.sl_de.add_version(parents=[])
        c3 = self.sl_cy.add_version(parents=[d5])
        d6 = self.sl_de.add_version(parents=[c3])
        e3 = self.sl_en.add_version(parents=[])
        c4 = self.sl_cy.add_version(parents=[e3])
        d7 = self.sl_de.add_version(parents=[c4])
        c5 = self.sl_cy.add_version(parents=[d7])
        f3 = self.sl_fr.add_version(parents=[])

        e1 = refresh(e1)
        d1 = refresh(d1)
        f1 = refresh(f1)
        e2 = refresh(e2)
        d2 = refresh(d2)
        f2 = refresh(f2)
        d3 = refresh(d3)
        c1 = refresh(c1)
        d4 = refresh(d4)
        c2 = refresh(c2)
        d5 = refresh(d5)
        c3 = refresh(c3)
        d6 = refresh(d6)
        e3 = refresh(e3)
        c4 = refresh(c4)
        d7 = refresh(d7)
        c5 = refresh(c5)
        f3 = refresh(f3)

        # Parents
        self.assertEqual(parent_ids(e1), ids([]))
        self.assertEqual(parent_ids(d1), ids([e1]))
        self.assertEqual(parent_ids(f1), ids([]))
        self.assertEqual(parent_ids(e2), ids([e1]))
        self.assertEqual(parent_ids(d2), ids([d1, e2, f1]))
        self.assertEqual(parent_ids(f2), ids([f1]))
        self.assertEqual(parent_ids(d3), ids([d2]))
        self.assertEqual(parent_ids(c1), ids([d3]))
        self.assertEqual(parent_ids(d4), ids([f2, d3, c1]))
        self.assertEqual(parent_ids(c2), ids([c1]))
        self.assertEqual(parent_ids(d5), ids([d4]))
        self.assertEqual(parent_ids(c3), ids([d5, c2]))
        self.assertEqual(parent_ids(d6), ids([d5, c3]))
        self.assertEqual(parent_ids(e3), ids([e2]))
        self.assertEqual(parent_ids(c4), ids([c3, e3]))
        self.assertEqual(parent_ids(d7), ids([d6, c4]))
        self.assertEqual(parent_ids(c5), ids([c4, d7]))
        self.assertEqual(parent_ids(f3), ids([f2]))

        # Ancestors
        self.assertEqual(ancestor_ids(e1), ids([]))
        self.assertEqual(ancestor_ids(d1), ids([e1]))
        self.assertEqual(ancestor_ids(f1), ids([]))
        self.assertEqual(ancestor_ids(e2), ids([e1]))
        self.assertEqual(ancestor_ids(d2), ids([e1, e2, f1, d1]))
        self.assertEqual(ancestor_ids(f2), ids([f1]))
        self.assertEqual(ancestor_ids(d3), ids([e1, e2, f1, d1, d2]))
        self.assertEqual(ancestor_ids(c1), ids([e1, e2, f1, d1, d2, d3]))
        self.assertEqual(ancestor_ids(d4), ids([e1, e2, f1, f2, d1, d2, d3, c1]))
        self.assertEqual(ancestor_ids(c2), ids([e1, e2, f1, d1, d2, d3, c1]))
        self.assertEqual(ancestor_ids(d5), ids([e1, e2, f1, f2, d1, d2, d3, d4, c1]))
        self.assertEqual(ancestor_ids(c3), ids([e1, e2, f1, f2, d1, d2, d3, d4, d5, c1, c2]))
        self.assertEqual(ancestor_ids(d6), ids([e1, e2, f1, f2, d1, d2, d3, d4, d5, c1, c2, c3]))
        self.assertEqual(ancestor_ids(e3), ids([e1, e2]))
        self.assertEqual(ancestor_ids(c4), ids([e1, e2, e3, f1, f2, d1, d2, d3, d4, d5, c1, c2, c3]))
        self.assertEqual(ancestor_ids(d7), ids([e1, e2, e3, f1, f2, d1, d2, d3, d4, d5, d6, c1, c2, c3, c4]))
        self.assertEqual(ancestor_ids(c5), ids([e1, e2, e3, f1, f2, d1, d2, d3, d4, d5, d6, d7, c1, c2, c3, c4]))
        self.assertEqual(ancestor_ids(f3), ids([f1, f2]))

        # Lineage
        self.assertEqual(e1.lineage, {})
        self.assertEqual(d1.lineage, {'en': 1})
        self.assertEqual(f1.lineage, {})
        self.assertEqual(e2.lineage, {'en': 1})
        self.assertEqual(d2.lineage, {'en': 2, 'fr': 1, 'de': 1})
        self.assertEqual(f2.lineage, {'fr': 1})
        self.assertEqual(d3.lineage, {'en': 2, 'fr': 1, 'de': 2})
        self.assertEqual(c1.lineage, {'en': 2, 'fr': 1, 'de': 3})
        self.assertEqual(d4.lineage, {'en': 2, 'fr': 2, 'de': 3, 'cy': 1})
        self.assertEqual(c2.lineage, {'en': 2, 'fr': 1, 'de': 3, 'cy': 1})
        self.assertEqual(d5.lineage, {'en': 2, 'fr': 2, 'de': 4, 'cy': 1})
        self.assertEqual(c3.lineage, {'en': 2, 'fr': 2, 'de': 5, 'cy': 2})
        self.assertEqual(d6.lineage, {'en': 2, 'fr': 2, 'de': 5, 'cy': 3})
        self.assertEqual(e3.lineage, {'en': 2})
        self.assertEqual(c4.lineage, {'en': 3, 'fr': 2, 'de': 5, 'cy': 3})
        self.assertEqual(d7.lineage, {'en': 3, 'fr': 2, 'de': 6, 'cy': 4})
        self.assertEqual(c5.lineage, {'en': 3, 'fr': 2, 'de': 7, 'cy': 4})
        self.assertEqual(f3.lineage, {'fr': 2})


class TestSubtitleLanguageHavingQueries(TestCase):
    """Test the [not_]having[_public/_nonempty]_versions methods of the SL manager.

    They contain raw SQL through extra() calls, so need to be carefully tested.

    """
    def _get(self, qs, video=None):
        if video:
            qs = qs.filter(video=video)

        return sorted([sl.language_code for sl in qs])

    def _get_langs(self, video=None):
        qs = SubtitleLanguage.objects.having_versions()
        return self._get(qs, video)

    def _get_public_langs(self, video=None):
        qs = SubtitleLanguage.objects.having_public_versions()
        return self._get(qs, video)

    def _get_not_langs(self, video=None):
        qs = SubtitleLanguage.objects.not_having_versions()
        return self._get(qs, video)

    def _get_not_public_langs(self, video=None):
        qs = SubtitleLanguage.objects.not_having_public_versions()
        return self._get(qs, video)

    def _get_nonempty_langs(self, video=None):
        qs = SubtitleLanguage.objects.having_nonempty_versions()
        return self._get(qs, video)

    def _get_not_nonempty_langs(self, video=None):
        qs = SubtitleLanguage.objects.not_having_nonempty_versions()
        return self._get(qs, video)

    def _get_nonempty_tip_langs(self, video=None):
        qs = SubtitleLanguage.objects.having_nonempty_tip()
        return self._get(qs, video)

    def _get_not_nonempty_tip_langs(self, video=None):
        qs = SubtitleLanguage.objects.not_having_nonempty_tip()
        return self._get(qs, video)


    def _get_sv(self, sl, n):
        return sl.subtitleversion_set.full().get(version_number=n)

    def _del_sv(self, sl, n):
        sv = self._get_sv(sl, n)
        sv.visibility_override = 'deleted'
        sv.save()

    def _set_vis(self, sl, n, vis, vis_over):
        sv = self._get_sv(sl, n)
        sv.visibility = vis
        sv.visibility_override = vis_over
        sv.save()


    def setUp(self):
        self.video = make_video()
        self.video2 = make_video_2()

        self.sl_1_en = make_sl(self.video, 'en')
        self.sl_1_fr = make_sl(self.video, 'fr')
        self.sl_2_en = make_sl(self.video2, 'en')
        self.sl_2_cy = make_sl(self.video2, 'cy')


    def test_having_versions(self):
        # No versions at all.
        self.assertEqual(self._get_langs(),            [])
        self.assertEqual(self._get_langs(self.video),  [])
        self.assertEqual(self._get_langs(self.video2), [])

        # A version for 1/en.
        self.sl_1_en.add_version()

        self.assertEqual(self._get_langs(),            ['en'])
        self.assertEqual(self._get_langs(self.video),  ['en'])
        self.assertEqual(self._get_langs(self.video2), [])

        # Two versions for 1/en.
        self.sl_1_en.add_version()

        self.assertEqual(self._get_langs(),            ['en'])
        self.assertEqual(self._get_langs(self.video),  ['en'])
        self.assertEqual(self._get_langs(self.video2), [])

        # Version for 2/cy.
        self.sl_2_cy.add_version()

        self.assertEqual(self._get_langs(),            ['cy', 'en'])
        self.assertEqual(self._get_langs(self.video),  ['en'])
        self.assertEqual(self._get_langs(self.video2), ['cy'])

        # Version for 2/en.
        self.sl_2_en.add_version()

        self.assertEqual(self._get_langs(),            ['cy', 'en', 'en'])
        self.assertEqual(self._get_langs(self.video),  ['en'])
        self.assertEqual(self._get_langs(self.video2), ['cy', 'en'])

        # Version for 1/fr.
        self.sl_1_fr.add_version()

        self.assertEqual(self._get_langs(),            ['cy', 'en', 'en', 'fr'])
        self.assertEqual(self._get_langs(self.video),  ['en', 'fr'])
        self.assertEqual(self._get_langs(self.video2), ['cy', 'en'])

        # Ensure making them private doesn't affect anything here.
        v = self.sl_2_cy.get_tip()
        v.visibility = 'private'
        v.save()

        v = self.sl_2_en.get_tip()
        v.visibility_override = 'private'
        v.save()

        v = self.sl_1_fr.get_tip()
        v.visibility = 'private'
        v.visibility_override = 'private'
        v.save()

        self.assertEqual(self._get_langs(),            ['cy', 'en', 'en', 'fr'])
        self.assertEqual(self._get_langs(self.video),  ['en', 'fr'])
        self.assertEqual(self._get_langs(self.video2), ['cy', 'en'])

        # Make sure deletion of versions is handled properly.

        # Current status looks like this:
        # video 1
        #   en 1 2
        #   fr 1
        # video 2
        #   en 1
        #   cy 1

        # Deleting the only version should take it out of the "having versions"
        # list.

        self._del_sv(self.sl_1_fr, 1)
        self.assertEqual(self._get_langs(),            ['cy', 'en', 'en'])
        self.assertEqual(self._get_langs(self.video),  ['en'])
        self.assertEqual(self._get_langs(self.video2), ['cy', 'en'])

        # Deleting one version out of two should NOT take it out of the list.
        self._del_sv(self.sl_1_en, 1)
        self.assertEqual(self._get_langs(),            ['cy', 'en', 'en'])
        self.assertEqual(self._get_langs(self.video),  ['en'])
        self.assertEqual(self._get_langs(self.video2), ['cy', 'en'])

        v = self._get_sv(self.sl_1_en, 1)
        v.visibility_override = ''
        v.save()

        self._del_sv(self.sl_1_en, 2)
        self.assertEqual(self._get_langs(),            ['cy', 'en', 'en'])
        self.assertEqual(self._get_langs(self.video),  ['en'])
        self.assertEqual(self._get_langs(self.video2), ['cy', 'en'])
        
        # But deleting all of the versions SHOULD take it out.
        self._del_sv(self.sl_1_en, 1)
        self.assertEqual(self._get_langs(),            ['cy', 'en'])
        self.assertEqual(self._get_langs(self.video),  [])
        self.assertEqual(self._get_langs(self.video2), ['cy', 'en'])

    def test_not_having_versions(self):
        # No versions at all.
        self.assertEqual(self._get_not_langs(),            ['cy', 'en', 'en', 'fr'])
        self.assertEqual(self._get_not_langs(self.video),  ['en', 'fr'])
        self.assertEqual(self._get_not_langs(self.video2), ['cy', 'en'])

        # A version for 1/en.
        self.sl_1_en.add_version()

        self.assertEqual(self._get_not_langs(),            ['cy', 'en', 'fr'])
        self.assertEqual(self._get_not_langs(self.video),  ['fr'])
        self.assertEqual(self._get_not_langs(self.video2), ['cy', 'en'])

        # Two versions for 1/en.
        self.sl_1_en.add_version()

        self.assertEqual(self._get_not_langs(),            ['cy', 'en', 'fr'])
        self.assertEqual(self._get_not_langs(self.video),  ['fr'])
        self.assertEqual(self._get_not_langs(self.video2), ['cy', 'en'])

        # Version for 2/cy.
        self.sl_2_cy.add_version()

        self.assertEqual(self._get_not_langs(),            ['en', 'fr'])
        self.assertEqual(self._get_not_langs(self.video),  ['fr'])
        self.assertEqual(self._get_not_langs(self.video2), ['en'])

        # Version for 2/en.
        self.sl_2_en.add_version()

        self.assertEqual(self._get_not_langs(),            ['fr'])
        self.assertEqual(self._get_not_langs(self.video),  ['fr'])
        self.assertEqual(self._get_not_langs(self.video2), [])

        # Version for 1/fr.
        self.sl_1_fr.add_version()

        self.assertEqual(self._get_not_langs(),            [])
        self.assertEqual(self._get_not_langs(self.video),  [])
        self.assertEqual(self._get_not_langs(self.video2), [])

        # Ensure making them private doesn't affect anything here.
        v = self.sl_2_cy.get_tip()
        v.visibility = 'private'
        v.save()

        v = self.sl_2_en.get_tip()
        v.visibility_override = 'private'
        v.save()

        v = self.sl_1_fr.get_tip()
        v.visibility = 'private'
        v.visibility_override = 'private'
        v.save()

        self.assertEqual(self._get_not_langs(),            [])
        self.assertEqual(self._get_not_langs(self.video),  [])
        self.assertEqual(self._get_not_langs(self.video2), [])

        # Make sure deletion of versions is handled properly.

        # Current status looks like this:
        # video 1
        #   en 1 2
        #   fr 1
        # video 2
        #   en 1
        #   cy 1

        # Deleting the only version should put it in the "not having versions"
        # list.
        self._del_sv(self.sl_1_fr, 1)
        self.assertEqual(self._get_not_langs(),            ['fr'])
        self.assertEqual(self._get_not_langs(self.video),  ['fr'])
        self.assertEqual(self._get_not_langs(self.video2), [])

        # Deleting one version out of two should NOT put it into the list.
        self._del_sv(self.sl_1_en, 2)
        self.assertEqual(self._get_not_langs(),            ['fr'])
        self.assertEqual(self._get_not_langs(self.video),  ['fr'])
        self.assertEqual(self._get_not_langs(self.video2), [])

        # But deleting both should.
        self._del_sv(self.sl_1_en, 1)
        self.assertEqual(self._get_not_langs(),            ['en', 'fr'])
        self.assertEqual(self._get_not_langs(self.video),  ['en', 'fr'])
        self.assertEqual(self._get_not_langs(self.video2), [])


    def test_having_public_versions(self):
        # No versions at all.
        self.assertEqual(self._get_public_langs(),            [])
        self.assertEqual(self._get_public_langs(self.video),  [])
        self.assertEqual(self._get_public_langs(self.video2), [])

        # A version for 1/en.
        self.sl_1_en.add_version()

        self.assertEqual(self._get_public_langs(),            ['en'])
        self.assertEqual(self._get_public_langs(self.video),  ['en'])
        self.assertEqual(self._get_public_langs(self.video2), [])

        # Two versions for 1/en.
        self.sl_1_en.add_version()

        self.assertEqual(self._get_public_langs(),            ['en'])
        self.assertEqual(self._get_public_langs(self.video),  ['en'])
        self.assertEqual(self._get_public_langs(self.video2), [])

        # Version for 2/cy.
        self.sl_2_cy.add_version()

        self.assertEqual(self._get_public_langs(),            ['cy', 'en'])
        self.assertEqual(self._get_public_langs(self.video),  ['en'])
        self.assertEqual(self._get_public_langs(self.video2), ['cy'])

        # Version for 2/en.
        self.sl_2_en.add_version()

        self.assertEqual(self._get_public_langs(),            ['cy', 'en', 'en'])
        self.assertEqual(self._get_public_langs(self.video),  ['en'])
        self.assertEqual(self._get_public_langs(self.video2), ['cy', 'en'])

        # Version for 1/fr.
        self.sl_1_fr.add_version()

        self.assertEqual(self._get_public_langs(),            ['cy', 'en', 'en', 'fr'])
        self.assertEqual(self._get_public_langs(self.video),  ['en', 'fr'])
        self.assertEqual(self._get_public_langs(self.video2), ['cy', 'en'])

        # Ensure making *one* of the two 1/en versions private doesn't affect anything.
        v = self.sl_1_en.get_tip()
        v.visibility = 'private'
        v.save()

        self.assertEqual(self._get_public_langs(),            ['cy', 'en', 'en', 'fr'])
        self.assertEqual(self._get_public_langs(self.video),  ['en', 'fr'])
        self.assertEqual(self._get_public_langs(self.video2), ['cy', 'en'])

        # But making all of the versions in a language private filters it.
        v = self.sl_2_cy.get_tip()
        v.visibility = 'private'
        v.save()

        self.assertEqual(self._get_public_langs(),            ['en', 'en', 'fr'])
        self.assertEqual(self._get_public_langs(self.video),  ['en', 'fr'])
        self.assertEqual(self._get_public_langs(self.video2), ['en'])

        v = self.sl_2_en.get_tip()
        v.visibility_override = 'private'
        v.save()

        self.assertEqual(self._get_public_langs(),            ['en', 'fr'])
        self.assertEqual(self._get_public_langs(self.video),  ['en', 'fr'])
        self.assertEqual(self._get_public_langs(self.video2), [])

        v = self.sl_1_fr.get_tip()
        v.visibility = 'private'
        v.visibility_override = 'private'
        v.save()

        self.assertEqual(self._get_public_langs(),            ['en'])
        self.assertEqual(self._get_public_langs(self.video),  ['en'])
        self.assertEqual(self._get_public_langs(self.video2), [])

        # Make sure deletion of versions is handled properly.

        # Let's reset all the visibility to something simple.
        self._set_vis(self.sl_1_en, 1, 'public', '')
        self._set_vis(self.sl_1_en, 2, 'public', '')
        self._set_vis(self.sl_1_fr, 1, 'public', '')
        self._set_vis(self.sl_2_en, 1, 'private', 'public')
        self._set_vis(self.sl_2_cy, 1, 'private', '')

        self.assertEqual(self._get_public_langs(),            ['en', 'en', 'fr'])
        self.assertEqual(self._get_public_langs(self.video),  ['en', 'fr'])
        self.assertEqual(self._get_public_langs(self.video2), ['en'])

        # Deleted versions are not considered public.
        self._del_sv(self.sl_1_fr, 1)
        self.assertEqual(self._get_public_langs(),            ['en', 'en'])
        self.assertEqual(self._get_public_langs(self.video),  ['en'])
        self.assertEqual(self._get_public_langs(self.video2), ['en'])

        self._del_sv(self.sl_1_en, 2)
        self.assertEqual(self._get_public_langs(),            ['en', 'en'])
        self.assertEqual(self._get_public_langs(self.video),  ['en'])
        self.assertEqual(self._get_public_langs(self.video2), ['en'])

        self._del_sv(self.sl_1_en, 1)
        self.assertEqual(self._get_public_langs(),            ['en'])
        self.assertEqual(self._get_public_langs(self.video),  [])
        self.assertEqual(self._get_public_langs(self.video2), ['en'])

    def test_not_having_public_versions(self):
        # No versions at all.
        self.assertEqual(self._get_not_public_langs(),            ['cy', 'en', 'en', 'fr'])
        self.assertEqual(self._get_not_public_langs(self.video),  ['en', 'fr'])
        self.assertEqual(self._get_not_public_langs(self.video2), ['cy', 'en'])

        # A version for 1/en.
        self.sl_1_en.add_version()

        self.assertEqual(self._get_not_public_langs(),            ['cy', 'en', 'fr'])
        self.assertEqual(self._get_not_public_langs(self.video),  ['fr'])
        self.assertEqual(self._get_not_public_langs(self.video2), ['cy', 'en'])

        # Two versions for 1/en.
        self.sl_1_en.add_version()

        self.assertEqual(self._get_not_public_langs(),            ['cy', 'en', 'fr'])
        self.assertEqual(self._get_not_public_langs(self.video),  ['fr'])
        self.assertEqual(self._get_not_public_langs(self.video2), ['cy', 'en'])

        # Version for 2/cy.
        self.sl_2_cy.add_version()

        self.assertEqual(self._get_not_public_langs(),            ['en', 'fr'])
        self.assertEqual(self._get_not_public_langs(self.video),  ['fr'])
        self.assertEqual(self._get_not_public_langs(self.video2), ['en'])

        # Version for 2/en.
        self.sl_2_en.add_version()

        self.assertEqual(self._get_not_public_langs(),            ['fr'])
        self.assertEqual(self._get_not_public_langs(self.video),  ['fr'])
        self.assertEqual(self._get_not_public_langs(self.video2), [])

        # Version for 1/fr.
        self.sl_1_fr.add_version()

        self.assertEqual(self._get_not_public_langs(),            [])
        self.assertEqual(self._get_not_public_langs(self.video),  [])
        self.assertEqual(self._get_not_public_langs(self.video2), [])

        # Ensure making *one* of the two 1/en versions private doesn't affect anything.
        v = self.sl_1_en.get_tip()
        v.visibility = 'private'
        v.save()

        self.assertEqual(self._get_not_public_langs(),            [])
        self.assertEqual(self._get_not_public_langs(self.video),  [])
        self.assertEqual(self._get_not_public_langs(self.video2), [])

        # But making all of the versions in a language private unfilters it.
        v = self.sl_2_cy.get_tip()
        v.visibility = 'private'
        v.save()

        self.assertEqual(self._get_not_public_langs(),            ['cy'])
        self.assertEqual(self._get_not_public_langs(self.video),  [])
        self.assertEqual(self._get_not_public_langs(self.video2), ['cy'])

        v = self.sl_2_en.get_tip()
        v.visibility_override = 'private'
        v.save()

        self.assertEqual(self._get_not_public_langs(),            ['cy', 'en'])
        self.assertEqual(self._get_not_public_langs(self.video),  [])
        self.assertEqual(self._get_not_public_langs(self.video2), ['cy', 'en'])

        v = self.sl_1_fr.get_tip()
        v.visibility = 'private'
        v.visibility_override = 'private'
        v.save()

        self.assertEqual(self._get_not_public_langs(),            ['cy', 'en', 'fr'])
        self.assertEqual(self._get_not_public_langs(self.video),  ['fr'])
        self.assertEqual(self._get_not_public_langs(self.video2), ['cy', 'en'])

        # Make sure deletion of versions is handled properly.

        # Let's reset all the visibility to something simple.
        self._set_vis(self.sl_1_en, 1, 'public', '')
        self._set_vis(self.sl_1_en, 2, 'public', '')
        self._set_vis(self.sl_1_fr, 1, 'public', '')
        self._set_vis(self.sl_2_en, 1, 'private', 'public')
        self._set_vis(self.sl_2_cy, 1, 'private', '')

        self.assertEqual(self._get_not_public_langs(),            ['cy'])
        self.assertEqual(self._get_not_public_langs(self.video),  [])
        self.assertEqual(self._get_not_public_langs(self.video2), ['cy'])

        # Deleted versions are not considered public.
        self._del_sv(self.sl_1_fr, 1)
        self.assertEqual(self._get_not_public_langs(),            ['cy', 'fr'])
        self.assertEqual(self._get_not_public_langs(self.video),  ['fr'])
        self.assertEqual(self._get_not_public_langs(self.video2), ['cy'])

        self._del_sv(self.sl_1_en, 2)
        self.assertEqual(self._get_not_public_langs(),            ['cy', 'fr'])
        self.assertEqual(self._get_not_public_langs(self.video),  ['fr'])
        self.assertEqual(self._get_not_public_langs(self.video2), ['cy'])

        self._del_sv(self.sl_1_en, 1)
        self.assertEqual(self._get_not_public_langs(),            ['cy', 'en', 'fr'])
        self.assertEqual(self._get_not_public_langs(self.video),  ['en', 'fr'])
        self.assertEqual(self._get_not_public_langs(self.video2), ['cy'])


    def test_having_nonempty_versions(self):
        v1 = self.video
        v2 = self.video2

        # Having no versions at all obviously means there are no nonempty ones.
        self.assertEqual(self._get_nonempty_langs(),   [])
        self.assertEqual(self._get_nonempty_langs(v1), [])
        self.assertEqual(self._get_nonempty_langs(v2), [])

        # Empty versions don't count toward this queryset.
        self.sl_1_en.add_version()
        self.sl_2_cy.add_version(subtitles=[])

        self.assertEqual(self._get_nonempty_langs(),   [])
        self.assertEqual(self._get_nonempty_langs(v1), [])
        self.assertEqual(self._get_nonempty_langs(v2), [])

        # Nonempty versions DO count toward this queryset.
        self.sl_1_en.add_version(subtitles=[(None, None, "foo")])
        self.sl_1_fr.add_version(subtitles=[(100, 200, "bar"), (200, 300, "bar")])

        self.assertEqual(self._get_nonempty_langs(),   ['en', 'fr'])
        self.assertEqual(self._get_nonempty_langs(v1), ['en', 'fr'])
        self.assertEqual(self._get_nonempty_langs(v2), [])

        # These querysets check all versions, not just tips.
        self.sl_1_en.add_version(subtitles=[])
        self.sl_1_fr.add_version(subtitles=[])

        self.assertEqual(self._get_nonempty_langs(),   ['en', 'fr'])
        self.assertEqual(self._get_nonempty_langs(v1), ['en', 'fr'])
        self.assertEqual(self._get_nonempty_langs(v2), [])

        # Make sure deletion of versions is handled properly.

        # Current status looks like this:
        # e: Empty, F: Full
        #
        # video 1
        #   en e F
        #   fr F e
        # video 2
        #   en
        #   cy e

        # Deleting empty versions should not affect this at all.
        self._del_sv(self.sl_1_fr, 2)
        self._del_sv(self.sl_2_cy, 1)
        self.assertEqual(self._get_nonempty_langs(),   ['en', 'fr'])
        self.assertEqual(self._get_nonempty_langs(v1), ['en', 'fr'])
        self.assertEqual(self._get_nonempty_langs(v2), [])

        # But deleting versions with subtitles might!
        self._del_sv(self.sl_1_fr, 1)
        self._del_sv(self.sl_1_en, 2)
        self.assertEqual(self._get_nonempty_langs(),   [])
        self.assertEqual(self._get_nonempty_langs(v1), [])
        self.assertEqual(self._get_nonempty_langs(v2), [])

        # Since this only cares about any verions, not tip versions, we can have
        # a deleted tip but still appear in the list as long as there's
        # a non-empty, non-deleted version *somewhere*.
        self.sl_1_en.add_version(subtitles=[(None, None, "foo 2")])
        self.sl_1_en.add_version(subtitles=[(None, None, "foo 3")])

        self._del_sv(self.sl_1_en, 4)

        # 1/en: e d F d
        self.assertEqual(self._get_nonempty_langs(),   ['en'])
        self.assertEqual(self._get_nonempty_langs(v1), ['en'])
        self.assertEqual(self._get_nonempty_langs(v2), [])

    def test_not_having_nonempty_versions(self):
        v1 = self.video
        v2 = self.video2

        # Having no versions at all fits the bill -- these languages have no
        # nonempty versions.
        self.assertEqual(self._get_not_nonempty_langs(),   ['cy', 'en', 'en', 'fr'])
        self.assertEqual(self._get_not_nonempty_langs(v1), ['en', 'fr'])
        self.assertEqual(self._get_not_nonempty_langs(v2), ['cy', 'en'])

        # Empty versions don't count toward this queryset.
        self.sl_1_en.add_version()
        self.sl_2_cy.add_version(subtitles=[])

        self.assertEqual(self._get_not_nonempty_langs(),   ['cy', 'en', 'en', 'fr'])
        self.assertEqual(self._get_not_nonempty_langs(v1), ['en', 'fr'])
        self.assertEqual(self._get_not_nonempty_langs(v2), ['cy', 'en'])

        # Nonempty versions DO count toward this queryset.
        self.sl_1_en.add_version(subtitles=[(None, None, "foo")])
        self.sl_1_fr.add_version(subtitles=[(100, 200, "bar"), (200, 300, "bar")])

        self.assertEqual(self._get_not_nonempty_langs(),   ['cy', 'en'])
        self.assertEqual(self._get_not_nonempty_langs(v1), [])
        self.assertEqual(self._get_not_nonempty_langs(v2), ['cy', 'en'])

        # These querysets check all versions, not just tips.
        self.sl_1_en.add_version(subtitles=[])
        self.sl_1_fr.add_version(subtitles=[])

        self.assertEqual(self._get_not_nonempty_langs(),   ['cy', 'en'])
        self.assertEqual(self._get_not_nonempty_langs(v1), [])
        self.assertEqual(self._get_not_nonempty_langs(v2), ['cy', 'en'])

        # Make sure deletion of versions is handled properly.

        # Current status looks like this:
        # e: Empty
        # F: Full
        #
        # video 1
        #   en e F e
        #   fr F e
        # video 2
        #   en
        #   cy e

        # Deleting empty versions should not affect this at all.
        self._del_sv(self.sl_1_fr, 2)
        self._del_sv(self.sl_2_cy, 1)
        # video 1
        #   en e F e
        #   fr F d
        # video 2
        #   en
        #   cy d
        self.assertEqual(self._get_not_nonempty_langs(),   ['cy', 'en'])
        self.assertEqual(self._get_not_nonempty_langs(v1), [])
        self.assertEqual(self._get_not_nonempty_langs(v2), ['cy', 'en'])

        # But deleting versions with subtitles might!
        self._del_sv(self.sl_1_fr, 1)
        self._del_sv(self.sl_1_en, 2)
        # video 1
        #   en e d e
        #   fr d d
        # video 2
        #   en
        #   cy d
        self._del_sv(self.sl_1_fr, 1)
        self._del_sv(self.sl_1_en, 2)
        self.assertEqual(self._get_not_nonempty_langs(),   ['cy', 'en', 'en', 'fr'])
        self.assertEqual(self._get_not_nonempty_langs(v1), ['en', 'fr'])
        self.assertEqual(self._get_not_nonempty_langs(v2), ['cy', 'en'])

        # Since this only cares about any verions, not tip versions, we can have
        # a deleted tip but still NOT appear in the list as long as there's
        # a non-empty, non-deleted version *somewhere*.
        self.sl_1_en.add_version(subtitles=[(None, None, "foo 2")])
        self.sl_1_en.add_version(subtitles=[(None, None, "foo 3")])

        self._del_sv(self.sl_1_en, 4)

        # 1/en: e d F d
        self.assertEqual(self._get_not_nonempty_langs(),   ['cy', 'en', 'fr'])
        self.assertEqual(self._get_not_nonempty_langs(v1), ['fr'])
        self.assertEqual(self._get_not_nonempty_langs(v2), ['cy', 'en'])


    def test_having_nonempty_tip(self):
        v1 = self.video
        v2 = self.video2

        # Having no versions at all obviously means there are none with a valid
        # tip.
        self.assertEqual(self._get_nonempty_tip_langs(),   [])
        self.assertEqual(self._get_nonempty_tip_langs(v1), [])
        self.assertEqual(self._get_nonempty_tip_langs(v2), [])

        # Empty versions don't count toward this queryset.
        self.sl_1_en.add_version()
        self.sl_2_cy.add_version(subtitles=[])

        self.assertEqual(self._get_nonempty_tip_langs(),   [])
        self.assertEqual(self._get_nonempty_tip_langs(v1), [])
        self.assertEqual(self._get_nonempty_tip_langs(v2), [])

        # Nonempty versions DO count toward this queryset.
        self.sl_1_en.add_version(subtitles=[(None, None, "foo")])
        self.sl_1_fr.add_version(subtitles=[(100, 200, "bar"), (200, 300, "bar")])

        self.assertEqual(self._get_nonempty_tip_langs(),   ['en', 'fr'])
        self.assertEqual(self._get_nonempty_tip_langs(v1), ['en', 'fr'])
        self.assertEqual(self._get_nonempty_tip_langs(v2), [])

        # These querysets check just the tips.
        self.sl_1_en.add_version(subtitles=[])

        self.assertEqual(self._get_nonempty_tip_langs(),   ['fr'])
        self.assertEqual(self._get_nonempty_tip_langs(v1), ['fr'])
        self.assertEqual(self._get_nonempty_tip_langs(v2), [])

        # Make sure deletion of versions is handled properly.

        # Current status looks like this:
        # e: Empty, F: Full
        #
        # video 1
        #   en e F e
        #   fr F
        # video 2
        #   en
        #   cy e

        # Deleting non-tip empty versions should not affect this at all.
        self._del_sv(self.sl_1_en, 1)
        self.assertEqual(self._get_nonempty_tip_langs(),   ['fr'])
        self.assertEqual(self._get_nonempty_tip_langs(v1), ['fr'])
        self.assertEqual(self._get_nonempty_tip_langs(v2), [])

        # Deleting a tip might not affect this, if it doesn't "reveal" a full
        # tip.
        self.sl_1_en.add_version(subtitles=[])

        # video 1
        #   en d F e e
        #   fr F
        # video 2
        #   en
        #   cy e
        self._del_sv(self.sl_1_en, 4)
        self.assertEqual(self._get_nonempty_tip_langs(),   ['fr'])
        self.assertEqual(self._get_nonempty_tip_langs(v1), ['fr'])
        self.assertEqual(self._get_nonempty_tip_langs(v2), [])

        # But deleting a tip might change things if it "reveals" a non-empty
        # version as the new tip!
        self._del_sv(self.sl_1_en, 3)

        # video 1
        #   en d F d d
        #   fr F
        # video 2
        #   en
        #   cy e
        self.assertEqual(self._get_nonempty_tip_langs(),   ['en', 'fr'])
        self.assertEqual(self._get_nonempty_tip_langs(v1), ['en', 'fr'])
        self.assertEqual(self._get_nonempty_tip_langs(v2), [])

        # Deleting a FULL tip might not change anything if there's still another
        # full version ready to take its place.
        self.sl_1_fr.add_version(subtitles=[(100, 200, "cats"), (200, 300, "dogs")])

        # video 1
        #   en d F d d
        #   fr F F
        # video 2
        #   en
        #   cy e
        self._del_sv(self.sl_1_fr, 2)

        # video 1
        #   en d F d d
        #   fr F d
        # video 2
        #   en
        #   cy e
        self.assertEqual(self._get_nonempty_tip_langs(),   ['en', 'fr'])
        self.assertEqual(self._get_nonempty_tip_langs(v1), ['en', 'fr'])
        self.assertEqual(self._get_nonempty_tip_langs(v2), [])

        # But deleting a tip to reveal an empty version (or no versions)
        # underneath WILL change things.
        self._del_sv(self.sl_1_fr, 1)
        self._del_sv(self.sl_1_en, 2)

        # video 1
        #   en d d d d
        #   fr d d
        # video 2
        #   en
        #   cy e
        self.assertEqual(self._get_nonempty_tip_langs(),   [])
        self.assertEqual(self._get_nonempty_tip_langs(v1), [])
        self.assertEqual(self._get_nonempty_tip_langs(v2), [])

    def test_not_having_nonempty_tip(self):
        v1 = self.video
        v2 = self.video2

        # Having no versions at all means they do not have "a non-empty tip".
        self.assertEqual(self._get_not_nonempty_tip_langs(),   ['cy', 'en', 'en', 'fr'])
        self.assertEqual(self._get_not_nonempty_tip_langs(v1), ['en', 'fr'])
        self.assertEqual(self._get_not_nonempty_tip_langs(v2), ['cy', 'en'])

        # Empty versions don't count toward this queryset.
        self.sl_1_en.add_version()
        self.sl_2_cy.add_version(subtitles=[])

        self.assertEqual(self._get_not_nonempty_tip_langs(),   ['cy', 'en', 'en', 'fr'])
        self.assertEqual(self._get_not_nonempty_tip_langs(v1), ['en', 'fr'])
        self.assertEqual(self._get_not_nonempty_tip_langs(v2), ['cy', 'en'])

        # Nonempty versions DO count toward this queryset.
        self.sl_1_fr.add_version(subtitles=[(100, 200, "bar"), (200, 300, "bar")])
        self.sl_1_en.add_version(subtitles=[(None, None, "foo")])

        self.assertEqual(self._get_not_nonempty_tip_langs(),   ['cy', 'en'])
        self.assertEqual(self._get_not_nonempty_tip_langs(v1), [])
        self.assertEqual(self._get_not_nonempty_tip_langs(v2), ['cy', 'en'])

        # These querysets check just the tips.
        self.sl_1_en.add_version(subtitles=[])

        self.assertEqual(self._get_not_nonempty_tip_langs(),   ['cy', 'en', 'en'])
        self.assertEqual(self._get_not_nonempty_tip_langs(v1), ['en'])
        self.assertEqual(self._get_not_nonempty_tip_langs(v2), ['cy', 'en'])

        # Make sure deletion of versions is handled properly.

        # Current status looks like this:
        # e: Empty, F: Full
        #
        # video 1
        #   en e F e
        #   fr F
        # video 2
        #   en
        #   cy e

        # Deleting non-tip empty versions should not affect this at all.
        self._del_sv(self.sl_1_en, 1)

        # video 1
        #   en d F e
        #   fr F
        # video 2
        #   en
        #   cy e
        self.assertEqual(self._get_not_nonempty_tip_langs(),   ['cy', 'en', 'en'])
        self.assertEqual(self._get_not_nonempty_tip_langs(v1), ['en'])
        self.assertEqual(self._get_not_nonempty_tip_langs(v2), ['cy', 'en'])

        # Deleting a tip might not affect this, if it doesn't "reveal" a full
        # tip.
        self.sl_1_en.add_version(subtitles=[])

        # video 1
        #   en d F e e
        #   fr F
        # video 2
        #   en
        #   cy e
        self._del_sv(self.sl_1_en, 4)

        # video 1
        #   en d F e d
        #   fr F
        # video 2
        #   en
        #   cy e
        self.assertEqual(self._get_not_nonempty_tip_langs(),   ['cy', 'en', 'en'])
        self.assertEqual(self._get_not_nonempty_tip_langs(v1), ['en'])
        self.assertEqual(self._get_not_nonempty_tip_langs(v2), ['cy', 'en'])

        # But deleting a tip might change things if it "reveals" a non-empty
        # version as the new tip!
        self._del_sv(self.sl_1_en, 3)

        # video 1
        #   en d F d d
        #   fr F
        # video 2
        #   en
        #   cy e
        self.assertEqual(self._get_not_nonempty_tip_langs(),   ['cy', 'en'])
        self.assertEqual(self._get_not_nonempty_tip_langs(v1), [])
        self.assertEqual(self._get_not_nonempty_tip_langs(v2), ['cy', 'en'])

        # Deleting a FULL tip might not change anything if there's still another
        # full version ready to take its place.
        self.sl_1_fr.add_version(subtitles=[(100, 200, "cats"), (200, 300, "dogs")])

        # video 1
        #   en d F d d
        #   fr F F
        # video 2
        #   en
        #   cy e
        self._del_sv(self.sl_1_fr, 2)

        # video 1
        #   en d F d d
        #   fr F d
        # video 2
        #   en
        #   cy e
        self.assertEqual(self._get_not_nonempty_tip_langs(),   ['cy', 'en'])
        self.assertEqual(self._get_not_nonempty_tip_langs(v1), [])
        self.assertEqual(self._get_not_nonempty_tip_langs(v2), ['cy', 'en'])

        # But deleting a tip to reveal an empty version (or no versions)
        # underneath WILL change things.
        self._del_sv(self.sl_1_fr, 1)
        self._del_sv(self.sl_1_en, 2)

        # video 1
        #   en d d d d
        #   fr d d
        # video 2
        #   en
        #   cy e
        self.assertEqual(self._get_not_nonempty_tip_langs(),   ['cy', 'en', 'en', 'fr'])
        self.assertEqual(self._get_not_nonempty_tip_langs(v1), ['en', 'fr'])
        self.assertEqual(self._get_not_nonempty_tip_langs(v2), ['cy', 'en'])


class TestSubtitleLanguageTipQueries(TestCase):
    def setUp(self):
        self.videos, self.langs, self.versions = bulk_subs({
            'v1': {
                'en': [
                    {},
                    {},
                    {}
                ],
                'fr': [
                    {},
                    {'visibility': 'private'},
                ],
                'de': [
                    {'visibility': 'private'},
                ],
                'es': [
                    {'visibility': 'private',
                     'visibility_override': 'public'},
                ],
            },
            'v2': {
                'en': [
                    {},
                ],
                'fr': [
                    {'visibility': 'public',
                     'visibility_override': 'private'},
                ],
                'de': [
                    {'visibility': 'public',
                     'visibility_override': 'deleted'},
                ],
            },
        })

    def test_tip_query(self):
        self.assertQuerysetEqual(
            SubtitleVersion.objects.public_tips(), map(repr, [
                self.versions['v1', 'en', 3],
                self.versions['v1', 'fr', 1],
                self.versions['v1', 'es', 1],
                self.versions['v2', 'en', 1],
            ]), ordered=False)
        self.assertQuerysetEqual(
            SubtitleVersion.objects.private_tips(), map(repr, [
            self.versions['v1', 'en', 3],
            self.versions['v1', 'fr', 2],
            self.versions['v1', 'de', 1],
            self.versions['v1', 'es', 1],
            self.versions['v2', 'en', 1],
            self.versions['v2', 'fr', 1],
        ]), ordered=False)

class TestSubtitleLanguageCaching(TestCase):
    def setUp(self):
        self.video = VideoFactory()
        pipeline.add_subtitles(self.video, 'en', None, visibility='public')
        self.public_tip = pipeline.add_subtitles(self.video, 'en', None,
                                            visibility='public')
        self.private_tip = pipeline.add_subtitles(self.video, 'en', None,
                                                  visibility='private')

    def get_lang(self):
        return SubtitleLanguage.objects.get(video=self.video,
                                            language_code='en')

    def test_get_tip_sets_cache(self):
        lang = self.get_lang()
        self.assertEquals(lang._tip_cache, {})
        public_tip = lang.get_tip(public=True)
        self.assertEquals(lang._tip_cache, {'public': public_tip})
        private_tip = lang.get_tip(public=False)
        self.assertEquals(lang._tip_cache,
                          {'public': public_tip, 'extant': private_tip})

    def test_cache_tip_sets_cache(self):
        lang = self.get_lang()
        lang.set_tip_cache('public', self.public_tip)
        self.assertEquals(lang._tip_cache, {'public': self.public_tip})

    def test_clear_cache(self):
        lang = self.get_lang()
        lang.set_tip_cache('public', self.public_tip)
        lang.clear_tip_cache()
        self.assertEquals(lang._tip_cache, {})

    def test_tip_cache_skips_query(self):
        lang = self.get_lang()
        def check_get_tip(**kwargs):
            # the first call should result in a query
            with self.assertNumQueries(1):
                lang.get_tip(**kwargs)
            # the subsequent calls should use the cache
            with self.assertNumQueries(0):
                lang.get_tip(**kwargs)
                lang.get_tip(**kwargs)
                lang.get_tip(**kwargs)
        check_get_tip()
        check_get_tip(public=True)
        check_get_tip(full=True)

    def test_get_tip_sets_video_and_language(self):
        lang = self.get_lang()
        lang.video = self.video
        # get_tip should set the video for the tip, since we know its the same
        # as our video
        tip = lang.get_tip()
        self.assert_(hasattr(tip, '_video_cache'))
        self.assert_(hasattr(tip, '_subtitle_language_cache'))
        self.assertEquals(tip.video.id, self.video.id)
        # check the cache when we don't have a video
        lang = self.get_lang()
        tip = lang.get_tip()
        self.assert_(not hasattr(tip, '_video_cache'))
        self.assert_(hasattr(tip, '_subtitle_language_cache'))
        self.assertEquals(tip.video.id, self.video.id)

def assert_tip_cache_correct(video, subtitle_language, public_tip,
                             private_tip):
    """Check that the tip cache is correct for a subtitle language

    Args:
        video -- video created with_many_visibility_combinations flag
        subtitle_language -- SubtitleLanguage to check
        public_tip -- should the public tip be in the cache?
        private_tip -- should the private tip be in the cache?
    """

    lang_id = subtitle_language.id
    corrent_tip_versions = {}
    if public_tip:
        corrent_tip_versions['public'] = video.public_tips[lang_id]
    if private_tip:
        corrent_tip_versions['extant'] = video.tips[lang_id]
    cached_tip_versions = dict(
        (k, v.version_number if v else None)
        for k, v in subtitle_language._tip_cache.items()
    )
    if cached_tip_versions == corrent_tip_versions:
        return
    # Generate a nice error message for debugging
    lines = []
    lines.append("Subtitle tip cache wrong:")
    lines.append("cached: {}".format(cached_tip_versions))
    lines.append("correct: {}".format(corrent_tip_versions))
    lines.append("")
    line_fmt = '{:<20}{:<20}{:<20}'
    lines.append(
        line_fmt.format('version', 'visibility', 'visibility_override'))
    lines.append('-' * 60)
    for v in subtitle_language.subtitleversion_set.full():
        lines.append(line_fmt.format(v.version_number, v.visibility,
                                     v.visibility_override))
    raise AssertionError('\n'.join(lines))

class FetchAndJoinTest(TestCase):
    def setUp(self):
        self.video = VideoFactory(with_many_visibility_combinations=True)

    def run_fetch_and_join(self, *args, **kwargs):
        qs = self.video.newsubtitlelanguage_set.all()
        return qs.fetch_and_join(*args, **kwargs)

    def languages_correct(self):
        correct_language_codes = (self.video.newsubtitlelanguage_set.all()
                                  .values_list('language_code', flat=True))
        languages = self.run_fetch_and_join()
        assert_items_equal([l.language_code for l in languages],
                           correct_language_codes)

    def test_public_tip_cache(self):
        for lang in self.run_fetch_and_join(public_tips=True):
            assert_tip_cache_correct(self.video, lang, True, False)

    def test_private_tip_cache(self):
        for lang in self.run_fetch_and_join(private_tips=True):
            assert_tip_cache_correct(self.video, lang, False, True)

    def test_both_tip_cache(self):
        for lang in self.run_fetch_and_join(private_tips=True,
                                            public_tips=True):
            assert_tip_cache_correct(self.video, lang, True, True)

    def test_language_cached(self):
        # check that the subtitle_language attribute is set, so we don't
        # need an extra query to fetch it
        for lang in self.run_fetch_and_join(public_tips=True,
                                            private_tips=True):
            with self.assertNumQueries(0):
                for v in lang._tip_cache.values():
                    if v is not None:
                        v.subtitle_language

    def test_video_cached(self):
        # check that the video attribute is set, so we don't need an extra
        # query to fetch it
        for lang in self.run_fetch_and_join(video=self.video,
                                            public_tips=True,
                                            private_tips=True):
            with self.assertNumQueries(0):
                lang.video
                for v in lang._tip_cache.values():
                    if v is not None:
                        v.video

class FetchForLanguagesTest(TestCase):
    def setUp(self):
        self.video = VideoFactory(with_many_visibility_combinations=True)
        self.languages = list(self.video.newsubtitlelanguage_set.all())

    def run_fetch_for_languages(self, *args, **kwargs):
        return SubtitleVersion.objects.fetch_for_languages(self.languages,
                                                           *args, **kwargs)

    def test_versions(self):
        versions = self.run_fetch_for_languages()
        assert_items_equal(versions.keys(), [l.id for l in self.languages])
        for language_id, version_list in versions.items():
            version_qs = (SubtitleVersion.objects
                          .filter(subtitle_language_id=language_id))
            assert_equal(version_list, list(version_qs))

    def test_order_by(self):
        versions = self.run_fetch_for_languages(order_by='-version_number')
        for language_id, version_list in versions.items():
            version_qs = (SubtitleVersion.objects
                          .filter(subtitle_language_id=language_id)
                          .order_by('-version_number'))
            assert_equal(version_list, list(version_qs))

    def test_select_related(self):
        versions = self.run_fetch_for_languages(select_related=('author',))
        for language_id, version_list in versions.items():
            for version in version_list:
                with self.assertNumQueries(0):
                    version.author.username

    def test_prefetch_related(self):
        versions = self.run_fetch_for_languages(prefetch_related=('author',))
        fetched_any_author = False
        for language_id, version_list in versions.items():
            for version in version_list:
                # The first time we fetch an author it should run a query to
                # fetch them all
                if not fetched_any_author:
                    version.author
                with self.assertNumQueries(0):
                    version.author.username

    def test_tip_cache(self):
        self.run_fetch_for_languages()
        for language in self.languages:
            assert_tip_cache_correct(self.video, language, True, True)

    def test_tip_cache_with_order_by(self):
        # test that ordering the versions differently doesn't mess up the tip
        # cache
        self.run_fetch_for_languages(order_by='-title')
        for language in self.languages:
            assert_tip_cache_correct(self.video, language, True, True)

    def test_public_only(self):
        versions = self.run_fetch_for_languages(public_only=True)
        for language in self.languages:
            assert_tip_cache_correct(self.video, language, True, False)
            version_qs = (SubtitleVersion.objects.public()
                          .filter(subtitle_language_id=language.id))
            assert_equal(versions[language.id], list(version_qs))

    def test_set_video(self):
        # test that fetch_for_languages() sets the video attribute, so
        # accessing it doesn't require an extra db query
        versions = self.run_fetch_for_languages(video=self.video)
        for lang in self.languages:
            with self.assertNumQueries(0):
                assert_equals(lang.video, self.video)
        for language_id, versions in versions.items():
            for version in versions:
                with self.assertNumQueries(0):
                    assert_equal(version.video, self.video)

    def test_fetch_for_languages_sets_cached_language(self):
        # test that fetch_for_languages() sets the subtitle_language
        # attribute, so accessing it doesn't require an extra db query
        versions = self.run_fetch_for_languages()
        for language_id, versions in versions.items():
            for version in versions:
                with self.assertNumQueries(0):
                    assert_equal(version.subtitle_language.id, language_id)

class TestBulkHasPublicVersion(TestCase):
    def setUp(self):
        self.video = VideoFactory()

    def check_bulk_has_public_version(self, **correct_values):
        languages = list(self.video.newsubtitlelanguage_set.all())
        SubtitleLanguage.bulk_has_public_version(languages)
        assert_equal(
            dict((l.language_code, l._has_public_version) for l in languages),
            correct_values
        )

    def test_no_versions(self):
        SubtitleLanguageFactory(video=self.video, language_code='en')
        self.check_bulk_has_public_version(en=False)

    def test_visibility_public(self):
        pipeline.add_subtitles(self.video, 'en', None, visibility='public')
        self.check_bulk_has_public_version(en=True)

    def test_visibility_private(self):
        pipeline.add_subtitles(self.video, 'en', None, visibility='private')
        self.check_bulk_has_public_version(en=False)

    def test_visibility_override_public(self):
        pipeline.add_subtitles(self.video, 'en', None, visibility='private',
                               visibility_override='public')
        self.check_bulk_has_public_version(en=True)

    def test_visibility_override_private(self):
        pipeline.add_subtitles(self.video, 'en', None, visibility='public',
                               visibility_override='private')
        self.check_bulk_has_public_version(en=False)

    def test_visibility_override_deleted(self):
        pipeline.add_subtitles(self.video, 'en', None, visibility='public',
                               visibility_override='deleted')
        self.check_bulk_has_public_version(en=False)

    def test_one_version_public(self):
        pipeline.add_subtitles(self.video, 'en', None, visibility='public')
        pipeline.add_subtitles(self.video, 'en', None, visibility='private')
        self.check_bulk_has_public_version(en=True)

    def test_multiple_languages(self):
        pipeline.add_subtitles(self.video, 'en', None, visibility='public')
        pipeline.add_subtitles(self.video, 'en', None, visibility='private')
        pipeline.add_subtitles(self.video, 'es', None, visibility='private')
        pipeline.add_subtitles(self.video, 'fr', None, visibility='public',
                               visibility_override='private')
        pipeline.add_subtitles(self.video, 'de', None, visibility='private',
                               visibility_override='public')
        self.check_bulk_has_public_version(en=True, es=False, fr=False,
                                           de=True)

    def test_has_public_version_is_optimized(self):
        # test that calling has_public_version() doesn't result in any db
        # queries
        pipeline.add_subtitles(self.video, 'en', None, visibility='public')
        pipeline.add_subtitles(self.video, 'fr', None, visibility='private')
        languages = list(self.video.newsubtitlelanguage_set.all())
        SubtitleLanguage.bulk_has_public_version(languages)
        with self.assertNumQueries(0):
            assert_true(languages[0].has_public_version())
            assert_false(languages[1].has_public_version())

class TestTeamInteractions(TestCase):
    def setUp(self):
        self.user1 = UserFactory()
        self.user2 = UserFactory()
        self.user_public = UserFactory()

        self.team1 = TeamFactory(name='One', slug='one')
        self.team2 = TeamFactory(name='Two', slug='two')

        TeamMemberFactory(user=self.user1, team=self.team1)
        TeamMemberFactory(user=self.user2, team=self.team2)

        self.video1 = make_video()
        self.video2 = make_video_2()
        self.video_public = make_video_3()

        TeamVideoFactory(video=self.video1, team=self.team1,
                         added_by=User.get_amara_anonymous())
        TeamVideoFactory(video=self.video2, team=self.team2,
                         added_by=User.get_amara_anonymous())

        self.en1 = make_sl(self.video1, 'en')
        self.en2 = make_sl(self.video2, 'en')
        self.en_public = make_sl(self.video_public, 'en')

        self.fr1 = make_sl(self.video1, 'fr')
        self.fr2 = make_sl(self.video2, 'fr')
        self.fr_public = make_sl(self.video_public, 'fr')


class TestSubtitleMetadata(TestCase):
    def setUp(self):
        self.video = make_video()
        self.sl_en = make_sl(self.video, 'en')
        self.user = UserFactory()

    def test_reviewed_by_setting(self):
        version = self.sl_en.add_version()

        self.assertEqual(version.get_reviewed_by(), None,
            "Version's reviewed_by metadata is not originally None.")

        version.set_reviewed_by(self.user)

        self.assertEqual(version.get_reviewed_by().pk, self.user.pk,
            "Version's reviewed_by metadata is not the correct User.")

        version = refresh(version)

        self.assertEqual(version.get_reviewed_by().pk, self.user.pk,
            "Version's reviewed_by metadata is not the correct User.")

        version = self.sl_en.add_version()

        self.assertEqual(version.get_reviewed_by(), None,
            "Versions should not inherit reviewed_by metadata.")

    def test_approved_by_setting(self):
        version = self.sl_en.add_version()

        self.assertEqual(version.get_approved_by(), None,
            "Version's approved_by metadata is not originally None.")

        version.set_approved_by(self.user)

        self.assertEqual(version.get_approved_by().pk, self.user.pk,
            "Version's approved_by metadata is not the correct User.")

        version = refresh(version)

        self.assertEqual(version.get_approved_by().pk, self.user.pk,
            "Version's approved_by metadata is not the correct User.")

        version = self.sl_en.add_version()

        self.assertEqual(version.get_approved_by(), None,
            "Versions should not inherit approved_by metadata.")
