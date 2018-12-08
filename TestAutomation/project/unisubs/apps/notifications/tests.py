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

from contextlib import contextmanager
from datetime import timedelta
from django.db.models import Max
from django.test import TestCase
from nose.tools import *
from requests.auth import HTTPBasicAuth
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
import mock

from notifications import handlers
from notifications.models import TeamNotificationSettings, TeamNotification
from notifications.tasks import REMOVE_AFTER, MIN_KEEP, prune_notification_history
from subtitles import pipeline
from subtitles.signals import subtitles_imported
from teams.models import TeamMember
from utils import dates
from utils.factories import *
from utils.test_utils import *
import subtitles.signals
import videos.signals

class TestNotificationHandlerLookup(TestCase):
    # Test that we lookup the correct NotificationHandler and call the correct
    # method on various events
    def setUp(self):
        self.user = UserFactory()
        self.team = TeamFactory(admin=self.user)
        self.url = 'http://example.com'

    def test_extra_teams_lookup(self):
        team = TeamFactory()
        team_extra_1 = TeamFactory()
        team_extra_2 = TeamFactory()
        team_extra_3 = TeamFactory()
        settings = TeamNotificationSettings(team=team,
                                            type='mock-type',
                                            url='http://example.com/')
        settings.save()
        settings.extra_teams.add(team_extra_1)
        settings.extra_teams.add(team_extra_2)
        assert_equal(TeamNotificationSettings.lookup(team), settings)
        assert_equal(TeamNotificationSettings.lookup(team_extra_1), settings)
        assert_equal(TeamNotificationSettings.lookup(team_extra_2), settings)
        assert_equal(TeamNotificationSettings.lookup(team_extra_3), None)

    def test_extra_teams_lookup_primary_first(self):
        team_1 = TeamFactory()
        team_2 = TeamFactory()
        team_3 = TeamFactory()
        settings_1 = TeamNotificationSettings(team=team_1,
                                            type='mock-type',
                                            url='http://example.com/')
        settings_2 = TeamNotificationSettings(team=team_2,
                                            type='mock-type',
                                            url='http://example.com/')
        settings_1.save()
        settings_2.save()
        settings_1.extra_teams.add(team_2)
        settings_1.extra_teams.add(team_3)
        assert_equal(TeamNotificationSettings.lookup(team_1), settings_1)
        assert_equal(TeamNotificationSettings.lookup(team_2), settings_2)
        assert_equal(TeamNotificationSettings.lookup(team_3), settings_1)

    def test_extra_teams_lookup_duplicate_teams(self):
        team = TeamFactory()
        team_extra_1 = TeamFactory()
        team_extra_2 = TeamFactory()
        settings = TeamNotificationSettings(team=team,
                                            type='mock-type',
                                            url='http://example.com/')
        settings.save()
        settings.extra_teams.add(team_extra_1)
        settings.extra_teams.add(team_extra_2)
        settings.extra_teams.add(team_extra_1)
        assert_equal(TeamNotificationSettings.lookup(team), settings)
        assert_equal(TeamNotificationSettings.lookup(team_extra_1), settings)
        assert_equal(TeamNotificationSettings.lookup(team_extra_2), settings)

    @contextmanager
    def patch_handler_lookup(self, call_expected=True):
        mock_settings = mock.Mock(
            team=self.team,
            type='unittest',
            url='http://example.com/unittests')
        mock_handler_class = mock.Mock()
        patcher = mock.patch(
            'notifications.models.TeamNotificationSettings.lookup')
        handlers._registry['unittest'] = mock_handler_class
        with patcher as lookup:
            lookup.return_value = mock_settings
            # We yield the mock handler instance.  This is what gets bound to
            # the as clause
            yield mock_handler_class.return_value
        if call_expected:
            # check that the handler gets instantiated with the correct arguments
            assert_true(mock_handler_class.called)
            assert_equal(mock_handler_class.call_args, mock.call(mock_settings))
        else:
            assert_false(mock_handler_class.called)
        del handlers._registry['unittest']

    def test_on_video_added(self):
        with self.patch_handler_lookup() as mock_handler:
            video = VideoFactory(team=self.team)
        assert_equal(mock_handler.on_video_added.call_args,
                     mock.call(video, None))
        # A second save shouldn't cause the handler to be called again
        with self.patch_handler_lookup(False) as mock_handler:
            video.get_team_video().save()
            assert_false(mock_handler.on_video_added.called)

    def test_on_video_added_from_other_team(self):
        other_team = TeamFactory()
        team_video = TeamVideoFactory(team=other_team)
        with self.patch_handler_lookup() as mock_handler:
            team_video.move_to(self.team)
        assert_equal(mock_handler.on_video_added.call_args,
                     mock.call(team_video.video, other_team))

    def test_on_video_removed(self):
        tv = TeamVideoFactory(team=self.team)
        with self.patch_handler_lookup() as mock_handler:
            tv.remove(self.user)
        assert_equal(mock_handler.on_video_removed.call_args,
                     mock.call(tv.video, None))

    def test_on_video_moved_to_other_team(self):
        other_team = TeamFactory()
        tv = TeamVideoFactory(team=self.team)
        with self.patch_handler_lookup() as mock_handler:
            tv.move_to(other_team)
        assert_equal(mock_handler.on_video_removed.call_args,
                     mock.call(tv.video, other_team))

    def test_on_video_moved_to_other_project_same_team(self):
        old_project = ProjectFactory(team=self.team)
        new_project = ProjectFactory(team=self.team)
        tv = TeamVideoFactory(team=self.team, project=old_project)
        with self.patch_handler_lookup() as mock_handler:
            tv.move_to(self.team, project=new_project)
        assert_equal(mock_handler.on_video_moved_project.call_args,
                     mock.call(tv.video, old_project, new_project))

    def test_on_video_moved_to_other_project_other_team(self):
        old_project = ProjectFactory(team=self.team)
        other_team = TeamFactory()
        new_project = ProjectFactory(team=other_team)
        tv = TeamVideoFactory(team=self.team, project=old_project)
        with self.patch_handler_lookup() as mock_handler:
            tv.move_to(other_team, project=new_project)
        assert_not_equal(mock_handler.on_video_moved_project.call_args,
                     mock.call(tv.video, old_project, new_project))
        assert_equal(mock_handler.on_video_removed.call_args,
                     mock.call(tv.video, other_team))

    def test_on_video_url_made_primary(self):
        video = VideoFactory(team=self.team)
        with self.patch_handler_lookup() as mock_handler:
            video_url = VideoURLFactory(video=video)
            video_url.make_primary(self.user)
        assert_equal(mock_handler.on_video_url_made_primary.call_args,
                     mock.call(video, video_url, self.user))

    def test_on_subtitle_version_added(self):
        video = VideoFactory(team=self.team)
        with self.patch_handler_lookup() as mock_handler:
            version = pipeline.add_subtitles(video, 'en', SubtitleSetFactory())
        assert_equal(mock_handler.on_subtitles_added.call_args,
                     mock.call(video, version))

    def test_on_subtitle_version_imported(self):
        # We do not actually import subtitles but send the signal
        video = VideoFactory(team=self.team)
        with self.patch_handler_lookup() as mock_handler:
            version = pipeline.add_subtitles(video, 'en', SubtitleSetFactory())
            subtitles_imported.send(sender=version.subtitle_language, versions=[version])
        assert_equal(mock_handler.on_subtitles_imported.call_args,
                     mock.call(video, [version]))

    def test_on_subtitles_published(self):
        video = VideoFactory(team=self.team)
        version = pipeline.add_subtitles(video, 'en', SubtitleSetFactory(),
                                         action='save-draft')
        with self.patch_handler_lookup() as mock_handler:
            workflow = video.get_workflow()
            workflow.perform_action(self.user, 'en', 'publish')
        assert_equal(mock_handler.on_subtitles_published.call_args,
                     mock.call(video, version.subtitle_language))

    def test_on_subtitles_deleted(self):
        video = VideoFactory(team=self.team)
        version = pipeline.add_subtitles(video, 'en', SubtitleSetFactory(),
                                         action='save-draft')
        with self.patch_handler_lookup() as mock_handler:
            version.subtitle_language.nuke_language()
        assert_equal(mock_handler.on_subtitles_deleted.call_args,
                     mock.call(video, version.subtitle_language))

    def test_on_user_added(self):
        with self.patch_handler_lookup() as mock_handler:
            member = TeamMemberFactory(team=self.team)
        assert_equal(mock_handler.on_user_added.call_args,
                     mock.call(member.user, self.team))
        # A second save shouldn't cause the handler to be called again
        with self.patch_handler_lookup(False) as mock_handler:
            member.save()
            assert_false(mock_handler.on_user_added.called)

    def test_on_user_removed(self):
        member = TeamMemberFactory(team=self.team)
        with self.patch_handler_lookup() as mock_handler:
            member.delete()
        assert_equal(mock_handler.on_user_removed.call_args,
                     mock.call(member.user, self.team))

    def test_on_user_info_updated(self):
        member = TeamMemberFactory(team=self.team)
        with self.patch_handler_lookup() as mock_handler:
            member.user.first_name = 'new'
            member.user.last_name = 'name'
            member.user.save()
        assert_equal(mock_handler.on_user_info_updated.call_args,
                     mock.call(member.user, self.team))

    def test_exception_in_handler(self):
        with self.patch_handler_lookup() as mock_handler:
            mock_handler.on_video_added.side_effect = ValueError()
            # Cause on_video_added to be called.  It should throw an
            # exception, but the exception should be delt and not bubble out
            video = VideoFactory(team=self.team)
        assert_true(mock_handler.on_video_added.called)

