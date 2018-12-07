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
import json
import time

from django.test import TestCase
from nose.tools import *
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient, APIRequestFactory
import factory
import mock

from api.tests.utils import format_datetime_field, user_field_data
from auth.models import CustomUser as User
from notifications.models import TeamNotification
from subtitles import pipeline
from teams.models import (Team, TeamMember, Task, Application, TeamVisibility,
                          VideoVisibility)
from utils import test_utils
from utils.test_utils.api import *
from utils.factories import *
import teams.signals

class TeamAPITestBase(TestCase):
    permissions_to_mock = []
    def setUp(self):
        self.user = UserFactory()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

        self.patch_permission_functions()

    def patch_permission_functions(self):
        for name in self.permissions_to_mock:
            spec = 'teams.permissions.' + name
            mock_obj = mock.Mock(return_value=True)
            patcher = mock.patch(spec, mock_obj)
            patcher.start()
            self.addCleanup(patcher.stop)
            setattr(self, name, mock_obj)

    def _make_timestamp(self, datetime):
        return int(time.mktime(datetime.timetuple()))

class TeamAPITest(TeamAPITestBase):
    permissions_to_mock = [
        'can_delete_team',
        'can_change_team_settings',
        'can_create_team',
    ]
    def setUp(self):
        TeamAPITestBase.setUp(self)
        self.list_url = reverse('api:teams-list')

    def detail_url(self, team):
        return reverse('api:teams-detail', kwargs={
            'team_slug': team.slug,
        }, request=APIRequestFactory().get('/'))

    def check_team_data(self, data, team):
        assert_equal(data['name'], team.name)
        assert_equal(data['slug'], team.slug)
        assert_equal(data['description'], team.description)
        assert_equal(data['is_visible'], team.team_public())
        assert_equal(data['team_visibility'], team.team_visibility.slug)
        assert_equal(data['video_visibility'], team.video_visibility.slug)
        assert_equal(data['membership_policy'],
                     team.get_membership_policy_display())
        assert_equal(data['video_policy'], team.get_video_policy_display())

    def test_get_list(self):
        # we should display these teams
        teams = [
            TeamFactory(team_visibility=TeamVisibility.PUBLIC),
            TeamFactory(team_visibility=TeamVisibility.PRIVATE,
                        member=self.user),
        ]
        # we should not display these teams
        TeamFactory(team_visibility=TeamVisibility.PRIVATE),
        TeamFactory(team_visibility=TeamVisibility.UNLISTED),

        team_map = dict((t.slug, t) for t in teams)
        response = self.client.get(self.list_url)
        assert_equal(response.status_code, status.HTTP_200_OK)
        teams_data = response.data['objects']
        assert_items_equal([t['slug'] for t in teams_data], team_map.keys())
        for team_data in teams_data:
            self.check_team_data(team_data, team_map[team_data['slug']])

    def test_get_details(self):
        team = TeamFactory(admin=self.user, workflow_type='S')
        response = self.client.get(self.detail_url(team))
        assert_equal(response.status_code, status.HTTP_200_OK)
        self.check_team_data(response.data, team)

    def test_create_team(self):
        response = self.client.post(self.list_url, data={
            'name': 'Test Team',
            'slug': 'test-team',
        })
        assert_equal(response.status_code, status.HTTP_201_CREATED,
                     response.content)
        team = Team.objects.get(slug='test-team')
        self.check_team_data(response.data, team)
        assert_equal(team.team_public(), True)
        assert_equal(team.videos_public(), True)
        assert_equal(team.workflow_type, 'O')
        # check that we set the owner of the team to be the user who created
        # it
        assert_true(team.members.filter(role=TeamMember.ROLE_OWNER,
                                        user=self.user).exists())

    def test_create_team_with_data(self):
        response = self.client.post(self.list_url, data={
            'name': 'Test Team',
            'slug': 'test-team',
            'description': 'Test Description',
            'is_visible': False,
            'membership_policy': u'Invitation by any team member',
            'video_policy': u'Managers and admins',
        })
        assert_equal(response.status_code, status.HTTP_201_CREATED,
                     response.content)
        team = Team.objects.get(slug='test-team')
        self.check_team_data(response.data, team)

    def test_create_team_with_type(self):
        response = self.client.post(self.list_url, data={
            'name': 'Test Team',
            'slug': 'test-team',
            'type': 'simple',
        })
        assert_equal(response.status_code, status.HTTP_201_CREATED,
                     response.content)
        team = Team.objects.get(slug='test-team')
        assert_equal(team.workflow_type, 'S')

    def test_create_team_slug_collision(self):
        TeamFactory(slug='slug')
        response = self.client.post(self.list_url, data={
            'slug': 'slug',
            'name': 'Name',
        })
        assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_policy_choice(self):
        response = self.client.post(self.list_url, data={
            'slug': 'slug',
            'name': 'Name',
            'membership_policy': 'invalid-choice',
            'video_policy': 'invalid-choice',
        })
        assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)

    @test_utils.mock_handler(teams.signals.team_settings_changed)
    def test_update_team(self, settings_changed_handler):
        team = TeamFactory(admin=self.user, description='first draft')
        response = self.client.put(self.detail_url(team), data={
            'description': 'second draft',
        })
        assert_equal(response.status_code, status.HTTP_200_OK,
                     response.content)
        team = test_utils.reload_obj(team)
        assert_equal(team.description, 'second draft')

        assert_true(settings_changed_handler.called)
        assert_equal(settings_changed_handler.call_args, mock.call(
            signal=teams.signals.team_settings_changed,
            sender=team,
            user=self.user,
            changed_settings={'description': 'second draft'},
            old_settings={'description': 'first draft'}
        ))

    def test_delete_team_not_allowed(self):
        team = TeamFactory()
        team_id = team.id
        response = self.client.delete(self.detail_url(team))
        assert_equal(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_team_allowed(self):
        self.can_delete_team.return_value = True
        team = TeamFactory()
        response = self.client.delete(self.detail_url(team))
        assert_equal(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        assert_equal(self.can_delete_team.call_args, None)

    def test_set_is_visible(self):
        response = self.client.post(self.list_url, data={
            'name': 'Test Team',
            'slug': 'test-team',
            'is_visible': False,
            'type': 'simple',
        })
        assert_equal(response.status_code, status.HTTP_201_CREATED,
                     response.content)
        team = Team.objects.get(slug='test-team')
        assert_equal(team.team_visibility, TeamVisibility.PRIVATE)
        assert_equal(team.video_visibility, VideoVisibility.PRIVATE)

        self.client.put(self.detail_url(team), data={
            'is_visible': True,
        })
        team = test_utils.reload_obj(team)
        assert_equal(team.team_visibility, TeamVisibility.PUBLIC)
        assert_equal(team.video_visibility, VideoVisibility.PUBLIC)

        # If is_visible is not set, then we should use the team_visibility and
        # video_visibility fields
        self.client.put(self.detail_url(team), data={
            'team_visibility': 'public',
            'video_visibility': 'unlisted',
        })
        team = test_utils.reload_obj(team)
        assert_equal(team.team_visibility, TeamVisibility.PUBLIC)
        assert_equal(team.video_visibility, VideoVisibility.UNLISTED)

    def test_create_team_permissions(self):
        self.can_create_team.return_value = False
        response = self.client.post(self.list_url, data={
            'slug': 'new-slug',
            'name': 'New Name',
        })
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)
        assert_equal(self.can_create_team.call_args, mock.call(self.user))

    def test_update_team_permissions(self):
        team = TeamFactory(admin=self.user)
        self.can_change_team_settings.return_value = False
        response = self.client.put(self.detail_url(team), data={
            'name': 'New Name',
            'slug': 'new-name',
        })
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)
        assert_equal(self.can_change_team_settings.call_args,
                     mock.call(team, self.user))

    def test_create_fields(self):
        response = self.client.options(self.list_url)
        assert_writable_fields(response, 'POST', [
            'name', 'slug', 'type', 'description', 'team_visibility',
            'video_visibility', 'is_visible', 'membership_policy',
            'video_policy',
        ])
        assert_required_fields(response, 'POST', [
            'name', 'slug',
        ])

    def test_update_writable_fields(self):
        team = TeamFactory(admin=self.user)
        response = self.client.options(self.detail_url(team))
        assert_writable_fields(response, 'PUT', [
            'name', 'slug', 'description', 'team_visibility',
            'video_visibility', 'is_visible', 'membership_policy',
            'video_policy',
        ])
        assert_required_fields(response, 'PUT', [])

