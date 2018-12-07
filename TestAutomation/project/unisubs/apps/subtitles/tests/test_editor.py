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
from __future__ import absolute_import

import datetime
import json

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from auth.models import CustomUser
from subtitles import pipeline
from subtitles.tests.utils import (
    make_video
)
from teams.models import TeamMember
from utils.factories import *

class EditorViewTest(TestCase):

    def setUp(self):
        self.user = CustomUser.objects.get_or_create(username='admin')[0]
        self.user.set_password('admin')
        self.user.save()

    def _login(self, user=None):
        user = user or self.user
        self.client.login(username=user.username, password='admin')

    def _get_boostrapped_data(self, response):
        '''
        Get the data that is passed to the angular app as a json object
        writen on a page <script> tag, as a python dict
        '''
        return json.loads(response.context['editor_data'])

    def test_login_required(self):
        video = make_video()
        url = reverse("subtitles:subtitle-editor", args=(video.video_id,'en'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        # redirect from the login_required decorator does not include
        # the locale name, but the reverse we use does ;)
        login_url = "/".join(reverse("auth:login").split("/")[2:])
        self.assertIn(login_url, response['location'])
        self._login()
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_valid_language_required(self):
        video = make_video()
        self._login()
        url = reverse("subtitles:subtitle-editor", args=(video.video_id,'xxxxx'))
        self.assertRaises(ValidationError, self.client.get, url)

    def test_apikey_present(self):
        video = make_video()
        self._login()
        url = reverse("subtitles:subtitle-editor", args=(video.video_id,'en'))
        response =  self.client.get(url)
        data = self._get_boostrapped_data(response)
        self.assertEqual(self.user.get_api_key(), data['authHeaders']['x-apikey'])
        self.assertEqual(self.user.username, data['authHeaders']['x-api-username'])

    def test_permission(self):
        # test public video is ok
        # test video on hidden team to non members is not ok
        # test video on public team with memebership requirements
        pass

    def test_writelock(self):
        # test two users can't access the same langauge at the same time
        # expire the first write lock
        # test second user can aquire it
        pass

    def test_translated_language_present(self):
        # make sure if the subtitle version to be edited
        # is a translation, that we bootstrap the data correctly on
        # the editor data
        pass

    def test_stand_alone_langauge_loads(self):
        # make sure the view doesn't blow up if there is
        # no translation to be showed
        pass

class NotLoggedInEditor(TestCase):
    def setUp(self):
        team = TeamFactory(slug="private-team", name="Private Team")
        self.public_video = VideoFactory()
        self.team_video = VideoFactory()
        self.user = UserFactory()
        TeamMember.objects.create_first_member(team, self.user)
        TeamVideoFactory(team=team, video=self.team_video, added_by=self.user)
        self.user.get_api_key()
        self.language_code = 'en'
        self.public_language = self.public_video.subtitle_language(self.language_code,
                                                     create=True)
        self.team_language = self.team_video.subtitle_language(self.language_code,
                                                     create=True)
        self.version_public = pipeline.add_subtitles(self.public_video, self.language_code,
                                              SubtitleSetFactory(), author=self.user,
                                              action='save-draft')
        self.version_private = pipeline.add_subtitles(self.team_video, self.language_code,
                                              SubtitleSetFactory(), author=self.user,
                                              action='save-draft')
    def test_download_subtitles(self):
        url = reverse("subtitles:download", args=(self.public_video.video_id,
                                                  self.language_code,
                                                  self.version_public.version_number,
                                                  "subs", "vtt"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        url = reverse("subtitles:download", args=(self.team_video.video_id,
                                                  self.language_code,
                                                  self.version_private.version_number,
                                                  "subs", "vtt"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        response = self.client.get(url, HTTP_X_API_USERNAME=self.user.username, HTTP_X_APIKEY=self.user.get_api_key())
        self.assertEqual(response.status_code, 200)