class TeamNotificationTest(TestCase):
    def test_create_new(TestCase):
        team = TeamFactory()
        notification = TeamNotification.create_new(
            team, 'http://example.com', {'foo': 'bar'})
        assert_equal(json.loads(notification.data), {
            'foo': 'bar',
            'number': notification.number,
        })

    def test_create_new_with_team_id(TestCase):
        team = TeamFactory()
        notification = TeamNotification.create_new(
            team.id, 'http://example.com', {'foo': 'bar'})
        assert_equal(notification.team, team)

    def test_notification_number(TestCase):
        # test setting the number field
        team = TeamFactory()
        def make_notification():
            return TeamNotification.create_new(
                team, 'http://example.com', {'foo': 'bar'})
        assert_equal(make_notification().number, 1)
        assert_equal(make_notification().number, 2)
        assert_equal(make_notification().number, 3)

    @patch_for_test('notifications.models.TeamNotification.next_number_for_team')
    def test_notification_number_collision(self, next_number_for_team):
        # Simulate a potential race condition where we create notifications in
        # different threads.  We should still get unique, increasing,
        # notification numbers and not get Integrity Errors
        next_number_for_team.return_value = 1
        team = TeamFactory()
        notification1 = TeamNotification.create_new(
            team, 'http://example.com', {'foo': 'bar'})
        # This next create_new() will try to save the same number as the
        # first.  It should recover from the IntegrityError
        notification2 = TeamNotification.create_new(
            team, 'http://example.com', {'foo': 'bar'})
        assert_equal(notification1.number, 1)
        assert_equal(notification2.number, 2)
        # check that the number is stored correctly in the data
        assert_equal(json.loads(notification1.data)['number'], 1)
        assert_equal(json.loads(notification2.data)['number'], 2)