class TeamMemberAPITest(TeamAPITestBase):
    permissions_to_mock = [
        'can_add_member',
        'can_assign_role',
        'can_remove_member',
    ]
    def setUp(self):
        TeamAPITestBase.setUp(self)
        self.team = TeamFactory(owner=self.user)
        self.list_url = reverse('api:team-members-list', kwargs={
            'team_slug': self.team.slug,
        })

    def detail_url(self, user):
        return reverse('api:team-members-detail', kwargs={
            'team_slug': self.team.slug,
            'identifier': 'id$' + user.secure_id(),
        }, request=APIRequestFactory().get('/'))

    def check_response_data(self, response, user):
        member = self.team.members.get(user=user)
        assert_equal(response.status_code, status.HTTP_200_OK)
        assert_equal(response.data['user'], user_field_data(user))
        assert_equal(response.data['role'], member.role)
        assert_equal(response.data['resource_uri'], self.detail_url(user))

    def test_get_details(self):
        user = TeamMemberFactory(team=self.team).user
        response = self.client.get(self.detail_url(user))
        self.check_response_data(response, user)

    def test_get_with_username(self):
        user = TeamMemberFactory(team=self.team).user
        url = reverse('api:team-members-detail', kwargs={
            'team_slug': self.team.slug,
            'identifier': user.username,
        })
        response = self.client.get(url)
        self.check_response_data(response, user)

    def test_get_non_member_username(self):
        non_member = UserFactory()
        response = self.client.get(self.detail_url(non_member))
        assert_equal(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_team_member(self):
        user = UserFactory()
        response = self.client.post(self.list_url, data={
            'user': user.username,
            'role': 'contributor',
        })
        assert_equal(response.status_code, status.HTTP_201_CREATED,
                     response.content)
        member = self.team.members.get(user=user)
        assert_equal(member.role, TeamMember.ROLE_CONTRIBUTOR)

    def test_add_existing_team_member(self):
        user = TeamMemberFactory(team=self.team).user
        response = self.client.post(self.list_url, data={
            'user': user.username,
            'role': 'contributor',
        })
        assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_role(self):
        member = TeamMemberFactory(team=self.team,
                                   role=TeamMember.ROLE_CONTRIBUTOR)
        response = self.client.put(self.detail_url(member.user), data={
            'role': 'admin',
        })
        assert_equal(response.status_code, status.HTTP_200_OK,
                     response.content)
        assert_equal(test_utils.reload_obj(member).role,
                     TeamMember.ROLE_ADMIN)

    def test_username_in_put(self):
        # test the username field being in a PUT request.  It doesn't really
        # make sense in this case so we should just ignore it
        member = TeamMemberFactory(team=self.team,
                                   role=TeamMember.ROLE_CONTRIBUTOR)
        response = self.client.put(self.detail_url(member.user), data={
            'user': 'foo',
            'role': 'admin',
        })
        assert_equal(response.status_code, status.HTTP_200_OK,
                     response.content)
        assert_equal(test_utils.reload_obj(member).role,
                     TeamMember.ROLE_ADMIN)

    def test_remove_member(self):
        member = TeamMemberFactory(team=self.team,
                                   role=TeamMember.ROLE_CONTRIBUTOR)
        user = member.user
        response = self.client.delete(self.detail_url(member.user))
        assert_equal(response.status_code, status.HTTP_204_NO_CONTENT,
                     response.content)
        assert_false(self.team.members.filter(user=user).exists())
    
    def test_cant_remove_owner(self):
        member = TeamMemberFactory(team=self.team, role=TeamMember.ROLE_OWNER)
        response = self.client.delete(self.detail_url(member.user))
        assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST,
                     response.content)
        assert_true(self.team.members.filter(
            user=member.user, role=TeamMember.ROLE_OWNER).exists())

    def test_cant_remove_self(self):
        response = self.client.delete(self.detail_url(self.user))
        assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST,
                     response.content)
        assert_true(self.team.members.filter(
            user=self.user, role=TeamMember.ROLE_OWNER).exists())

    def test_view_list_permissions(self):
        # only members can view the membership list
        non_member = UserFactory()
        self.client.force_authenticate(user=non_member)
        response = self.client.get(self.list_url)
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_view_details_permissions(self):
        # only members can view details on a member
        non_member = UserFactory()
        self.client.force_authenticate(user=non_member)
        response = self.client.get(self.detail_url(self.user))
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_add_checks_permissions(self):
        self.can_add_member.return_value = False
        response = self.client.post(self.list_url, data={
            'user': UserFactory().username,
            'role': 'contributor',
        })
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)
        assert_equal(self.can_add_member.call_args,
                     mock.call(self.team, self.user,
                               TeamMember.ROLE_CONTRIBUTOR))

    def test_change_checks_permissions(self):
        self.can_assign_role.return_value = False
        member = TeamMemberFactory(team=self.team,
                                   role=TeamMember.ROLE_CONTRIBUTOR)
        response = self.client.put(self.detail_url(member.user), data={
            'user': member.user.username,
            'role': TeamMember.ROLE_ADMIN,
        })
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)
        assert_equal(test_utils.reload_obj(member).role,
                     TeamMember.ROLE_CONTRIBUTOR)
        assert_equal(self.can_assign_role.call_args,
                     mock.call(self.team, self.user, TeamMember.ROLE_ADMIN,
                               member.user))

    def test_remove_checks_permissions(self):
        self.can_remove_member.return_value = False
        member = TeamMemberFactory(team=self.team,
                                   role=TeamMember.ROLE_CONTRIBUTOR)
        response = self.client.delete(self.detail_url(member.user))
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)
        assert_true(self.team.members.filter(user=member.user).exists())
        assert_equal(self.can_remove_member.call_args,
                     mock.call(self.team, self.user))

