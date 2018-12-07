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
import logging
import mock

from videos.signals import video_deleted
from teams import forms
from teams.models import EmailInvite, TeamMember
from utils.factories import *
from utils.test_utils import *

logger = logging.getLogger(__name__)

class TeamVideoManagementFormBase(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.team = self.make_team()
        self.project = ProjectFactory(team=self.team)
        self.team_videos = [
            TeamVideoFactory(team=self.team)
            for i in range(10)
        ]
        self.videos = [tv.video for tv in self.team_videos]

    def make_team(self):
        return TeamFactory(owner=self.user)

    def build_form(self, form_class, selected_videos, all_selected=False,
                   data=None, files=None, skip_submit=False):
        form = form_class(self.team, self.user, self.team.videos.all(),
                          [v.id for v in selected_videos], all_selected,
                          data=data, files=files)
        if data is not None:
            if form.errors:
                logger.warn(form.errors.as_text())
            if not skip_submit:
                form.submit()
        return form

class TestEditVideosForm(TeamVideoManagementFormBase):
    def test_set_project(self):
        videos = self.videos[:2]
        form = self.build_form(forms.EditVideosForm, videos, data={
            'project': self.project.id,
        })
        for v in videos:
            assert_equal(reload_obj(v).get_team_video().project, self.project)

    def test_unset_project(self):
        self.team.teamvideo_set.update(project=self.project)
        videos = self.videos[:2]
        form = self.build_form(forms.EditVideosForm, videos, data={
            'project': self.team.default_project.id,
        })
        for v in videos:
            assert_equal(reload_obj(v).get_team_video().project,
                         self.team.default_project)

    @patch_for_test('utils.amazon.fields.S3ImageFieldFile.save', autospec=True)
    def test_change_thumbnail(self, mock_save):
        mock_file = UploadedFileFactory()
        videos = self.videos[:2]
        form = self.build_form(forms.EditVideosForm, videos, data={},
                               files={
            'thumbnail': mock_file,
        })
        assert_items_equal(mock_save.call_args_list, [
            mock.call(v.thumbnail, mock_file.name, mock_file)
            for v in videos
        ])

    def test_set_language(self):
        videos = self.videos[:2]
        form = self.build_form(forms.EditVideosForm, videos, data={
            'language': 'en',
        })
        for v in videos:
            assert_equal(reload_obj(v).primary_audio_language_code, 'en')

    def test_no_changes(self):
        self.team.videos.update(primary_audio_language_code='en')
        videos = self.videos[:2]
        form = self.build_form(forms.EditVideosForm, videos, data={
            'language': '',
        })
        for v in videos:
            assert_equal(reload_obj(v).primary_audio_language_code, 'en')

    def test_single_selection_mode(self):
        video = self.videos[0]
        video.primary_audio_language_code = 'en'
        video.save()
        self.team_videos[0].project = self.project
        self.team_videos[0].save()
        video = reload_obj(video)

        form = self.build_form(forms.EditVideosForm, [video])
        assert_true(form.single_selection())
        assert_true(form.fields['language'].initial, 'en')
        assert_true(form.fields['project'].initial, self.project.slug)

class TestDeleteVideosForm(TeamVideoManagementFormBase):
    def test_remove(self):
        videos = self.videos[:2]
        form = self.build_form(forms.DeleteVideosForm, videos, data={})
        for v in videos:
            v = reload_obj(v)
            assert_equal(v.get_team_video(), None)
            assert_true(obj_exists(v))

    def test_delete(self):
        videos = self.videos[:2]
        with mock_handler(video_deleted) as handler:
            form = self.build_form(forms.DeleteVideosForm, videos, data={
                'delete': 'yes',
                'verify': unicode(forms.DeleteVideosForm.VERIFY_STRING)
            })
        for v in videos:
            assert_false(obj_exists(v))
        for call, v in zip(handler.call_args_list, videos):
            args, kwargs = call
            assert_equals(kwargs['user'], self.user)

    def test_delete_requires_verify(self):
        videos = self.videos[:2]
        form = self.build_form(forms.DeleteVideosForm, videos, data={
            'delete': 1,
            'verify': "invalid string",
        }, skip_submit=True)
        assert_false(form.is_valid())

    @patch_for_test('teams.permissions.can_delete_video_in_team')
    def test_delete_permissions(self, can_delete_video_in_team):
        can_delete_video_in_team.return_value = False
        form = self.build_form(forms.DeleteVideosForm, self.videos)
        assert_false('delete' in form.fields)
        assert_equal(can_delete_video_in_team.call_args,
                     mock.call(self.team, self.user))

class TestMoveVideosForm(TeamVideoManagementFormBase):
    def setUp(self):
        super(TestMoveVideosForm, self).setUp()
        self.other_team = TeamFactory(admin=self.user)
        self.other_project = ProjectFactory(team=self.other_team)

    def test_move(self):
        videos = self.videos[:2]
        form = self.build_form(forms.MoveVideosForm, videos, data={
            'new_team': self.other_team.id,
            'project': self.other_project.id,
        })
        for v in videos:
            v = reload_obj(v)
            tv = v.get_team_video()
            assert_equal(tv.team, self.other_team)
            assert_equal(tv.project, self.other_project)

    def test_move_no_project(self):
        videos = self.videos[:2]
        form = self.build_form(forms.MoveVideosForm, videos, data={
            'new_team': self.other_team.id,
            'project': '',
        })
        for v in videos:
            v = reload_obj(v)
            tv = v.get_team_video()
            assert_equal(tv.team, self.other_team)
            assert_equal(tv.project, self.other_team.default_project)

    @patch_for_test('teams.permissions.can_move_videos_to')
    def test_team_and_project_choices(self, can_move_videos_to):
        invalid_team = TeamFactory()
        invalid_project = ProjectFactory(team=invalid_team)
        can_move_videos_to.return_value = [ self.team, self.other_team ]
        form = self.build_form(forms.MoveVideosForm, self.videos)
        assert_items_equal([c[0] for c in form.fields['new_team'].choices],
                           [self.team.id, self.other_team.id])
        assert_items_equal([c[0] for c in form.fields['project'].choices],
                           ['', self.project.id, self.other_project.id])
        assert_equal(form.project_map, {
            self.team.id: ['', self.project.id],
            self.other_team.id: ['', self.other_project.id],
        })

class EmailInviteFormTest(TestCase):
    def setUp(self):
        self.author = UserFactory()
        self.team = TeamFactory()
        self.form = forms.InviteForm(self.team, self.author)
        self.form.cleaned_data = {}
        self.form.cleaned_data['role'] = TeamMember.ROLE_CONTRIBUTOR
        self.form.cleaned_data['message'] = ''
        self.form.cleaned_data['username'] = ''

    '''
    Test for when an email invite is sent to an email address
    already associated with a CustomUser account
    '''
    def test_email_recipient_is_already_registered(self):
        user = UserFactory()
        self.form.cleaned_data['email'] = user.email
        self.form.process_email_invite(user.email)        
        assert_true(user.team_invitations.filter(team=self.team).exists())

    def test_email_receipient_has_no_account(self):
        user = UserFactory()
        email = user.email
        user.delete()
        self.form.cleaned_data['email'] = email
        self.form.process_email_invite(self.form.cleaned_data['email'])
        assert_true(EmailInvite.objects.filter(email=email).exists())

    def test_multiple_email_recipients_are_already_registered(self):
        user1 = UserFactory()
        user2 = UserFactory()
        user3 = UserFactory()
        emails = [ user1.email, user2.email, user3.email ]
        self.form.emails = emails
        self.form.save()

        assert_true(user1.team_invitations.filter(team=self.team).exists())
        assert_true(user2.team_invitations.filter(team=self.team).exists())
        assert_true(user3.team_invitations.filter(team=self.team).exists())

    def test_multiple_email_recipients_no_account(self):
        user1 = UserFactory()
        user2 = UserFactory()
        user3 = UserFactory()
        user1.delete()
        user2.delete()
        user3.delete()
        emails = [ user1.email, user2.email, user3.email ]
        self.form.emails = emails
        self.form.save()

        assert_true(EmailInvite.objects.filter(email=user1.email).exists())
        assert_true(EmailInvite.objects.filter(email=user2.email).exists())
        assert_true(EmailInvite.objects.filter(email=user3.email).exists())
        