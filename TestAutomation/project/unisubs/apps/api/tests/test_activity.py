# Amara, universalsubtitles.org
#
# Copyright (C) 2015 Participatory Culture Foundation
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
from datetime import datetime, timedelta
import time

from django.test import TestCase
from nose.tools import *
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient, APIRequestFactory

from api.tests.utils import format_datetime_field, format_datetime_field_as_date, user_field_data
from comments.models import Comment
from subtitles import pipeline
from utils.test_utils import *
from utils.factories import *
from activity.models import ActivityRecord

class ActivityTest(TestCase):
    def setUp(self):
        self.user = UserFactory(username='test-user')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def clear_records(self):
        ActivityRecord.objects.all().delete()

    def check_list(self, url, *records):
        response = self.client.get(url)
        assert_equal(response.status_code, status.HTTP_200_OK)
        assert_equal(len(response.data['objects']), len(records))
        for data, record in zip(response.data['objects'], records):
            self.check_data(data, record)

    def check_data(self, activity_data, record):
        assert_equal(activity_data['type'], record.type)
        assert_equal(activity_data['date'],
                     format_datetime_field(record.created))
        if record.video:
            assert_equal(activity_data['video'], record.video.video_id)
            assert_equal(activity_data['video_uri'], reverse(
                'api:video-detail', kwargs={
                         'video_id': record.video.video_id,
                }, request=APIRequestFactory().get('/'))
            )
        else:
            assert_equal(activity_data['video'], None)
            assert_equal(activity_data['video_uri'], None)
        if record.language_code:
            assert_equal(activity_data['language'], record.language_code)
            assert_equal(activity_data['language_uri'], reverse(
                'api:subtitle-language-detail', kwargs={
                    'video_id': record.video.video_id,
                    'language_code': record.language_code,
                }, request=APIRequestFactory().get('/'))
            )
        else:
            assert_equal(activity_data['language'], None)
            assert_equal(activity_data['language_uri'], None)
        assert_equal(activity_data['user'], user_field_data(record.user))

    def test_video(self):
        video = VideoFactory(user=self.user)
        other_video = VideoFactory()
        v1 = pipeline.add_subtitles(video, 'en', SubtitleSetFactory())
        v2 = pipeline.add_subtitles(video, 'fr', SubtitleSetFactory(),
                                    author=self.user)
        self.clear_records()
        record1 = ActivityRecord.objects.create_for_video_added(video)
        record2 = ActivityRecord.objects.create_for_subtitle_version(v1)
        record3 = ActivityRecord.objects.create_for_subtitle_version(v2)
        # this record should never be listed in the endpoint
        ActivityRecord.objects.create_for_video_added(other_video)
        url = reverse('api:video-activity', args=(video.video_id,))

        self.check_list(url, record3, record2, record1)
        self.check_list(url + '?type=video-added', record1)
        self.check_list(url + '?user=test-user', record3, record1)
        self.check_list(url + '?language=en', record2)
        # We should accept filtering with or without time zone, date or datetime
        self.check_list(
            url + '?before=' + format_datetime_field(record2.created),
            record1)
        self.check_list(
            url + '?before=' + record2.created.isoformat(),
            record1)
        self.check_list(
            url + '?after=' + format_datetime_field(record2.created),
            record3, record2)
        self.check_list(
            url + '?after=' + record2.created.isoformat(),
            record3, record2)
        self.check_list(
            url + '?before=' + format_datetime_field_as_date(record2.created))
        self.check_list(
            url + '?after=' + format_datetime_field_as_date(record3.created),
            record3, record2, record1)
        tomorrow = record1.created + timedelta(days=1)
        self.check_list(
            url + '?before=' + format_datetime_field_as_date(tomorrow),
            record3, record2, record1)
        yesterday = record1.created - timedelta(days=1)
        self.check_list(
            url + '?after=' + format_datetime_field_as_date(yesterday),
            record3, record2, record1)
        self.check_list(url + '?user=test-user&language=fr', record3)

    def test_user(self):
        video1 = VideoFactory(user=self.user, video_id='video1',
                              primary_audio_language_code='fr')
        video2 = VideoFactory(user=self.user, video_id='video2',
                              team=TeamFactory(slug='team'))
        other_video = VideoFactory()
        v1 = pipeline.add_subtitles(video1, 'en', SubtitleSetFactory(),
                                    author=self.user)
        self.clear_records()
        record1 = ActivityRecord.objects.create_for_video_added(video1)
        record2 = ActivityRecord.objects.create_for_video_added(video2)
        record3 = ActivityRecord.objects.create_for_subtitle_version(v1)
        # this record should never be listed in the endpoint
        ActivityRecord.objects.create_for_video_added(other_video)
        url = reverse('api:user-activity', args=(self.user.username,))
        self.check_list(url, record3, record2, record1)
        self.check_list(url + '?video=video1', record3, record1)
        self.check_list(url + '?team=team', record2)
        self.check_list(url + '?video_language=fr', record3, record1)
        self.check_list(url + '?type=video-added', record2, record1)
        self.check_list(url + '?language=en', record3)
        self.check_list(
            url + '?before=' + format_datetime_field(record2.created),
            record1)
        self.check_list(
            url + '?after=' + format_datetime_field(record2.created),
            record3, record2)

    def test_team(self):
        team = TeamFactory(slug='team', admin=self.user)
        video1 = VideoFactory(video_id='video1',
                              primary_audio_language_code='fr', team=team)
        video2 = VideoFactory(video_id='video2', team=team)
        other_video = VideoFactory()
        v1 = pipeline.add_subtitles(video1, 'en', SubtitleSetFactory(),
                                    author=self.user)
        self.clear_records()
        record1 = ActivityRecord.objects.create_for_video_added(video1)
        record2 = ActivityRecord.objects.create_for_video_added(video2)
        record3 = ActivityRecord.objects.create_for_subtitle_version(v1)
        # this record should never be listed in the endpoint
        ActivityRecord.objects.create_for_video_added(other_video)
        url = reverse('api:team-activity', args=(team.slug,))
        self.check_list(url, record3, record2, record1)
        self.check_list(url + '?video=video1', record3, record1)
        self.check_list(url + '?user=test-user', record3)
        self.check_list(url + '?user=id${}'.format(self.user.secure_id()),
                        record3)
        self.check_list(url + '?video_language=fr', record3, record1)
        self.check_list(url + '?type=video-added', record2, record1)
        self.check_list(url + '?language=en', record3)
        self.check_list(
            url + '?before=' + format_datetime_field(record2.created),
            record1)
        self.check_list(
            url + '?after=' + format_datetime_field(record2.created),
            record3, record2)

    def check_extra_field(self, activity_type, **extra_fields):
        # We should be able to get just the record we care about by using our
        # user stream and filtering by activity type
        url = reverse('api:user-activity', args=(self.user.username,))
        response = self.client.get(url + '?type={}'.format(activity_type))
        assert_equal(response.status_code, status.HTTP_200_OK)
        assert_equal(len(response.data['objects']), 1)
        data = response.data['objects'][0]

        for name, value in extra_fields.items():
            assert_equal(data[name], value)

    def test_video_url_added(self):
        video = VideoFactory()
        vurl = VideoURLFactory(video=video, added_by=self.user)
        ActivityRecord.objects.create_for_video_url_added(vurl)
        self.check_extra_field('video-url-added', url=vurl.url)

    def test_video_url_edited(self):
        video = VideoFactory()
        old_vurl = video.get_primary_videourl_obj()
        new_vurl = VideoURLFactory(video=video)
        ActivityRecord.objects.create_for_video_url_made_primary(
            new_vurl, old_vurl, self.user)
        self.check_extra_field('video-url-edited', new_url=new_vurl.url,
                               old_url=old_vurl.url)

    def test_video_url_deleted(self):
        video = VideoFactory()
        vurl = VideoURLFactory(video=video)
        ActivityRecord.objects.create_for_video_url_deleted(vurl, self.user)
        self.check_extra_field('video-url-deleted', url=vurl.url)

    def test_video_deleted(self):
        video = VideoFactory()
        ActivityRecord.objects.create_for_video_deleted(video, self.user)
        self.check_extra_field('video-deleted', title=video.title_display())

    @patch_for_test('teams.permissions.can_view_activity')
    def test_permissions_team(self, can_view_activity):
        can_view_activity.return_value = False
        team = TeamFactory()
        url = reverse('api:team-activity', args=(team.slug,))
        response = self.client.get(url)
        assert_equal(response.status_code, status.HTTP_404_NOT_FOUND)
        assert_equal(can_view_activity.call_args, mock.call(team, self.user))

    @patch_for_test('auth.permissions.can_view_activity')
    def test_permissions_user(self, can_view_activity):
        can_view_activity.return_value = False
        user = UserFactory()
        url = reverse('api:user-activity', args=(user.username,))
        response = self.client.get(url)
        assert_equal(response.status_code, status.HTTP_404_NOT_FOUND)
        assert_equal(can_view_activity.call_args, mock.call(user, self.user))

    @patch_for_test('videos.permissions.can_view_activity')
    def test_permissions_video(self, can_view_activity):
        can_view_activity.return_value = False
        video = VideoFactory()
        url = reverse('api:video-activity', args=(video.video_id,))
        response = self.client.get(url)
        assert_equal(response.status_code, status.HTTP_404_NOT_FOUND)
        assert_equal(can_view_activity.call_args, mock.call(video, self.user))

