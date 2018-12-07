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


from django.test import TestCase

from teams import tasks
from utils.factories import *
from utils.test_utils import *
from videos.models import Video, make_title_from_url

class BulkAddVideosTest(TestCase):
    @patch_for_test('teams.tasks.send_templated_email')
    def setUp(self, mock_send_templated_email):
        self.mock_send_templated_email = mock_send_templated_email
        self.user = UserFactory(is_staff=True, is_superuser=True)
        self.team = TeamFactory(admin=self.user)
        self.url = 'http://example.com/video1.mp4'

    def check_email(self, *messages):
        assert_true(self.mock_send_templated_email.called)
        assert_equal(self.mock_send_templated_email.call_args[0][0], self.user)
        context = self.mock_send_templated_email.call_args[0][3]
        assert_equal([msg.strip() for msg in context['messages']],
                     [unicode(msg.format(url=self.url)) for msg in messages])

    def check_video(self, video_url, primary_audio_language_code='', title='',
                    description='', project=None, duration=None):
        video = Video.objects.get(videourl__url=video_url)

        assert_equal(video.primary_audio_language_code,
                     primary_audio_language_code)
        assert_equal(video.description, description)
        assert_equal(video.duration, duration)
        if title:
            assert_equal(video.title, title)
        else:
            assert_equal(video.title, make_title_from_url(video_url))
        team_video = video.get_team_video()
        assert_equal(team_video.team, self.team)
        if project:
            assert_equal(team_video.project, project)
        else:
            assert_equal(team_video.project, self.team.default_project)
        return video

    def run_add_team_videos(self, video_info_list):
        for video_info in video_info_list:
            for name in ('title', 'description'):
                if name not in video_info:
                    video_info[name] = ''
        tasks.add_team_videos(self.team.pk, self.user.pk, video_info_list)

    def test_import_one_video(self):
        # test the simple case of importing a single video
        self.run_add_team_videos([{
            'url': self.url,
        }])
        self.check_video(self.url)
        self.check_email('Number of videos added to team: 1')

    def test_title(self):
        # test setting the title
        self.run_add_team_videos([{
            'url': self.url,
            'title': 'test-title',
        }])
        self.check_video(self.url, title='test-title')
        self.check_email('Number of videos added to team: 1')

    def test_description(self):
        # test setting the description
        self.run_add_team_videos([{
            'url': self.url,
            'description': 'test-description',
        }])
        self.check_video(self.url, description='test-description')
        self.check_email('Number of videos added to team: 1')

    def test_language(self):
        # test setting the primary audio language
        self.run_add_team_videos([{
            'url': self.url,
            'language': 'en',
        }])
        self.check_video(self.url, primary_audio_language_code='en')
        self.check_email('Number of videos added to team: 1')

    def test_invalid_language(self):
        # test an invalid language code
        self.run_add_team_videos([{
            'url': self.url,
            'language': 'abcdef',
        }])
        self.check_video(self.url, primary_audio_language_code='')
        self.check_email(
            "Badly formated language for {url}: abcdef, ignoring it.",
            'Number of videos added to team: 1')

    def test_create_project(self):
        # test setting the project to an new project
        self.run_add_team_videos([{
            'url': self.url,
            'project': 'New project',
        }])
        project = self.team.project_set.get(slug='new-project')
        self.check_video(self.url, project=project)
        self.check_email('Number of videos added to team: 1')

    def test_existing_project(self):
        # test setting the project to an existing project
        project = self.team.project_set.create(name='Existing project',
                                               slug='existing-project')
        self.run_add_team_videos([{
            'url': self.url,
            'project': 'Existing project',
        }])
        self.check_video(self.url, project=project)
        self.check_email('Number of videos added to team: 1')

    def test_set_duration(self):
        # test setting a duration
        self.run_add_team_videos([{
            'url': self.url,
            'duration': '100',
        }])
        self.check_video(self.url, duration=100)
        self.check_email('Number of videos added to team: 1')

    @with_mock_video_type_registrar
    def test_dont_override_video_type_duration(self, mock_registrar):
        # test that the video type's duration doesn't get overwritten
        mock_registrar.values_to_set['duration'] = 200
        self.run_add_team_videos([{
            'url': self.url,
            'duration': '100',
        }])
        self.check_video(self.url, duration=200)
        self.check_email('Number of videos added to team: 1')

    def test_invalid_duration(self):
        # test an invalid duration
        self.run_add_team_videos([{
            'url': self.url,
            'duration': 'one hundred',
        }])
        self.check_video(self.url, duration=None)
        self.check_email(
            "Badly formated duration for {url}: one hundred, ignoring it.",
            'Number of videos added to team: 1')

    def test_transcript(self):
        # test downloading subtitles using the transcript URL
        mocker = RequestsMocker()
        mocker.expect_request('get', 'http://example.com/transcript.txt',
                              body='first sub\n\nsecond sub')
        with mocker:
            self.run_add_team_videos([{
                'url': self.url,
                'language': 'en',
                'transcript': 'http://example.com/transcript.txt'
            }])
        video = self.check_video(self.url, primary_audio_language_code='en')
        subtitles = video.subtitle_language('en').get_tip().get_subtitles()
        assert_equal([i.text for i in subtitles.subtitle_items()],
                     ['first sub', 'second sub'])

    def test_transcript_no_language(self):
        # we should ignore the transcript URL if no language is set
        mocker = RequestsMocker()
        with mocker:
            self.run_add_team_videos([{
                'url': self.url,
                'transcript': 'http://example.com/transcript.txt'
            }])
        video = self.check_video(self.url)
        assert_equal(video.newsubtitleversion_set.count(), 0)

    def test_complex_case(self):
        # test a complex case with multiple videos and various values set
        url = 'http://example.com/video1.mp4'
        url2 = 'http://example.com/video2.mp4'
        url3 = 'http://example.com/video3.mp4'
        self.run_add_team_videos([
            {
                'url': url,
                'title': 'title 1',
                'description': 'desc 1',
                'duration': '100',
            },
            {
                'url': url2,
                'title': 'title 2',
                'language': 'fr',
                'project': 'project',
                'duration': 'invalid',
            },
            {
                'url': url3,
                'title': 'title 3',
                'language': 'abcdef',
                'project': 'project',
            },
        ])
        project = self.team.project_set.get(slug='project')
        self.check_video(url, title='title 1', description='desc 1',
                         duration=100)
        self.check_video(url2, title='title 2',
                         primary_audio_language_code='fr',
                         project=project)
        self.check_video(url3, title='title 3',
                         project=project)

        self.check_email(
            "Badly formated duration for http://example.com/video2.mp4: invalid, ignoring it.",
            "Badly formated language for http://example.com/video3.mp4: abcdef, ignoring it.",
            'Number of videos added to team: 3',
        )
