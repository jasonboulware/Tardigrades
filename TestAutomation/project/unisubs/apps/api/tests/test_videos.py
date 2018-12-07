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

from django import http
from django.test import TestCase
from nose.tools import *
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.reverse import reverse
from rest_framework.test import APIClient, APIRequestFactory
import mock
import unittest

from api.tests.utils import format_datetime_field
from api.views.videos import VideoSerializer, VideoViewSet
from subtitles import pipeline
from teams.models import VideoVisibility
from utils.factories import *
from utils import test_utils
from utils.test_utils.api import *
from videos.models import Video
import teams.signals

class VideoSerializerTest(TestCase):
    @test_utils.patch_for_test('videos.models.Video.get_wide_thumbnail')
    def setUp(self, get_wide_thumbnail):
        # The thumbnail field should use the return value from
        # get_wide_thumbnail() which uses the S3 thumbnail if available.
        # On staging/production, get_wide_thumbnail() returns the URL without
        # a scheme.  We should make sure to add https in that case
        get_wide_thumbnail.return_value = '//example.com/processed-thumb.jpg'
        self.thumbnail_url = 'https://example.com/processed-thumb.jpg'
        self.user = UserFactory()
        self.video = VideoFactory(
            title='test-title',
            description='test-description',
            duration=100,
            thumbnail='http://example.com/image.jpg',
        )
        request = APIRequestFactory().get("/mock-url/")
        # Add query_params which is available from django rest framework's
        # Request object, but not when you use APIRequestFactory for some
        # reason.
        request.query_params = request.GET
        self.serializer_context = {
            'request': request,
            'user': self.user,
        }

    def get_serialized_data(self):
        video_serializer = VideoSerializer(test_utils.reload_obj(self.video), 
                                           context=self.serializer_context)
        return video_serializer.data

    def run_create(self, data):
        video_serializer = VideoSerializer(data=data,
                                           context=self.serializer_context)
        video_serializer.is_valid(raise_exception=True)
        return video_serializer.save()

    def run_update(self, data):
        video_serializer = VideoSerializer(instance=self.video, data=data,
                                           context=self.serializer_context)
        video_serializer.is_valid(raise_exception=True)
        return video_serializer.save()

    def test_simple_fields(self):
        data = self.get_serialized_data()
        assert_equal(data['id'], self.video.video_id)
        assert_equal(data['title'], self.video.title)
        assert_equal(data['description'], self.video.description)
        assert_equal(data['duration'], self.video.duration)
        assert_equal(data['created'],
                     format_datetime_field(self.video.created))
        assert_equal(data['thumbnail'], self.thumbnail_url)
        assert_equal(data['resource_uri'],
                     'http://testserver/api/videos/{0}/'.format(
                         self.video.video_id))

    def test_language_field(self):
        # test the original_language/primary_audio_language_code fields
        data = self.get_serialized_data()
        assert_equal(data['original_language'], None)
        assert_equal(data['primary_audio_language_code'], None)
        self.video.primary_audio_language_code = 'en'
        self.video.save()
        data = self.get_serialized_data()
        assert_equal(data['original_language'], 'en')
        assert_equal(data['primary_audio_language_code'], 'en')

    def test_team_field(self):
        data = self.get_serialized_data()
        assert_equal(data['team'], None)
        tv = TeamVideoFactory(video=self.video, team__slug='test-team')
        self.video.clear_team_video_cache()
        data = self.get_serialized_data()
        assert_equal(data['team'], 'test-team')

    def test_project_field(self):
        assert_equal(self.get_serialized_data()['project'], None)
        # if the project is the default project, we should set it to None
        team = TeamFactory()
        team_video = TeamVideoFactory(video=self.video, team=team)
        assert_equal(self.get_serialized_data()['project'], None)

        team_video.project = ProjectFactory(team=team, slug='test-project')
        team_video.save()
        assert_equal(self.get_serialized_data()['project'], 'test-project')

    def test_invalid_project(self):
        with assert_raises(ValidationError):
            self.run_update({
                'team': TeamFactory().slug,
                'project': 'invalid-project',
            })


    def test_project_without_team(self):
        with assert_raises(ValidationError):
            self.run_update({
                'project': ProjectFactory().slug
            })

    def test_metadata_field(self):
        data = self.get_serialized_data()
        assert_equal(data['metadata'], {})
        self.video.update_metadata({
            'speaker-name': 'Someone',
        })
        data = self.get_serialized_data()
        assert_equal(data['metadata'], {
            'speaker-name': 'Someone',
        })

    def test_all_urls(self):
        primary_url = self.video.get_primary_videourl_obj()
        secondary_url = VideoURLFactory(video=self.video)
        data = self.get_serialized_data()
        assert_equal(data['all_urls'], [
            primary_url.url,
            secondary_url.url,
        ])

    def test_languages(self):
        pipeline.add_subtitles(self.video, 'en', SubtitleSetFactory(),
                               visibility='public')
        pipeline.add_subtitles(self.video, 'he', SubtitleSetFactory(),
                               visibility='private')

        data = self.get_serialized_data()
        lang_url_root = 'http://testserver/api/videos/{}/languages/'.format(
            self.video.video_id)
        assert_items_equal(data['languages'], [
            {
                'code': 'en',
                'name': 'English',
                u'subtitles_uri': lang_url_root + 'en/subtitles/',
                'dir': 'ltr',
                'published': True,
                'resource_uri':  lang_url_root + 'en/'
            },
            {
                'code': 'he',
                'name': 'Hebrew',
                u'subtitles_uri': lang_url_root + 'he/subtitles/',
                'dir': 'rtl',
                'published': False,
                'resource_uri':  lang_url_root + 'he/'
            },
        ])

    def test_create(self):
        data = {
            'video_url': 'http://example.com/new-video.mp4',
            'primary_audio_language_code': 'en',
            'title': 'title',
            'description': 'description',
            'duration': '100',
            'thumbnail': 'http://example.com/thumb.jpg',
        }
        result = self.run_create(data)
        assert_equal(result.get_primary_videourl_obj().url, data['video_url'])
        assert_equal(result.primary_audio_language_code,
                     data['primary_audio_language_code'])
        assert_equal(result.title, data['title'])
        assert_equal(result.description, data['description'])
        assert_equal(result.duration, 100)
        assert_equal(result.thumbnail, data['thumbnail'])
        assert_equal(result.get_primary_videourl_obj().added_by, self.user)
        test_utils.assert_saved(result)

    def test_cant_create_with_existing_video_url(self):
        url = 'http://example.com/existing-video.mp4'
        VideoFactory(video_url__url=url)
        with assert_raises(ValidationError) as cm:
            self.run_create({
                'video_url': url,
            })
        assert_in('Video already added', str(cm.exception))

    def test_cant_create_with_invalid_video_url(self):
        url = 'http://junk.com/junky/fake1.mov'
        VideoFactory(video_url__url=url)
        with assert_raises(ValidationError) as cm:
            self.run_create({
                'video_url': url,
            })
        assert_in('Invalid URL', str(cm.exception))

    def test_update(self):
        data = {
            'primary_audio_language_code': 'fr',
            'title': 'new-title',
            'description': 'new-description',
            'duration': '100',
            'thumbnail': 'http://example.com/new-thumbnail.png',
        }
        result = self.run_update(data)
        assert_equal(result.id, self.video.id)
        assert_equal(result.primary_audio_language_code,
                     data['primary_audio_language_code'])
        assert_equal(result.title, data['title'])
        assert_equal(result.description, data['description'])
        assert_equal(result.duration, 100)
        assert_equal(result.thumbnail, data['thumbnail'])

    def test_save_thumbnail_in_s3(self):
        # We should call save_thumbnail_in_s3 when the client POSTs a new
        # thumbnail URL
        result = self.run_update({
            'thumbnail': 'http://example.com/new-thumbnail.png',
        })
        assert_true(test_utils.save_thumbnail_in_s3.delay.called)
        assert_equal(test_utils.save_thumbnail_in_s3.delay.call_args,
                     mock.call(self.video.id))
        test_utils.save_thumbnail_in_s3.reset_mock()
        # If thumbnail is not present, then no need to call
        # save_thumbnail_in_s3
        result = self.run_update({
            'title': 'new-title',
        })
        assert_false(test_utils.save_thumbnail_in_s3.delay.called)

    def test_set_metadata(self):
        new_metadata = {
            'speaker-name': 'Test Speaker',
            'location': 'Test Location',
        }
        result = self.run_update({
            'metadata': new_metadata,
        })
        assert_equal(result.get_metadata(), new_metadata)

    def test_set_metadata_invalid_key(self):
        with assert_raises(ValidationError):
            self.run_update({
                'metadata': {
                    'invalid-key': 'Test Value'
                }
            })

    def test_writable_fields(self):
        video_serializer = VideoSerializer(data={},
                                           context=self.serializer_context)
        writable_fields = [
            name for (name, field) in video_serializer.fields.items()
            if not field.read_only
        ]
        assert_items_equal(writable_fields, [
            'video_url',
            'title',
            'description',
            'duration',
            'primary_audio_language_code',
            'thumbnail',
            'metadata',
            'team',
            'project',
        ])

    def test_writable_fields_update(self):
        video_serializer = VideoSerializer(instance=VideoFactory(), data={},
                                           context=self.serializer_context)
        writable_fields = [
            name for (name, field) in video_serializer.fields.items()
            if not field.read_only
        ]
        assert_items_equal(writable_fields, [
            'title',
            'description',
            'duration',
            'primary_audio_language_code',
            'thumbnail',
            'metadata',
            'team',
            'project',
        ])

    def test_create_with_team(self):
        team = TeamFactory(slug='test-team')
        data = {
            'video_url': 'http://example.com/video.mp4',
            'team': 'test-team',
        }
        result = self.run_create(data)
        assert_equal(result.get_team_video().team, team)

    def test_add_to_team(self):
        team = TeamFactory(slug='test-team')
        self.run_update({ 'team': 'test-team', })
        assert_equal(self.video.get_team_video().team, team)

    @test_utils.patch_for_test('teams.models.Team.add_existing_video')
    def test_add_to_team_duplicate_url_error(self, add_existing_video):
        add_existing_video.side_effect = Video.DuplicateUrlError(
            self.video.get_primary_videourl_obj())
        team = TeamFactory(slug='test-team')
        with assert_raises(ValidationError):
            self.run_update({ 'team': 'test-team', })

    @test_utils.mock_handler(teams.signals.video_moved_from_team_to_team)
    def test_move_team(self, mock_handler):
        team1 = TeamFactory(slug='team1')
        team2 = TeamFactory(slug='team2')
        TeamVideoFactory(video=self.video, team=team1)
        self.run_update({ 'team': 'team2' })
        assert_equal(self.video.get_team_video().team, team2)
        assert_equal(mock_handler.call_count, 1)

    @test_utils.patch_for_test('teams.models.TeamVideo.move_to')
    def test_move_to_team_duplicate_url_error(self, move_to):
        move_to.side_effect = Video.DuplicateUrlError(
            self.video.get_primary_videourl_obj())
        team1 = TeamFactory(slug='team1')
        team2 = TeamFactory(slug='team2')
        TeamVideoFactory(video=self.video, team=team1)
        with assert_raises(ValidationError):
            self.run_update({ 'team': 'team2' })

    def test_remove_team(self):
        team = TeamFactory(slug='team')
        TeamVideoFactory(video=self.video, team=team)
        self.run_update({ 'team': None })
        assert_equal(test_utils.reload_obj(self.video).get_team_video(), None)

    @test_utils.patch_for_test('teams.models.TeamVideo.remove')
    def test_remove_team_duplicate_url_error(self, remove):
        remove.side_effect = Video.DuplicateUrlError(
            self.video.get_primary_videourl_obj())
        team = TeamFactory(slug='test-team')
        TeamVideoFactory(video=self.video, team=team)
        with assert_raises(ValidationError):
            self.run_update({ 'team': None})

    def test_set_project(self):
        project = ProjectFactory()
        self.run_update({
            'team': project.team.slug,
            'project': project.slug,
        })
        team_video = self.video.get_team_video()
        assert_equal(team_video.project, project)
        # None signifies the default project
        self.run_update({
            'team': project.team.slug,
            'project': None,
        })
        assert_true(
            test_utils.reload_obj(team_video).project.is_default_project
        )

    def test_update_without_team_or_project(self):
        # if we run an update without team or project field, we should keep it
        # in its current place
        team = TeamFactory(slug='team', admin=self.user)
        project = ProjectFactory(team=team)
        TeamVideoFactory(video=self.video, team=team, project=project)
        self.run_update({ 'title': 'new-title'})
        team_video = test_utils.reload_obj(self.video).get_team_video()
        assert_equal(team_video.team, team)
        assert_equal(team_video.project, project)

    def test_add_to_invalid_team(self):
        with assert_raises(ValidationError):
            self.run_update({
                'team': 'non-existent-team',
            })

    def test_update_with_blank_values(self):
        # test that blank values don't overwrite existing values
        self.video.primary_audio_language_code = 'en'
        self.video.title = 'orig-title'
        self.video.description = 'orig-description'
        self.video.duration = 100
        self.video.save()
        orig_thumbnail = 'http://example.com/new-thumbnail.png'
        self.video.thumbnail = orig_thumbnail
        project = ProjectFactory(team__slug='test-team', slug='test-project')
        TeamVideoFactory(video=self.video, team=project.team, project=project)
        result = self.run_update({
            'primary_audio_language_code': '',
            'title': '',
            'duration': '',
            'description': '',
            'duration': '',
            'thumbnail': '',
            'project': '',
            'team': '',
        })
        assert_equal(result.primary_audio_language_code, 'en')
        assert_equal(result.title, 'orig-title')
        assert_equal(result.description, 'orig-description')
        assert_equal(result.duration, 100)
        assert_equal(result.thumbnail, orig_thumbnail)
        team_video = result.get_team_video()
        assert_equal(team_video.team.slug, 'test-team')
        assert_equal(team_video.project.slug, 'test-project')

    def test_null_team_string(self):
        # sending the string "null" for team should work the same as sending
        # None
        TeamVideoFactory(video=self.video)
        result = self.run_update({
            'team': 'null',
        })
        assert_equal(test_utils.reload_obj(result).get_team_video(), None)

    def test_null_project_string(self):
        # sending the string "null" for project should work the same as
        # sending None
        team = TeamFactory()
        project = ProjectFactory(team=team)
        TeamVideoFactory(video=self.video, team=team, project=project)
        result = self.run_update({
            'team': team.slug,
            'project': 'null'
        })
        assert_true(result.get_team_video().project.is_default_project)

