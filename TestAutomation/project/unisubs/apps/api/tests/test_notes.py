# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program.  If not, see http://www.gnu.org/licenses/agpl-3.0.html.

from __future__ import absolute_import
import json

from django.test import TestCase
from nose.tools import *
from rest_framework.test import APIClient
import mock

from api.tests.utils import format_datetime_field, user_field_data
from subtitles import workflows
from subtitles.models import SubtitleNote
from utils import test_utils
from utils.factories import *

class TestActionsAPI(TestCase):
    def setUp(self):
        self.video = VideoFactory()
        self.user = UserFactory()
        self.api_path = ('/api/videos/{0}/languages/en'
                         '/subtitles/notes/'.format(self.video.video_id))
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_list(self):
        note = SubtitleNote.objects.create(user=self.user,
                                           video=self.video,
                                           language_code='en',
                                           body='test note')
        # also create a note from another language.  This one shouldn't be
        # included in the reply
        SubtitleNote.objects.create(user=self.user,
                                    video=self.video,
                                    language_code='fr',
                                    body='wrong test note')
        response = self.client.get(self.api_path)
        assert_equal(response.status_code, 200)
        data = json.loads(response.content)
        assert_equal(data['objects'], [
            {
                'user': user_field_data(self.user),
                'body': 'test note',
                'created': format_datetime_field(note.created),
            }
        ])

    def test_post(self):
        real_post = workflows.EditorNotes.post
        patcher = mock.patch('subtitles.workflows.EditorNotes.post',
                             autospec=True)
        with patcher as mock_post:
            mock_post.side_effect = real_post
            response = self.client.post(self.api_path, {
                'body': 'new note',
            })
        assert_equal(response.status_code, 201, response.content)
        mock_post.assert_called_with(mock.ANY, self.user, 'new note')
