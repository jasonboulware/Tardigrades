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

"""Tests for the subtitle pipeline implementation."""

from __future__ import absolute_import

from django.core.exceptions import ValidationError
from django.test import TestCase
from nose.tools import *

from babelsubs.storage import SubtitleSet, SubtitleLine

from auth.models import CustomUser as User
from subtitles import pipeline
from subtitles.models import SubtitleLanguage, SubtitleVersion
from subtitles.tests.utils import make_video, make_video_2
from subtitles.tests.test_workflows import MockAction
from utils.factories import *
from utils import test_utils

class TestHelperFunctions(TestCase):
    def setUp(self):
        self.video = make_video()
        self.video2 = make_video_2()

    def test_get_version(self):
        def _assert_eq(a, b):
            if (not a) or (not b):
                self.assertTrue((not a) and (not b))
            else:
                self.assertEqual(a.id, b.id)

        def _assert_notfound(l):
            self.assertRaises(SubtitleVersion.DoesNotExist, l)

        def _assert_badtype(l):
            self.assertRaises(ValueError, l)

        def _get_version(v):
            return pipeline._get_version(self.video, v)


        en = SubtitleLanguage.objects.create(video=self.video, language_code='en')
        fr = SubtitleLanguage.objects.create(video=self.video, language_code='fr')

        en1 = en.add_version()
        en2 = en.add_version()
        en3 = en.add_version()

        fr1 = fr.add_version()
        fr2 = fr.add_version()
        fr3 = fr.add_version()

        # Test passthrough.
        _assert_eq(en1, _get_version(en1))
        _assert_eq(en2, _get_version(en2))
        _assert_eq(en3, _get_version(en3))
        _assert_eq(fr1, _get_version(fr1))
        _assert_eq(fr2, _get_version(fr2))
        _assert_eq(fr3, _get_version(fr3))

        # Test version IDs (integers).
        _assert_eq(en1, _get_version(en1.id))
        _assert_eq(en2, _get_version(en2.id))
        _assert_eq(en3, _get_version(en3.id))
        _assert_eq(fr1, _get_version(fr1.id))
        _assert_eq(fr2, _get_version(fr2.id))
        _assert_eq(fr3, _get_version(fr3.id))

        # Test language_code, version_number pairs.
        _assert_eq(fr1, _get_version(('fr', 1)))
        _assert_eq(fr2, _get_version(('fr', 2)))
        _assert_eq(fr3, _get_version(('fr', 3)))
        _assert_eq(en1, _get_version(['en', 1]))
        _assert_eq(en2, _get_version(['en', 2]))
        _assert_eq(en3, _get_version(['en', 3]))

        # Test mismatching passthrough.
        _assert_notfound(lambda: pipeline._get_version(self.video2, en1))
        _assert_notfound(lambda: pipeline._get_version(self.video2, fr3))

        # Test bad version ID.
        _assert_notfound(lambda: _get_version(424242))

        # Test bad language_code, version_number pair.
        _assert_notfound(lambda: _get_version(('fr', 0)))
        _assert_notfound(lambda: _get_version(('fr', 4)))
        _assert_notfound(lambda: _get_version(('cats', 1)))

        # Test entirely invalid types.
        _assert_badtype(lambda: _get_version(u'squirrel'))
        _assert_badtype(lambda: _get_version(1.2))


