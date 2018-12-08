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

import os
import json

from django.conf import settings
from django.urls import reverse

from auth.models import CustomUser as User
from subtitles import pipeline
from subtitles.models import ORIGIN_UPLOAD
from videos import metadata_manager
from videos.models import Video, SubtitleLanguage, Subtitle
from videos.tasks import video_changed_tasks
from videos.tests.data import (
    get_video, get_user, make_subtitle_language
)
from videos.tests.videotestutils import (
    WebUseTest, refresh_obj, _create_trans
)
from widget.rpc import Rpc

up = os.path.dirname

def refresh(m):
    return m.__class__._default_manager.get(pk=m.pk)

class UploadRequiresLoginTest(WebUseTest):
    def test_upload_requires_login(self):
        # When not logged in trying to upload should redirect to the login page.
        self._simple_test('videos:upload_subtitles', status=302)

class UploadSubtitlesTest(WebUseTest):
    def _srt(self, filename):
        return os.path.join(settings.PROJECT_ROOT, 'apps/videos/fixtures',
                            filename)

    def _data(self, video, language_code, primary_audio_language_code,
              from_language_code, complete, draft):
        return {
            'video': video.pk,
            'language_code': language_code,
            'primary_audio_language_code': primary_audio_language_code,
            'from_language_code': from_language_code or '',
            'complete': '1' if complete else '0',
            'draft': draft,
        }

    def _upload(self, video, language_code, primary_audio_language_code,
                from_language_code, complete, filename):
        with open(self._srt(filename)) as draft:
            return self.client.post(
                reverse('videos:upload_subtitles'),
                self._data(video, language_code, primary_audio_language_code,
                           from_language_code, complete, draft))


    def setUp(self):
        self._login()


    def _assertVersionCount(self, video, n):
        self.assertEqual(video.newsubtitleversion_set.full().count(), n)


    def _assertCounts(self, video, counts):
        self.assertEqual(
            counts, dict([(sl.language_code, sl.subtitleversion_set.full().count())
                            for sl in video.newsubtitlelanguage_set.all()]))


    # Basic uploading tests.
    def test_upload_subtitles_primary_language(self):
        # Start with a fresh video.
        video = get_video()
        self.assertEqual(video.primary_audio_language_code, '')
        self.assertFalse(video.has_original_language())
        self.assertIsNone(video.complete_date)

        # Upload subtitles in the primary audio language.
        response = self._upload(video, 'en', 'en', None, True, 'test.srt')
        self.assertEqual(response.status_code, 200)

        video = refresh(video)

        # The video should now have a primary audio language, since it was set
        # as part of the upload process.
        self.assertEqual(video.primary_audio_language_code, 'en')
        self.assertTrue(video.has_original_language())

        # Ensure that the subtitles actually got uploaded too.
        sl_en = video.subtitle_language()
        self.assertIsNotNone(sl_en)
        self.assertEqual(sl_en.subtitleversion_set.full().count(), 1)

        en1 = sl_en.get_tip()
        subtitles = en1.get_subtitles()
        self.assertEqual(en1.subtitle_count, 32)
        self.assertEqual(len(subtitles), 32)

        # Now that we've uploaded a complete set of subtitles, the video and
        # language should be marked as completed.
        self.assertIsNotNone(video.complete_date)
        self.assertTrue(sl_en.subtitles_complete)

        # Let's make sure they didn't get mistakenly marked as a translation.
        self.assertIsNone(sl_en.get_translation_source_language())

        # Upload another version just to be sure.
        response = self._upload(video, 'en', 'en', None, True, 'test.srt')
        self.assertEqual(response.status_code, 200)

        video = refresh(video)
        sl_en = refresh(sl_en)

        self.assertEqual(sl_en.subtitleversion_set.full().count(), 2)

    def test_upload_subtitles_non_primary_language(self):
        # Start with a fresh video.
        video = get_video()
        self.assertEqual(video.primary_audio_language_code, '')
        self.assertFalse(video.has_original_language())
        self.assertIsNone(video.complete_date)

        # Upload subtitles in a language other than the primary.
        response = self._upload(video, 'fr', 'en', None, True, 'test.srt')
        self.assertEqual(response.status_code, 200)

        video = refresh(video)

        # The video should now have a primary audio language, since it was set
        # as part of the upload process.
        self.assertEqual(video.primary_audio_language_code, 'en')

        # But it doesn't have a SubtitleLanguage for it.
        self.assertFalse(video.has_original_language())
        self.assertIsNone(video.subtitle_language())
        self.assertIsNone(video.get_primary_audio_subtitle_language())

        # Ensure that the subtitles actually got uploaded too.
        sl_fr = video.subtitle_language('fr')
        self.assertIsNotNone(sl_fr)
        self.assertEqual(sl_fr.subtitleversion_set.full().count(), 1)

        fr1 = sl_fr.get_tip()
        subtitles = fr1.get_subtitles()
        self.assertEqual(fr1.subtitle_count, 32)
        self.assertEqual(len(subtitles), 32)

        # Now that we've uploaded a complete set of subtitles, the video and
        # language should be marked as completed.
        self.assertIsNotNone(video.complete_date)
        self.assertTrue(sl_fr.subtitles_complete)

        # Let's make sure they didn't get mistakenly marked as a translation.
        # They're not in the primary language but are still a transcription.
        self.assertIsNone(sl_fr.get_translation_source_language())

        # Upload another version just to be sure.
        response = self._upload(video, 'fr', 'en', None, True, 'test.srt')
        self.assertEqual(response.status_code, 200)

        video = refresh(video)
        sl_fr = refresh(sl_fr)

        self.assertFalse(video.has_original_language())
        self.assertIsNone(video.subtitle_language())
        self.assertIsNone(video.get_primary_audio_subtitle_language())
        self.assertIsNotNone(video.complete_date)
        self.assertTrue(sl_fr.subtitles_complete)
        self.assertEqual(sl_fr.subtitleversion_set.full().count(), 2)

    def test_upload_respects_lock(self):
        user1 = get_user(1)
        user2 = get_user(2)
        video = get_video()
        sl_en = make_subtitle_language(video, 'en')

        # Lock the language for user 1.
        sl_en.writelock(user1, 'test-browser-id')
        self.assertTrue(sl_en.is_writelocked)

        # Now try to upload subtitles as user 2.
        self._login(user2)
        self._upload(video, 'en', 'en', None, True, 'test.srt')

        # The subtitles should not have been created.
        #
        # We can't really tests the response here because the upload_subtitles
        # view is terrible and always returns a 200 with a horrible mix of HTML
        # and JSON as a response.  So instead we'll just make sure that the
        # subtitles were not actually created.
        self.assertFalse(sl_en.subtitleversion_set.full().exists())

        # User 1 has the writelock, so uploading subtitles should work for them.
        self._login(user1)
        self._upload(video, 'en', 'en', None, True, 'test.srt')
        self.assertEqual(sl_en.subtitleversion_set.full().count(), 1)

        # User 1 still has the writelock, so user 2 still can't upload.
        self._login(user2)
        self._upload(video, 'en', 'en', None, True, 'test.srt')
        self.assertEqual(sl_en.subtitleversion_set.full().count(), 1)

        # Release the writelock.
        sl_en.release_writelock()

        # Now user 2 can finally upload their subtitles.
        self._login(user2)
        self._upload(video, 'en', 'en', None, True, 'test.srt')
        self.assertEqual(sl_en.subtitleversion_set.full().count(), 2)

    def test_upload_unsynced_subs(self):
        video = get_video()
        self._upload(video, 'en', 'en', None, True, 'subs-with-unsynced.srt')
        self._assertCounts(video, {'en': 1})

        subs = video.subtitle_language('en').get_tip().get_subtitles()

        fully_synced = len([1 for start, end, _, _ in subs if start and end])
        synced_begin = len([1 for start, _, _, _ in subs if start])
        synced_end = len([1 for _, end, _, _ in subs if end])
        fully_unsynced = len([1 for start, end, _, _ in subs
                              if (not start) and (not end)])
        
        self.assertEqual(fully_synced, 56)
        self.assertEqual(synced_begin, 57)
        self.assertEqual(synced_end, 56)
        self.assertEqual(fully_unsynced, 5)


    # Translation-related tests.
    def test_upload_translation(self):
        video = get_video()
        self._assertVersionCount(video, 0)

        # Try uploading a translation of language that doesn't exist.
        self._upload(video, 'fr', 'en', 'en', True, 'test.srt')

        # This should fail.  Translations need to be based on an existing
        # langauge.
        self._assertVersionCount(video, 0)

        # Let's upload the first language.
        self._upload(video, 'en', 'en', None, True, 'test.srt')
        self._assertVersionCount(video, 1)

        # And now uploading a translation should work.
        self._upload(video, 'fr', 'en', 'en', True, 'test.srt')
        self._assertVersionCount(video, 2)

        # Translations of translations are okay too I guess.
        self._upload(video, 'ru', 'en', 'fr', True, 'test.srt')
        self._assertVersionCount(video, 3)

    def test_upload_translation_over_nontranslation(self):
        video = get_video()
        self._assertVersionCount(video, 0)

        self._upload(video, 'en', 'en', None, True, 'test.srt')
        self._upload(video, 'de', 'en', None, True, 'test.srt')
        self._assertVersionCount(video, 2)

        # You can't upload a translation over an existing non-translation
        # language.
        self._upload(video, 'de', 'en', 'en', True, 'test.srt')
        self._assertVersionCount(video, 2)

    def test_upload_translation_over_other_translation(self):
        video = get_video()
        self._assertVersionCount(video, 0)

        self._upload(video, 'en', 'en', None, True, 'test.srt')
        self._upload(video, 'de', 'en', None, True, 'test.srt')
        self._upload(video, 'fr', 'en', 'en', True, 'test.srt')
        self._assertVersionCount(video, 3)

        # Now fr is  translated from de, this should fail
        self._upload(video, 'fr', 'en', 'de', True, 'test.srt')
        self._assertVersionCount(video, 3)


    def test_upload_to_language_with_dependents(self):
        video = get_video()
        self._assertVersionCount(video, 0)

        # You CAN upload subtitles to a language that already has dependents (it
        # will just fork the dependents).
        self._upload(video, 'en', 'en', None, True, 'test.srt')
        self._upload(video, 'fr', 'en', 'en', True, 'test.srt')
        self._assertVersionCount(video, 2)

        self._upload(video, 'en', 'en', None, True, 'test.srt')
        self._assertVersionCount(video, 3)

    def test_upload_translation_with_fewer_subs(self):
        video = get_video()
        self._assertVersionCount(video, 0)

        self._upload(video, 'en', 'en', None, True, 'test.srt')
        self._assertVersionCount(video, 1)

        # Uploading a translation with a different number of subs than the
        # original language is not allowed.
        self._upload(video, 'is', 'en', 'en', True, 'test_fewer_subs.srt')
        self.assertEqual(video.newsubtitlelanguage_set.count(), 2)

        self._upload(video, 'is', 'en', 'en', True, 'test.srt')
        self.assertEqual(video.newsubtitlelanguage_set.count(), 2)

    def test_upload_and_rollbacks(self):
        video = get_video()

        self._assertCounts(video, {})

        self._upload(video, 'en', 'en', None, True, 'test.srt')
        self._upload(video, 'en', 'en', None, True, 'test_fewer_subs.srt')
        self._upload(video, 'fr', 'en', 'en', True, 'test_fewer_subs.srt')
        self._assertCounts(video, {'en': 2, 'fr': 1})

        # We now have:
        #
        # en fr
        #    1
        #   /
        #  /
        # 2
        # |
        # 1

        # Let's sanity check that we can still upload to English now that it has
        # a dependent language (French).
        self._upload(video, 'en', 'en', None, True, 'test_fewer_subs.srt')
        self._assertCounts(video, {'en': 3, 'fr': 1})

        # The translation should now be forked.
        self.assertTrue(video.subtitle_language('fr').is_forked)

        # Now let's roll English back to v1.
        pipeline.rollback_to(video, 'en', 1)
        self._assertCounts(video, {'en': 4, 'fr': 1})

        # And try uploading something on top of the rollback.
        self._upload(video, 'en', 'en', None, True, 'test_fewer_subs.srt')
        self._assertCounts(video, {'en': 5, 'fr': 1})


    def test_upload_origin_on_version(self):
        # Start with a fresh video.
        video = get_video()

        self._upload(video, 'fr', 'en', None, True, 'test.srt')
        sv = video.newsubtitlelanguage_set.get(language_code='fr').get_tip()
        self.assertEqual(sv.origin, ORIGIN_UPLOAD)
