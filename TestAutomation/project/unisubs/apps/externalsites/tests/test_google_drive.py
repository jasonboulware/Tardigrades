# Amara, universalsubtitles.org
#
# Copyright (C) 2017 Participatory Culture Foundation
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

from django.test import TestCase
from nose.tools import *

from externalsites import google
from utils.factories import *
from utils.test_utils import *

class GoogleDriveTest(TestCase):
    @patch_for_test('externalsites.google.get_service_account_access_token')
    def test_get_info(self, get_service_account_access_token):
        get_service_account_access_token.return_value = 'test-access-token'
        mocker = RequestsMocker()
        mocker.expect_request(
            'get',
            'https://www.googleapis.com/drive/v3/files/test-file-id',
            params={
                'fields': 'name,description,mimeType,webContentLink,thumbnailLink,videoMediaMetadata',
            }, headers={
                'Authorization': 'Bearer test-access-token',
            },
            body=json.dumps({
                "name": "Test title",
                "description": "Test description",
                "mimeType": "video/mp4",
                "webContentLink": "https://example.com/download/",
                "thumbnailLink": "https://example.com/thumbnail.jpg",
                "videoMediaMetadata": {
                     "width": 1920,
                     "height": 1080,
                     "durationMillis": "100400"
                 },
            })
        )
        google.get_drive_file_info.run_original_for_test()
        with mocker:
            file_info = google.get_drive_file_info('test-file-id')
        assert_equal(file_info.title, 'Test title')
        assert_equal(file_info.description, 'Test description')
        assert_equal(file_info.duration, 100)
        assert_equal(file_info.content_url,
                     "https://example.com/download/")
        assert_equal(file_info.thumbnail_url,
                     'https://example.com/thumbnail.jpg')
        assert_equal(file_info.embed_url,
                     'https://drive.google.com/file/d/test-file-id/preview')
        assert_equal(get_service_account_access_token.call_args, mock.call(
            'https://www.googleapis.com/auth/drive.readonly'))

    @patch_for_test('externalsites.google.get_service_account_access_token')
    def test_missing_metadata(self, get_service_account_access_token):
        # Not all fields are guarenteed to be returned.  Test what happens
        # when they're not there
        get_service_account_access_token.return_value = 'test-access-token'
        mocker = RequestsMocker()
        mocker.expect_request(
            'get',
            'https://www.googleapis.com/drive/v3/files/test-file-id',
            params={
                'fields': 'name,description,mimeType,webContentLink,thumbnailLink,videoMediaMetadata',
            }, headers={
                'Authorization': 'Bearer test-access-token',
            },
            body=json.dumps({
                "name": "Test title",
            })
        )
        google.get_drive_file_info.run_original_for_test()
        with mocker:
            file_info = google.get_drive_file_info('test-file-id')
        assert_equal(file_info.title, 'Test title')
        assert_equal(file_info.description, None)
        assert_equal(file_info.duration, None)
        assert_equal(file_info.content_url, None)
        assert_equal(file_info.thumbnail_url, None)
        assert_equal(get_service_account_access_token.call_args, mock.call(
            'https://www.googleapis.com/auth/drive.readonly'))