class TestBasicAdding(TestCase):
    def setUp(self):
        self.video = make_video()
        self.u1 = UserFactory()
        self.u2 = UserFactory()
        self.anon = User.get_amara_anonymous()

    def test_add_empty_versions(self):
        # Start with no SubtitleLanguages.
        self.assertEqual(
            SubtitleLanguage.objects.filter(video=self.video).count(), 0)

        # Put a version through the pipeline.
        pipeline.add_subtitles(self.video, 'en', None)

        # It should create the SubtitleLanguage automatically, with one version.
        self.assertEqual(
            SubtitleLanguage.objects.filter(video=self.video).count(), 1)
        self.assertEqual(
            SubtitleVersion.objects.filter(video=self.video).count(), 1)

        sl = SubtitleLanguage.objects.get(video=self.video, language_code='en')

        # Make sure the version seems sane.
        v = sl.get_tip(full=True)
        self.assertEqual(v.version_number, 1)
        self.assertEqual(v.language_code, 'en')

        # Put another version through the pipeline.
        pipeline.add_subtitles(self.video, 'en', None)

        # Now we should have two versions for a single language.
        self.assertEqual(
            SubtitleLanguage.objects.filter(video=self.video).count(), 1)
        self.assertEqual(
            SubtitleVersion.objects.filter(video=self.video).count(), 2)

        # Make sure it looks sane too.
        sl.clear_tip_cache()
        v = sl.get_tip(full=True)
        self.assertEqual(v.version_number, 2)
        self.assertEqual(v.language_code, 'en')

    def test_add_subtitles(self):
        def _get_tip_subs():
            sl = SubtitleLanguage.objects.get(video=self.video,
                                              language_code='en')
            return list(sl.get_tip(full=True).get_subtitles().subtitle_items())

        def _add(subs):
            pipeline.add_subtitles(self.video, 'en', subs)


        # Passing nil.
        _add(None)

        self.assertEqual(_get_tip_subs(), [])

        # Passing a list of tuples.
        _add([(100, 200, "foo",{'new_paragraph':True} ),
              (300, None, "bar",{'new_paragraph':False} )])

        self.assertEqual(_get_tip_subs(), [SubtitleLine(100, 200, "foo",{'new_paragraph':True} ),
                                           SubtitleLine(300, None, "bar",{'new_paragraph':False} ),])

        # Passing an iterable of tuples.
        iterable = (s for s in [(101, 200, "foo", {'new_paragraph':True} ),
                                (300, None, "bar", {'new_paragraph':False} )])

        # FIXME: this is failing because the genertator is getting exhausted along the pipeline
        # debug and pass the iterable directly
        _add(tuple(iterable))
        self.assertEqual(_get_tip_subs(), [SubtitleLine(101, 200, "foo", {'new_paragraph':True} ),
                                           SubtitleLine(300, None, "bar", {'new_paragraph':False} )])

        # Passing a SubtitleSet.
        subs = SubtitleSet.from_list( 'en', [SubtitleLine(110, 210, "foo", {'new_paragraph':True} ),
                                      SubtitleLine(310, 410, "bar", {'new_paragraph':False} ),
                                      SubtitleLine(None, None, '"baz"', {'new_paragraph': False} )])

        _add(subs)

        self.assertEqual(_get_tip_subs(), [
            SubtitleLine(110, 210, "foo", {'new_paragraph': True} ),
            SubtitleLine(310, 410, "bar", {'new_paragraph': False} ),
            SubtitleLine(None, None, '"baz"', {'new_paragraph': False} ),
        ])

        # Passing a hunk of XML.
        subs = SubtitleSet.from_list("en", [SubtitleLine(10000, 22000, "boots", {}),
                                      SubtitleLine(23000, 29000, "cats", {})])

        _add(subs.to_xml())

        self.assertEqual(_get_tip_subs(), [SubtitleLine(10000, 22000, "boots", {'new_paragraph':True}),
                                           SubtitleLine(23000, 29000, "cats", {'new_paragraph':False})])


        # Passing nonsense should TypeError out.
        self.assertRaises(TypeError, lambda: _add(1))

        # Make sure all the versions are there.
        sl = SubtitleLanguage.objects.get(video=self.video, language_code='en')
        self.assertEqual(sl.subtitleversion_set.full().count(), 5)

    def test_title_description(self):
        def _get_tip_td():
            sl = SubtitleLanguage.objects.get(video=self.video,
                                              language_code='en')
            tip = sl.get_tip(full=True)
            return (tip.title, tip.description)

        def _add(*args, **kwargs):
            pipeline.add_subtitles(self.video, 'en', None, *args, **kwargs)


        # Not passing at all.
        _add()
        self.assertEqual(_get_tip_td(), ('', ''))

        # Passing nil.
        _add(title=None, description=None)
        self.assertEqual(_get_tip_td(), ('', ''))

        # Passing empty strings.
        _add(title='', description='')
        self.assertEqual(_get_tip_td(), ('', ''))

        # Passing title.
        _add(title='Foo')
        self.assertEqual(_get_tip_td(), ('Foo', ''))

        # Passing description.
        _add(description='Bar')
        self.assertEqual(_get_tip_td(), ('', 'Bar'))

        # Passing both.
        _add(title='Foo', description='Bar')
        self.assertEqual(_get_tip_td(), ('Foo', 'Bar'))

        # Passing unicode.
        _add(title=u'ಠ_ಠ', description=u'ಠ‿ಠ')
        self.assertEqual(_get_tip_td(), (u'ಠ_ಠ', u'ಠ‿ಠ'))

        # Passing nonsense.
        self.assertRaises(ValidationError, lambda: _add(title=1234))
        self.assertRaises(ValidationError, lambda: _add(title=['a', 'b']))

    def test_author(self):
        def _get_tip_author():
            sl = SubtitleLanguage.objects.get(video=self.video,
                                              language_code='en')
            return sl.get_tip(full=True).author

        def _add(*args, **kwargs):
            pipeline.add_subtitles(self.video, 'en', None, *args, **kwargs)


        # Not passing at all.
        _add()
        self.assertEqual(_get_tip_author(), self.anon)

        # Passing nil.
        _add(author=None)
        self.assertEqual(_get_tip_author(), self.anon)

        # Passing anonymous.
        _add(author=User.get_amara_anonymous())
        self.assertEqual(_get_tip_author(), self.anon)

        # Passing u1.
        _add(author=self.u1)
        self.assertEqual(_get_tip_author().id, self.u1.id)

        # Passing u2.
        _add(author=self.u2)
        self.assertEqual(_get_tip_author().id, self.u2.id)

        # Passing nonsense
        self.assertRaises(ValueError, lambda: _add(author='dogs'))
        self.assertRaises(ValueError, lambda: _add(author=-1234))
        self.assertRaises(ValueError, lambda: _add(author=[self.u1]))

    def test_visibility(self):
        def _get_tip_vis():
            sl = SubtitleLanguage.objects.get(video=self.video,
                                              language_code='en')
            tip = sl.get_tip(full=True)
            return (tip.visibility, tip.visibility_override)

        def _add(*args, **kwargs):
            pipeline.add_subtitles(self.video, 'en', None, *args, **kwargs)


        # Not passing at all.
        _add()
        self.assertEqual(_get_tip_vis(), ('public', ''))

        # Passing nil.
        _add(visibility=None, visibility_override=None)
        self.assertEqual(_get_tip_vis(), ('public', ''))

        # Passing visibility.
        _add(visibility='public')
        self.assertEqual(_get_tip_vis(), ('public', ''))

        _add(visibility='private')
        self.assertEqual(_get_tip_vis(), ('private', ''))

        # Passing visibility_override.
        _add(visibility_override='')
        self.assertEqual(_get_tip_vis(), ('public', ''))

        _add(visibility_override='public')
        self.assertEqual(_get_tip_vis(), ('public', 'public'))

        _add(visibility_override='private')
        self.assertEqual(_get_tip_vis(), ('public', 'private'))

        # Passing nonsense.
        self.assertRaises(ValidationError, lambda: _add(visibility=42))
        self.assertRaises(ValidationError, lambda: _add(visibility='llamas'))
        self.assertRaises(ValidationError, lambda: _add(visibility_override=3.1415))
        self.assertRaises(ValidationError, lambda: _add(visibility_override='cats'))

    def test_parents(self):
        def _add(language_code, parents):
            return pipeline.add_subtitles(self.video, language_code, None,
                                          parents=parents)

        def _get_tip_parents(language_code):
            sl = SubtitleLanguage.objects.get(video=self.video,
                                              language_code=language_code)
            tip = sl.get_tip(full=True)
            return sorted(["%s%d" % (v.language_code, v.version_number)
                           for v in tip.parents.full()])

        def _assert_notfound(l):
            self.assertRaises(SubtitleVersion.DoesNotExist, l)

        def _assert_badtype(l):
            self.assertRaises(ValueError, l)


        # First, check the default parents.
        #
        # en fr
        #
        #    1
        # 2
        # |
        # 1
        en1 = _add('en', None)
        self.assertEqual(_get_tip_parents('en'), [])

        en2 = _add('en', None)
        self.assertEqual(_get_tip_parents('en'), ['en1'])

        fr1 = _add('fr', None)
        self.assertEqual(_get_tip_parents('fr'), [])

        # Parents can be SV objects directly.
        #
        # en fr de
        #       1
        #      /
        #     /
        #    3
        #    |
        #    2
        #   /|
        #  / 1
        # 2
        # |
        # 1
        fr2 = _add('fr', [en2])
        self.assertEqual(_get_tip_parents('fr'), ['en2', 'fr1'])

        fr3 = _add('fr', None)
        self.assertEqual(_get_tip_parents('fr'), ['fr2'])

        de1 = _add('de', [fr3])
        self.assertEqual(_get_tip_parents('de'), ['fr3'])

        # Parents can be given with just their IDs.
        #
        # cy en fr de
        # 2___
        # |   \
        # 1    \
        # |\____|_
        # |     | \
        # |     |  1
        # |     | /
        # |     |/
        # |     3
        # |     |
        # |     2
        #  \   /|
        #   \ / 1
        #    2
        #    |
        #    1
        cy1 = _add('cy', [en2.id, de1.id])
        self.assertEqual(_get_tip_parents('cy'), ['de1', 'en2'])

        cy2 = _add('cy', [fr3.id])
        self.assertEqual(_get_tip_parents('cy'), ['cy1', 'fr3'])

        # Parents can be language_code, version_number pairs for convenience.
        #
        # en fr de ja
        #       2
        #       |\
        #       | \
        #       |  1
        #       | /|
        #       |/ |
        #       1  |
        #      /   |
        #     /    |
        #    3-----+
        #    |
        #    2
        #   /|
        #  / 1
        # 2
        # |
        # 1
        ja1 = _add('ja', [('fr', 3), ['de', 1]])
        self.assertEqual(_get_tip_parents('ja'), ['de1', 'fr3'])

        de2 = _add('de', [('ja', 1)])
        self.assertEqual(_get_tip_parents('de'), ['de1', 'ja1'])

        # Parent specs can be mixed in a single add call.
        #
        # en fr de ja
        #      ____2
        #     / / /|
        #    / / / |
        #   / / |  |
        #  / |  2  |
        # |  |  |\ |
        # |  |  | \|
        # |  |  |  1
        # |  |  | /|
        # |  |  |/ |
        # |  |  1  |
        # |  | /   |
        # |  |/    |
        # |  3-----+
        # |  |
        # |  2
        # | /|
        # |/ 1
        # 2
        # |
        # 1
        ja2 = _add('ja', [de2, ('fr', 3), en2.id])
        self.assertEqual(_get_tip_parents('ja'), ['de2', 'en2', 'fr3', 'ja1'])

        # Check that nonsense IDs don't work.
        _assert_notfound(lambda: _add('en', [12345]))
        _assert_notfound(lambda: _add('en', [0]))
        _assert_notfound(lambda: _add('en', [-1]))

        # Check that nonsense pairs don't work.
        _assert_notfound(lambda: _add('en', [['en', 400]]))
        _assert_notfound(lambda: _add('en', [['fr', -10]]))
        _assert_notfound(lambda: _add('en', [['pt', 1]]))
        _assert_notfound(lambda: _add('en', [['puppies', 1]]))

        # Check that nonsense types don't work.
        _assert_badtype(lambda: _add('en', "Hello!"))
        _assert_badtype(lambda: _add('en', ["Hello!"]))
        _assert_badtype(lambda: _add('en', [{}]))

        # Shut up, Pyflakes.
        assert (en1 and en2 and fr1 and fr2 and fr3 and de1 and de2 and cy1 and
                cy2 and ja1 and ja2)

    def test_bad_parents(self):
        """Test trying to add invalid parents."""

        def _add(language_code, parents):
            return pipeline.add_subtitles(self.video, language_code, None,
                                          parents=parents)

        def _assert_invalid(l):
            self.assertRaises(ValidationError, l)


        # en fr de cy
        #          2
        #   ______/|
        #  /       1
        # |    ___/
        # |   /
        # |  4
        # |  |\
        # 3  | \
        # |  |  |
        # |  3  |
        # |  |\ |
        # |  2 \|
        # |  |  |
        # |  |  2
        # |  |  |
        # |  1  |
        # | / \ |
        # |/   \|
        # 2     |
        # |     |
        # 1     1
        en1 = _add('en', [])
        en2 = _add('en', [])
        de1 = _add('de', [])
        fr1 = _add('fr', [en2, de1])
        de2 = _add('de', [])
        fr2 = _add('fr', [])
        fr3 = _add('fr', [de2])
        en3 = _add('en', [])
        fr4 = _add('fr', [de2])
        cy1 = _add('cy', [fr4])
        cy2 = _add('cy', [en3])

        # Versions cannot have multiple parents from the same language.
        _assert_invalid(lambda: _add('en', [fr1, fr2]))
        _assert_invalid(lambda: _add('en', [de1, fr1, de2]))
        _assert_invalid(lambda: _add('en', [en1, en2]))
        _assert_invalid(lambda: _add('en', [en1]))

        # Versions cannot have duplicate parents.  We could remove this
        # restriction and collapse it down automatically, but needing to do so
        # is almost certainly a sign of a mistake, so it's better to fail loudly
        # instead.
        _assert_invalid(lambda: _add('en', [fr4, fr4]))

        # Versions cannot have parents that precede other parents in their
        # lineage.
        _assert_invalid(lambda: _add('fr', [en1]))
        _assert_invalid(lambda: _add('fr', [de1]))
        _assert_invalid(lambda: _add('cy', [fr1]))
        _assert_invalid(lambda: _add('cy', [fr3]))
        _assert_invalid(lambda: _add('cy', [de1]))
        _assert_invalid(lambda: _add('cy', [en1]))

        # Shut up, Pyflakes.
        assert (en1 and en2 and en3 and fr1 and fr2 and fr3 and fr4 and
                de1 and de2 and cy1 and cy2)

    def test_completion(self):
        def _get_sl_completion():
            sl = SubtitleLanguage.objects.get(video=self.video,
                                              language_code='en')
            return sl.subtitles_complete

        def _add(complete, subs=None):
            pipeline.add_subtitles(self.video, 'en', subs or [], complete=complete)

        # Completion defaults to false.
        _add(None)
        self.assertEqual(_get_sl_completion(), False)

        # And stays false.
        _add(False)
        self.assertEqual(_get_sl_completion(), False)

        _add(False)
        self.assertEqual(_get_sl_completion(), False)

        # Until we specifically set it to true.
        _add(True)
        self.assertEqual(_get_sl_completion(), True)

        # Then it stays true.
        _add(None)
        self.assertEqual(_get_sl_completion(), True)

        # Until we explicitely set it back to false.
        _add(False)
        self.assertEqual(_get_sl_completion(), False)


        # tell it's complete, but it isn't really:
        _add(True, [(100,200, "hey"), (None, None, "there")])
        self.assertFalse(_get_sl_completion())

    @test_utils.patch_for_test('subtitles.workflows.DefaultLanguageWorkflow.get_actions')
    def test_action(self, mock_get_actions):
        user = UserFactory()
        test_action = MockAction('action')
        mock_get_actions.return_value = [ test_action ]
        version = pipeline.add_subtitles(self.video, 'en', None,
                                         author=user, action='action')
        test_action.perform.assert_called_with(
            user, self.video, version.subtitle_language, version)

    @test_utils.patch_for_test('subtitles.workflows.DefaultLanguageWorkflow.get_actions')
    def test_action_completes_subtitles(self, mock_get_actions):
        user = UserFactory()
        test_action = MockAction('action', True)
        mock_get_actions.return_value = [ test_action ]
        version = pipeline.add_subtitles(self.video, 'en',
                                         SubtitleSetFactory(num_subs=10),
                                         author=user, action='action')

        self.assertEqual(version.subtitle_language.subtitles_complete, True)
        test_action.perform.assert_called_with(
            user, self.video, version.subtitle_language, version)

    @test_utils.patch_for_test('subtitles.workflows.DefaultLanguageWorkflow.get_actions')
    def test_complete_and_action_set(self, mock_get_actions):
        # test an action that has complete set to a value, but the
        # pipeline.add_subtitles call has complete set to a different value.
        user = UserFactory()
        test_action = MockAction('action', True)
        mock_get_actions.return_value = [ test_action ]
        with assert_raises(ValueError):
            version = pipeline.add_subtitles(self.video, 'en',
                                             SubtitleSetFactory(num_subs=10),
                                             complete=False, author=user,
                                             action='action')

