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
from django.conf import settings
from django.core import mail

from localeurl.utils import universal_url, DEFAULT_PROTOCOL
from subtitles import pipeline
from utils.factories import *

class UniversalUrlsTest(TestCase):
    def test_universal_urls(self):
        domain = settings.HOSTNAME
        vid = 'test-video-id'
        correct_url = "%s://%s/videos/%s/info/" % (
            DEFAULT_PROTOCOL, domain, vid)
        self.assertEqual(correct_url,
                         universal_url("videos:video",
                                       kwargs={"video_id":vid}))
        self.assertEqual(correct_url,
                         universal_url("videos:video", args=(vid,)))

class VideoCommentEmailTest(TestCase):
    def setUp(self):
        self.user = UserFactory(email='video-user@example.com')
        self.other_user = UserFactory(email='other-user@example.com')
        self.video = VideoFactory(user=self.user)
        for x in range(5):
            self.video.followers.add(
                UserFactory(email='follower-%s@example.com' % x))
        self.followers = list(self.video.followers.all())
        mail.outbox = []

    def comment_subject(self, user):
        return u'%s left a comment on the video %s' % (
            user, self.video.title_display())

    def check_emails(self, subject, correct_recipients):
        recipients = set()
        for email in mail.outbox:
            recipients.update(email.to)
            self.assertEqual(email.subject, subject)
        self.assertEqual(recipients,
                         set([u.email for u in correct_recipients]))
        mail.outbox = []

    def test_video_comment_emails(self):
        # normally we should send notifications to all followers
        comment = CommentFactory(content_object=self.video,
                                 user=self.other_user)
        self.check_emails(self.comment_subject(self.other_user),
                          self.followers)
        # if one of those users posts the comment, then we should not send it
        # to them
        comment = CommentFactory(content_object=self.video,
                                 user=self.followers[0])
        self.check_emails(self.comment_subject(self.followers[0]),
                          self.followers[1:])

    def test_language_comment_emails(self):
        # posting a comment on the language should also notify the video
        # followers
        pipeline.add_subtitles(self.video, 'en', None)
        comment = CommentFactory(
            content_object=self.video.subtitle_language('en'),
            user=self.other_user)
        self.check_emails(self.comment_subject(self.other_user),
                          self.followers)
