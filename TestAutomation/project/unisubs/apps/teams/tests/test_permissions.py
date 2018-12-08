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
from django.test import TestCase
from django.urls import reverse
from teams.models import Team, TeamVideo, TeamMember, Workflow, Task
from auth.models import CustomUser as User
from contextlib import contextmanager
from testhelpers import views as helpers
from utils.factories import *
from utils.translation import ALL_LANGUAGE_CODES

from teams.permissions_const import *
from teams.permissions import (
    remove_role, add_role, can_message_all_members, can_add_video,
    roles_user_can_assign, can_rename_team, can_view_settings_tab,
    can_change_team_settings, can_view_tasks_tab, can_invite,
    can_change_video_settings, can_review, can_edit_project,
    can_create_and_edit_subtitles, can_create_task_subtitle,
    can_create_task_translate, can_join_team, can_edit_video, can_approve,
    roles_user_can_invite, can_add_video_somewhere, can_assign_tasks,
    can_create_and_edit_translations, save_role, can_remove_video,
    can_delete_team, can_delete_video, can_post_edit_subtitles, can_manage_subtitles, can_send_email_invite
)


TOTAL_LANGS = len(ALL_LANGUAGE_CODES)


def _set_subtitles(team_video, language, original, complete, translations=[]):
    translations = [{'code': lang, 'is_original': False, 'is_complete': True,
                     'num_subs': 1} for lang in translations]

    data = {'code': language, 'is_original': original, 'is_complete': complete,
            'num_subs': 1, 'translations': translations}

    helpers._add_lang_to_video(team_video.video, data, None)


class BaseTestPermission(TestCase):
    def setUp(self):
        self.setup_users()
        self.setup_team()
        self.setup_videos()

    def setup_users(self):
        self.user = UserFactory()
        self.owner_account = UserFactory(username='owner')
        self.outsider = UserFactory(username='outsider')
        self.site_admin = UserFactory(username='site_admin', is_staff=True)

    def setup_team(self):
        self.team = TeamFactory()
        self.owner = TeamMemberFactory(team=self.team,
                                       user=self.owner_account,
                                       role=TeamMember.ROLE_OWNER)
        self.test_project = ProjectFactory(team=self.team)
        self.default_project = self.team.default_project

    def setup_videos(self):
        self.project_video = TeamVideoFactory(team=self.team,
                                              added_by=self.owner_account,
                                              project=self.test_project)
        self.nonproject_video = TeamVideoFactory(team=self.team,
                                                 added_by=self.owner_account)

    def clear_cached_workflows(self):
        # delete the _cached_workflow attributes of our videos.  Their values
        # may have been changed.
        for video in (self.nonproject_video, self.project_video):
            if hasattr(video, '_cached_workflow'):
                del video._cached_workflow

    @contextmanager
    def role(self, r, project=None, lang=None):
        add_role(self.team, self.user, self.owner, r, project=project,
                 lang=lang)

        # Handle the caching in permissions.get_role_for_target().
        self.uncache_team_member()

        try:
            yield
        finally:
            remove_role(self.team, self.user, r)

        # Handle the caching in permissions.get_role_for_target().
        self.uncache_team_member()

    def uncache_team_member(self):
        self.team.uncache_member(self.user)
        if hasattr(self.user, '_cached_teammember'):
            delattr(self.user, '_cached_teammember')

    def update_team(self, **attrs):
        for name, value in attrs.items():
            setattr(self.team, name, value)
        self.team.save()

    def update_workflow(self, **attrs):
        workflow = self.team.get_workflow()
        for name, value in attrs.items():
            setattr(workflow, name, value)
        workflow.save()

