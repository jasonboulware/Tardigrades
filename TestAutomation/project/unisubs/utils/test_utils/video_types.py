# Amara, universalsubtitles.org
#
# Copyright (C) 2016 Participatory Culture Foundation
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

"""
VideoType test code

This module contains codes to mock up the VideoType code.  This is the code
that handles the specifics of various videos (Youtube, Vimeo, etc).  The main
reason you would want to use it is to test the video type setting a value on a
created video, e.g. setting the duration
"""

import mock

from utils.test_utils.monkeypatch import patch_for_test

class MockVideoType(mock.Mock):
    """Mock VideoType object.
    """

    abbreviation = 'T'

    def __init__(self, url, **values_to_set):
        super(MockVideoType, self).__init__(
            owner_username=mock.Mock(return_value=None),
            convert_to_video_url=mock.Mock(return_value=url),
            set_values=mock.Mock(
                side_effect=lambda v, u, t, r: v.__dict__.update(self.values_to_set)
            ),
        )
        self.url = url
        self.values_to_set = values_to_set
        self.video_id = 'test-video-id'

def with_mock_video_type_registrar(test_method):
    """Decorator to force a mock video type to be used for Video.add()

    This decorator installs a mock object in the video type registrar object
    and passes it to the test function.  You can then use the values_to_set
    attribute to force the MockVideoType to set some values on newly created
    videos.

    Example:
        @with_mock_video_type_registrar
        def test_func(self, mock_registrar):
            mock_registrar.values_to_set['duration'] = 100
            video, video_url = Video.add(...)
            # video.duration will be 100
    """
    @patch_for_test('videos.models.video_type_registrar')
    def wrapper(self, mock_registrar, *args, **kwargs):
        mock_registrar.values_to_set = {}
        def video_type_for_url(url):
            return MockVideoType(url, **mock_registrar.values_to_set)
        mock_registrar.video_type_for_url.side_effect = video_type_for_url

        patcher2 = mock.patch('videos.types.video_type_registrar',
                              mock_registrar)
        patcher2.start()
        self.addCleanup(patcher2.stop)
        test_method(self, mock_registrar, *args, **kwargs)
    return wrapper