class VideoSerializerTeamChangeTest(TestCase):
    def setUp(self):
        self.team = TeamFactory(slug='team')
        self.other_team = TeamFactory(slug='other-team')
        self.team_video = TeamVideoFactory(team=self.team).video
        self.non_team_video = VideoFactory()

    def make_serializer(self, instance, data):
        serializer = VideoSerializer(instance=instance, data=data, context={
            'request': None,
            'user': None,
        })
        serializer.is_valid(raise_exception=True)
        return serializer

    def test_creating_with_a_team(self):
        serializer = self.make_serializer(None, {
            'video_url': 'http://example.com/video.mp4',
            'team': self.team.slug,
        })
        assert_true(serializer.will_add_video_to_team())
        assert_false(serializer.will_remove_video_from_team())

    def test_create_without_team(self):
        serializer = self.make_serializer(None, {
            'video_url': 'http://example.com/video.mp4',
        })
        assert_false(serializer.will_add_video_to_team())
        assert_false(serializer.will_remove_video_from_team())

    def test_update_with_team(self):
        serializer = self.make_serializer(self.non_team_video, {
            'team': self.team.slug,
        })
        assert_true(serializer.will_add_video_to_team())
        assert_false(serializer.will_remove_video_from_team())

    def test_update_with_different_team(self):
        serializer = self.make_serializer(self.team_video, {
            'team': self.other_team.slug,
        })
        assert_true(serializer.will_add_video_to_team())
        assert_true(serializer.will_remove_video_from_team())

    def test_update_with_different_project(self):
        other_project = ProjectFactory(team=self.team,
                                       slug='new-project')
        serializer = self.make_serializer(self.team_video, {
            'team': self.team.slug,
            'project': other_project.slug,
        })
        assert_true(serializer.will_add_video_to_team())
        assert_false(serializer.will_remove_video_from_team())

    def test_update_with_no_changes(self):
        serializer = self.make_serializer(self.team_video, {
            'team': self.team.slug,
            'project': self.team.default_project.slug,
        })
        assert_false(serializer.will_add_video_to_team())
        assert_false(serializer.will_remove_video_from_team())

    def test_update_with_fields_missing(self):
        # simulate an update that doesn't have the team/project fields.  IN
        # this case we shouldn't touch the team video
        serializer = self.make_serializer(self.team_video, {
            'title': 'new-title',
        })
        assert_false(serializer.will_add_video_to_team())
        assert_false(serializer.will_remove_video_from_team())

class VideoViewSetTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.viewset = VideoViewSet()
        self.query_params = {
        }
        self.viewset.request = mock.Mock(user=self.user,
                                         query_params=self.query_params)
        self.viewset.kwargs = {}

    def test_listing_with_no_filters(self):
        # Listing videos without a filter should return the last 20 public videos
        public_videos = [
            VideoFactory(title='public', is_public=True)
            for i in range(30)
        ]
        private_videos = [
            VideoFactory(title='private', is_public=False)
            for i in range(30)
        ]
        assert_equal(list(reversed([v.id for v in public_videos[-20:]])),
                     [v.id for v in self.viewset.get_queryset()])

    @test_utils.patch_for_test('subtitles.workflows.get_workflow')
    def test_get_detail_checks_workflow_permissions(self, mock_get_workflow):
        video = VideoFactory()
        workflow = mock.Mock()
        workflow.user_can_view_video.return_value = True
        mock_get_workflow.return_value = workflow
        # test successful permissions check
        self.viewset.kwargs['video_id'] = video.video_id
        assert_equal(self.viewset.get_object(), video)
        # test failed permissions check
        workflow.user_can_view_video.return_value = False
        with assert_raises(http.Http404):
            self.viewset.get_object()

    def test_get_detail_returns_403_when_video_not_found(self):
        # for non-staff users, if they try to get a video ID that's not in the
        # DB, we should return a 403 error.  This way they can't use the API
        # to query if a team video exists or not.
        self.viewset.kwargs['video_id'] = 'bad-video-id'
        with assert_raises(PermissionDenied):
            self.viewset.get_object()

    def test_video_url_filter(self):
        v1 = VideoFactory(title='correct video url')
        v2 = VideoFactory(title='other video url')
        self.query_params['video_url'] = v1.get_video_url()
        assert_items_equal([v1], self.viewset.get_queryset())

    def test_team_filter(self):
        team = TeamFactory(video_visibility=VideoVisibility.PUBLIC)
        v1 = VideoFactory(title='correct team')
        v2 = VideoFactory(title='wrong team')
        v3 = VideoFactory(title='not in team')
        TeamVideoFactory(team=team, video=v1)
        TeamVideoFactory(video=v2)
        self.query_params['team'] = team.slug
        assert_items_equal([v1], self.viewset.get_queryset())

    def test_project_filter(self):
        team = TeamFactory(video_visibility=VideoVisibility.PUBLIC)
        project = ProjectFactory(team=team, slug='project')
        other_project = ProjectFactory(team=team, slug='wrong-project')
        v1 = VideoFactory(title='correct project')
        v2 = VideoFactory(title='wrong project')
        v3 = VideoFactory(title='default project')
        v4 = VideoFactory(title='no team')
        TeamVideoFactory(video=v1, team=team, project=project)
        TeamVideoFactory(video=v2, team=team, project=other_project)
        TeamVideoFactory(video=v3, team=team)

        self.query_params['team'] = team.slug
        self.query_params['project'] = project.slug
        assert_items_equal([v1], self.viewset.get_queryset())

    def test_default_project_filter(self):
        team = TeamFactory(video_visibility=VideoVisibility.PUBLIC)
        project = ProjectFactory(team=team, slug='project-slug')
        v1 = VideoFactory(title='in default project')
        v2 = VideoFactory(title='not in default project')
        TeamVideoFactory(video=v1, team=team)
        TeamVideoFactory(video=v2, team=team, project=project)

        self.query_params['team'] = team.slug
        self.query_params['project'] = 'null'
        assert_items_equal([v1], self.viewset.get_queryset())

    def test_team_filter_user_is_not_member(self):
        team = TeamFactory()
        video = TeamVideoFactory(team=team).video
        self.query_params['team'] = team.slug
        assert_items_equal([], self.viewset.get_queryset())