class ProjectAPITest(TeamAPITestBase):
    permissions_to_mock = [
        'can_create_project',
        'can_edit_project',
        'can_delete_project',
    ]
    def setUp(self):
        TeamAPITestBase.setUp(self)
        self.team = TeamFactory(owner=self.user)
        self.list_url = reverse('api:projects-list', kwargs={
            'team_slug': self.team.slug,
        })

    def detail_url(self, project):
        return reverse('api:projects-detail', kwargs={
            'team_slug': self.team.slug,
            'slug': project.slug,
        })

    def check_project_data(self, data, project):
        assert_equal(data['name'], project.name)
        assert_equal(data['slug'], project.slug)
        assert_equal(data['description'], project.description)
        assert_equal(data['guidelines'], project.guidelines)
        assert_equal(data['created'], format_datetime_field(project.created))
        assert_equal(data['modified'],
                     format_datetime_field(project.modified))
        assert_equal(data['workflow_enabled'], project.workflow_enabled)
        assert_equal(data['resource_uri'],
                     reverse('api:projects-detail', kwargs={
                         'team_slug': self.team.slug,
                         'slug': project.slug,
                     }, request=APIRequestFactory().get('/')))

    def test_list(self):
        projects = [ProjectFactory(team=self.team) for i in xrange(3)]
        project_slug_map = dict((p.slug, p) for p in projects)
        response = self.client.get(self.list_url)
        assert_equal(response.status_code, status.HTTP_200_OK)
        assert_items_equal([p['slug'] for p in response.data['objects']],
                           project_slug_map.keys())
        for project_data in response.data['objects']:
            self.check_project_data(project_data,
                                    project_slug_map[project_data['slug']])

    def test_get(self):
        project = ProjectFactory(team=self.team)
        response = self.client.get(self.detail_url(project))
        assert_equal(response.status_code, status.HTTP_200_OK)
        self.check_project_data(response.data, project)

    def test_create(self):
        response = self.client.post(self.list_url, data={
            'name': 'Test project',
            'slug': 'test-project',
            'description': 'test-description',
            'guidelines': 'test-guidelines',
        })
        assert_equal(response.status_code, status.HTTP_201_CREATED)
        project = self.team.project_set.get(slug='test-project')
        assert_equal(project.name, 'Test project')
        assert_equal(project.description, 'test-description')
        assert_equal(project.guidelines, 'test-guidelines')

    def test_update(self):
        project = ProjectFactory(team=self.team)
        response = self.client.put(self.detail_url(project), data={
            'description': 'New description',
        })
        assert_equal(response.status_code, status.HTTP_200_OK,
                     response.content)
        assert_equal(test_utils.reload_obj(project).description,
                     'New description')

    def test_delete(self):
        project = ProjectFactory(team=self.team, slug='test-slug')
        response = self.client.delete(self.detail_url(project))
        assert_equal(response.status_code, status.HTTP_204_NO_CONTENT,
                     response.content)
        assert_false(self.team.project_set
                     .filter(slug='project-slug').exists())

    def test_list_permissions(self):
        self.client.force_authenticate(user=UserFactory())
        response = self.client.get(self.list_url)
        assert_equals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_permissions(self):
        project = ProjectFactory(team=self.team)
        self.client.force_authenticate(user=UserFactory())
        response = self.client.get(self.detail_url(project))
        assert_equals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_required_fields(self):
        response = self.client.options(self.list_url)
        assert_required_fields(response, 'POST', ['name', 'slug'])

    def test_update_required_fields(self):
        project = ProjectFactory(team=self.team)
        response = self.client.options(self.detail_url(project))
        assert_required_fields(response, 'PUT', [])

    def test_create_permissions(self):
        self.can_create_project.return_value = False
        response = self.client.post(self.list_url, data={
            'name': 'Test project',
            'slug': 'test-project',
        })
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)
        assert_equal(self.can_create_project.call_args,
                     mock.call(self.user, self.team))

    def test_update_permissions(self):
        project = ProjectFactory(team=self.team)
        self.can_edit_project.return_value = False
        response = self.client.put(self.detail_url(project), data={
            'name': 'Test project',
        })
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN,
                     response.content)
        assert_equal(self.can_edit_project.call_args,
                     mock.call(self.team, self.user, project))

    def test_delete_permissions(self):
        project = ProjectFactory(team=self.team)
        self.can_delete_project.return_value = False
        response = self.client.delete(self.detail_url(project))
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN,
                     response.content)
        assert_equal(self.can_delete_project.call_args,
                     mock.call(self.user, self.team, project))

