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

import datetime

from BeautifulSoup import BeautifulSoup
from babelsubs.storage import SubtitleSet
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.test import TestCase

from auth.models import CustomUser as User
from comments.forms import CommentForm
from comments.models import Comment
from messages.models import Message
from videos.models import Video
from subtitles.models import (
    SubtitleLanguage, SubtitleVersion
)
from subtitles import pipeline
from utils.factories import *
from videos.tasks import video_changed_tasks, send_change_title_email, send_new_version_notification

class SendChangeTitleTaskTest(TestCase):
    def setUp(self):
        self.video = VideoFactory()
        self.follower = UserFactory()
        self.other_user = UserFactory()
        self.video.followers.add(self.follower)
        mail.outbox = []

    def run_send_change_title_email(self, user_id):
        send_change_title_email(self.video.id, user_id, 'old-title', 'new-title')

    def check_emails(self, recipients):
        email_tos = set()
        for email in mail.outbox:
            self.assertEqual(email.subject,
                             u'Video\'s title changed on Amara')
            email_tos.update(email.to)
        self.assertEquals(email_tos, set([u.email for u in recipients]))


    def test_email(self):
        self.run_send_change_title_email(self.other_user.id)
        self.check_emails([self.follower])

    def test_dont_send_email_to_title_changer(self):
        self.run_send_change_title_email(self.follower.id)
        self.check_emails([])

    def test_title_changer_is_none(self):
        self.run_send_change_title_email(None)
        self.check_emails([self.follower])

class TestVideoChangedEmailNotification(TestCase):
    def setUp(self):
        self.user_1 = User.objects.create(username='user_1',
                                          notify_by_email=False)
        self.user_2 = User.objects.create(username='user_2',
                                          notify_by_email=False)

        def setup_video(video, video_url):
            video.primary_audio_language_code = 'en'

        self.video = video = Video.add("http://www.example.com/video.mp4",
                                       self.user_1)[0]
        mail.outbox = []
        self.original_language = SubtitleLanguage.objects.create(
            video=video, language_code='en')
        subs = SubtitleSet.from_list('en',[
            (1000, 2000, "1"),
            (2000, 3000, "2"),
            (3000, 4000, "3"),
        ])
        self.original_language.add_version(subtitles=subs)

    def test_no_version_no_breakage(self):
        initial_count= len(mail.outbox)
        res = send_new_version_notification(1000)
        self.assertEqual(res, False)
        self.assertEqual(len(mail.outbox), initial_count)

    def test_email_diff_not_for_private(self):
        # make sure we never send email for private versions
        initial_count= len(mail.outbox)
        version = self.original_language.get_tip()
        version.visibility = 'private'
        version.save()

        self.assertTrue(version.is_private())
        res = send_new_version_notification(version.pk)
        self.assertEqual(res, False)
        self.assertEqual(len(mail.outbox), initial_count )

    def test_email_diff_notification_wont_fire_without_changes(self):
        initial_count= len(mail.outbox)
        # version is indentical to previous one
        old_version = self.original_language.get_tip()
        new_version = self.original_language.add_version(subtitles=old_version.get_subtitles())
        # no notifications should be sent
        res = send_new_version_notification(new_version.pk)
        self.assertEqual(res, None)
        self.assertEqual(len(mail.outbox), initial_count )

    def test_email_diff_subtitles(self):
        initial_count= len(mail.outbox)
        # set a user who can receive notification
        # make sure we have a different author, else he won't get notified
        author = User(username='author2',
            email='author2@example.com', notify_by_email = True,
            valid_email = True)
        author.save(send_email_confirmation=False)
        # bypass logic from hell
        author.valid_email = True
        author.save()

        # this is needed for the non_editor template check
        user2 = User(username='user2',
            email='user2@example.com', notify_by_email = True,
            valid_email = True)
        user2.save(send_email_confirmation=False)
        # bypass logic from hell
        user2.valid_email = True
        user2.save()
        # version is indentical to previous one
        video, video_url = Video.add(
            "http://wwww.example.com/video-diff.mp4", None)
        video.followers.add(author)
        video.followers.add(user2)

        language = SubtitleLanguage(video=video, language_code='en')
        language.save()
        subs_data = [
            [0, 1000, '1'],
            [1000, 2000, '2'],
        ]

        subtitles_1 = SubtitleSet.from_list('en', subs_data)
        old_version = language.add_version(subtitles=subtitles_1, author=author)

        # now we change the text on the second sub
        subs_data[1][2] = '2 changed'
        # add a regular sub
        subs_data.append([2000, 3000, 'new sub'])
        # add an unsyced
        subs_data.append([None, None, 'no sync'])
        subtitles_2 = SubtitleSet.from_list('en', subs_data)
        new_version = language.add_version(subtitles=subtitles_2)
        self.assertTrue(len(video.notification_list()) > 0)

        res = send_new_version_notification(new_version.pk)
        self.assertNotEqual(res, None)
        # we expect two emails, one is the new-edits-non-editor, and
        # the other for mail_notification.html
        self.assertEqual(len(mail.outbox), initial_count + 2)
        for email_number, email_msg in enumerate(mail.outbox):
            # make sure this is the right message
            self.assertIn("New edits to ", email_msg.subject)
            self.assertIn("video-diff.mp4", email_msg.subject)
            html = BeautifulSoup(email_msg.body)
            html_text = "".join(html.body(text=True)).replace("\n", "")
            if email_number == 0:
                # assert text and timing changes are correct
                self.assertIn('67% of the text', html_text)
                self.assertIn('33% of the timing was changed.', html_text)
            # find the listed text changes to make sure they match
            diff_table =html.findAll('table', attrs={'class':'diffs'})[0]
            old_version_changes = []
            new_version_changes = []
            for i,node in enumerate(diff_table.findAll('td')):
                if i % 2 == 0:
                    old_version_changes.append(node.text)
                else:
                    new_version_changes.append(node.text)
            self.assertEqual(old_version_changes, [u'2', u'', u''])
            self.assertEqual(new_version_changes, [u'2 changed',  u'new sub', u'no sync',])