class TestRollbacks(TestCase):
    def setUp(self):
        self.video = make_video()
        self.u1 = UserFactory()
        self.u2 = UserFactory()
        self.anon = User.get_amara_anonymous()

        v = self.video
        self.en1 = pipeline.add_subtitles(v, 'en',
                                          title="title 1", description="desc 1",
                                          subtitles=[(100, 200, "sub 1")],
                                          author=self.u1)
        self.en2 = pipeline.add_subtitles(v, 'en',
                                          title="title 2", description="desc 2",
                                          subtitles=[(100, 200, "sub 2")],
                                          author=self.u2)
        self.en3 = pipeline.add_subtitles(v, 'en',
                                          title="title 3", description="desc 3",
                                          subtitles=[(100, 200, "sub 3")],
                                          author=self.u1)


    def test_basic_rollback(self):
        v = self.video
        en1, en2, en3 = self.en1, self.en2, self.en3

        def _ids(s):
            return set(i.id for i in s)


        source = en1
        rb = pipeline.rollback_to(v, 'en', 1)

        self.assertTrue(rb.is_rollback())
        self.assertEqual(rb.get_rollback_source(full=True), en1)

        self.assertEqual(rb.video.id, source.video.id)
        self.assertEqual(rb.subtitle_language.id, source.subtitle_language.id)
        self.assertEqual(rb.language_code, source.language_code)
        self.assertEqual(rb.get_subtitles(), source.get_subtitles())
        self.assertEqual(rb.title, source.title)
        self.assertEqual(rb.description, source.description)
        self.assertEqual(_ids(rb.parents.full()), _ids([en3]))

    def test_rollback_authors(self):
        v = self.video
        en1, en2, en3 = self.en1, self.en2, self.en3
        u1, us, anon = self.u1, self.u2, self.anon

        # Rollbacks do not inherit the author of their sources.
        rb = pipeline.rollback_to(v, 'en', 1)
        self.assertEqual(rb.author.id, anon.id)

        rb = pipeline.rollback_to(v, 'en', 2)
        self.assertEqual(rb.author.id, anon.id)

        # The rollback author can be explicitely given.
        rb = pipeline.rollback_to(v, 'en', 3, rollback_author=u1)
        self.assertEqual(rb.author.id, u1.id)

        rb = pipeline.rollback_to(v, 'en', 2, rollback_author=u1)
        self.assertEqual(rb.author.id, u1.id)

    def test_rollback_parents(self):
        v = self.video

        de1 = pipeline.add_subtitles(v, 'de', [])
        is1 = pipeline.add_subtitles(v, 'is', [])
        is2 = pipeline.add_subtitles(v, 'is', [], parents=[de1])
        is3 = pipeline.add_subtitles(v, 'is', [])

        def _ids(s):
            return set(i.id for i in s)


        self.assertEqual(_ids(is2.parents.full()), _ids([is1, de1]))

        # Rollbacks do not inherit the parents of their sources.
        is4 = pipeline.rollback_to(v, 'is', 1)
        self.assertEqual(_ids(is4.parents.full()), _ids([is3]))

        is5 = pipeline.rollback_to(v, 'is', 2)
        self.assertEqual(_ids(is5.parents.full()), _ids([is4]))

    def test_rollback_visibility(self):
        v = self.video

        # Fully public subtitle histories result in public rollbacks.
        en1 = pipeline.add_subtitles(v, 'en', [])
        en2 = pipeline.add_subtitles(v, 'en', [])

        rb = pipeline.rollback_to(v, 'en', 1)
        self.assertTrue(rb.is_public())

        is1 = pipeline.add_subtitles(v, 'is', [], visibility='public')
        is2 = pipeline.add_subtitles(v, 'is', [], visibility='private',
                                     visibility_override='public')

        rb = pipeline.rollback_to(v, 'is', 1)
        self.assertTrue(rb.is_public())

        # Fully private subtitle histories result in private rollbacks.
        de1 = pipeline.add_subtitles(v, 'de', [], visibility='private')
        de2 = pipeline.add_subtitles(v, 'de', [], visibility='private')

        rb = pipeline.rollback_to(v, 'de', 1)
        self.assertTrue(rb.is_private())

        fr1 = pipeline.add_subtitles(v, 'fr', [], visibility_override='private')
        fr2 = pipeline.add_subtitles(v, 'fr', [], visibility_override='private')

        rb = pipeline.rollback_to(v, 'fr', 1)
        self.assertTrue(rb.is_private())

        # Histories with a mix of public and private result in public rollbacks.
        pt1 = pipeline.add_subtitles(v, 'pt', [], visibility='public')
        pt2 = pipeline.add_subtitles(v, 'pt', [], visibility='private')

        rb = pipeline.rollback_to(v, 'pt', 1)
        self.assertTrue(rb.is_public())

        pl1 = pipeline.add_subtitles(v, 'pl', [], visibility='private')
        pl2 = pipeline.add_subtitles(v, 'pl', [], visibility='public')

        rb = pipeline.rollback_to(v, 'pl', 1)
        self.assertTrue(rb.is_public())

        ja1 = pipeline.add_subtitles(v, 'ja', [], visibility='private')
        ja2 = pipeline.add_subtitles(v, 'ja', [], visibility='public')
        ja3 = pipeline.add_subtitles(v, 'ja', [], visibility='private')

        rb = pipeline.rollback_to(v, 'ja', 1)
        self.assertTrue(rb.is_public())

        rb = pipeline.rollback_to(v, 'ja', 2)
        self.assertTrue(rb.is_public())

        rb = pipeline.rollback_to(v, 'ja', 3)
        self.assertTrue(rb.is_public())

        # Shut up, Pyflakes.
        assert (en1 and en2 and is1 and is2 and de1 and de2 and fr1 and fr2 and
                pt1 and pt2 and pl1 and pl2 and ja1 and ja2 and ja3)