class TasksAPITest(TeamAPITestBase):
    TYPE_SUBTITLE = Task.TYPE_IDS['Subtitle']
    TYPE_TRANSLATE = Task.TYPE_IDS['Translate']
    TYPE_REVIEW = Task.TYPE_IDS['Review']
    TYPE_APPROVAL = Task.TYPE_IDS['Approve']

    permissions_to_mock = [
        'can_assign_tasks',
        'can_delete_tasks',
    ]

    @test_utils.patch_for_test('messages.tasks.team_task_assigned')
    @test_utils.patch_for_test('teams.models.Task.now')
    def setUp(self, mock_now, mock_team_task_assigned):
        TeamAPITestBase.setUp(self)
        self.member = UserFactory()
        self.manager = UserFactory()
        self.admin = UserFactory()
        self.team = TeamFactory(
            workflow_type='O', workflow_enabled=True, task_expiration=1,
            owner=self.user, admin=self.admin, manager=self.manager,
            member=self.member,
        )
        workflow = self.team.get_workflow()
        workflow.review_allowed = 20 # manager must review
        workflow.approve_allowed = 20 # admin must approve
        workflow.save()
        self.list_url = reverse('api:tasks-list', kwargs={
            'team_slug': self.team.slug,
        })
        self.project = ProjectFactory(team=self.team)
        self.team_video = TeamVideoFactory(team=self.team,
                                           project=self.project)
        self.task_factory = factory.make_factory(
            TaskFactory, team=self.team, team_video=self.team_video)
        mock_now.return_value = self.now = datetime(2015, 1, 1)
        self.mock_team_task_assigned = mock_team_task_assigned

    def detail_url(self, task):
        return reverse('api:tasks-detail', kwargs={
            'team_slug': self.team.slug,
            'id': task.id,
        })

    def check_task_data(self, data, task):
        assert_equal(data['video_id'], task.team_video.video.video_id)
        assert_equal(data['language'], task.language)
        assert_equal(data['id'], task.id)
        assert_equal(data['type'], task.get_type_display())
        assert_equal(data['assignee'], user_field_data(task.assignee))
        assert_equal(data['priority'], task.priority)
        assert_equal(data['created'], format_datetime_field(task.created))
        assert_equal(data['modified'], format_datetime_field(task.modified))
        assert_equal(data['completed'], format_datetime_field(task.completed))
        assert_equal(data['approved'], task.get_approved_display())
        assert_equal(data['resource_uri'],
                     reverse('api:tasks-detail', kwargs={
                         'team_slug': self.team.slug,
                         'id': task.id,
                     }, request=APIRequestFactory().get('/')))

    def make_a_bunch_of_tasks(self):
        """Make a bunch of tasks in different states."""
        return [
            self.task_factory(language='en'),
            self.task_factory(language='es', assignee=self.member, priority=1),
            self.task_factory(language='fr', assignee=self.manager,
                              type=self.TYPE_REVIEW, priority=-1),
            self.task_factory(language='de', assignee=self.admin,
                              type=self.TYPE_APPROVAL),
            self.task_factory(language='pt-br', assignee=self.member,
                              completed=datetime(2015, 1, 1))
        ]

    def check_list_results(self, correct_tasks, params=None):
        task_map = dict((t.id, t) for t in correct_tasks)
        response = self.client.get(self.list_url, params)
        assert_equal(response.status_code, status.HTTP_200_OK)
        response_objects = response.data['objects']
        assert_items_equal([t['id'] for t in response_objects], task_map.keys())
        for task_data in response_objects:
            self.check_task_data(task_data, task_map[task_data['id']])

    def test_list(self):
        self.check_list_results(self.make_a_bunch_of_tasks())

    def test_assignee_filter(self):
        correct_tasks = [
            self.task_factory(language='es', assignee=self.member),
            self.task_factory(language='fr', assignee=self.member,
                              completed=datetime(2015, 1, 1))
        ]
        incorrect_tasks = [
            self.task_factory(language='en'),
            self.task_factory(language='fr', assignee=self.admin),
        ]
        self.check_list_results(correct_tasks, {
            'assignee': self.member.username,
        })
        self.check_list_results(correct_tasks, {
            'assignee': 'id$' + self.member.secure_id(),
        })

    def test_priority_filter(self):
        correct_tasks = [
            t for t in self.make_a_bunch_of_tasks()
            if t.priority == 1
        ]
        self.check_list_results(correct_tasks, {
            'priority': 1,
        })

    def test_language_filter(self):
        correct_tasks = [
            t for t in self.make_a_bunch_of_tasks()
            if t.language == 'en'
        ]
        self.check_list_results(correct_tasks, {
            'language': 'en',
        })

    def check_subtitle_filter(self, type_value, type_label):
        correct_tasks = [
            t for t in self.make_a_bunch_of_tasks()
            if t.type==type_value
        ]
        self.check_list_results(correct_tasks, {
            'type': type_label,
        })

    def test_subtitle_type_filter(self):
        self.check_subtitle_filter(self.TYPE_SUBTITLE, 'Subtitle')

    def test_translate_type_filter(self):
        self.check_subtitle_filter(self.TYPE_TRANSLATE, 'Translate')

    def test_review_type_filter(self):
        self.check_subtitle_filter(self.TYPE_REVIEW, 'Review')

    def test_approve_type_filter(self):
        self.check_subtitle_filter(self.TYPE_APPROVAL, 'Approve')

    def test_invalid_type_filter(self):
        self.make_a_bunch_of_tasks()
        self.check_list_results([], {
            'type': 'invalid-type-name',
        })

    def test_video_id_filter(self):
        tasks = self.make_a_bunch_of_tasks()
        self.check_list_results(tasks, {
            'video_id': self.team_video.video.video_id,
        })

    def test_video_id_filter_video_not_in_team(self):
        # if the video isn't in the team, we should return no tasks
        self.make_a_bunch_of_tasks()
        team_video = TeamVideoFactory()
        TaskFactory(team=team_video.team, team_video=team_video,
                    type=self.TYPE_SUBTITLE)
        self.check_list_results([], {
            'video_id': team_video.video.video_id,
        })

    def test_completed_filter(self):
        correct_tasks = [
            t for t in self.make_a_bunch_of_tasks()
            if t.completed
        ]
        self.check_list_results(correct_tasks, {
            'completed': 1,
        })

    def test_completed_before_filter(self):
        corrrect_tasks = [
            self.task_factory(language='en', assignee=self.member,
                              completed=datetime(2014, 12, 31)),
        ]
        incorrect_tasks = [
            self.task_factory(language='es', assignee=self.member),
            self.task_factory(language='fr', assignee=self.member,
                              completed=datetime(2015, 1, 1))
        ]
        self.check_list_results(corrrect_tasks, {
            'completed-before': self._make_timestamp(datetime(2015,1,1)),
        })

    def test_completed_after_filter(self):
        corrrect_tasks = [
            self.task_factory(language='en', assignee=self.member,
                              completed=datetime(2015, 1, 1))
        ]
        incorrect_tasks = [
            self.task_factory(language='es', assignee=self.member),
            self.task_factory(language='fr', assignee=self.member,
                              completed=datetime(2014, 12, 31)),
        ]
        self.check_list_results(corrrect_tasks, {
            'completed-after': self._make_timestamp(datetime(2015,1,1)),
        })

    def test_open_filter(self):
        correct_tasks = [
            t for t in self.make_a_bunch_of_tasks()
            if not t.completed
        ]
        self.check_list_results(correct_tasks, {
            'open': 1,
        })

    def test_deleted_tasks(self):
        task = self.task_factory(language='es', deleted=True)
        self.check_list_results([])

    def check_list_order(self, order_param):
        task_qs = self.team.task_set.all().order_by(order_param)
        response = self.client.get(self.list_url, {'order_by': order_param})
        assert_equal(response.status_code, status.HTTP_200_OK)
        assert_equal([t['id'] for t in response.data['objects']],
                     [t.id for t in task_qs])

    def test_order_by_filter(self):
        tasks = self.make_a_bunch_of_tasks()
        self.check_list_order('created')
        self.check_list_order('-created')
        self.check_list_order('modified')
        self.check_list_order('-modified')
        self.check_list_order('priority')
        self.check_list_order('-priority')
        self.check_list_order('type')
        self.check_list_order('-type')

    def test_detail(self):
        tasks = self.make_a_bunch_of_tasks()
        for task in tasks:
            response = self.client.get(self.detail_url(task))
            assert_equal(response.status_code, status.HTTP_200_OK)
            self.check_task_data(response.data, task)

    def check_task_creation_extra(self, task, assigned):
        """Check that extra tasks were run for the task."""
        if assigned:
            assert_equal(self.mock_team_task_assigned.delay.call_args,
                         mock.call(task.id))
            # since the task was assigned, we should set the expiration date
            assert_equal(task.expiration_date,
                         self.now + timedelta(days=self.team.task_expiration))
        else:
            assert_equal(self.mock_team_task_assigned.delay.call_count, 0)
            assert_equal(task.expiration_date, None)

        assert_equal(test_utils.video_changed_tasks.delay.call_args,
                     mock.call(task.team_video.video_id))

    def test_create(self):
        response = self.client.post(self.list_url, {
            'video_id': self.team_video.video.video_id,
            'type': 'Subtitle',
            'priority': 3,
        })
        assert_equal(response.status_code, status.HTTP_201_CREATED,
                     response.content)
        task = Task.objects.get(id=response.data['id'])
        assert_equal(task.team_video, self.team_video)
        assert_equal(task.team, self.team)
        assert_equal(task.language, '')
        assert_equal(task.type, self.TYPE_SUBTITLE)
        assert_equal(task.priority, 3)
        self.check_task_data(response.data, task)
        self.check_task_creation_extra(task, assigned=False)

    def test_create_and_assign(self):
        response = self.client.post(self.list_url, {
            'video_id': self.team_video.video.video_id,
            'language': 'en',
            'type': 'Subtitle',
            'assignee': self.member.username,
        })
        assert_equal(response.status_code, status.HTTP_201_CREATED,
                     response.content)
        task = Task.objects.get(id=response.data['id'])
        assert_equal(task.assignee, self.member)
        self.check_task_creation_extra(task, assigned=True)

    def test_create_with_invalid_video_id(self):
        # try creating with a video that's not in our team
        video = VideoFactory()
        response = self.client.post(self.list_url, {
            'video_id': video.video_id,
            'language': 'en',
            'type': 'Subtitle',
            'priority': 3,
        })
        assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_invalid_assignee(self):
        # try creating with a user that's not in our team
        user = UserFactory()
        response = self.client.post(self.list_url, {
            'video_id': self.team_video.video.video_id,
            'language': 'en',
            'type': 'Subtitle',
            'assignee': user.username,
        })
        assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update(self):
        task = self.task_factory(language='es')
        response = self.client.put(self.detail_url(task), {
            'priority': 3
        })
        assert_equal(response.status_code, status.HTTP_200_OK,
                     response.content)
        assert_equal(test_utils.reload_obj(task).priority, 3)
        self.check_task_creation_extra(task, assigned=False)

    def test_set_approved(self):
        # I have no clue why a client would change the approved field
        # manually, but the old API supported it.
        task = self.task_factory(language='es')
        response = self.client.put(self.detail_url(task), {
            'approved': 'Rejected',
        })
        assert_equal(response.status_code, status.HTTP_200_OK,
                     response.content)
        assert_equal(test_utils.reload_obj(task).approved,
                     Task.APPROVED_IDS['Rejected'])
        self.check_task_creation_extra(task, assigned=False)

    def test_assign(self):
        task = self.task_factory(language='es')
        response = self.client.put(self.detail_url(task), {
            'assignee': self.member.username,
        })
        assert_equal(response.status_code, status.HTTP_200_OK,
                     response.content)
        task = test_utils.reload_obj(task)
        assert_equal(task.assignee, self.member)
        self.check_task_creation_extra(task, assigned=True)

    def test_assign_with_max_tasks(self):
        self.team.max_tasks_per_member = 1
        self.team.save()
        self.task_factory(language='en', assignee=self.member)
        task = self.task_factory(language='es')
        response = self.client.put(self.detail_url(task), {
            'assignee': self.member.username,
        })
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_complete(self):
        task = self.task_factory(language='es', assignee=self.member)
        pipeline.add_subtitles(self.team_video.video, 'es', None,
                               author=self.member)
        response = self.client.put(self.detail_url(task), {
            'complete': 1,
        })
        assert_equal(response.status_code, status.HTTP_200_OK,
                     response.content)
        task = test_utils.reload_obj(task)
        assert_not_equal(task.completed, None)
        assert_equal(task.approved, Task.APPROVED_IDS['Approved'])
        self.check_task_creation_extra(task, assigned=False)

    def test_complete_assigns_task(self):
        task = self.task_factory(language='es')
        pipeline.add_subtitles(self.team_video.video, 'es', None,
                               author=self.member)
        response = self.client.put(self.detail_url(task), {
            'complete': 1,
        })
        assert_equal(response.status_code, status.HTTP_200_OK,
                     response.content)
        task = test_utils.reload_obj(task)
        assert_equal(task.approved, Task.APPROVED_IDS['Approved'])
        assert_equal(task.assignee, self.user)

    def test_send_back(self):
        task = self.task_factory(language='es', assignee=self.member)
        pipeline.add_subtitles(self.team_video.video, 'es', None,
                               author=self.member)
        task.approved = Task.APPROVED_IDS['Approved']
        task.complete()
        review_task = self.team_video.task_set.incomplete().get()
        response = self.client.put(self.detail_url(review_task), {
            'send_back': 1,
        })
        assert_equal(response.status_code, status.HTTP_200_OK,
                     response.content)
        assert_equal(test_utils.reload_obj(review_task).approved,
                     Task.APPROVED_IDS['Rejected'])

    def test_delete(self):
        task = self.task_factory(language='es', assignee=self.member)
        response = self.client.delete(self.detail_url(task))
        assert_equal(response.status_code, status.HTTP_204_NO_CONTENT)
        # deleting should flag the task as deleted, but keep the object around
        # in the DB
        assert_equal(self.team_video.task_set.not_deleted().count(), 0)
        assert_true(test_utils.obj_exists(task))

    def test_create_fields(self):
        response = self.client.options(self.list_url)
        assert_writable_fields(response, 'POST', [
            'video_id', 'language', 'type', 'assignee', 'priority',
            'approved',
        ])
        assert_required_fields(response, 'POST', [
            'video_id', 'type',
        ])

    def test_update_writable_fields(self):
        task = self.task_factory()
        response = self.client.options(self.detail_url(task))
        assert_writable_fields(response, 'PUT', [
            'language', 'assignee', 'priority', 'send_back', 'complete',
            'approved',
        ])
        assert_required_fields(response, 'PUT', [])

    # these permissions checks seem strange, but I tried to match what the old
    # API code did
    def test_create_checks_can_assign_permission(self):
        self.can_assign_tasks.return_value = False
        response = self.client.post(self.list_url, data={
            'video_id': self.team_video.video.video_id,
            'type': 'Subtitle',
        })
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)
        assert_equal(self.can_assign_tasks.call_args,
                     mock.call(self.team, self.user, self.team_video.project))

    def test_update_checks_can_assign_permission(self):
        self.can_assign_tasks.return_value = False
        task = self.task_factory()
        response = self.client.put(self.detail_url(task), data={})
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN,
                     response.content)
        assert_equal(self.can_assign_tasks.call_args,
                     mock.call(self.team, self.user, self.team_video.project))

    def test_delete_checks_can_assign_permission(self):
        self.can_delete_tasks.return_value = False
        task = self.task_factory(language='en')
        response = self.client.delete(self.detail_url(task))
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN,
                     response.content)
        assert_equal(self.can_delete_tasks.call_args, mock.call(
            self.team, self.user, self.team_video.project, task.language))

    def test_get_doesnt_complete(self):
        task = self.task_factory(language='en')
        self.client.get(self.detail_url(task))
        task = test_utils.reload_obj(task)
        assert_equal(task.completed, None)