class TeamNotificationSettingsTest(TestCase):
    def test_get_headers(self):
        settings = TeamNotificationSettings(
            header1='Foo: bar',
            header2='  Foo2:  bar2',  # extra space should be trimmed
        )
        assert_equal(settings.get_headers(), {
            'Foo': 'bar',
            'Foo2': 'bar2',
        })

class TestSendNotification(TestCase):
    def test_send_notification(self):
        team = TeamFactory()
        settings = TeamNotificationSettings(team=team,
                                            type='mock-type',
                                            url='http://example.com/')
        settings.save()
        handler = handlers.NotificationHandlerBase(settings)
        data = {'foo': 'bar'}
        handler.send_notification(data)
        # Note: do_http_post gets replaced with a mock function for the
        # unittests
        assert_equal(handlers.do_http_post.delay.call_args,
                     mock.call(team.id, settings.url, data,
                               settings.get_headers(), settings.auth_username,
                               settings.auth_password))

class TestDoHTTPPost(TestCase):
    def setUp(self):
        self.team = TeamFactory()
        self.data = {'foo': 'bar'}
        self.url = 'http://example.com/notifications/'
        handlers.do_http_post.run_original_for_test()
        self.now = dates.now.freeze()

    def check_notification(self, status_code, error_message=None):
        notification = TeamNotification.objects.get(team=self.team)
        assert_equal(notification.team, self.team)
        assert_equal(notification.url, self.url)
        assert_equal(notification.timestamp, self.now)
        assert_equal(notification.response_status, status_code)
        assert_equal(notification.error_message, error_message)
        self.check_notification_data(notification)

    def check_notification_data(self, notification):
        correct_data = self.data.copy()
        correct_data['number'] = notification.number
        assert_equal(json.loads(notification.data), correct_data)

    def calc_post_data(self):
        post_data = self.data.copy()
        post_data['number'] = TeamNotification.next_number_for_team(self.team)
        return json.dumps(post_data)

    def test_http_request(self):
        mocker = RequestsMocker()
        mocker.expect_request(
            'post', self.url, data=self.calc_post_data(),
            headers={
                'Content-type': 'application/json',
                'extra-header': '123',
            },
            auth=HTTPBasicAuth('alice', '1234'),
        )
        with mocker:
            handlers.do_http_post(self.team.id, self.url, self.data,
                                  {'extra-header': '123'}, 'alice', '1234')
        self.check_notification(200)

    def test_status_code_error(self):
        mocker = RequestsMocker()
        mocker.expect_request(
            'post', self.url, data=self.calc_post_data(),
            headers={'Content-type': 'application/json'},
            status_code=500,
        )
        with mocker:
            handlers.do_http_post(self.team.id, self.url, self.data, {}, '', '')
        self.check_notification(500, "Response status: 500")

    def test_network_errors(self):
        self.check_network_error(ConnectionError(), 'Connection error')
        self.check_network_error(Timeout(), 'Request timeout')
        self.check_network_error(TooManyRedirects(), 'Too many redirects')

    def check_network_error(self, exception, error_message):
        mocker = RequestsMocker()
        mocker.expect_request(
            'post', self.url, data=self.calc_post_data(),
            headers={'Content-type': 'application/json'},
            error=exception,
        )
        with mocker:
            handlers.do_http_post(self.team.id, self.url, self.data, {}, '',
                                  '')
        self.check_notification(None, error_message)
        TeamNotification.objects.all().delete()

@mock.patch('notifications.tasks.MIN_KEEP', 100)
@mock.patch('notifications.tasks.REMOVE_AFTER', 15)
class NotificationHistoryTests(TestCase):

    def setUp(self):
        self.remove_after = dates.now() - timedelta(days=15)
        self.keep_up_to = 50
        self.teams = [TeamFactory() for i in range(0, 3)]
        self.notifications = []

        self.build_notifications()

    def build_notifications(self):
        time_keep = dates.now()
        time_remove = dates.now() - timedelta(days=30)

        for team in self.teams:
            for i in range(1, 151):
                time = time_remove if i < 80 else time_keep
                n = TeamNotification.objects.create(
                    number=i,
                    data={'text': 'Notification {}'.format(i)},
                    url='https://example.com/{}'.format(team.slug),
                    timestamp=time,
                    team=team)
                self.notifications.append(n)

    def test_cleanup_notification(self):
        prune_notification_history()

        notification_list = TeamNotification.objects.all()

        # check if notifications that should be removed are, those that shouldn't aren't
        for n in self.notifications:
            if n.timestamp <= self.remove_after and n.number <= self.keep_up_to:
                self.assertNotIn(n, notification_list)
            else:
                self.assertIn(n, notification_list)