class ViewSetCreateUpdateTestCase(TestCase):
    def setUp(self):
        # set up a bunch of mock objects so that we can test VideoViewSetTest
        # methods.
        self.user = UserFactory()
        self.team = TeamFactory(admin=self.user)
        self.project = ProjectFactory(team=self.team)
        self.serializer = mock.Mock(
            validated_data={
                'team': self.team,
                'project': self.project,
            },
            instance=None,
        )
        self.serializer.will_add_video_to_team.return_value = False
        self.serializer.will_remove_video_from_team.return_value = False
        self.viewset = VideoViewSet()
        self.viewset.request = mock.Mock(user=self.user)

    @test_utils.patch_for_test('teams.permissions.can_add_video')
    def test_add_videos_perm_check(self, mock_can_add_video):
        # if will_add_video_to_team() returns False, we shouldn't check the
        # permission
        mock_can_add_video.return_value = True
        self.serializer.will_add_video_to_team.return_value = False
        self.viewset.check_save_permissions(self.serializer)
        assert_equal(mock_can_add_video.call_count, 0)
        # if will_add_video_to_team() returns True, we should
        self.serializer.will_add_video_to_team.return_value = True
        self.viewset.check_save_permissions(self.serializer)
        assert_equal(mock_can_add_video.call_count, 1)
        assert_equal(mock_can_add_video.call_args, mock.call(
            self.team, self.user, self.project))
        # test can_add_video returning False
        mock_can_add_video.return_value = False
        with assert_raises(PermissionDenied):
            self.viewset.check_save_permissions(self.serializer)

    def test_edit_video_permission_check(self):
        team_video = TeamVideoFactory(team=self.team)
        self.serializer.instance = team_video.video
        with test_utils.patch_get_workflow() as workflow:
            workflow.user_can_edit_video.return_value = False
            with assert_raises(PermissionDenied):
                self.viewset.check_save_permissions(self.serializer)
            assert_equal(workflow.user_can_edit_video.call_args,
                         mock.call(self.user))

    @test_utils.patch_for_test('teams.permissions.can_remove_video')
    def test_remove_video_perm_check(self, mock_can_remove_video):
        team_video = TeamVideoFactory(team=self.team)
        self.serializer.instance = team_video.video
        mock_can_remove_video.return_value = True
        # if will_remove_video_from_team() returns False, we shouldn't check the
        # permission
        self.serializer.will_remove_video_from_team.return_value = False
        self.viewset.check_save_permissions(self.serializer)
        assert_equal(mock_can_remove_video.call_count, 0)
        # if will_remove_video_from_team() returns True, we should
        self.serializer.will_remove_video_from_team.return_value = True
        self.viewset.check_save_permissions(self.serializer)
        assert_equal(mock_can_remove_video.call_count, 1)
        assert_equal(mock_can_remove_video.call_args, mock.call(
            team_video, self.user))
        # test mock_can_remove_video returning False
        mock_can_remove_video.return_value = False
        with assert_raises(PermissionDenied):
            self.viewset.check_save_permissions(self.serializer)

    @test_utils.patch_for_test('videos.tasks.video_changed_tasks')
    def test_perform_update_runs_task(self, mock_video_changed_tasks):
        video = VideoFactory()
        self.serializer.save.return_value = video
        self.viewset.perform_update(self.serializer)
        assert_equal(mock_video_changed_tasks.delay.call_count, 1)
        assert_equal(mock_video_changed_tasks.delay.call_args,
                     mock.call(video.pk))