class TeamApplicationAPITest(TeamAPITestBase):
    permissions_to_mock = [
        'can_invite',
    ]
    def setUp(self):
        TeamAPITestBase.setUp(self)
        self.team = TeamFactory(admin=self.user,
                                membership_policy=Team.APPLICATION)
        self.setup_applications()
        self.list_url = reverse('api:team-application-list', kwargs={
            'team_slug': self.team.slug,
        })

    def setup_applications(self):
        self.applications = []
        self.application_by_status = {}
        # will map application status -> application objects
        for status, label in Application.STATUSES:
            if status == Application.STATUS_PENDING:
                modified = None
            else:
                modified = datetime(2015, 2, 1)
            app = Application.objects.create(
                team=self.team, user=UserFactory(), note='test-note',
                status=status, created=datetime(2015, 1, 1),
                modified=modified)
            self.applications.append(app)
            self.application_by_status[status] = app

    def detail_url(self, application):
        return reverse('api:team-application-detail', kwargs={
            'team_slug': self.team.slug,
            'id': application.id,
        }, request=APIRequestFactory().get('/'))

    def check_application_data(self, data, application):
        assert_equal(data['user'], user_field_data(application.user))
        assert_equal(data['note'], application.note)
        assert_equal(data['status'], application.get_status_display())
        assert_equal(data['id'], application.id)
        assert_equal(data['created'],
                     format_datetime_field(application.created))
        if application.modified:
            assert_equal(data['modified'],
                         format_datetime_field(application.modified))
        else:
            assert_equal(data['modified'], None)
        assert_equal(data['resource_uri'], self.detail_url(application))

    def test_list(self):
        application_map = {a.id: a for a in self.applications}
        response = self.client.get(self.list_url)
        assert_equal(response.status_code, status.HTTP_200_OK)
        assert_equal([a['id'] for a in response.data['objects']],
                     application_map.keys())
        for application_data in response.data['objects']:
            self.check_application_data(
                application_data, application_map[application_data['id']])

    def test_details(self):
        for application in self.applications:
            response = self.client.get(self.detail_url(application))
            assert_equal(response.status_code, status.HTTP_200_OK)
            self.check_application_data(response.data, application)

    def check_filter_result(self, filters, correct_applications):
        response = self.client.get(self.list_url, filters)
        assert_equal(response.status_code, status.HTTP_200_OK)
        assert_equal([a['id'] for a in response.data['objects']],
                     [a.id for a in correct_applications])

    def test_user_filter(self):
        user = self.applications[0].user
        self.check_filter_result({'user': user.username},
                                 [self.applications[0]])

    def test_user_filter_with_id(self):
        user = self.applications[0].user
        self.check_filter_result({'user': 'id$' + user.secure_id()},
                                 [self.applications[0]])

    def test_status_filter(self):
        self.check_filter_result(
            {'status': 'Denied'},
            [self.application_by_status[Application.STATUS_DENIED]])

    def test_invalid_status_filter(self):
        self.check_filter_result({'status': 'Invalid-Value'}, [])

    def test_before_filter(self):
        app = self.applications[0]
        app.created = datetime(2014, 1, 1)
        app.save()
        self.check_filter_result(
            {'before': self._make_timestamp(datetime(2014, 1, 2))},
            [app])

    def test_after_filter(self):
        app = self.applications[0]
        app.created = datetime(2014, 1, 1)
        app.save()
        self.check_filter_result(
            {'after': self._make_timestamp(datetime(2014, 1, 2))},
            self.applications[1:])

    def test_approve(self):
        app = self.application_by_status[Application.STATUS_PENDING]
        response = self.client.put(self.detail_url(app), {
            'status': 'Approved',
        })
        app = test_utils.reload_obj(app)
        assert_equal(app.status, Application.STATUS_APPROVED)
        assert_not_equal(app.modified, None)
        assert_true(self.team.user_is_member(app.user))

    def test_deny(self):
        app = self.application_by_status[Application.STATUS_PENDING]
        response = self.client.put(self.detail_url(app), {
            'status': 'Denied',
        })
        assert_equal(response.status_code, status.HTTP_200_OK,
                     response.content)
        app = test_utils.reload_obj(app)
        assert_equal(app.status, Application.STATUS_DENIED)
        assert_not_equal(app.modified, None)

    def test_cant_change_status_if_not_pending(self):
        for status_value, label in Application.STATUSES:
            if status_value == Application.STATUS_PENDING:
                continue
            app = self.application_by_status[status_value]
            response = self.client.put(self.detail_url(app), {
                'status': 'Denied',
            })
            assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST,
                         response.content)

    def test_get_list_checks_can_invite_permission(self):
        self.can_invite.return_value = False
        response = self.client.get(self.list_url)
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)
        assert_equal(self.can_invite.call_args,
                     mock.call(self.team, self.user))

    def test_get_detail_checks_can_invite_permission(self):
        self.can_invite.return_value = False
        response = self.client.get(self.detail_url(self.applications[0]))
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)
        assert_equal(self.can_invite.call_args,
                     mock.call(self.team, self.user))

    def test_put_checks_can_invite_permission(self):
        self.can_invite.return_value = False
        response = self.client.put(self.detail_url(self.applications[0]), {})
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)
        assert_equal(self.can_invite.call_args,
                     mock.call(self.team, self.user))

    def test_get_list_for_non_application_team(self):
        # if the team is not an application team, we should always return 0
        # applications for the listing
        self.team.membership_policy = Team.INVITATION_BY_MANAGER
        self.team.save()
        response = self.client.get(self.list_url)
        assert_equal(response.status_code, status.HTTP_200_OK)
        assert_equal(response.data['objects'], [])

    def test_get_detail_for_non_application_team(self):
        # if the team is not an application team, we should always return 404
        # errors for the detail request
        self.team.membership_policy = Team.INVITATION_BY_MANAGER
        self.team.save()
        response = self.client.get(self.detail_url(self.applications[0]))
        assert_equal(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cant_put_for_non_application_team(self):
        # if the team is not an application team, we should always return 404
        # errors for put requests
        self.team.membership_policy = Team.INVITATION_BY_MANAGER
        self.team.save()
        response = self.client.put(self.detail_url(self.applications[0]), {})
        assert_equal(response.status_code, status.HTTP_404_NOT_FOUND)

class TeamNotificationsAPITest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.team = TeamFactory(admin=self.user)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.notifications = [
            self.make_notification(response_status=200),
            self.make_notification(response_status=500,
                                   error_message="Response status: 500"),
            self.make_notification(error_message="Response timeout"),
            self.make_notification() # still in progress
        ]
        self.list_url = reverse('api:team-notifications-list',
                                args=(self.team.slug,))

    def details_url(self, notification):
        return reverse('api:team-notifications-detail',
                       args=(self.team.slug, notification.number))

    def make_notification(self, response_status=None, error_message=None):
        notification = TeamNotification.create_new(
            self.team,
            'http://example.com/notification/',
            {"foo": "bar"})
        notification.response_status = response_status
        notification.error_message = error_message
        notification.save()
        return notification

    def check_data(self, notification, data):
        assert_equal(data['number'], notification.number)
        assert_equal(data['url'], notification.url)
        assert_equal(data['data'], json.loads(notification.data))
        assert_equal(data['timestamp'],
                     format_datetime_field(notification.timestamp))
        assert_equal(data['in_progress'], notification.is_in_progress())
        assert_equal(data['response_status'], notification.response_status)
        assert_equal(data['error_message'], notification.error_message)

    def test_listing(self):
        response = self.client.get(self.list_url)
        assert_equal(response.status_code, status.HTTP_200_OK)
        assert_equal(len(response.data['objects']), len(self.notifications))
        # notifications should be listed last to first
        for notification, data in zip(reversed(self.notifications),
                                      response.data['objects']):
            self.check_data(notification, data)

    def test_details(self):
        for notification in self.notifications:
            response = self.client.get(self.details_url(notification))
            assert_equal(response.status_code, status.HTTP_200_OK)
            self.check_data(notification, response.data)

    @test_utils.patch_for_test('teams.permissions.can_view_notifications')
    def test_permissions_check(self, can_view_notifications):
        can_view_notifications.return_value = False
        def check_permission_denied(url):
            response = self.client.get(url)
            assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)
            assert_equal(can_view_notifications.call_args,
                         mock.call(self.team, self.user))

        check_permission_denied(self.list_url)
        check_permission_denied(self.details_url(self.notifications[0]))