class TestRules(BaseTestPermission):
    # Testing specific permissions
    def test_roles_assignable(self):
        user, team = self.user, self.team

        # Owners can do anything including creating other owners.
        with self.role(ROLE_OWNER):
            self.assertItemsEqual(roles_user_can_assign(team, user, None), [
                ROLE_OWNER, ROLE_ADMIN, ROLE_MANAGER, ROLE_CONTRIBUTOR,
                ROLE_PROJ_LANG_MANAGER
            ])

        # Admins can do anything except assign owners and changing owners' roles.
        with self.role(ROLE_ADMIN):
            self.assertItemsEqual(roles_user_can_assign(team, user, None), [
                ROLE_MANAGER, ROLE_CONTRIBUTOR, ROLE_PROJ_LANG_MANAGER
            ])
            self.assertItemsEqual(roles_user_can_assign(team, user, self.owner.user), [])

        # Restricted Admins can't assign roles at all.
        with self.role(ROLE_ADMIN, self.test_project):
            self.assertItemsEqual(roles_user_can_assign(team, user, None), [])

        # No one else can assign roles.
        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER]:
            with self.role(r):
                self.assertItemsEqual(roles_user_can_assign(team, user, None), [])

    def test_roles_inviteable(self):
        user, team = self.user, self.team

        # Owners can do anything but owners.
        with self.role(ROLE_OWNER):
            self.assertItemsEqual(roles_user_can_invite(team, user), [
                ROLE_ADMIN, ROLE_MANAGER, ROLE_CONTRIBUTOR
            ])

        # Admins can do anything except invite owners.
        with self.role(ROLE_ADMIN):
            self.assertItemsEqual(roles_user_can_invite(team, user), [
                ROLE_ADMIN, ROLE_MANAGER, ROLE_CONTRIBUTOR
            ])

        # Restricted Admins can only invite contributors.
        with self.role(ROLE_ADMIN, self.test_project):
            self.assertItemsEqual(roles_user_can_invite(team, user), [ROLE_CONTRIBUTOR])

        # Everyone else can only invite contributors.
        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER]:
            with self.role(r):
                self.assertItemsEqual(roles_user_can_invite(team, user), [ROLE_CONTRIBUTOR])

    def test_can_rename_team(self):
        user = self.user
        team = self.team

        # Owners can rename teams
        with self.role(ROLE_OWNER):
            self.assertTrue(can_rename_team(team, user))

        # But no one else can rename a team
        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN]:
            with self.role(r):
                self.assertFalse(can_rename_team(team, user))

    def test_can_delete_team(self):
        user = self.user
        team = self.team

        # Owners can delete teams
        with self.role(ROLE_OWNER):
            self.assertTrue(can_delete_team(team, user))

        # But no one else can delete a team
        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN]:
            with self.role(r):
                self.assertFalse(can_delete_team(team, user))

    def test_can_join_team(self):
        user, team, outsider = self.user, self.team, self.outsider

        # Current members can't join the team.
        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertFalse(can_join_team(team, user))

        # Outsiders can join the team.
        team.membership_policy = Team.OPEN
        team.save()
        self.assertTrue(can_join_team(team, outsider))

        # But not if the team requires invitation/application.
        for policy in [Team.APPLICATION, Team.INVITATION_BY_ALL, Team.INVITATION_BY_MANAGER, Team.INVITATION_BY_ADMIN]:
            team.membership_policy = policy
            team.save()
            self.assertFalse(can_join_team(team, outsider))

    def test_can_add_video(self):
        user = self.user
        team = self.team

        # Policy: members.
        team.video_policy = Team.VP_MEMBER
        team.save()

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_add_video(team, user))

        self.assertFalse(can_add_video(team, self.outsider))

        # Policy: managers.
        team.video_policy = Team.VP_MANAGER
        team.save()

        for r in [ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_add_video(team, user))

        with self.role(ROLE_CONTRIBUTOR):
            self.assertFalse(can_add_video(team, user))

        self.assertFalse(can_add_video(team, self.outsider))

        # Make sure narrowings are taken into account.
        with self.role(ROLE_MANAGER, self.test_project):
            self.assertFalse(can_add_video(team, user))
            self.assertTrue(can_add_video(team, user, project=self.test_project))

        # Policy: admins.
        team.video_policy = Team.VP_ADMIN
        team.save()

        for r in [ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_add_video(team, user))

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER]:
            with self.role(r):
                self.assertFalse(can_add_video(team, user))

        self.assertFalse(can_add_video(team, self.outsider))

    def test_can_edit_video(self):
        user, team = self.user, self.team

        # Policy: members.
        team.video_policy = Team.VP_MEMBER
        team.save()

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_edit_video(self.nonproject_video, user))

        self.assertFalse(can_edit_video(self.nonproject_video, self.outsider))

        # Policy: managers.
        team.video_policy = Team.VP_MANAGER
        team.save()

        for r in [ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_edit_video(self.nonproject_video, user))

        with self.role(ROLE_CONTRIBUTOR):
            self.assertFalse(can_edit_video(self.nonproject_video, user))

        self.assertFalse(can_edit_video(self.nonproject_video, self.outsider))

        # Make sure narrowings are taken into account.
        with self.role(ROLE_MANAGER, self.test_project):
            self.assertFalse(can_edit_video(self.nonproject_video, user))
            self.assertTrue(can_edit_video(self.project_video, user))

        # Policy: admins.
        team.video_policy = Team.VP_ADMIN
        team.save()

        for r in [ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_edit_video(self.nonproject_video, user))

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER]:
            with self.role(r):
                self.assertFalse(can_edit_video(self.nonproject_video, user))

        self.assertFalse(can_edit_video(self.nonproject_video, self.outsider))

    def test_can_remove_video(self):
        user, team = self.user, self.team

        # Policy: members.
        team.video_policy = Team.VP_MEMBER
        team.save()

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_remove_video(self.nonproject_video, user))

        self.assertFalse(can_remove_video(self.nonproject_video, self.outsider))

        # Policy: managers.
        team.video_policy = Team.VP_MANAGER
        team.save()

        for r in [ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_remove_video(self.nonproject_video, user))

        with self.role(ROLE_CONTRIBUTOR):
            self.assertFalse(can_remove_video(self.nonproject_video, user))

        self.assertFalse(can_remove_video(self.nonproject_video, self.outsider))

        # Make sure narrowings are taken into account.
        with self.role(ROLE_MANAGER, self.test_project):
            self.assertFalse(can_remove_video(self.nonproject_video, user))
            self.assertTrue(can_remove_video(self.project_video, user))

        # Policy: admins.
        team.video_policy = Team.VP_ADMIN
        team.save()

        for r in [ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_remove_video(self.nonproject_video, user))

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER]:
            with self.role(r):
                self.assertFalse(can_remove_video(self.nonproject_video, user))

        self.assertFalse(can_remove_video(self.nonproject_video, self.outsider))

    def test_can_delete_video(self):
        user, team = self.user, self.team

        for r in [ROLE_OWNER, ROLE_ADMIN]:
            with self.role(r):
                self.assertTrue(can_delete_video(self.nonproject_video, user))
        for r in [ROLE_MANAGER, ROLE_CONTRIBUTOR]:
            with self.role(r):
                self.assertFalse(can_delete_video(self.nonproject_video, user))

        self.assertFalse(can_delete_video(self.nonproject_video, self.outsider))


    def test_can_view_settings_tab(self):
        # Only admins and owners can view/change the settings tab, so this one
        # is pretty simple.
        user = self.user
        team = self.team

        for r in [ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_view_settings_tab(team, user))

        with self.role(ROLE_ADMIN, self.test_project):
            self.assertFalse(can_view_settings_tab(team, user))

        for r in [ROLE_MANAGER, ROLE_CONTRIBUTOR]:
            with self.role(r):
                self.assertFalse(can_view_settings_tab(team, user))

    def test_can_change_team_settings(self):
        # Only admins and owners can view/change the settings tab, so this one
        # is pretty simple.
        user = self.user
        team = self.team

        for r in [ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_change_team_settings(team, user))

        with self.role(ROLE_ADMIN, self.test_project):
            self.assertFalse(can_change_team_settings(team, user))

        for r in [ROLE_MANAGER, ROLE_CONTRIBUTOR]:
            with self.role(r):
                self.assertFalse(can_change_team_settings(team, user))

    def test_can_view_tasks_tab(self):
        # Any team member can view tasks.
        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_view_tasks_tab(self.team, self.user))

        # Outsiders can't.
        self.assertFalse(can_view_tasks_tab(self.team, self.outsider))

    def test_can_invite(self):
        team, user, outsider = self.team, self.user, self.outsider

        # If the policy is by-application, only admins+ can send invites.
        team.membership_policy = Team.APPLICATION
        team.save()

        for r in [ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_invite(team, user))

        for r in [ROLE_ADMIN]:
            with self.role(r, self.test_project):
                self.assertFalse(can_invite(team, user))

        for r in [ROLE_MANAGER, ROLE_CONTRIBUTOR]:
            with self.role(r):
                self.assertFalse(can_invite(team, user))

        self.assertFalse(can_invite(team, outsider))

        # Manager invites.
        team.membership_policy = Team.INVITATION_BY_MANAGER
        team.save()

        for r in [ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_invite(team, user))

        for r in [ROLE_MANAGER, ROLE_ADMIN]:
            with self.role(r, self.test_project):
                self.assertFalse(can_invite(team, user))

        for r in [ROLE_CONTRIBUTOR]:
            with self.role(r):
                self.assertFalse(can_invite(team, user))

        self.assertFalse(can_invite(team, outsider))

        # Admin invites.
        team.membership_policy = Team.INVITATION_BY_ADMIN
        team.save()

        for r in [ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_invite(team, user))

        for r in [ROLE_ADMIN]:
            with self.role(r, self.test_project):
                self.assertFalse(can_invite(team, user))

        for r in [ROLE_MANAGER, ROLE_CONTRIBUTOR]:
            with self.role(r):
                self.assertFalse(can_invite(team, user))

        self.assertFalse(can_invite(team, outsider))

        # Open and All are the same for the purpose of sending invites.
        for policy in [Team.OPEN, Team.INVITATION_BY_ALL]:
            team.membership_policy = policy
            team.save()

            for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
                with self.role(r):
                    self.assertTrue(can_invite(team, user))

            for r in [ROLE_MANAGER, ROLE_ADMIN]:
                with self.role(r, self.test_project):
                    self.assertTrue(can_invite(team, user))

            self.assertFalse(can_invite(team, outsider))

    def test_can_send_email_invite(self):
        for r in [ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_send_email_invite(self.team, self.user))

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER]:
            with self.role(r):
                self.assertFalse(can_send_email_invite(self.team, self.user))

    def test_can_change_video_settings(self):
        user, outsider = self.user, self.outsider

        for r in [ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_change_video_settings(user, self.project_video))
                self.assertTrue(can_change_video_settings(user, self.nonproject_video))

        for r in [ROLE_CONTRIBUTOR]:
            with self.role(r):
                self.assertFalse(can_change_video_settings(user, self.project_video))
                self.assertFalse(can_change_video_settings(user, self.nonproject_video))

        for r in [ROLE_MANAGER, ROLE_ADMIN]:
            with self.role(r, self.test_project):
                self.assertTrue(can_change_video_settings(user, self.project_video))
                self.assertFalse(can_change_video_settings(user, self.nonproject_video))

        self.assertFalse(can_change_video_settings(outsider, self.project_video))
        self.assertFalse(can_change_video_settings(outsider, self.nonproject_video))

    def test_can_review(self):
        user, outsider = self.user, self.outsider
        workflow = Workflow.get_for_team_video(self.nonproject_video)

        self.team.workflow_enabled = True
        self.team.save()

        # TODO: Test with Project/video-specific workflows.

        # Review disabled.
        workflow.review_allowed = Workflow.REVIEW_IDS["Don't require review"]
        workflow.save()
        self.clear_cached_workflows()

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertFalse(can_review(self.nonproject_video, user))

        self.assertFalse(can_review(self.nonproject_video, outsider))

        # Peer reviewing.
        workflow.review_allowed = Workflow.REVIEW_IDS["Peer must review"]
        workflow.save()
        self.clear_cached_workflows()

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_review(self.nonproject_video, user))

        self.assertFalse(can_review(self.nonproject_video, outsider))

        # Manager review.
        workflow.review_allowed = Workflow.REVIEW_IDS["Manager must review"]
        workflow.save()
        self.clear_cached_workflows()

        for r in [ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_review(self.nonproject_video, user))

        for r in [ROLE_CONTRIBUTOR]:
            with self.role(r):
                self.assertFalse(can_review(self.nonproject_video, user))

        for r in [ROLE_MANAGER, ROLE_ADMIN]:
            with self.role(r, self.test_project):
                self.assertFalse(can_review(self.nonproject_video, user))
                self.assertTrue(can_review(self.project_video, user))

        self.assertFalse(can_review(self.nonproject_video, outsider))

        # Admin review.
        workflow.review_allowed = Workflow.REVIEW_IDS["Admin must review"]
        workflow.save()
        self.clear_cached_workflows()

        for r in [ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_review(self.nonproject_video, user))

        for r in [ROLE_MANAGER, ROLE_CONTRIBUTOR]:
            with self.role(r):
                self.assertFalse(can_review(self.nonproject_video, user))

        for r in [ROLE_ADMIN]:
            with self.role(r, self.test_project):
                self.assertFalse(can_review(self.nonproject_video, user))
                self.assertTrue(can_review(self.project_video, user))

        self.assertFalse(can_review(self.nonproject_video, outsider))

        # Workflows disabled entirely.
        self.team.workflow_enabled = False
        self.team.save()
        self.clear_cached_workflows()

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertFalse(can_review(self.nonproject_video, user))

        self.assertFalse(can_review(self.nonproject_video, outsider))

    def test_can_approve(self):
        user, outsider = self.user, self.outsider

        self.team.workflow_enabled = True
        self.team.save()

        workflow = Workflow.get_for_team_video(self.nonproject_video)

        # TODO: Test with Project/video-specific workflows.

        # Approval disabled.
        workflow.approve_allowed = Workflow.APPROVE_IDS["Don't require approval"]
        workflow.save()
        self.clear_cached_workflows()

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertFalse(can_approve(self.nonproject_video, user))

        self.assertFalse(can_approve(self.nonproject_video, outsider))

        # Manager approval.
        workflow.approve_allowed = Workflow.APPROVE_IDS["Manager must approve"]
        workflow.save()
        self.clear_cached_workflows()

        for r in [ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_approve(self.nonproject_video, user))

        for r in [ROLE_CONTRIBUTOR]:
            with self.role(r):
                self.assertFalse(can_approve(self.nonproject_video, user))

        for r in [ROLE_MANAGER, ROLE_ADMIN]:
            with self.role(r, self.test_project):
                self.assertFalse(can_approve(self.nonproject_video, user))
                self.assertTrue(can_approve(self.project_video, user))

        self.assertFalse(can_approve(self.nonproject_video, outsider))

        # Admin approval.
        workflow.approve_allowed = Workflow.APPROVE_IDS["Admin must approve"]
        workflow.save()
        self.clear_cached_workflows()

        for r in [ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_approve(self.nonproject_video, user))

        for r in [ROLE_MANAGER, ROLE_CONTRIBUTOR]:
            with self.role(r):
                self.assertFalse(can_approve(self.nonproject_video, user))

        for r in [ROLE_ADMIN]:
            with self.role(r, self.test_project):
                self.assertFalse(can_approve(self.nonproject_video, user))
                self.assertTrue(can_approve(self.project_video, user))

        self.assertFalse(can_approve(self.nonproject_video, outsider))

        # Workflows disabled entirely.
        self.team.workflow_enabled = False
        self.team.save()
        self.clear_cached_workflows()

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertFalse(can_approve(self.nonproject_video, user))

        self.assertFalse(can_approve(self.nonproject_video, outsider))


    def test_can_message_all_members(self):
        team, user, outsider = self.team, self.user, self.outsider

        for r in [ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_message_all_members(team, user))

        for r in [ROLE_ADMIN]:
            with self.role(r, self.test_project):
                self.assertFalse(can_message_all_members(team, user))

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER]:
            with self.role(r):
                self.assertFalse(can_message_all_members(team, user))

        self.assertFalse(can_message_all_members(team, outsider))

    def test_can_edit_project(self):
        team, user, outsider = self.team, self.user, self.outsider
        default_project, test_project = self.default_project, self.test_project

        # The default project cannot be edited at all.
        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertFalse(can_edit_project(team, user, default_project))

        self.assertFalse(can_edit_project(team, outsider, default_project))

        # Projects can only be edited by admins+.
        for r in [ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_edit_project(team, user, test_project))

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER]:
            with self.role(r):
                self.assertFalse(can_edit_project(team, user, test_project))

        self.assertFalse(can_edit_project(team, outsider, test_project))

        # TODO: Test with a second project.

    def test_can_create_and_edit_subtitles(self):
        team, user, outsider = self.team, self.user, self.outsider

        # Anyone
        team.subtitle_policy = Team.SUBTITLE_IDS['Anyone']
        team.save()

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_create_and_edit_subtitles(user, self.nonproject_video))

        self.assertTrue(can_create_and_edit_subtitles(outsider, self.nonproject_video))

        # Contributors only.
        team.subtitle_policy = Team.SUBTITLE_IDS['Any team member']
        team.save()

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_create_and_edit_subtitles(user, self.nonproject_video))

        self.assertFalse(can_create_and_edit_subtitles(outsider, self.nonproject_video))

        # Managers only.
        team.subtitle_policy = Team.SUBTITLE_IDS['Only managers and admins']
        team.save()

        for r in [ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_create_and_edit_subtitles(user, self.nonproject_video))

        for r in [ROLE_MANAGER, ROLE_ADMIN]:
            with self.role(r, self.test_project):
                self.assertFalse(can_create_and_edit_subtitles(user, self.nonproject_video))
                self.assertTrue(can_create_and_edit_subtitles(user, self.project_video))

        for r in [ROLE_CONTRIBUTOR]:
            with self.role(r):
                self.assertFalse(can_create_and_edit_subtitles(user, self.nonproject_video))

        self.assertFalse(can_create_and_edit_subtitles(outsider, self.nonproject_video))

        # Admins only.
        team.subtitle_policy = Team.SUBTITLE_IDS['Only admins']
        team.save()

        for r in [ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_create_and_edit_subtitles(user, self.nonproject_video))

        for r in [ROLE_ADMIN]:
            with self.role(r, self.test_project):
                self.assertFalse(can_create_and_edit_subtitles(user, self.nonproject_video))
                self.assertTrue(can_create_and_edit_subtitles(user, self.project_video))

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER]:
            with self.role(r):
                self.assertFalse(can_create_and_edit_subtitles(user, self.nonproject_video))

        self.assertFalse(can_create_and_edit_subtitles(outsider, self.nonproject_video))

    def test_can_manage_subtitles_as_project_manager(self):
        member = TeamMemberFactory(team=self.team,
                                user=self.user,
                                role=TeamMember.ROLE_CONTRIBUTOR)
        member.make_project_manager(self.test_project)

        self.assertTrue(can_manage_subtitles(self.user, self.project_video))
        self.assertFalse(can_manage_subtitles(self.user, self.nonproject_video))

    def test_can_manage_subtitles_as_language_manager(self):
        member = TeamMemberFactory(team=self.team,
                                user=self.user,
                                role=TeamMember.ROLE_CONTRIBUTOR)
        member.make_language_manager('en')

        self.assertTrue(can_manage_subtitles(self.user, self.project_video, 'en'))
        self.assertFalse(can_manage_subtitles(self.user, self.nonproject_video, 'es'))   

    # TODO: Ensure later steps block earlier steps.
    def test_can_create_task_subtitle(self):
        team, user, outsider = self.team, self.user, self.outsider

        # When no subtitles exist yet, it depends on the team's task creation
        # policy.
        self.assertTrue(can_create_task_subtitle(self.nonproject_video))

        # Any team member.
        team.task_assign_policy = Team.TASK_ASSIGN_IDS['Any team member']
        team.save()

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_create_task_subtitle(self.nonproject_video, user))

        self.assertFalse(can_create_task_subtitle(self.nonproject_video, outsider))

        # Manager+
        team.task_assign_policy = Team.TASK_ASSIGN_IDS['Managers and admins']
        team.save()

        for r in [ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_create_task_subtitle(self.nonproject_video, user))

        for r in [ROLE_CONTRIBUTOR]:
            with self.role(r):
                self.assertFalse(can_create_task_subtitle(self.nonproject_video, user))

        for r in [ROLE_MANAGER, ROLE_ADMIN]:
            with self.role(r, self.test_project):
                self.assertFalse(can_create_task_subtitle(self.nonproject_video, user))

        self.assertFalse(can_create_task_subtitle(self.nonproject_video, outsider))

        # Admin+
        team.task_assign_policy = Team.TASK_ASSIGN_IDS['Admins only']
        team.save()

        for r in [ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_create_task_subtitle(self.nonproject_video, user))

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER]:
            with self.role(r):
                self.assertFalse(can_create_task_subtitle(self.nonproject_video, user))

        for r in [ROLE_ADMIN]:
            with self.role(r, self.test_project):
                self.assertFalse(can_create_task_subtitle(self.nonproject_video, user))

        self.assertFalse(can_create_task_subtitle(self.nonproject_video, outsider))

        # Once a subtitle task exists, no one can create another.
        team.task_assign_policy = Team.TASK_ASSIGN_IDS['Any team member']
        team.save()

        t = Task(type=Task.TYPE_IDS['Subtitle'], team=team, team_video=self.nonproject_video)
        t.save()

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertFalse(can_create_task_subtitle(self.nonproject_video, user))

        # Even if it's completed.
        t.completed = datetime.datetime.now()
        t.save()

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertFalse(can_create_task_subtitle(self.nonproject_video, user))

        # Unless it's deleted, of course.
        t.deleted = True
        t.save()

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertTrue(can_create_task_subtitle(self.nonproject_video, user))

        # Once subtitles exist, no one can create a new task.
        helpers._add_language_via_pipeline(self.nonproject_video.video, 'en')

        self.assertFalse(can_create_task_subtitle(self.nonproject_video))

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                self.assertFalse(can_create_task_subtitle(self.nonproject_video, user))

        self.assertFalse(can_create_task_subtitle(self.nonproject_video, outsider))

    def test_can_create_task_translate(self):
        team, user, outsider = self.team, self.user, self.outsider

        # When no subtitles exist yet, no translations can be created.
        self.assertEqual(can_create_task_translate(self.nonproject_video), [])

        # Add some sample subtitles.  Now we can create translation tasks
        # (but not to that language, since it's already done).
        _set_subtitles(self.nonproject_video, 'en', True, True)

        langs = can_create_task_translate(self.nonproject_video)

        self.assertEqual(len(langs), TOTAL_LANGS - 1)
        self.assertTrue('en' not in langs)

        # Languages with translations finished can't have new translation tasks.
        _set_subtitles(self.nonproject_video, 'en', True, True, ['fr', 'de'])

        langs = can_create_task_translate(self.nonproject_video)

        self.assertEqual(len(langs), TOTAL_LANGS - 3)
        self.assertTrue('en' not in langs)
        self.assertTrue('fr' not in langs)

        # Test role restrictions.
        _set_subtitles(self.nonproject_video, 'en', True, True, ['fr'])

        # Any team member.
        team.task_assign_policy = Team.TASK_ASSIGN_IDS['Any team member']
        team.save()


        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                langs = can_create_task_translate(self.nonproject_video, user)

                self.assertEqual(len(langs), TOTAL_LANGS - 2)
                self.assertTrue('en' not in langs)
                self.assertTrue('fr' not in langs)

        langs = can_create_task_translate(self.nonproject_video, outsider)
        self.assertEqual(langs, [])

        # Managers+
        team.task_assign_policy = Team.TASK_ASSIGN_IDS['Managers and admins']
        team.save()

        for r in [ROLE_MANAGER, ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                langs = can_create_task_translate(self.nonproject_video, user)

                self.assertEqual(len(langs), TOTAL_LANGS - 2)
                self.assertTrue('en' not in langs)
                self.assertTrue('fr' not in langs)

        for r in [ROLE_CONTRIBUTOR]:
            with self.role(r):
                langs = can_create_task_translate(self.nonproject_video, user)
                self.assertEqual(langs, [])

        for r in [ROLE_MANAGER, ROLE_ADMIN]:
            with self.role(r, self.test_project):
                langs = can_create_task_translate(self.nonproject_video, user)
                self.assertEqual(langs, [])

        langs = can_create_task_translate(self.nonproject_video, outsider)
        self.assertEqual(langs, [])

        # Admins+
        team.task_assign_policy = Team.TASK_ASSIGN_IDS['Admins only']
        team.save()

        for r in [ROLE_ADMIN, ROLE_OWNER]:
            with self.role(r):
                langs = can_create_task_translate(self.nonproject_video, user)

                self.assertEqual(len(langs), TOTAL_LANGS - 2)
                self.assertTrue('en' not in langs)
                self.assertTrue('fr' not in langs)

        for r in [ROLE_CONTRIBUTOR, ROLE_MANAGER]:
            with self.role(r):
                langs = can_create_task_translate(self.nonproject_video, user)
                self.assertEqual(langs, [])

        for r in [ROLE_ADMIN]:
            with self.role(r, self.test_project):
                langs = can_create_task_translate(self.nonproject_video, user)
                self.assertEqual(langs, [])

        langs = can_create_task_translate(self.nonproject_video, outsider)
        self.assertEqual(langs, [])

class RolePermissionsTest(BaseTestPermission):
    """ Test a permission using role-based checking

    Subclasses of RolePermissionsTest should test exactly 1 permission.  They
    should define check_perm(), which checks if a given user has the permission
    for a video.  They may optionally define check_perm_for_language, which
    also includes a language.

    Subclasses can call check_role_required(), which will test that
    check_perm() and check_perm_for_language() return True for that role and
    higher.  It will test it the following:
        - check_perm() using simple roles logic with a non-project video
        - check_perm() with a project manager with a project video
        - check_perm_for_language() with a language manager
    """

    def check_perm(self, user, video):
        raise NotImplementedError()

    def check_perm_for_language(self, user, video, language):
        raise NotImplementedError()

    staff_members_always_have_permission = True

    def check_perm_for_language_overrided(self):
        return (self.check_perm_for_language.im_func !=
                RolePermissionsTest.check_perm_for_language.im_func)

    def check_permission_for_outsider(self, has_perm):
        if has_perm:
            self.assertTrue(self.check_perm(self.outsider,
                                            self.nonproject_video))
        else:
            self.assertFalse(self.check_perm(self.outsider,
                                             self.nonproject_video))

    def check_permission_without_project_narrowing(self, role, has_perm):
        with self.role(role):
            if has_perm:
                self.assertTrue(self.check_perm(self.user,
                                                self.nonproject_video))
            else:
                self.assertFalse(self.check_perm(self.user,
                                                 self.nonproject_video))

    def check_permission_with_project_narrowing(self, role, has_perm):
        with self.role(role, project=self.test_project):
            if has_perm:
                self.assertTrue(self.check_perm(self.user,
                                                self.project_video))
            else:
                self.assertFalse(self.check_perm(self.user,
                                                 self.project_video))

        # for non-project videos, we should treat the user as a contributor,
        # regardless of their role for the project
        if role == ROLE_CONTRIBUTOR:
            with self.role(ROLE_ADMIN, project=self.test_project):
                if has_perm:
                    self.assertTrue(self.check_perm(self.user,
                                                    self.nonproject_video))
                else:
                    self.assertFalse(self.check_perm(self.user,
                                                     self.nonproject_video))

    def check_permission_with_language_narrowing(self, role, has_perm):
        with self.role(role, lang='en'):
            if has_perm:
                self.assertTrue(self.check_perm_for_language(
                    self.user, self.nonproject_video, 'en'))
            else:
                self.assertFalse(self.check_perm_for_language(
                    self.user, self.nonproject_video, 'en'))

        # for other languages, we should treat the user as a contributor,
        # regardless of their role for the language
        if role == ROLE_CONTRIBUTOR:
            with self.role(ROLE_ADMIN, lang='en'):
                if has_perm:
                    self.assertTrue(self.check_perm_for_language(
                        self.user, self.nonproject_video, 'fr'))
                else:
                    self.assertFalse(self.check_perm_for_language(
                        self.user, self.nonproject_video, 'fr'))

    def check_permission_for_role(self, role, has_perm):
        if role == ROLE_OUTSIDER:
            self.check_permission_for_outsider(has_perm)
            return

        self.check_permission_without_project_narrowing(role, has_perm)
        self.check_permission_with_project_narrowing(role, has_perm)

        if self.check_perm_for_language_overrided():
            self.check_permission_with_language_narrowing(role, has_perm)

    def check_role_required(self, role):
        self.clear_cached_workflows()
        self.check_permission_for_role(ROLE_OWNER, True)
        self.check_permission_for_role(ROLE_ADMIN,
                                       role in (ROLE_ADMIN,
                                                ROLE_MANAGER,
                                                ROLE_CONTRIBUTOR,
                                                ROLE_OUTSIDER))
        self.check_permission_for_role(ROLE_MANAGER,
                                       role in (ROLE_MANAGER,
                                                ROLE_CONTRIBUTOR,
                                                ROLE_OUTSIDER))
        self.check_permission_for_role(ROLE_CONTRIBUTOR,
                                       role in (ROLE_CONTRIBUTOR,
                                                ROLE_OUTSIDER))
        self.check_permission_for_role(ROLE_OUTSIDER,
                                       role==ROLE_OUTSIDER)
        self.check_staff_permission()

    def check_staff_permission(self):
        if self.staff_members_always_have_permission:
            self.assertTrue(self.check_perm(self.site_admin,
                                            self.nonproject_video))
        else:
            self.assertFalse(self.check_perm(self.site_admin,
                                             self.nonproject_video))


class CanPostEditSubtitlesTest(RolePermissionsTest):
    def check_perm(self, user, video):
        return can_post_edit_subtitles(video, user)

    def check_perm_for_language(self, user, video, language):
        return can_post_edit_subtitles(video, user, language)

    def test_can_post_edit_subtitles(self):
        self.update_team(workflow_enabled=True)
        # If approval is enabled, then users who can approve can post edit
        self.update_workflow(
            review_allowed=Workflow.REVIEW_IDS["Manager must review"],
            approve_allowed=Workflow.APPROVE_IDS["Admin must approve"],
        )
        self.check_role_required(ROLE_ADMIN)
        self.update_workflow(
            approve_allowed=Workflow.APPROVE_IDS["Manager must approve"],
        )
        self.check_role_required(ROLE_MANAGER)
        # If approval is disabled, then users who can review can post edit
        self.update_workflow(
            review_allowed=Workflow.REVIEW_IDS["Admin must review"],
            approve_allowed=Workflow.APPROVE_IDS["Don't require approval"]
        )
        self.check_role_required(ROLE_ADMIN)
        self.update_workflow(
            review_allowed=Workflow.REVIEW_IDS["Manager must review"],
        )
        self.check_role_required(ROLE_MANAGER)
        self.update_workflow(
            review_allowed=Workflow.REVIEW_IDS["Peer must review"]
        )
        self.check_role_required(ROLE_CONTRIBUTOR)
        # If neither is enabled, then team members can post edit
        self.update_workflow(
            review_allowed=Workflow.REVIEW_IDS["Don't require review"]
        )
        self.check_role_required(ROLE_CONTRIBUTOR)
        # if workflows are disabled, but we fall back to the subtitle policy
        self.update_team(workflow_enabled=False,
                         subtitle_policy=Team.SUBTITLE_IDS['Only admins'])
        self.check_role_required(ROLE_ADMIN)
        self.update_team(
            subtitle_policy=Team.SUBTITLE_IDS['Only managers and admins'])
        self.check_role_required(ROLE_MANAGER)
        self.update_team(
            subtitle_policy=Team.SUBTITLE_IDS['Any team member'])
        self.check_role_required(ROLE_CONTRIBUTOR)
        self.update_team(
            subtitle_policy=Team.SUBTITLE_IDS['Anyone'])
        self.check_role_required(ROLE_OUTSIDER)

    # TODO: Review/approve task tests.

class TestViews(BaseTestPermission):
    def test_save_role(self):
        owner = self.owner

        member_account = UserFactory(username='member', password='hey')
        member = TeamMemberFactory(team=self.team, user=member_account,
                                   role=TeamMember.ROLE_CONTRIBUTOR)

        tv = self.project_video
        video_url = reverse("videos:video", args=(tv.video.video_id,))
        owner.user.set_password("hey")
        owner.user.save()

        resp = self.client.get(video_url, follow=True)
        self.assertNotEqual(resp.status_code, 200)

        self.team.video_policy = Team.VP_MEMBER
        self.task_assign_policy = 10
        self.team.save()
        self.assertTrue(can_add_video(self.team, member.user))

        self.assertTrue(can_add_video_somewhere(self.team, member.user))
        self.assertTrue(can_view_tasks_tab(self.team, member.user))
        self.assertTrue(can_create_and_edit_subtitles(member.user, tv))
        self.assertTrue(can_create_and_edit_translations(member.user, tv))
        self.assertFalse(can_view_settings_tab(self.team, member.user))

        self.save_role(member, owner, ROLE_ADMIN)
        self.assertTrue(can_add_video_somewhere(self.team, member.user))
        self.assertTrue(can_view_tasks_tab(self.team, member.user))
        self.assertTrue(can_create_and_edit_subtitles(member.user, tv))
        self.assertTrue(can_create_and_edit_translations(member.user, tv))
        self.assertTrue(can_view_settings_tab(self.team, member.user))

        self.save_role(member, owner, ROLE_CONTRIBUTOR)
        self.assertFalse(can_view_settings_tab(self.team, member.user))
        self.assertTrue(can_add_video_somewhere(self.team, member.user))
        self.assertTrue(can_view_tasks_tab(self.team, member.user))
        self.assertTrue(can_create_and_edit_subtitles(member.user, tv))
        self.assertTrue(can_create_and_edit_translations(member.user, tv))

        self.client.login(username=member.user.username, password="hey")
        resp = self.client.get(video_url, follow=True)
        self.assertEqual(resp.status_code, 200)

    def save_role(self, member, owner, role):
        save_role(self.team, member, role, [], [], owner.user)
        self.team.uncache_member(member.user)
        self.assertEquals(self.team.get_member(member.user).role, role)