class VideoURLTestCase(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.video = VideoFactory()
        self.primary_url = self.video.get_primary_videourl_obj()
        self.other_url = VideoURLFactory(video=self.video)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.list_url = reverse('api:video-url-list',
                                args=(self.video.video_id,))

    def detail_url(self, video_url):
        return reverse('api:video-url-detail', kwargs={
            'video_id': video_url.video.video_id,
            'pk': video_url.id,
        }, request=APIRequestFactory().get('/'))

    def correct_data(self, video_url):
        return {
            'created': format_datetime_field(video_url.created),
            'url': video_url.url,
            'primary': video_url.primary,
            'original': video_url.original,
            'id': video_url.id,
            'resource_uri': self.detail_url(video_url),
            'type': 'HTML5',
            'videoid': '',
        }

    def test_list_urls(self):
        response = self.client.get(self.list_url)
        assert_equal(response.status_code, status.HTTP_200_OK)
        assert_items_equal(response.data['objects'], [
            self.correct_data(self.primary_url),
            self.correct_data(self.other_url)
        ])

    def test_get_detail(self):
        response = self.client.get(self.detail_url(self.primary_url))
        assert_equal(response.status_code, status.HTTP_200_OK)
        assert_dict_contains_subset(response.data, self.correct_data(self.primary_url))

    def test_add_url(self):
        url = 'http://example.com/added-video.mp4'
        response = self.client.post(self.list_url, {'url': url})
        assert_equal(response.status_code, status.HTTP_201_CREATED)
        qs = self.video.videourl_set.filter(url=url)
        assert_equal(qs.count(), 1)
        assert_equal(qs[0].added_by, self.user)

    def check_primary_url(self, url):
        qs = self.video.videourl_set.filter(primary=True)
        assert_equal([vurl.url for vurl in qs], [url])

    def test_add_primary_url(self):
        url = 'http://example.com/added-video.mp4'
        response = self.client.post(self.list_url, {
            'url': url,
            'primary': True}
        )
        assert_equal(response.status_code, status.HTTP_201_CREATED)
        self.check_primary_url(url)

    def test_add_with_original(self):
        url = 'http://example.com/added-video.mp4'
        response = self.client.post(self.list_url, {
            'url': url,
            'original': True}
        )
        assert_equal(response.status_code, status.HTTP_201_CREATED)
        assert_true(self.video.videourl_set.get(url=url).original)

    def test_set_primary(self):
        response = self.client.put(self.detail_url(self.other_url), {
            'primary': True
        })
        assert_equal(response.status_code, status.HTTP_200_OK,
                     response.content)
        self.check_primary_url(self.other_url.url)

    def test_set_original(self):
        response = self.client.put(self.detail_url(self.other_url), {
            'original': True
        })
        assert_equal(response.status_code, status.HTTP_200_OK,
                     response.content)
        assert_true(test_utils.reload_obj(self.other_url).original)

    def test_delete_url(self):
        response = self.client.delete(self.detail_url(self.other_url))
        assert_equal(response.status_code, status.HTTP_204_NO_CONTENT,
                     response.content)
        assert_equal(list(self.video.videourl_set.all()), [self.primary_url])

    def test_cant_delete_primary_url(self):
        response = self.client.delete(self.detail_url(self.primary_url))
        assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST,
                     response.content)
        assert_items_equal(self.video.videourl_set.all(),
                           [self.primary_url, self.other_url])

    def test_writeable_fields(self):
        response = self.client.options(self.list_url)
        assert_writable_fields(response, 'POST',
                               ['url', 'original', 'primary'])

    def test_writeable_fields_details(self):
        response = self.client.options(self.detail_url(self.primary_url))
        assert_writable_fields(response, 'PUT',
                               ['original', 'primary'])

class VideoViewTestCase(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.team = TeamFactory(owner=self.user)
        self.video = VideoFactory()
        self.project = ProjectFactory(team=self.team)
        self.team_video = TeamVideoFactory(video=self.video, team=self.team)
        self.url = reverse('api:video-detail', kwargs={
            'video_id': self.video.video_id,
        })

    @unittest.skip("waiting on amara-enterprise#1115")
    def test_delete_video(self):
        video_pk = self.video.pk
        response = self.client.delete(self.url)
        assert_equal(response.status_code, status.HTTP_204_NO_CONTENT)
        assert_false(Video.objects.filter(pk=video_pk).exists())
