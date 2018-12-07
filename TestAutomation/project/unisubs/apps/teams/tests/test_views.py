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

from os import path

from django.conf import settings
from django.urls import reverse
from django.test import TestCase, TransactionTestCase

from teams.models import Team, TeamMember, TeamVideo, Project, EmailInvite
from videos.models import Video, VideoUrl
from auth.models import CustomUser as User
from utils.factories import *
from utils.panslugify import pan_slugify
from utils.test_utils import *

import datetime

class ViewsTests(TestCase):
    def setUp(self):
        self.auth = {
            "username": u"admin",
            "password": u"admin"}
        self.user = UserFactory(is_staff=True, is_superuser=True, **self.auth)

    def _create_base_team(self):
       self.team = Team(
           slug="new-team",
            membership_policy=4,
            video_policy =1,
           name="New-name")
       self.team.save()
       user, created = User.objects.get_or_create(
           username=self.auth["username"])
       TeamMember.objects.create_first_member(self.team, user)
       return self.team


    def test_team_create(self):
        self.client.login(**self.auth)

        #------- create ----------
        response = self.client.get(reverse("teams:create"))
        self.failUnlessEqual(response.status_code, 200)

        data = {
            "description": u"",
            "video_url": u"",
            "membership_policy": u"4",
            "video_policy": u"1",
            "workflow_type": u"O",
            "logo": u"",
            "slug": u"new-team",
            "name": u"New team"
        }
        response = self.client.post(reverse("teams:create"), data)
        self.failUnlessEqual(response.status_code, 302)
        self.assertEqual(Team.objects.get(slug=data['slug']).slug, data["slug"])

    def test_team_edit(self):
        team = self._create_base_team()
        self.client.login(**self.auth)
        url = reverse("teams:settings_basic", kwargs={"slug": team.slug})

        member = TeamMemberFactory(team=team, role=TeamMember.ROLE_ADMIN)
        videos = [VideoFactory() for i in xrange(4)]

        response = self.client.get(url)
        self.failUnlessEqual(response.status_code, 200)

        for video in videos:
            TeamVideoFactory(team=team, video=video, added_by=member.user)

        self.assertTrue(all([v.is_public for v in videos]))

        self.assertFalse(team.logo)

        data = {
            "name": u"New team",
            "description": u"testing",
            "logo": open(path.join(settings.STATIC_ROOT, "test/71600102.jpg"), "rb")
        }

        url = reverse("teams:settings_basic", kwargs={"slug": team.slug})
        response = self.client.post(url, data)
        self.failUnlessEqual(response.status_code, 302)

        team = Team.objects.get(pk=team.pk)
        self.assertTrue(team.logo)
        self.assertEqual(team.name, u"New team")
        self.assertEqual(team.description, u"testing")
        self.assertTrue(team.team_private())
        self.assertTrue(team.videos_private())
        self.assertTrue(all([v.is_public for v in videos]))

        data = {
            "name": u"New team",
            "is_visible": u"1",
            "description": u"testing",
        }

        url = reverse("teams:settings_basic", kwargs={"slug": team.slug})
        response = self.client.post(url, data)
        team = reload_obj(team)

        self.failUnlessEqual(response.status_code, 302)
        self.assertTrue(team.team_public())
        self.assertTrue(team.videos_public())
        self.assertTrue(all([v.is_public for v in videos]))

    def test_create_project(self):
        team = self._create_base_team()
        self.client.login(**self.auth)

        url = reverse("teams:add_project", kwargs={"slug": team.slug})

        data = {
            "name": u"Test Project",
            "description": u"Test Project",
            "review_allowed": u"0",
            "approve_allowed": u"0",
        }

        response = self.client.post(url, data)
        self.failUnlessEqual(response.status_code, 302)

        slug = pan_slugify(data['name'])

        project = Project.objects.get(slug=slug)
        self.assertEqual(project.name, data['name'])
        self.assertEqual(project.description, data['description'])

        # creating a duplicated project results in error
        response = self.client.post(url, data)
        self.failUnlessEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].is_valid())

    def test_remove_video(self):
        team = TeamFactory(slug="new-team",
                           membership_policy=4,
                           video_policy=1,
                           name="New-name")

        def create_member(role):
            return TeamMemberFactory(role=role, team=team)

        admin = create_member(TeamMember.ROLE_ADMIN)
        contributor = create_member(TeamMember.ROLE_CONTRIBUTOR)
        manager = create_member(TeamMember.ROLE_MANAGER)
        owner = create_member(TeamMember.ROLE_OWNER)

        def create_team_video():
            return TeamVideoFactory(team=team, added_by=owner.user)

        # The video policy determines who can remove videos from teams.
        for member in [contributor, manager, admin, owner]:
            self.client.login(username=member.user.username,
                              password='password')
            tv = create_team_video()
            video_url = tv.video.get_video_url()

            url = reverse("teams:remove_video", kwargs={"team_video_pk": tv.pk})
            response = self.client.post(url)

            self.assertEqual(response.status_code, 302)
            self.assertFalse(TeamVideo.objects.filter(pk=tv.pk).exists())
            self.assertTrue(VideoUrl.objects.get(url=video_url).video)

        # Owners and admins can delete videos entirely.
        for role in [owner, admin]:
            self.client.login(username=role.user.username,
                              password='password')
            tv = create_team_video()
            video_url = tv.video.get_video_url()

            url = reverse("teams:remove_video", kwargs={"team_video_pk": tv.pk})
            response = self.client.post(url, {'del-opt': 'total-destruction'})

            self.assertEqual(response.status_code, 302)
            self.assertFalse(TeamVideo.objects.filter(pk=tv.pk).exists())
            self.assertFalse(VideoUrl.objects.filter(url=video_url).exists())

        for role in [contributor, manager]:
            self.client.login(username=role.user.username,
                              password='password')
            tv = create_team_video()
            video_url = tv.video.get_video_url()

            url = reverse("teams:remove_video", kwargs={"team_video_pk": tv.pk})
            response = self.client.post(url, {'del-opt': 'total-destruction'})

            self.assertEqual(response.status_code, 302)
            self.assertTrue(TeamVideo.objects.filter(pk=tv.pk).exists())
            self.assertTrue(VideoUrl.objects.filter(url=video_url).exists())

        # POST request required
        tv = create_team_video()
        video_url = tv.video.get_video_url()
        url = reverse("teams:remove_video", kwargs={"team_video_pk": tv.pk})
        self.client.login(username=self.user.username, password='password')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(TeamVideo.objects.filter(pk=tv.pk).exists())
        self.assertTrue(VideoUrl.objects.filter(url=video_url).exists())


    def test_move_video_allowed(self):
        # Check that moving works when the user has permission.
        video = VideoFactory()
        old_team = TeamFactory(video_policy=Team.VP_MANAGER)
        new_team = TeamFactory(video_policy=Team.VP_MANAGER)
        team_video = TeamVideoFactory(team=old_team, video=video,
                                      added_by=self.user)
        # Convenient functions for pulling models fresh from the DB.
        get_video = lambda: Video.objects.get(pk=video.pk)
        get_team_video = lambda: get_video().get_team_video()

        # Create a member that's an admin of BOTH teams.
        # This member should be able to move the video.
        member = TeamMemberFactory(team=old_team, role=TeamMember.ROLE_ADMIN)
        TeamMemberFactory(team=new_team, role=TeamMember.ROLE_ADMIN,
                          user=member.user)

        self.assertEqual(get_team_video().team.pk, old_team.pk,
                         "Video did not start in the correct team.")

        # Move the video.
        self.client.login(username=member.user.username, password='password')
        url = reverse("teams:move_video")
        response = self.client.post(url, {'team_video': get_team_video().pk,
                                          'team': new_team.pk,})
        self.assertEqual(response.status_code, 302)

        self.assertEqual(get_team_video().team.pk, new_team.pk,
                         "Video was not moved to the new team.")

        self.assertEqual(get_team_video().project.team, new_team,
                         "Video ended up with a project for the first team")

    def test_move_video_disallowed_old(self):
        # Check that moving does not work when the user is blocked by the old
        # team.
        video = VideoFactory()
        old_team = TeamFactory(video_policy=Team.VP_MANAGER)
        new_team = TeamFactory(video_policy=Team.VP_MANAGER)
        team_video = TeamVideoFactory(team=old_team, video=video,
                                      added_by=self.user)
        # Convenient functions for pulling models fresh from the DB.
        get_video = lambda: Video.objects.get(pk=video.pk)
        get_team_video = lambda: get_video().get_team_video()

        # Create a member that's a contributor to the old/current team.
        # This member should NOT be able to move the video because they cannot
        # remove it from the first team.
        member = TeamMemberFactory(team=old_team,
                                   role=TeamMember.ROLE_CONTRIBUTOR)
        TeamMemberFactory(team=new_team, role=TeamMember.ROLE_ADMIN,
                          user=member.user)

        self.assertEqual(get_team_video().team.pk, old_team.pk,
                         "Video did not start in the correct team.")

        # Try to move the video.
        self.client.login(username=member.user.username, password='password')
        url = reverse("teams:move_video")
        response = self.client.post(url, {'team_video': get_team_video().pk,
                                          'team': new_team.pk,})
        self.assertEqual(response.status_code, 302)

        self.assertEqual(get_team_video().team.pk, old_team.pk,
                         "Video did not stay in the old team.")

    def test_move_video_disallowed_new(self):
        # Check that moving does not work when the user is blocked by the new
        # team.
        video = VideoFactory()
        old_team = TeamFactory(video_policy=Team.VP_MANAGER)
        new_team = TeamFactory(video_policy=Team.VP_MANAGER)
        team_video = TeamVideoFactory(team=old_team, video=video,
                                      added_by=self.user)
        # Convenient functions for pulling models fresh from the DB.
        get_video = lambda: Video.objects.get(pk=video.pk)
        get_team_video = lambda: get_video().get_team_video()

        # Create a member that's a contributor to the new/target team.
        # This member should NOT be able to move the video because they cannot
        # add it to the second team.
        member = TeamMemberFactory(team=old_team, role=TeamMember.ROLE_ADMIN)
        TeamMemberFactory(team=new_team, role=TeamMember.ROLE_CONTRIBUTOR,
                          user=member.user)

        self.assertEqual(get_team_video().team.pk, old_team.pk,
                         "Video did not start in the correct team.")

        # Try to move the video.
        self.client.login(username=member.user.username, password='password')
        url = reverse("teams:move_video")
        response = self.client.post(url, {'team_video': get_team_video().pk,
                                          'team': new_team.pk,})
        self.assertEqual(response.status_code, 302)

        self.assertEqual(get_team_video().team.pk, old_team.pk,
                         "Video did not stay in the old team.")

    def test_team_permission(self):
        team = TeamFactory(slug="private-team", name="Private Team")
        TeamMember.objects.create_first_member(team, self.user)
        video = VideoFactory()
        TeamVideoFactory(team=team, video=video, added_by=self.user)

        url = reverse("videos:video", kwargs={"video_id": video.video_id})

        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 403)

        self.client.login(**self.auth)

        response = self.client.get(url, follow=True)
        self.assertEquals(response.status_code, 200)

        self.client.logout()

    def _create_member(self, team, role, user=None):
        if not user:
            user = User.objects.create(username='test' + role)
            user.set_password('test' + role)
            user.save()
        return TeamMember.objects.create(user=user, role=role, team=team)

class EmailInviteViewTest(TransactionTestCase):
    def setUp(self):
        self.author = UserFactory()
        self.user = UserFactory()
        self.team = TeamFactory()
        self.email_invite = EmailInvite.create_invite(email=self.user.email,
            team=self.team, author=self.author)

    def test_invite_valid(self):
        response = self.client.get(self.email_invite.get_url())
        self.assertTemplateUsed(response, 'new-teams/email_invite_accept.html')

    def test_invite_expired(self):
        self.email_invite.created = self.email_invite.created - datetime.timedelta(days=3, minutes=1)
        self.email_invite.save()
        response = self.client.get(self.email_invite.get_url())
        self.assertRedirects(
            response,
            reverse('teams:email_invite_invalid'),
            fetch_redirect_response=False)

    def test_invite_has_been_used(self):
        self.email_invite.link_to_account(self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.email_invite.get_url())
        self.assertRedirects(
            response,
            reverse('teams:email_invite_invalid'),
            fetch_redirect_response=False)