class LegacyActivityTestCase(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.list_url = reverse('api:activity-list')
        # create a bunch of activity records of various types
        self.team = TeamFactory()
        self.team_member = TeamMemberFactory(user=self.user, team=self.team)
        self.video = VideoFactory(user=self.user)
        TeamVideoFactory(video=self.video, team=self.team)
        self.user2 = UserFactory()
        ActivityRecord.objects.create_for_video_added(self.video)
        self.video.title = 'new-title'
        self.video.save()
        v = pipeline.add_subtitles(self.video, 'en', None, author=self.user)
        ActivityRecord.objects.create_for_subtitle_version(v)
        ActivityRecord.objects.create_for_version_approved(v, self.user2)
        ActivityRecord.objects.create_for_version_rejected(v, self.user2)
        ActivityRecord.objects.create_for_new_member(self.team_member)
        ActivityRecord.objects.create_for_member_deleted(self.team_member)
        self.record_qs = ActivityRecord.objects.all()

    def detail_url(self, record):
        return reverse('api:activity-detail', (record.id,))

    def filtered_list_url(self, filters):
        query = '&'.join('{}={}'.format(k, v) for k, v in filters.items())
        return '{}?{}'.format(self.list_url, query)

    def check_activity_data(self, activity_data, record):
        assert_equal(activity_data['id'], record.id)
        assert_equal(activity_data['type'], record.type_code)
        assert_equal(activity_data['type_name'], record.type)
        assert_equal(activity_data['created'],
                     format_datetime_field(record.created))
        if record.type == 'video-url-edited':
            assert_equal(activity_data['new_video_title'],
                         record.get_related_obj().new_title)
        else:
            assert_equal(activity_data['new_video_title'], None)
        if record.type == 'comment-added':
            assert_equal(activity_data['comment'],
                         record.get_related_obj().content)
        else:
            assert_equal(activity_data['comment'], None)
        assert_equal(activity_data['resource_uri'], reverse(
            'api:activity-detail', kwargs={'id': record.id},
            request=APIRequestFactory().get('/')))
        if record.video:
            assert_equal(activity_data['video'], record.video.video_id)
            assert_equal(activity_data['video_uri'], reverse(
                'api:video-detail', kwargs={
                         'video_id': record.video.video_id,
                }, request=APIRequestFactory().get('/'))
            )
        else:
            assert_equal(activity_data['video'], None)
            assert_equal(activity_data['video_uri'], None)
        if record.language_code:
            assert_equal(activity_data['language'], record.language_code)
            assert_equal(activity_data['language_url'], reverse(
                'api:subtitle-language-detail', kwargs={
                    'video_id': record.video.video_id,
                    'language_code': record.language_code,
                }, request=APIRequestFactory().get('/'))
            )
        else:
            assert_equal(activity_data['language'], None)
            assert_equal(activity_data['language_url'], None)
        if record.user:
            assert_equal(activity_data['user'], record.user.username)
        else:
            assert_equal(activity_data['user'], None)

    def test_list(self):
        activity_map = {a.id: a for a in self.record_qs}
        response = self.client.get(self.list_url)
        assert_equal(response.status_code, status.HTTP_200_OK)
        assert_items_equal([a['id'] for a in response.data['objects']],
                           activity_map.keys())
        for activity_data in response.data['objects']:
            self.check_activity_data(activity_data,
                                     activity_map[activity_data['id']])

    def test_detail(self):
        for record in self.record_qs:
            response = self.client.get(self.detail_url(record))
            assert_equal(response.status_code, status.HTTP_200_OK)
            self.check_activity_data(response.data, record)

    def check_filter(self, filters, correct_records):
        response = self.client.get(self.filtered_list_url(filters))
        assert_equal(response.status_code, status.HTTP_200_OK)
        assert_items_equal([a['id'] for a in response.data['objects']],
                           [a.id for a in correct_records])

    def test_team_filter(self):
        self.check_filter({
            'team': self.team.slug,
        }, ActivityRecord.objects.filter(team=self.team, video__isnull=False))

    def test_team_activity_flag(self):
        self.check_filter({
            'team': self.team.slug,
            'team-activity': 1,
        }, ActivityRecord.objects.filter(team=self.team, video__isnull=True))

    def test_video_filter(self):
        self.check_filter({
            'video': self.video.video_id,
        }, ActivityRecord.objects.filter(video=self.video))

    def test_type_filter(self):
        type_field = ActivityRecord._meta.get_field('type')
        for (slug, label) in type_field.choices:
            self.check_filter({
                'type': type_field.get_prep_value(slug),
            }, self.record_qs.filter(type=slug))

    def test_language_filter(self):
        self.check_filter({
            'language': 'en'
        }, self.record_qs.filter(language_code='en'))

    def _make_timestamp(self, datetime):
        return int(time.mktime(datetime.timetuple()))

    def test_before_and_after_filters(self):
        all_records = list(self.record_qs)
        old_records = all_records[:4]
        new_records = all_records[4:]
        (ActivityRecord.objects
         .filter(id__in=[a.id for a in old_records])
         .update(created=datetime(2014, 12, 31)))
        self.check_filter({
            'before': self._make_timestamp(datetime(2015, 1, 1))
        }, old_records)
        self.check_filter({
            'after': self._make_timestamp(datetime(2015, 1, 1))
        }, new_records)

    def test_comment(self):
        # Test the comment activity, which fills in the comment field
        Comment(content_object=self.video, user=self.user,
                content="Test Comment").save()
        record = ActivityRecord.objects.get(type='comment-added',
                                            video=self.video)
        response = self.client.get(self.detail_url(record))
        assert_equal(response.status_code, status.HTTP_200_OK)
        assert_equal(response.data['comment'], 'Test Comment')
        self.check_activity_data(response.data, record)

    def test_team_filter_permission_check(self):
        # users should get a 403 response when trying to get activity for a
        # team that they are not a member of
        self.team_member.delete()
        url = self.filtered_list_url({'team': self.team.slug})
        response = self.client.get(url)
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_team_video_filter_permission_check(self):
        # users should get a 403 response when trying to get activity for a
        # team video when they are not a member of the team
        self.team_member.delete()
        url = self.filtered_list_url({'video': self.video.video_id})
        response = self.client.get(url)
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)
