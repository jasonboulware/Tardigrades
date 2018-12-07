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

import bleach
import datetime
import json
import logging
import re

from django import forms
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError as django_core_ValidationError
from django.core.files.base import ContentFile
from django.urls import reverse
from django.core.validators import EMPTY_VALUES, validate_email
from django.db.models import Q
from django.db import transaction, IntegrityError
from django.forms.formsets import formset_factory
from django.forms.utils import ErrorDict
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from django.utils.translation import ungettext

from auth.forms import UserField
from auth.models import CustomUser as User
from activity.models import ActivityRecord
from messages.models import Message, SYSTEM_NOTIFICATION
from messages.tasks import send_new_messages_notifications
from subtitles.forms import SubtitlesUploadForm
from subtitles.models import ORIGIN_MANAGEMENT_PAGE
from subtitles.pipeline import add_subtitles
from teams.models import (
    Team, TeamMember, TeamVideo, Task, Project, Workflow, Invite,
    BillingReport, MembershipNarrowing, Application, TeamVisibility,
    VideoVisibility, EmailInvite, Setting
)
from teams import behaviors, notifymembers, permissions, tasks
from teams.exceptions import ApplicationInvalidException
from teams.fields import TeamMemberInput, TeamMemberRoleSelect, MultipleProjectField, MultipleUsernameInviteField
from teams.permissions import (
    roles_user_can_invite, can_delete_task, can_add_video, can_perform_task,
    can_assign_task, can_remove_video, can_change_video_titles,
    can_add_video_somewhere
)
from teams.permissions_const import ROLE_NAMES
from teams.signals import member_remove
from teams.workflows import TeamWorkflow
from ui.forms import (FiltersForm, ManagementForm, AmaraChoiceField,
                      AmaraMultipleChoiceField, AmaraRadioSelect, SearchField,
                      AmaraClearableFileInput, AmaraFileInput, HelpTextList,
                      MultipleLanguageField, AmaraImageField, SwitchInput, DependentBooleanField,
                      ContentHeaderSearchBar)
from ui.forms import LanguageField as NewLanguageField
from utils.html import clean_html
from utils import send_templated_email, enum
from utils.forms import (ErrorableModelForm, get_label_for_value,
                         UserAutocompleteField, LanguageField,
                         LanguageDropdown, Dropdown)
from utils.panslugify import pan_slugify
from utils.translation import get_language_choices, get_language_label
from utils.text import fmt
from utils.validators import MaxFileSizeValidator
from videos.forms import (AddFromFeedForm, VideoForm, CreateSubtitlesForm,
                          MultiVideoCreateSubtitlesForm, VideoURLField,
                          VideoDurationField)
from videos.models import (
        VideoMetadata, VIDEO_META_TYPE_IDS, Video, VideoFeed,
)
from videos.tasks import import_videos_from_feed
from videos.types import video_type_registrar, VideoTypeError

logger = logging.getLogger(__name__)

class TeamMemberField(AmaraChoiceField):
    default_error_messages = {
        'invalid': _(u'Invalid user'),
    }
    def setup(self, team):
        self.team = team
        self.set_select_data('ajax', reverse('teams:ajax-member-search',
                                             args=(team.slug,)))
        self.set_select_data('placeholder', ugettext('Select member'))

    def to_python(self, value):
        if value in EMPTY_VALUES:
            return None
        if isinstance(value, User):
            return value
        try:
            return User.objects.get(username=value)
        except User.DoesNotExist:
            raise forms.ValidationError(self.error_messages['invalid'])

    def prepare_value(self, value):
        # Handles initial values and submitted data.  There are a few cases we
        # need to handle:
        #  - choice tuples
        #  - User instances
        #  - usernames
        if isinstance(value, User):
            value = self.choice_for_user(value)
        elif isinstance(value, basestring):
            try:
                value = self.choice_for_user(
                    User.objects.get(username=value))
            except User.DoesNotExist:
                return None
        if value:
            choices = [
                ('', ugettext('Select member')),
                value,
            ]
            if self.choices != choices:
                self.choices = choices
            return value[0]
        else:
            return None

    def choice_for_user(self, user):
        return (user.username, unicode(user))

    def validate(self, user):
        if user and not self.team.user_is_member(user):
            raise forms.ValidationError(self.error_messages['invalid'])

class TeamVideoField(AmaraChoiceField):
    default_error_messages = {
        'invalid': _(u'Invalid video'),
    }

    # TODO: Move some of the code shared between here and TeamMemberField into
    # a base class

    def setup(self, team):
        self.team = team
        self.set_select_data('ajax', reverse('teams:ajax-video-search',
                                             args=(team.slug,)))
        self.set_select_data('placeholder', ugettext('Select video'))

    def to_python(self, value):
        if value in EMPTY_VALUES:
            return None
        if isinstance(value, Video):
            return value
        try:
            return Video.objects.get(video_id=value)
        except Video.DoesNotExist:
            raise forms.ValidationError(self.error_messages['invalid'])

    def choice_for_video(self, video):
        return (video.video_id, unicode(video))

    def prepare_value(self, value):
        # Handles initial values and submitted data.  There are a few cases we
        # need to handle:
        #  - choice tuples
        #  - Video instances
        #  - video ids
        if isinstance(value, Video):
            value = self.choice_for_video(value)
        elif isinstance(value, basestring):
            try:
                value = self.choice_for_video(
                    Video.objects.get(video_id=value,
                                      teamvideo__team=self.team))
            except Video.DoesNotExist:
                return None
        if value:
            choices = [
                ('', ugettext('Select video')),
                value,
            ]
            if self.choices != choices:
                self.choices = choices
            return value[0]
        else:
            return None

    def validate(self, video):
        if video:
            team_video = video.get_team_video()
            if not (team_video and team_video.team == self.team):
                raise forms.ValidationError(self.error_messages['invalid'])

class TeamField(AmaraChoiceField):
    default_error_messages = {
        'invalid': _(u'Invalid Team'),
    }

    def to_python(self, value):
        if value in EMPTY_VALUES:
            return None
        if isinstance(value, Team):
            return value
        # Like for UserField, we use "$" for special values
        if isinstance(value, basestring) and value.startswith("$"):
            return value
        try:
            return Team.objects.get(slug=value)
        except Team.DoesNotExist:
            raise forms.ValidationError(self.error_messages['invalid'])

    def validate(self, team):
        if isinstance(team, Team):
            for choice in self.choices:
                if choice[0] == team.slug:
                    return
            raise forms.ValidationError(self.error_messages['invalid'])

class ProjectField(AmaraChoiceField):
    def __init__(self, *args, **kwargs):
        self.null_label = kwargs.pop('null_label', _('Any'))
        if 'label' not in kwargs:
            kwargs['label'] = _("Project")
        self.futureui = kwargs.pop('futureui', False)
        super(ProjectField, self).__init__(*args, **kwargs)
        self.enabled = True

    def setup(self, team, promote_main_project=False, initial=None, source_teams=None):
        self.team = team
        if source_teams:
            self.source_teams = source_teams
            projects = []
            for team in source_teams:
                projects += list(Project.objects.for_team(team))
        else:
            projects = list(Project.objects.for_team(self.team))
        if projects:
            if promote_main_project:
                main_project = behaviors.get_main_project(self.team)
                if main_project:
                    projects.remove(main_project)
                    projects.insert(0, main_project)
                    if initial is None:
                        initial = main_project.id
            choices = []
            if not self.required:
                choices.append(('', self.null_label))
            choices.append(('none', _('No project')))
            if source_teams and len(source_teams) > 1:
                choices.extend((p.id, p.team.name + ' - ' + p.name) for p in projects)
            else:
                choices.extend((p.id, p.name) for p in projects)
            self.choices = choices
            if initial is None:
                initial = choices[0][0]
            self.initial = initial
            if self.futureui:
                self.setup_widget()
        else:
            self.enabled = False

    def setup_widget(self):
        if len(self.choices) < 7:
            self.widget = AmaraRadioSelect()
            self.widget.attrs.update(self.widget_attrs(self.widget))
            self._setup_widget_choices()

    def prepare_value(self, value):
        return value.id if isinstance(value, Project) else value

    def clean(self, value):
        if not self.enabled or value in EMPTY_VALUES or not self.team:
            return None
        if value == 'none':
            if getattr(self, 'source_teams', None):
                project = [p for p in Project.objects.filter(team__in=self.source_teams)
                           if p.slug == Project.DEFAULT_NAME]
            else:
                project = Project.objects.get(team=self.team, slug=Project.DEFAULT_NAME)
        else:
            project = Project.objects.get(id=value)
        return project

class EditTeamVideoForm(forms.ModelForm):
    author = forms.CharField(max_length=255, required=False)
    creation_date = forms.DateField(required=False, input_formats=['%Y-%m-%d'],
                                    help_text="Format: YYYY-MM-DD")

    project = forms.ModelChoiceField(
        label=_(u'Project'),
        queryset = Project.objects.none(),
        required=True,
        empty_label=None,
        help_text=_(u"Let's keep things tidy, shall we?")
    )

    class Meta:
        model = TeamVideo
        fields = ('description', 'thumbnail', 'project',)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")

        super(EditTeamVideoForm, self).__init__(*args, **kwargs)

        self.fields['project'].queryset = self.instance.team.project_set.all()

    def clean(self, *args, **kwargs):
        super(EditTeamVideoForm, self).clean(*args, **kwargs)

        return self.cleaned_data

    def save(self, *args, **kwargs):
        obj = super(EditTeamVideoForm, self).save(*args, **kwargs)

        video = obj.video

        author = self.cleaned_data['author'].strip()
        creation_date = VideoMetadata.date_to_string(self.cleaned_data['creation_date'])

        self._save_metadata(video, 'Author', author)
        self._save_metadata(video, 'Creation Date', creation_date)
        # store the uploaded thumb on the video itself
        # TODO: simply remove the teamvideo.thumbnail image
        if obj.thumbnail:
            content = ContentFile(obj.thumbnail.read())
            name = obj.thumbnail.url.split('/')[-1]
            video.s3_thumbnail.save(name, content)

    def _save_metadata(self, video, meta, data):
        '''Save a single piece of metadata for the given video.

        The metadata is only saved if necessary (i.e. it's not blank OR it's blank
        but there's already other data that needs to be overwritten).

        '''
        meta_type_id = VIDEO_META_TYPE_IDS[meta]

        try:
            meta = VideoMetadata.objects.get(video=video, key=meta_type_id)
            meta.data = data
            meta.save()
        except VideoMetadata.DoesNotExist:
            if data:
                VideoMetadata(video=video, key=meta_type_id, data=data).save()

class MoveTeamVideoForm(forms.Form):
    team_video = forms.ModelChoiceField(queryset=TeamVideo.objects.all(),
                                        required=True)
    team = forms.ModelChoiceField(queryset=Team.objects.all(),
                                  required=True)

    project = forms.ModelChoiceField(queryset=Project.objects.all(),
                                     required=False)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(MoveTeamVideoForm, self).__init__(*args, **kwargs)

    def clean(self):
        team_video = self.cleaned_data.get('team_video')
        team = self.cleaned_data.get('team')
        project = self.cleaned_data.get('project')

        if not team_video or not team:
            return

        if project and project.team != team:
            raise forms.ValidationError(u"That project does not belong to that team.")

        if team_video.team.pk == team.pk:
            raise forms.ValidationError(u"That video is already in that team.")

        if not can_add_video(team, self.user):
            raise forms.ValidationError(u"You can't add videos to that team.")

        if not can_remove_video(team_video, self.user):
            raise forms.ValidationError(u"You can't remove that video from its team.")

        return self.cleaned_data

class AddVideoToTeamForm(forms.Form):
    """Used to add a non-team video to one of the user's managed teams."""

    team = forms.ChoiceField()

    def __init__(self, user, data=None, **kwargs):
        super(AddVideoToTeamForm, self).__init__(data, **kwargs)
        team_qs = (Team.objects
                   .filter(users=user)
                   .prefetch_related('project_set'))
        self.fields['team'].choices = [
            (team.id, unicode(team)) for team in team_qs
            if can_add_video_somewhere(team, user)
        ]

class AddTeamVideoForm(forms.ModelForm):
    language = NewLanguageField(label=_(u'Video language'),
                                required=True,
                                options='null popular all dont-set',
                                help_text=_(u'It will be saved only if video does not exist in our database.'),
                                error_messages={'required': 'Please select the video language.'})

    project = ProjectField(
        label=_(u'Project'),
        help_text=_(u"Let's keep things tidy, shall we?")
    )
    video_url = VideoURLField(label=_('Video URL'),
        help_text=_("Enter the URL of any compatible video or any video on our site. You can also browse the site and use the 'Add Video to Team' menu."))

    class Meta:
        model = TeamVideo
        fields = ('video_url', 'language', 'description', 'thumbnail', 'project',)

    def __init__(self, team, user, *args, **kwargs):
        self.team = team
        self.user = user
        super(AddTeamVideoForm, self).__init__(*args, **kwargs)
        self.fields['project'].setup(team)

    def use_future_ui(self):
        self.fields['project'].help_text = None
        self.fields['language'].help_text = None

    def clean_project(self):
        project = self.cleaned_data['project']
        return project if project else self.team.default_project

    def clean(self):
        if self._errors:
            return self.cleaned_data

        # See if any error happen when we create our video
        try:
            Video.add(self.cleaned_data['video_url'], self.user,
                      self.setup_video, self.team)
        except Video.DuplicateUrlError, e:
            msg = _(u'This video already belongs to your team.')
            self._errors['video_url'] = self.error_class([msg])
        return self.cleaned_data

    def setup_video(self, video, video_url):
        video.is_public = self.team.videos_public()
        video.primary_audio_language_code = self.cleaned_data['language']
        self.saved_team_video = TeamVideo.objects.create(
            video=video, team=self.team, project=self.cleaned_data['project'],
            added_by=self.user)
        self._success_message = ugettext('Video successfully added to team.')

    def success_message(self):
        return self._success_message

    def save(self):
        # TeamVideo was already created in clean()
        return self.saved_team_video

class MultipleURLsField(forms.CharField):
    def __init__(self, *args, **kwargs):
        if 'max_length' not in kwargs:
            kwargs['max_length'] = 2000
        super(MultipleURLsField, self).__init__(
            required=False, widget=forms.Textarea,
            *args, **kwargs)

class AddMultipleTeamVideoForm(forms.Form):
    language = NewLanguageField(label=_(u'Video language'),
                                required=True,
                                options='null popular all dont-set',
                                help_text=_(u'It will be saved only if video does not exist in our database.'),
                                error_messages={'required': 'Please select the video language.'})

    project = ProjectField(
        label=_(u'Project'),
        help_text=_(u"Let's keep things tidy, shall we?")
    )
    video_urls = MultipleURLsField(label="",
                                   help_text=_("Enter the URLs of any compatible videos or any videos on our site. Enter one URL per line. You can also browse the site and use the 'Add Video to Team' menu."),
                                   error_messages={'required': 'Please add video URLs.'})

    def __init__(self, team, user, *args, **kwargs):
        self.team = team
        self.user = user
        super(AddMultipleTeamVideoForm, self).__init__(*args, **kwargs)
        self.fields['project'].setup(team)
        # [# of OK, # of existing, # of errors]
        self.summary = [0, 0, 0]

    def use_future_ui(self):
        self.fields['project'].help_text = None
        self.fields['language'].help_text = None

    def clean_project(self):
        project = self.cleaned_data['project']
        return project if project else self.team.default_project

    def clean(self):
        if self._errors:
            return self.cleaned_data
        video_urls = self.cleaned_data['video_urls'].split("\n")
        # See if any error happen when we create our videos
        for video_url in video_urls:
            video_url = video_url.strip()
            if len(video_url) == 0:
                continue
            try:
                Video.add(video_url, self.user, self.setup_video, self.team)
            except Video.DuplicateUrlError, e:
                self.summary[1] += 1
            except:
                self.summary[2] += 1
        return self.cleaned_data

    def setup_video(self, video, video_url):
        video.is_public = self.team.videos_public()
        video.primary_audio_language_code = self.cleaned_data['language']
        self.saved_team_video = TeamVideo.objects.create(
            video=video, team=self.team, project=self.cleaned_data['project'],
            added_by=self.user)
        self.summary[0] += 1

    def success_message(self):
        message = ""
        if self.summary[0] > 0:
            message += "{} videos successfully added, ".format(self.summary[0])
        if self.summary[1] > 0:
            message += "{} videos already added to your team, ".format(self.summary[1])
        if self.summary[2] > 0:
            message += "{} videos URL are not valid, ".format(self.summary[3])
        if len(message) > 2:
            message = message[:len(message) - 2]
        else:
            message = _(u'Please input valid video URLs')
        return message

    def save():
        return self.clean()
 
class AddTeamVideosFromFeedForm(AddFromFeedForm):
    def __init__(self, team, user, *args, **kwargs):
        if not can_add_video(team, user):
            raise ValueError("%s can't add videos to %s" % (user, team))
        self.team = team
        super(AddTeamVideosFromFeedForm, self).__init__(user, *args, **kwargs)

    def make_feed(self, url):
        return VideoFeed.objects.create(team=self.team, user=self.user,
                                        url=url)

class CreateTeamForm(forms.ModelForm):
    logo = forms.ImageField(widget=AmaraClearableFileInput,
                validators=[MaxFileSizeValidator(settings.AVATAR_MAX_SIZE)], required=False)
    workflow_type = forms.ChoiceField(choices=(), initial="O")
    is_visible = forms.BooleanField(required=False)

    class Meta:
        model = Team
        fields = ('name', 'slug', 'description', 'logo', 'workflow_type',
                  'is_visible', 'sync_metadata')

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(CreateTeamForm, self).__init__(*args, **kwargs)
        self.fields['workflow_type'].choices = TeamWorkflow.get_choices()
        self.fields['is_visible'].widget.attrs['class'] = 'checkbox'
        self.fields['sync_metadata'].widget.attrs['class'] = 'checkbox'
        self.fields['slug'].label = _(u'Team URL: https://amara.org/teams/')

    def clean_slug(self):
        slug = self.cleaned_data['slug']
        if re.match('^\d+$', slug):
            raise forms.ValidationError('Field can\'t contains only numbers')
        return slug

    def save(self, user):
        is_visible = self.cleaned_data.get('is_visible', False)
        self.instance.set_legacy_visibility(is_visible)
        team = super(CreateTeamForm, self).save()
        TeamMember.objects.create_first_member(team=team, user=user)
        return team

class TaskCreateForm(ErrorableModelForm):
    choices = [(10, 'Transcribe'), Task.TYPE_CHOICES[1]]
    type = forms.TypedChoiceField(choices=choices, coerce=int)
    language = forms.ChoiceField(choices=(), required=False)
    assignee = forms.ModelChoiceField(queryset=User.objects.none(), required=False)

    def __init__(self, user, team, team_video, *args, **kwargs):
        self.non_display_form = False
        if kwargs.get('non_display_form'):
            self.non_display_form = kwargs.pop('non_display_form')
        super(TaskCreateForm, self).__init__(*args, **kwargs)

        self.user = user
        self.team_video = team_video

        # TODO: This is bad for teams with 10k members.
        team_user_ids = team.members.values_list('user', flat=True)

        langs = get_language_choices(with_empty=True,
                                     limit_to=team.get_writable_langs())
        self.fields['language'].choices = langs
        self.fields['assignee'].queryset = User.objects.filter(pk__in=team_user_ids)

        if self.non_display_form:
            self.fields['type'].choices = Task.TYPE_CHOICES

    def _check_task_creation_subtitle(self, tasks, cleaned_data):
        if self.team_video.subtitles_finished():
            self.add_error(_(u"This video has already been transcribed."),
                           'type', cleaned_data)
            return

    def _check_task_creation_translate(self, tasks, cleaned_data):
        if not self.team_video.subtitles_finished():
            self.add_error(_(u"No one has transcribed this video yet, so it can't be translated."),
                           'type', cleaned_data)
            return

        sl = self.team_video.video.subtitle_language(cleaned_data['language'])

        if sl and sl.is_complete_and_synced():
            self.add_error(_(u"This language already has a complete set of subtitles."),
                           'language', cleaned_data)

    def _check_task_creation_review_approve(self, tasks, cleaned_data):
        if not self.non_display_form:
            return

        lang = cleaned_data['language']
        video = self.team_video.video
        subtitle_language = video.subtitle_language(lang)

        if not subtitle_language or not subtitle_language.get_tip():
            self.add_error(_(
                u"This language for this video does not exist or doesn't have a version."
            ), 'language', cleaned_data)

    def clean(self):
        cd = self.cleaned_data

        type = cd['type']
        lang = cd['language']

        team_video = self.team_video
        project, team = team_video.project, team_video.team

        # TODO: Manager method?
        existing_tasks = list(Task.objects.filter(deleted=False, language=lang,
                                                  team_video=team_video))

        if any(not t.completed for t in existing_tasks):
            self.add_error(_(u"There is already a task in progress for that video/language."))

        type_name = Task.TYPE_NAMES[type]

        # TODO: Move into _check_task_creation_translate()?
        if type_name != 'Subtitle' and not lang:
            self.add_error(fmt(_(u"You must select a language for a "
                                 "%(task_type)s task."),
                               task_type=type_name))

        {'Subtitle': self._check_task_creation_subtitle,
         'Translate': self._check_task_creation_translate,
         'Review': self._check_task_creation_review_approve,
         'Approve': self._check_task_creation_review_approve
        }[type_name](existing_tasks, cd)

        return cd


    class Meta:
        model = Task
        fields = ('type', 'language', 'assignee')

class TaskAssignForm(forms.Form):
    task = forms.ModelChoiceField(queryset=Task.objects.none())
    assignee = forms.ModelChoiceField(queryset=User.objects.none(), required=False)

    def __init__(self, team, user, *args, **kwargs):
        super(TaskAssignForm, self).__init__(*args, **kwargs)

        self.team = team
        self.user = user
        self.fields['assignee'].queryset = User.objects.filter(team_members__team=team)
        self.fields['task'].queryset = team.task_set.incomplete()


    def clean_assignee(self):
        assignee = self.cleaned_data['assignee']

        if assignee:
            member = self.team.members.get(user=assignee)
            if member.has_max_tasks():
                raise forms.ValidationError(_(
                    u'That user has already been assigned the maximum number of tasks.'))

        return assignee

    def clean(self):
        task = self.cleaned_data['task']
        assignee = self.cleaned_data.get('assignee', -1)

        if assignee != -1:
            # There are a bunch of edge cases here that we need to check.
            unassigning_from_self      = (not assignee) and task.assignee and task.assignee.id == self.user.id
            assigning_to_self          = assignee and self.user.id == assignee.id
            can_assign_to_other_people = can_assign_task(task, self.user)

            # Users can always unassign a task from themselves.
            if not unassigning_from_self:
                # They can also assign a task TO themselves, assuming they can
                # perform it (which is checked further down).
                if not assigning_to_self:
                    # Otherwise they must have assign permissions in the team.
                    if not can_assign_to_other_people:
                        raise forms.ValidationError(_(
                            u'You do not have permission to assign this task.'))

            if assignee is None:
                return self.cleaned_data
            else:
                if not can_perform_task(assignee, task):
                    raise forms.ValidationError(_(
                        u'This user cannot perform that task.'))

        return self.cleaned_data

class TaskDeleteForm(forms.Form):
    task = forms.ModelChoiceField(queryset=Task.objects.all())
    discard_subs = forms.BooleanField(required=False)

    def __init__(self, team, user, *args, **kwargs):
        super(TaskDeleteForm, self).__init__(*args, **kwargs)

        self.user = user

        self.fields['task'].queryset = team.task_set.incomplete()


    def clean_task(self):
        task = self.cleaned_data['task']

        if not can_delete_task(task, self.user):
            raise forms.ValidationError(_(
                u'You do not have permission to delete this task.'))

        return task

class MessageTextField(forms.CharField):
    def __init__(self, *args, **kwargs):
        if 'max_length' not in kwargs:
            kwargs['max_length'] = 4000
        super(MessageTextField, self).__init__(
            required=False, widget=forms.Textarea,
            *args, **kwargs)

    def clean(self, value):
        value = super(MessageTextField, self).clean(value)
        value = clean_html(value)
        return value

class GuidelinesMessagesForm(forms.Form):
    pagetext_welcome_heading = MessageTextField(
        label=_('Welcome heading on your landing page for non-members'))

    messages_invite = MessageTextField(
        label=_('When a member is invited to join the team'))
    messages_application = MessageTextField(
        label=_('Custom message to display at the top of the application form'), max_length=15000)
    messages_joins = MessageTextField(
        label=_('When a member joins the team'))
    messages_manager = MessageTextField(
        label=_('When a member is given the Manager role'))
    messages_admin = MessageTextField(
        label=_('When a member is given the Admin role'))

    resources_page_content = MessageTextField(
        label=_('Team resource page text'))

    guidelines_subtitle = MessageTextField(
        label=('When transcribing'))
    guidelines_translate = MessageTextField(
        label=('When translating'))
    guidelines_review = MessageTextField(
        label=('When reviewing'))

    def save(self, team):
        with transaction.atomic():
            for key, val in self.cleaned_data.items():
                if key in Setting.KEY_IDS:
                    setting, _ = Setting.objects.get_or_create(
                        team=team, key=Setting.KEY_IDS[key])
                    setting.data = val
                    setting.save()
            team.resources_page_content = self.cleaned_data['resources_page_content']
            team.save()

class GuidelinesLangMessagesForm(forms.Form):
  def __init__(self, *args, **kwargs):
    languages = kwargs.pop('languages')
    super(GuidelinesLangMessagesForm, self).__init__(*args, **kwargs)
    self.fields["messages_joins_language"] = forms.ChoiceField(label=_(u'New message language'), choices=get_language_choices(True),
                                                               required=False)

    self.fields["messages_joins_localized"] = MessageTextField(
        label=_('When a member speaking that language joins the team'))

    keys = []
    for language in languages:
        key = 'messages_joins_localized_%s' % language["code"]
        label = _('When a member joins the team, message in ' + get_language_label(language["code"]))
        keys.append({"key": key, "label": label})
        self.fields[key] = MessageTextField(initial=language["data"],
                                            label=label)
    sorted_keys = map(lambda x: x["key"], sorted(keys, key=lambda x: x["label"]))
    self.fields.keyOrder = ["messages_joins_language", "messages_joins_localized"] + sorted_keys

class LegacySettingsForm(forms.ModelForm):
    logo = forms.ImageField(
        validators=[MaxFileSizeValidator(settings.AVATAR_MAX_SIZE)],
        help_text=_('Max 940 x 235'),
        widget=forms.FileInput,
        required=False)
    square_logo = forms.ImageField(
        validators=[MaxFileSizeValidator(settings.AVATAR_MAX_SIZE)],
        help_text=_('Recommended size: 100 x 100'),
        widget=forms.FileInput,
        required=False)
    is_visible = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super(LegacySettingsForm, self).__init__(*args, **kwargs)
        self.fields['is_visible'].initial = self.instance.team_public()
        self.initial_settings = self.instance.get_settings()

    def use_future_ui(self):
        self.fields['logo'].widget = AmaraClearableFileInput()
        self.fields['square_logo'].widget = AmaraClearableFileInput()

    def save(self, user):
        is_visible = self.cleaned_data.get('is_visible', False)
        with transaction.atomic():
            self.instance.set_legacy_visibility(is_visible)
            super(LegacySettingsForm, self).save()
            self.instance.handle_settings_changes(user, self.initial_settings)

    class Meta:
        model = Team
        fields = ('description', 'logo', 'square_logo', 'sync_metadata')

class LegacyRenameableSettingsForm(LegacySettingsForm):
    class Meta(LegacySettingsForm.Meta):
            fields = LegacySettingsForm.Meta.fields + ('name',)

class GeneralSettingsForm(forms.ModelForm): 
    BY_INVITATION = 0

    ADMISSION_CHOICES = [
        (BY_INVITATION, _(u'Invitation')),
        (Team.APPLICATION, _(u'Application')),
        (Team.OPEN, _(u'Open admission')),
    ]

    ADMISSION_CHOICES_HELP_TEXT = [
        (BY_INVITATION, ugettext(u'The selected roles below can invite new users from the Member Directory page.')),
        (Team.APPLICATION, ugettext(u'Admins can review and approve team member applications from the Member Directory page.')),
        (Team.OPEN, ugettext(u'Users can join the team from the team landing page, and any team member can invite new members from the Member Directory.')),
    ]

    ADMISSION_BY_INVITATION_CHOICES = [
        (Team.INVITATION_BY_ADMIN, _('Admin')),
        (Team.INVITATION_BY_MANAGER, _('Manager')),
        (Team.INVITATION_BY_ALL, _('Contributor'))
    ]

    TeamVisibilityHelpText = enum.Enum('TeamVisibilityHelpText', [
        ('PUBLIC', ugettext(u'The team will be listed in the public team directory.')),
        ('UNLISTED', ugettext(u'The team landing page can be seen by anyone with the team link.')),
        ('PRIVATE', ugettext(u'The team can only be viewed and accessed by members.')),
    ])

    VideoVisibilityHelpText = enum.Enum('VideoVisibilityHelpText', [
        ('PUBLIC', ugettext(u'Videos on this team will be available in the public video library.')),
        ('UNLISTED', ugettext(u'Videos on this team can be seen by anyone with the link.')),
        ('PRIVATE', ugettext(u'Videos on this team can only be viewed and accessed by members.')),
    ])

    square_logo = AmaraImageField(label=_('Team Logo'),
                                  validators=[MaxFileSizeValidator(settings.AVATAR_MAX_SIZE)],
                                  preview_size=(100, 100),
                                  help_text=_('Recommended size 100 x 100 px. Maximum file size 1 MB.'),
                                  required=False)
    logo = AmaraImageField(label=_('Team Banner Image'),
                           validators=[MaxFileSizeValidator(settings.AVATAR_MAX_SIZE)],
                           preview_size=(280, 100),
                           help_text=_('Recommended size 940 x 235 px. Maximum file size 1 MB.'),
                           required=False)
    
    # need to use a different field name because the choices are a little bit
    # different compared to teams.model.Teams.membership_policy field
    #
    # we also set required=False to force this field to just use custom validation
    # (things get funky with the help text when there is an error in this field)
    admission = AmaraChoiceField(
        required=False,
        label=_('Team Admission'), 
        choices=ADMISSION_CHOICES,
        widget=AmaraRadioSelect(inline=True, 
                                attrs={'class': 'teamMembershipSetting'},
                                dynamic_choice_help_text=ADMISSION_CHOICES_HELP_TEXT)
    )

    # checkboxes for multi-field when Invitation radio choice is selected
    inviter_roles = DependentBooleanField(
        label=_('Role'),
        initial=Team.INVITATION_BY_ADMIN,
        choices=ADMISSION_BY_INVITATION_CHOICES)

    # switches for multi-field for subtitle visibility
    subtitles_public = forms.BooleanField(
        label=_('Completed subtitles'), required=False,
        widget=SwitchInput('Public', 'Private'))
    drafts_public = forms.BooleanField(
        label=_('Draft subtitles'), required=False,
        widget=SwitchInput('Public', 'Private'))

    team_visibility = AmaraChoiceField(
        choices=TeamVisibility.choices(),
        label=_('Team visibility'),
        dynamic_choice_help_text=TeamVisibilityHelpText.choices())
    video_visibility = AmaraChoiceField(
        choices=VideoVisibility.choices(),
        label=_('Video visibility'),
        dynamic_choice_help_text=VideoVisibilityHelpText.choices())
    prevent_duplicate_public_videos = forms.BooleanField(
        label=_('Prevent duplicate copies of your team videos in '
                'the Amara public area.'), required=False, 
        help_text=HelpTextList(
            _("Don't allow Amara users to post copies of your "
              "team videos in the public area."),
            _("When adding team videos, move videos from the public "
              "area to your team rather than creating copies."),
        ))

    def __init__(self, allow_rename, *args, **kwargs):
        super(GeneralSettingsForm, self).__init__(*args, **kwargs)
        self.initial_settings = self.instance.get_settings()
        self.initial_video_visibility = self.instance.video_visibility

        self.fields['subtitles_public'].label_additional_classes = " subtitleVisibilityLabel"
        self.fields['drafts_public'].label_additional_classes = " subtitleVisibilityLabel"
        self.fields['subtitles_public'].additional_classes = " subtitleVisibilityInput"
        self.fields['drafts_public'].additional_classes = " subtitleVisibilityInput"

        # we dont render this field in the page but still save it in this form
        self.fields['membership_policy'].required = False

        self._calc_subtitle_visibility()

        # calc the stuff according to POST data if it exists
        if self.data:

            if (self.data.get('admission', None)):
                admission = int(self.data['admission'])
                self._calc_admission(admission)
                if self.errors.get('admission', None) is not None and admission == self.BY_INVITATION:
                    self.fields['admission'].widget.dynamic_choice_help_text_initial = 'Please select a role below.'
            else:
                self.fields['admission'].widget.dynamic_choice_help_text_initial = 'Please select a team admission policy.'
            
            self._calc_team_visibility_help_text(self.data['team_visibility'])
            self._calc_video_visibility_help_text(self.data['video_visibility'])

        else:
            self._calc_admission(self.instance.membership_policy)   
            self._calc_team_visibility_help_text(self.instance.team_visibility.number)
            self._calc_video_visibility_help_text(self.instance.video_visibility.number)

        if not allow_rename:
            del self.fields['name']

    # determines which role checkboxes are ticked based on the team's membership_policy
    def _calc_admission(self, membership_policy):
        membership_policy = int(membership_policy)
        if membership_policy in [Team.INVITATION_BY_ALL, Team.INVITATION_BY_MANAGER, Team.INVITATION_BY_ADMIN]:
            self.initial['admission'] = GeneralSettingsForm.BY_INVITATION
            self.fields['admission'].widget.dynamic_choice_help_text_initial = dict(self.ADMISSION_CHOICES_HELP_TEXT)[self.BY_INVITATION]

            self.initial['inviter_roles'] = membership_policy
        else:
            self.initial['admission'] = membership_policy
            self.fields['admission'].widget.dynamic_choice_help_text_initial = dict(self.ADMISSION_CHOICES_HELP_TEXT)[membership_policy]

    # subtitle visibility setting are for collab teams only
    def _calc_subtitle_visibility(self):
        if self.instance.new_workflow.has_subtitle_visibility_setting:
            if self.instance.collaboration_settings.subtitle_visibility == Team.SUBTITLES_PUBLIC:
                self.initial['subtitles_public'] = True
                self.initial['drafts_public'] = True
            elif self.instance.collaboration_settings.subtitle_visibility == Team.SUBTITLES_PRIVATE_UNTIL_COMPLETE:
                self.initial['subtitles_public'] = True
        else:
            del self.fields['subtitles_public']
            del self.fields['drafts_public']

    def _calc_team_visibility_help_text(self, team_visibility):
        team_visibility = int(team_visibility)
        self.fields['team_visibility'].help_text = self.TeamVisibilityHelpText.lookup_number(team_visibility)

    def _calc_video_visibility_help_text(self, video_visibility):
        video_visibility = int(video_visibility)
        self.fields['video_visibility'].help_text = self.VideoVisibilityHelpText.lookup_number(video_visibility)

    def prevent_duplicate_public_videos_set(self):
        if self.is_bound:
            return bool(self.data.get('prevent_duplicate_public_videos'))
        else:
            return self.instance.prevent_duplicate_public_videos

    def clean(self):
        cleaned_data = super(GeneralSettingsForm, self).clean()

        admission = cleaned_data.get('admission', None)

        if admission:
            if int(cleaned_data['admission']) == GeneralSettingsForm.BY_INVITATION:
                membership_policy = cleaned_data['inviter_roles']
            else:
                membership_policy = cleaned_data['admission']

            cleaned_data['membership_policy'] = membership_policy
        else:
            '''
            hack to add error to the team admission field but not display an error message
            this is to avoid the help text getting funky when there is an error in this particular field
            '''
            self.add_error('admission', '')

        return cleaned_data        

    def save(self, user):
        with transaction.atomic():
            team = super(GeneralSettingsForm, self).save()

            # for some reason the form does not save membership_policy after upgrading to django 1.11
            team.membership_policy = self.cleaned_data['membership_policy']
            team.save()

            if self.instance.new_workflow.has_subtitle_visibility_setting:
                if self.cleaned_data['drafts_public']:
                    self.instance.collaboration_settings.subtitle_visibility = Team.SUBTITLES_PUBLIC
                elif self.cleaned_data['subtitles_public']:
                    self.instance.collaboration_settings.subtitle_visibility = Team.SUBTITLES_PRIVATE_UNTIL_COMPLETE
                else:
                    self.instance.collaboration_settings.subtitle_visibility = Team.SUBTITLES_PRIVATE
                self.instance.collaboration_settings.save()

            self.instance.handle_settings_changes(user, self.initial_settings)
        if team.video_visibility != self.initial_video_visibility:
            tasks.update_video_public_field.delay(team.id)
            tasks.invalidate_video_visibility_caches.delay(team)
        return team

    class Meta:
        model = Team
        fields = ('name', 'description', 'logo', 'square_logo', 'membership_policy',
                  'team_visibility', 'video_visibility', 'sync_metadata',
                  'prevent_duplicate_public_videos')
        labels = {
            'name': _('Team Name'),
            'description': _('Team Description'),
        }
        help_texts = {
            'description': '',
        }
        widgets = {
          'description': forms.Textarea(attrs={'rows':5}),
        }


class NewPermissionsForm(forms.Form):
    membership_policy = DependentBooleanField(
        label=_('Invite users to the team'), required=True, choices=[
            (Team.INVITATION_BY_ADMIN, _('Admins')),
            (Team.INVITATION_BY_MANAGER, _('Managers')),
            (Team.INVITATION_BY_ALL, _('Any Team Member')),
        ])

    video_policy = DependentBooleanField(
        label=_('Add videos, update, or remove videos from team'),
        required=True, choices=[
            (Team.VP_ADMIN, _('Admins')),
            (Team.VP_MANAGER, _('Managers')),
            # VP_MEMBER is disabled until we add a UI for them to add videos
            #(Team.VP_MEMBER, _('Managers')),
        ])

    def __init__(self, team, **kwargs):
        self.team = team
        self.initial_settings = team.get_settings()
        super(NewPermissionsForm, self).__init__(**kwargs)
        if team.video_policy == Team.VP_MEMBER:
            # need to special case this one, since it's not an option
            self.initial['video_policy'] = Team.VP_MANAGER
        else:
            self.initial['video_policy'] = team.video_policy
        if self.team.is_by_invitation():
            self.initial['membership_policy'] = team.membership_policy
            self.fields['membership_policy'].help_text = self.invite_help_text()
        else:
            del self.fields['membership_policy']

    def invite_help_text(self):
        general_settings_link = format_html(
            '<a href="{}">{}</a>',
            reverse('teams:settings_basic', args=(self.team.slug,)),
            ugettext(u'General settings'))
        return mark_safe(fmt(
            ugettext('Your admission policy is invitation only. You can '
                     'change your admission policy on the '
                     '%(general_settings_link)s page.'),
            general_settings_link=general_settings_link))

    def save(self, user):
        with transaction.atomic():
            for name, value in self.cleaned_data.items():
                setattr(self.team, name, value)
            self.team.save()
            self.team.handle_settings_changes(user, self.initial_settings)

class WorkflowForm(forms.ModelForm):
    class Meta:
        model = Workflow
        fields = ('autocreate_subtitle', 'autocreate_translate',
                  'review_allowed', 'approve_allowed')

class PermissionsForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ('membership_policy', 'video_policy', 'subtitle_policy',
                  'translate_policy', 'task_assign_policy', 'workflow_enabled',
                  'max_tasks_per_member', 'task_expiration',)

    def __init__(self, *args, **kwargs):
        super(PermissionsForm, self).__init__(*args, **kwargs)
        self.initial_settings = self.instance.get_settings()

    def save(self, user):
        with transaction.atomic():
            super(PermissionsForm, self).save()
            self.instance.handle_settings_changes(user, self.initial_settings)

class SimplePermissionsForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ('membership_policy', 'video_policy')
        labels = {
            'membership_policy': _('How can users join your team?'),
            'video_policy': _('Who can add/remove videos?'),
        }

    def __init__(self, *args, **kwargs):
        super(SimplePermissionsForm, self).__init__(*args, **kwargs)
        self.initial_settings = self.instance.get_settings()

    def save(self, user):
        with transaction.atomic():
            super(SimplePermissionsForm, self).save()
            self.instance.handle_settings_changes(user, self.initial_settings)

class LanguagesForm(forms.Form):
    preferred = forms.MultipleChoiceField(required=False, choices=())
    blacklisted = forms.MultipleChoiceField(required=False, choices=())

    def __init__(self, team, *args, **kwargs):
        super(LanguagesForm, self).__init__(*args, **kwargs)

        self.team = team
        self.fields['preferred'].choices = get_language_choices(flat=True)
        self.fields['blacklisted'].choices = get_language_choices(flat=True)

    def clean(self):
        preferred = set(self.cleaned_data['preferred'])
        blacklisted = set(self.cleaned_data['blacklisted'])

        if len(preferred & blacklisted):
            raise forms.ValidationError(_(u'You cannot blacklist a preferred language.'))

        return self.cleaned_data

class AddMembersForm(forms.Form):
    role = AmaraChoiceField(choices=TeamMember.ROLES[::-1],
                             initial='contributor',
                             label=_("Assign a role"))
    members = forms.CharField(widget=forms.Textarea(attrs={'rows': 10}),
                              label=_("Users to add to team"))

    def __init__(self, team, user, data=None, *args, **kwargs):
        super(AddMembersForm, self).__init__(data=data, *args, **kwargs)
        self.team = team
        self.user = user        

    def save(self):
        summary = {
            "added": 0,
            "unknown": [],
            "already": [],
            }
        member_role = self.cleaned_data['role']

        for username in set(self.cleaned_data['members'].split()):
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                summary["unknown"].append(username)
            else:
                member, created = TeamMember.objects.get_or_create(team=self.team, user=user)
                if created:
                    summary["added"] += 1
                    if member.role != member_role:
                        member.role = member_role
                        member.save()
                else:
                    summary["already"].append(username)
        return summary


# The form is kinda in a weird state since it tries to work both for old style
# and new style teams
class InviteForm(forms.Form):
    # For old style team invite page, the auto-complete actually works 
    username = UserAutocompleteField(required=False, error_messages={
        'invalid': _(u'User has a pending invite or is already a member of this team')
        },
        help_text="Amara username of the user you want to invite")

    # For new style teams that allow sending invites to multiple users at a time
    usernames = MultipleUsernameInviteField(label=_('Username'),
                                  required=False,
                                  help_text=_('Amara username of the existing user you want to invite. '
                                              'You can invite multiple users. '
                                              'Pasting a comma-separated or a line-by-line list of usernames and pressing the "Enter" key also works!'))
    email = forms.CharField(required=False,
                            widget=forms.Textarea(attrs={'rows': 3}),
                            help_text=_('Email address of the new member you want to invite. '
                                        'You can invite multiple users by entering one email address per line.') )
    message = forms.CharField(required=False,
                              widget=forms.Textarea(attrs={'rows': 4}),
                              label=_("Message to user"))
    role = AmaraChoiceField(choices=TeamMember.ROLES[1:][::-1],
                             initial='contributor',
                             label=_("Assign a role"))

    def __init__(self, team, user, data=None, *args, **kwargs):
        super(InviteForm, self).__init__(data=data, *args, **kwargs)
        if data:
            # getting the current modal tab from invalidated POST data
            self.modal_tab = data.get('modalTab', None)

            # getting the current username selections from invalidated POST data
            form_data_usernames = data.getlist('usernames')
            if form_data_usernames:
                self.fields['usernames'].set_initial_selections(form_data_usernames)

        self.team = team
        self.user = user # the invite author
        self.users = [] # the users to be invited
        self.emails = []
        self.usernames = []
        
        self.fields['role'].choices = [(r, ROLE_NAMES[r])
                                       for r in roles_user_can_invite(team, user)]
        
        if self.team.is_old_style():
            del self.fields['usernames']
            self.fields['username'].queryset = team.invitable_users()
            self.fields['username'].set_autocomplete_url(
                reverse('teams:autocomplete-invite-user', args=(team.slug,))
            )
        else:
            del self.fields['username']
            self.fields['usernames'].set_ajax_autocomplete_url(
                reverse('teams:ajax-inviteable-users-search', kwargs={'slug':team.slug})
                )
            self.fields['usernames'].set_ajax_multiple_username_url(
                reverse('teams:ajax-inviteable-users-multiple-search', kwargs={'slug':team.slug})
                )

    def validate_emails(self):
        for email in self.emails:
            try:
                validate_email(email)
            except django_core_ValidationError:
                self.add_error('email', _(u"{} is an invalid email address.".format(email)))

            invitee = self.team.users.filter(email=email).first()
            if invitee:
                self.add_error('email', _(u"The email address {} belongs to {} who is already a part of the team!".format(email, invitee)))

    def validate_usernames(self):
        for username in self.usernames:
            try:
                user = User.objects.get(username=username)
                if self.team.is_member(user):
                    self.add_error('usernames', _(u'The user {} already belongs to this team!').format(username))
                elif Invite.objects.filter(user=user, team=self.team, approved=None).exists():
                    self.add_error('usernames', _(u'The user {} already has an invite for this team!').format(username))
                else:
                    self.users.append(user)
            except User.DoesNotExist:
                self.add_error('usernames', _(u'The user {} does not exist.').format(username))

    def clean_username(self):
        username = self.data['username']
        if username:
            try:
                user = User.objects.get(username=username)
                if self.team.is_member(user):
                    self.add_error('username', _(u'The user {} already belongs to this team!').format(username))
                elif Invite.objects.filter(user=user, team=self.team, approved=None).exists():
                    self.add_error('username', _(u'The user {} already has an invite for this team!').format(username))
                else:
                    return username
            except User.DoesNotExist:
                self.add_error('usernames', _(u'The user {} does not exist.').format(username))

    def clean(self):
        cleaned_data = super(InviteForm, self).clean()

        if (self.team.is_old_style() and
            not (self['email'].errors or self['username'].errors) and
            not (cleaned_data.get('email') or cleaned_data.get('username'))):
            raise forms.ValidationError(_(u"A valid username or email address must be provided"))

        emails = cleaned_data.get('email')
        usernames = cleaned_data.get('usernames')

        if self.modal_tab == 'username' and not usernames:
            self.add_error('usernames', _(u'At least one username must be provided!'))
        if self.modal_tab == 'email' and not emails:
            self.add_error('email', _(u'At least one email must be provided!'))

        if emails:
            self.emails = emails.split()
            self.emails = set(self.emails)
            self.validate_emails()
            
        if usernames:
            self.usernames = usernames
            self.usernames = set(self.usernames)
            self.validate_usernames()

        return cleaned_data        

    def save(self):
        for email in self.emails:
            self.process_email_invite(email)
        for user in self.users:
            self.create_invite(user)

        if self.team.is_old_style() and self.cleaned_data['username']:
            return self.create_invite(User.objects.get(username=self.cleaned_data['username']))

    def create_invite(self, user):        
        invite = Invite.objects.create(
            team=self.team, user=user, 
            author=self.user, role=self.cleaned_data['role'],
            note=self.cleaned_data['message'])
        invite.save()
        notifymembers.send_invitation_message(invite)
        return invite

    def process_email_invite(self, email):
        invitees = User.objects.filter(email=email)
        for invitee in invitees:
            self.create_invite(invitee)
            '''
            If email notifs for the existing user is turned off, should we still send an email message?
            Taking into account that possibly the intention of the team owner/admin is to communicate
            the email invite via email.
            '''

        if invitees.count() == 0:
            email_invite = EmailInvite.create_invite(email=email, 
                author=self.user, team=self.team, role=self.cleaned_data['role'])
            email_invite.send_mail(self.cleaned_data['message'])

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ('name', 'description', 'workflow_enabled')

    def __init__(self, team, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        self.team = team

    def clean_name(self):
        name = self.cleaned_data['name']

        same_name_qs = self.team.project_set.filter(slug=pan_slugify(name))
        if self.instance.id is not None:
            same_name_qs = same_name_qs.exclude(id=self.instance.id)

        if same_name_qs.exists():
            raise forms.ValidationError(
                _(u"There's already a project with this name"))
        return name

    def save(self):
        project = super(ProjectForm, self).save(commit=False)
        project.team = self.team
        project.save()
        return project

class EditProjectForm(forms.Form):
    project = forms.ChoiceField(choices=[])
    name = forms.CharField(required=True)
    description = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, team, *args, **kwargs):
        super(EditProjectForm, self).__init__(*args, **kwargs)
        self.team = team
        self.fields['project'].choices = [
            (p.id, p.id) for p in team.project_set.all()
        ]

    def clean(self):
        if self.cleaned_data.get('name') and self.cleaned_data.get('project'):
            self.check_duplicate_name()
        return self.cleaned_data

    def check_duplicate_name(self):
        name = self.cleaned_data['name']

        same_name_qs = (
            self.team.project_set
            .filter(slug=pan_slugify(name))
            .exclude(id=self.cleaned_data['project'])
        )

        if same_name_qs.exists():
            self._errors['name'] = self.error_class([
                _(u"There's already a project with this name")
            ])
            del self.cleaned_data['name']

    def save(self):
        project = self.team.project_set.get(id=self.cleaned_data['project'])
        project.name = self.cleaned_data['name']
        project.description = self.cleaned_data['description']
        project.save()
        return project

class AddProjectManagerForm(forms.Form):
    member = UserAutocompleteField()

    def __init__(self, team, project, *args, **kwargs):
        super(AddProjectManagerForm, self).__init__(*args, **kwargs)
        self.team = team
        self.project = project
        self.fields['member'].queryset = project.potential_managers()
        self.fields['member'].set_autocomplete_url(
            reverse('teams:autocomplete-project-manager',
                    args=(team.slug, project.slug))
        )

    def clean_member(self):
        return self.team.get_member(self.cleaned_data['member'])

    def save(self):
        member = self.cleaned_data['member']
        member.make_project_manager(self.project)

class RemoveProjectManagerForm(forms.Form):
    member = TeamMemberInput()

    def __init__(self, team, project, *args, **kwargs):
        super(RemoveProjectManagerForm, self).__init__(*args, **kwargs)
        self.team = team
        self.project = project
        self.fields['member'].set_team(team)

    def clean_member(self):
        member = self.cleaned_data['member']
        if not member.is_project_manager(self.project):
            raise forms.ValidationError(_(u'%(user)s is not a manager'),
                                        user=username)
        return member

    def save(self):
        member = self.cleaned_data['member']
        member.remove_project_manager(self.project)

class AddLanguageManagerForm(forms.Form):
    member = UserAutocompleteField()

    def __init__(self, team, language_code, *args, **kwargs):
        super(AddLanguageManagerForm, self).__init__(*args, **kwargs)
        self.team = team
        self.language_code = language_code
        self.fields['member'].queryset = team.potential_language_managers(
            language_code)
        self.fields['member'].widget.set_autocomplete_url(
            reverse('teams:autocomplete-language-manager',
                    args=(team.slug, language_code))
        )

    def clean_member(self):
        return self.team.get_member(self.cleaned_data['member'])

    def save(self):
        member = self.cleaned_data['member']
        member.make_language_manager(self.language_code)

class RemoveLanguageManagerForm(forms.Form):
    member = TeamMemberInput()

    def __init__(self, team, language_code, *args, **kwargs):
        super(RemoveLanguageManagerForm, self).__init__(*args, **kwargs)
        self.team = team
        self.language_code = language_code
        self.fields['member'].set_team(team)

    def clean_member(self):
        member = self.cleaned_data['member']
        if not member.is_language_manager(self.language_code):
            raise forms.ValidationError(_(u'%(user)s is not a manager'),
                                        user=username)
        return member

    def save(self):
        member = self.cleaned_data['member']
        member.remove_language_manager(self.language_code)

class TaskUploadForm(SubtitlesUploadForm):
    task = forms.ModelChoiceField(Task.objects, required=True)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        video = kwargs.pop('video')
        super(TaskUploadForm, self).__init__(user, video, False,
                                             *args, **kwargs)

    def clean_task(self):
        task = self.cleaned_data['task']

        if not can_perform_task(self.user, task):
            raise forms.ValidationError(_(u'You cannot perform that task.'))

        if task.team_video.video_id != self.video.id:
            raise forms.ValidationError(_(u'Mismatched video and task!'))

        return task

    def clean(self):
        super(TaskUploadForm, self).clean()

        try:
            task = self.cleaned_data['task']
        except KeyError:
            raise forms.ValidationError(_(u'Task has been deleted'))
        language_code = self.cleaned_data['language_code']
        from_language_code = self.cleaned_data['from_language_code']

        if task.language and task.language != language_code:
            raise forms.ValidationError(_(
                'The selected language does not match the task.'))

        current_version = task.get_subtitle_version()
        if current_version:
            current_sl = current_version.subtitle_language
            current_source_lc = current_sl.get_translation_source_language_code()
            if current_source_lc and current_source_lc != from_language_code:
                raise forms.ValidationError(fmt(_(
                    "The selected source language %(from_code)s "
                    "does not match the existing source language "
                    "%(cur_code)s for that task."),
                      from_code=from_language_code,
                      cur_code=current_source_lc,
                ))
        return self.cleaned_data

    def save(self, *args, **kwargs):
        task = self.cleaned_data['task']
        language_code = self.cleaned_data['language_code']

        version = super(TaskUploadForm, self).save(*args, **kwargs)

        if not task.assignee:
            task.assignee = self.user
            task.set_expiration()

        task.new_subtitle_version = version
        task.language = language_code

        task.save()

        return version

def make_billing_report_form():
    """Factory function to create a billing report form """
    class BillingReportForm(forms.Form):
        teams = forms.ModelMultipleChoiceField(
            required=True,
            queryset=(Team.objects.with_recent_billing_record(40)
                      .order_by('name')),
            widget=forms.CheckboxSelectMultiple)
        start_date = forms.DateField(required=True, help_text='YYYY-MM-DD')
        end_date = forms.DateField(required=True, help_text='YYYY-MM-DD')
        type = forms.ChoiceField(required=True,
                                 choices=BillingReport.TYPE_CHOICES,
                                 initial=BillingReport.TYPE_BILLING_RECORD)
    return BillingReportForm

class TaskCreateSubtitlesForm(CreateSubtitlesForm):
    """CreateSubtitlesForm that also sets the language for task."""

    def __init__(self, request, task, data=None):
        CreateSubtitlesForm.__init__(self, request, task.team_video.video,
                                     data)
        self.task = task

    def handle_post(self):
        self.task.language = self.cleaned_data['subtitle_language_code']
        self.task.save()
        return CreateSubtitlesForm.handle_post(self)

class TeamMultiVideoCreateSubtitlesForm(MultiVideoCreateSubtitlesForm):
    """MultiVideoCreateSubtitlesForm that is task-aware."""

    def __init__(self, request, team, data=None):
        MultiVideoCreateSubtitlesForm.__init__(self, request, team.videos,
                                               data)
        self.team = team

    def handle_post(self):
        if self.team.workflow_enabled:
            # set the language for the task being performed (if needed)
            language = self.cleaned_data['subtitle_language_code']
            tasks = self.get_video().get_team_video().task_set
            (tasks.incomplete_subtitle().filter(language='')
             .update(language=language))
        return MultiVideoCreateSubtitlesForm.handle_post(self)

class OldMoveVideosForm(forms.Form):
    team = forms.ModelChoiceField(queryset=Team.objects.none(),
                                  required=True,
                                  empty_label=None)

    class Meta:
        fields = ('team')

    def __init__(self, user,  *args, **kwargs):
        super(OldMoveVideosForm, self).__init__(*args, **kwargs)
        self.fields['team'].queryset = user.managed_teams(include_manager=False)

class VideoFiltersForm(FiltersForm):
    q = SearchField(label=_('Search for videos'), required=False)
    language = NewLanguageField(label=_("Video language"), required=False,
                                placeholder=_("All languages"), filter=True)
    project = ProjectField(required=False, futureui=True, filter=True)
    duration = VideoDurationField(required=False, widget=AmaraRadioSelect)
    sort = AmaraChoiceField(label="", choices=[
        ('-time', _('Time, newest')),
        ('time', _('Time, oldest')),
        ('name', _('Name, a-z')),
        ('-name', _('Name, z-a')),
        ('-subs', _('Most completed languages')),
        ('subs', _('Least completed languages')),
    ], initial='-time', required=False)

    promote_main_project = True

    def __init__(self, team, get_data=None, **kwargs):
        self.team = team
        super(VideoFiltersForm, self).__init__(get_data, **kwargs)
        self.fields['project'].setup(team, self.promote_main_project)

    def _get_queryset(self, data):
        project = data.get('project')
        duration = data.get('duration')
        language = data.get('language')
        q = data.get('q')
        sort = data.get('sort')

        qs = Video.objects.filter(teamvideo__team=self.team)

        if not (self.is_bound and self.is_valid()):
            return qs.order_by('-created')

        if q:
            qs = qs.search(q)
        if project:
            if isinstance(project, Project):
                qs = qs.filter(teamvideo__project=project)
            else:
                qs = qs.filter(teamvideo__project__slug=project)
        if language:
            qs = qs.filter(primary_audio_language_code=language)
        if duration:
            qs = self.fields['duration'].filter(qs, duration)

        if sort in ('subs', '-subs'):
            qs = qs.add_num_completed_languages()

        qs = qs.order_by({
             'name':  'title',
            '-name': '-title',
             'subs':  'num_completed_languages',
            '-subs': '-num_completed_languages',
             'time':  'created',
            '-time': '-created',
        }.get(sort or '-time'))

        return qs

class ManagementVideoFiltersForm(VideoFiltersForm):
    language = NewLanguageField(label=_("Video language"),
                                required=False,
                                placeholder=_('All languages'),
                                options="null popular all", filter=True)
    completed_subtitles = NewLanguageField(label=_("Completed subtitles"),
                                           required=False,
                                           options="null popular all",
                                           filter=True)
    needs_subtitles = NewLanguageField(label=_("Needs subtitles"), 
                                       required=False,
                                       options="null popular all",
                                       filter=True)

    promote_main_project = False

    def _get_queryset(self, data):
        qs = super(ManagementVideoFiltersForm, self)._get_queryset(data)
        completed_subtitles = data.get('completed_subtitles')
        needs_subtitles = data.get('needs_subtitles')
        if completed_subtitles:
            qs = qs.has_completed_language(completed_subtitles)
        if needs_subtitles:
            qs = qs.missing_completed_language(needs_subtitles)
        return qs

class ActivityFiltersForm(FiltersForm):
    SORT_CHOICES = [
        ('-created', _('newest first (default)')),
        ('created', _('oldest first')),
    ]
    SORT_CHOICES_OLD = [
        ('-created', _('date, newest')),
        ('created', _('date, oldest')),
    ]
    type = AmaraMultipleChoiceField(
        label=_('Select Type'), required=False,
        choices=[])
    video = forms.CharField(label=_('Search for video'), required=False)
    video_language = MultipleLanguageField(
        label=_('Select Video Language'), required=False,
        options='my popular all')
    subtitle_language = MultipleLanguageField(
        label=_('Select Subtitle Language'), required=False,
        options='my popular all')
    sort = AmaraChoiceField(
        label=_('Select sort'), required=False,
        choices=SORT_CHOICES)

    def __init__(self, team, get_data):
        super(ActivityFiltersForm, self).__init__(get_data)
        self.team = team
        self.fields['type'].choices = self.calc_activity_choices()

    def calc_activity_choices(self):
        choices = [
            ('', _('Any type')),
        ]
        choice_map = dict(ActivityRecord.active_type_choices())
        choices.extend(
            (value, choice_map[value])
            for value in self.team.new_workflow.activity_type_filter_options()
        )
        choices.sort(key=lambda choice: unicode(choice[1]))
        return choices

    def _get_queryset(self, cleaned_data):
        qs = ActivityRecord.objects.for_team(self.team)
        if not (self.is_bound and self.is_valid()):
            return qs
        type = cleaned_data.get('type')
        video = cleaned_data.get('video')
        subtitle_language = cleaned_data.get('subtitle_language')
        video_language = cleaned_data.get('video_language')
        sort = cleaned_data.get('sort', '-created')
        if type:
            qs = qs.filter(type__in=type)
        if video:
            qs = qs.filter(video__in=Video.objects.search(video))
        if subtitle_language:
            qs = qs.filter(language_code__in=subtitle_language)
        if video_language:
            qs = qs.filter(video_language_code__in=video_language)
        if sort:
            qs = qs.order_by(sort)
        return qs

class MemberFiltersForm(forms.Form):
    LANGUAGE_CHOICES = [
        ('any', _('Any language')),
    ] + get_language_choices()

    q = SearchField(label=_('Search'), required=False,
                    widget=ContentHeaderSearchBar)

    role = AmaraChoiceField(label=_('Select role'), choices=[
        ('any', _('All roles')),
        (TeamMember.ROLE_ADMIN, _('Admins')),
        (TeamMember.ROLE_MANAGER, _('Managers')),
        (TeamMember.ROLE_PROJ_LANG_MANAGER, _('Project/Language Managers')),
        (TeamMember.ROLE_CONTRIBUTOR, _('Contributors')),        
    ], initial='any', required=False, filter=True)
    language = AmaraChoiceField(choices=LANGUAGE_CHOICES,
                                 label=_('Select language'),
                                 initial='any', required=False, filter=True)
    sort = AmaraChoiceField(label=_('Change sort'), choices=[
        ('recent', _('Newest joined')),
        ('oldest', _('Oldest joined')),
    ], initial='recent', required=False)

    def __init__(self, get_data=None):
        super(MemberFiltersForm, self).__init__(
            self.calc_data(get_data)
        )

    def calc_data(self, get_data):
        if get_data is None:
            return None
        data = {k:v for k, v in get_data.items() if k != 'page'}
        return data if data else None

    def update_qs(self, qs):
        if not (self.is_bound and self.is_valid()):
            return qs.order_by('-created')
        else:
            data = self.cleaned_data

        q = data.get('q', '')
        role = data.get('role', 'any')
        language = data.get('language', 'any')
        sort = data.get('sort', 'recent')

        for term in [term.strip() for term in q.split()]:
            if term:
                qs = qs.filter(Q(user__first_name__icontains=term)
                               | Q(user__last_name__icontains=term)
                               | Q(user__full_name__icontains=term)
                               | Q(user__email__icontains=term)
                               | Q(user__username__icontains=term)
                               | Q(user__biography__icontains=term))
        if role and role != 'any':
            if role == TeamMember.ROLE_PROJ_LANG_MANAGER:
                qs = qs.exclude(Q(projects_managed=None) & Q(languages_managed=None))
            elif role == TeamMember.ROLE_CONTRIBUTOR:
                qs = qs.filter(role=role,
                               projects_managed=None,
                               languages_managed=None)
            elif role != TeamMember.ROLE_ADMIN:
                qs = qs.filter(role=role)
            else:
                qs = qs.filter(Q(role=TeamMember.ROLE_ADMIN)|
                               Q(role=TeamMember.ROLE_OWNER))
        if language and language != 'any':
            qs = qs.filter(user__userlanguage__language=language)
        if sort == 'oldest':
            qs = qs.order_by('created')
        else:
            qs = qs.order_by('-created')
        return qs

class ApplicationFiltersForm(forms.Form):
    LANGUAGE_CHOICES = [
        ('any', _('Any language')),
    ] + get_language_choices()

    language = forms.ChoiceField(choices=LANGUAGE_CHOICES,
                                 label=_('Language spoken'),
                                 initial='any', required=False)

    def __init__(self, get_data=None):
        super(ApplicationFiltersForm, self).__init__(self.calc_data(get_data))

    def calc_data(self, get_data):
        if get_data is None:
            return None
        data = {k:v for k, v in get_data.items() if k != 'page'}
        return data if data else None

    def update_qs(self, qs):
        if not (self.is_bound and self.is_valid()):
            return qs
        language = self.cleaned_data.get('language', 'any')
        if language and language != 'any':
            qs = qs.filter(user__userlanguage__language=language)

        return qs

class ApproveApplicationForm(ManagementForm):

    name = "approve_application"
    label = _("Approve Application")

    def __init__(self, user, queryset, selection, all_selected,
                 data=None, files=None):
        self.user = user
        super(ApproveApplicationForm, self).__init__(
            queryset, selection, all_selected, data=data, files=files)

    def perform_submit(self, applications):
        self.approved_count = 0
        self.invalid_count = 0
        self.error_count = 0
        for application in applications:
            try:
                application.approve(self.user, "web UI")
                self.approved_count += 1
            except ApplicationInvalidException:
                self.invalid_count += 1
                _(u'Application already processed.')
            except Exception as e:
                logger.warn(e, exc_info=True)
                self.error_count += 1

    def message(self):
        if self.approved_count:
            return fmt(self.ungettext('Application has been approved',
                                      '%(count)s application has been approved',
                                      '%(count)s applications have been approved',
                                      self.approved_count), count=self.approved_count)
        else:
            return None

    def error_messages(self):
        errors = []
        if self.invalid_count:
            errors.append(fmt(self.ungettext(
                "Application could not be approved because it was already processed",
                "%(count)s application could not be approved because it was already processed",
                "%(count)s applications could not be approved because they were already processed",
                self.invalid_count), count=self.invalid_count))
        if self.error_count:
            errors.append(fmt(self.ungettext(
                "Application could not be processed",
                "%(count)s application could not be processed",
                "%(count)s applications could not be processed",
                self.error_count), count=self.error_count))
        return errors

class DenyApplicationForm(ManagementForm):

    name = "deny_application"
    label = _("Deny Application")

    def __init__(self, user, queryset, selection, all_selected,
                 data=None, files=None):
        self.user = user
        super(DenyApplicationForm, self).__init__(
            queryset, selection, all_selected, data=data, files=files)

    def perform_submit(self, applications):
        self.denied_count = 0
        self.invalid_count = 0
        self.error_count = 0
        for application in applications:
            try:
                application.deny(self.user, "web UI")
                self.denied_count += 1
            except ApplicationInvalidException:
                self.invalid_count += 1
                _(u'Application already processed.')
            except Exception as e:
                logger.warn(e, exc_info=True)
                self.error_count += 1

    def message(self):
        if self.denied_count:
            return fmt(self.ungettext('Application has been denied',
                                      '%(count)s application has been denied',
                                      '%(count)s applications have been denied',
                                      self.denied_count), count=self.denied_count)
        else:
            return None

    def error_messages(self):
        errors = []
        if self.invalid_count:
            errors.append(fmt(self.ungettext(
                "Application could not be denied because it was already processed",
                "%(count)s application could not be denied because it was already processed",
                "%(count)s applications could not be denied because they were already processed",
                self.invalid_count), count=self.invalid_count))
        if self.error_count:
            errors.append(fmt(self.ungettext(
                "Application could not be processed",
                "%(count)s application could not be processed",
                "%(count)s applications could not be processed",
                self.error_count), count=self.error_count))
        return errors

class ChangeMemberRoleForm(ManagementForm):
    name = "change_role"
    label = _("Change Role")

    role = TeamMemberRoleSelect(choices=[
                ('', _("Don't change")),
                (TeamMember.ROLE_CONTRIBUTOR, _('Contributor')),
                (TeamMember.ROLE_PROJ_LANG_MANAGER, _('Project/Language Manager')),
                (TeamMember.ROLE_MANAGER, _('Manager')),
           ], initial='', label=_('Member Role'))

    projects = MultipleProjectField(label=_('Project'), null_label=_('No change'), required=False)
    languages = MultipleLanguageField(label=_('Subtitle language(s)'), options='null all', required=False)

    def __init__(self, user, queryset, selection, all_selected,
                 data=None, files=None, is_owner=False, team=None, **kwargs):
        self.user = user
        self.is_owner = is_owner
        self.team = team
        super(ChangeMemberRoleForm, self).__init__(
            queryset, selection, all_selected, data=data, files=files)
        self.fields['projects'].setup(team)

    def clean(self):
        cleaned_data = super(ChangeMemberRoleForm, self).clean()
        role = cleaned_data.get('role')

        if (role == TeamMember.ROLE_PROJ_LANG_MANAGER and
            not (cleaned_data['projects'] or cleaned_data['languages'])):
                raise forms.ValidationError(_(u"Please select a project or language"))

        return cleaned_data

    def setup_fields(self):
        if self.is_owner:
            self.fields['role'].choices += [(TeamMember.ROLE_ADMIN, _('Admin'))]
            self.fields['role'].choices += [(TeamMember.ROLE_OWNER, _('Owner'))]

    def would_remove_last_owner(self, member, role):
        if role == TeamMember.ROLE_OWNER:
            return False
        elif not member.role == TeamMember.ROLE_OWNER:
            return False
        else:
            team_owners = member.team.members.owners()
            return (len(team_owners) <= 1)

    def perform_submit(self, members):
        self.error_count = 0
        self.only_owner_count = 0
        self.invalid_permission_count = 0
        self.changed_count = 0

        role = self.cleaned_data['role']

        if role != '':
            for member in members:
                # check if user is last owner on team
                if self.would_remove_last_owner(member, role):
                    self.only_owner_count += 1
                # check if user has permission to change the member's role
                elif not permissions.can_assign_role(member.team, self.user, role, member.user):
                    self.invalid_permission_count += 1
                else:
                    try:
                        if role == TeamMember.ROLE_PROJ_LANG_MANAGER:
                            member.change_role(
                                self.user, TeamMember.ROLE_CONTRIBUTOR,
                                self.cleaned_data.get('projects'),
                                self.cleaned_data.get('languages'))
                        else:
                            member.change_role(self.user, role)
                        self.changed_count += 1
                    except Exception as e:
                        logger.error(e, exc_info=True)
                        self.error_count += 1

    def message(self):
        if self.changed_count:
            return fmt(self.ungettext('Member role has been updated',
                                      '%(count)s member role has been updated',
                                      '%(count)s member roles have been updated',
                                      self.changed_count), count=self.changed_count)
        else:
            return None

    def error_messages(self):
        errors = []
        if self.only_owner_count:
            errors.append(fmt(self.ungettext(
            "Could not change the member role because there would be no owners left in the team",
            "Could not change %(count)s member role because there would be no owners left in the team",
            "Could not change %(count)s member roles because there would be no owners left in the team",
            self.only_owner_count), count=self.only_owner_count))
        if self.invalid_permission_count:
            errors.append(fmt(self.ungettext(
            "Member not changed because you do not have permission to change this role",
            "%(count)s member not changed because you do not have permission to change this role",
            "%(count)s members not changed because you do not have permission to change these roles",
            self.invalid_permission_count), count=self.invalid_permission_count))
        if self.error_count:
            errors.append(fmt(self.ungettext(
                "Member could not be edited",
                "%(count)s member could not be edited",
                "%(count)s members could not be edited",
                self.error_count), count=self.error_count))
        return errors

    def get_pickle_state(self):
        return (
            self.user.id,
            self.team.id,
            self.is_owner,
            self.queryset.query,
            self.selection,
            self.all_selected,
            self.data,
            self.files,
        )

    @classmethod
    def restore_from_pickle_state(cls, state):
        user = User.objects.get(id=state[0])
        team = Team.objects.get(id=state[1])
        is_owner = state[2]
        queryset = TeamMember.objects.all()
        queryset.query = state[3]
        return cls(user, queryset, is_owner=is_owner, team=team, *state[4:])

class RemoveMemberForm(ManagementForm):
    name = "remove_member"
    label = _("Remove Member")

    def __init__(self, user, queryset, selection, all_selected,
                 data=None, files=None, is_owner=False, **kwargs):
        self.user = user
        super(RemoveMemberForm, self).__init__(
            queryset, selection, all_selected, data=data, files=files, **kwargs)

    def would_remove_last_owner(self, members):
        # if no owners are going to be removed
        selected_owners = [member for member in members if member.role == TeamMember.ROLE_OWNER]
        if not selected_owners:
            return False
        else:
            team_owners = members[0].team.members.owners()
            return (len(team_owners) - len(selected_owners) <= 1)

    def perform_submit(self, members):
        self.error_count = 0
        self.only_owner_count = 0
        self.removed_count = 0

        # convert generator to list
        members = list(members)

        # if there would be no more members left on the team
        if self.would_remove_last_owner(members):
            self.only_owner_count += len(members)
            return

        for member in members:
            try:
                member_remove.send(sender=member)
                member.delete()
                for app in member.team.applications.filter(user=member.user):
                    app.on_member_removed(self.user, "web UI")
                self.removed_count += 1
            except Exception as e:
                logger.warn(e, exc_info=True)
                self.error_count += 1

    def message(self):
        if self.removed_count:
            return fmt(self.ungettext('User has been removed',
                                      '%(count)s user has been removed',
                                      '%(count)s users have been removed',
                                      self.removed_count), count=self.removed_count)
        else:
            return None

    def error_messages(self):
        errors = []
        if self.only_owner_count:
            errors.append(fmt(self.ungettext(
            "Could not remove the user because there would be no owners left in the team",
            "Could not remove %(count)s user because there would be no owners left in the team",
            "Could not remove %(count)s users because there would be no owners left in the team",
            self.only_owner_count), count=self.only_owner_count))
        if self.error_count:
            errors.append(fmt(self.ungettext(
                "Member could not be removed",
                "%(count)s member could not be removed",
                "%(count)s members could not be removed",
                self.error_count), count=self.error_count))
        return errors

class EditMembershipForm(forms.Form):
    member = forms.ChoiceField()
    remove = forms.BooleanField(required=False)
    role = forms.ChoiceField(choices=[
        (TeamMember.ROLE_CONTRIBUTOR, _('Contributor')),
        (TeamMember.ROLE_MANAGER, _('Manager')),
        (TeamMember.ROLE_ADMIN, _('Admin')),
    ], initial=TeamMember.ROLE_CONTRIBUTOR, label=_('Member Role'))
    language_narrowings = forms.MultipleChoiceField(required=False)
    project_narrowings = forms.MultipleChoiceField(required=False)

    def __init__(self, member, *args, **kwargs):
        super(EditMembershipForm, self).__init__(*args, **kwargs)
        edit_perms = permissions.get_edit_member_permissions(member)
        self.enabled = True
        member_qs = (TeamMember.objects
                     .filter(team_id=member.team_id)
                     .exclude(id=member.id))

        if edit_perms == permissions.EDIT_MEMBER_NOT_PERMITTED:
            self.enabled = False
            self.fields['role'].choices = []
            member_qs = TeamMember.objects.none()
            del self.fields['remove']
        elif edit_perms == permissions.EDIT_MEMBER_CANT_EDIT_ADMIN:
            del self.fields['role'].choices[-1]
            member_qs = member_qs.exclude(role__in=[
                TeamMember.ROLE_ADMIN, TeamMember.ROLE_OWNER,
            ])

        self.editable_member_ids = set(m.id for m in member_qs)
        # no need for a fancy label, since we set the choices with JS anyway
        self.fields['member'].choices = [
            (mid, mid) for mid in self.editable_member_ids
        ]

    def show_remove_button(self):
        return 'remove' in self.fields

    def save(self):
        member_to_edit = TeamMember.objects.get(
            id=self.cleaned_data['member']
        )
        if self.cleaned_data.get('remove'):
            member_to_edit.delete()
        else:
            member_to_edit.role = self.cleaned_data['role']
            member_to_edit.save()

class ApplicationForm(forms.Form):
    about_you = forms.CharField(widget=forms.Textarea, label="")
    language1 = NewLanguageField(required=True)
    language2 = NewLanguageField(required=False)
    language3 = NewLanguageField(required=False)
    language4 = NewLanguageField(required=False)
    language5 = NewLanguageField(required=False)
    language6 = NewLanguageField(required=False)

    def __init__(self, application, *args, **kwargs):
        super(ApplicationForm, self).__init__(*args, **kwargs)
        self.application = application
        self.fields['about_you'].help_text = fmt(
            ugettext('Tell us a little bit about yourself and why '
                     'you\'re interested in translating with '
                     '%(team)s.  This should be 3-5 sentences, no '
                     'longer!'),
            team=application.team)
        for i, language in enumerate(application.user.get_languages()):
            field = self.fields['language{}'.format(i+1)]
            field.initial = language

    def notify(self):
        send_to = [tm.user for tm in self.application.team.members.admins()]
        url_base = '{}://{}'.format(settings.DEFAULT_PROTOCOL,
                                    settings.HOSTNAME)
        context = {
            'application': self.application,
            'applicant': self.application.user,
            'team': self.application.team,
            'note': self.application.note,
            'url_base': url_base
        }
        subject = _(u"A user has requested to join your team")
        ids = []

        for user in send_to:
            context['user'] = user
            body = render_to_string("messages/application-sent.txt", context)
            msg = Message(user=user, subject=subject, content=body,
                          message_type=SYSTEM_NOTIFICATION)
            msg.save()
            ids.append(msg.pk)
            if user.notify_by_email:
                send_templated_email(user, subject,
                        "messages/email/application-sent-email.html", context)
        send_new_messages_notifications.delay(ids)

    def _get_language_list(self):
        languages = []
        for i in xrange(1, 7):
            value = self.cleaned_data.get('language{}'.format(i))
            if value:
                languages.append({"language": value, "priority": i})

        if not languages:
            raise forms.ValidationError(_("Please select at least one language"), code='no-language')
        return languages

    def clean(self):
        try:
            self.application.check_can_submit()
        except ApplicationInvalidException, e:
            raise forms.ValidationError(e.message)
        self._get_language_list()
        return self.cleaned_data

    def save(self):
        try:
            self.application.note = self.cleaned_data['about_you']
        except IntegrityError as e:
            raise forms.ValidationError(e.__cause__, code='duplicate')
        languages = self._get_language_list()
        self.application.save()
        self.application.user.set_languages(languages)
        self.notify()

class TeamVideoCSVForm(forms.Form):
    csv_file = forms.FileField(widget=AmaraFileInput,
            label="", required=True, allow_empty_file=False)

class VideoManagementForm(ManagementForm):
    """Base class for forms on the video management page."""

    iter_objects_select_related = ('teamvideo', 'teamvideo__project')

    @staticmethod
    def permissions_check(team, user):
        """Check if we should enable the form for a given user."""
        return True

    def __init__(self, team, user, queryset, selection, all_selected,
                 data=None, files=None):
        self.team = team
        self.user = user
        super(VideoManagementForm, self).__init__(
            queryset, selection, all_selected, data=data, files=files)

    def get_pickle_state(self):
        return (
            self.team.id,
            self.user.id,
            self.queryset.query,
            self.selection,
            self.all_selected,
            self.data,
            self.files,
        )

    @classmethod
    def restore_from_pickle_state(cls, state):
        team = Team.objects.get(id=state[0])
        user = User.objects.get(id=state[1])
        queryset = Video.objects.all()
        queryset.query = state[2]
        return cls(team, user, queryset, *state[3:])

class EditVideosForm(VideoManagementForm):
    name = 'edit'
    label = _('Edit')
    permissions_check = staticmethod(permissions.can_edit_videos)

    title = forms.CharField(max_length=2048, label=_('Title'))
    language = NewLanguageField(label=_("Language"), options="null popular all")
    project = ProjectField(label=_('Project'), required=False,
                           null_label=_('No change'))
    thumbnail = AmaraImageField(label=_('Thumbnail'), preview_size=(220, 123),
                                required=False)

    '''
    don't allow project managers to change the project of a video
    '''
    def setup_fields(self):
        member = self.team.get_member(self.user)
        if not member.is_manager():
            del self.fields['project']
            self.show_project_field = False
        else:
            self.fields['project'].setup(self.team)
            self.show_project_field = True

    def setup_single_selection(self, video):
        team_video = video.teamvideo
        self.fields['title'].required = True
        if self.show_project_field:
            self.fields['project'].required = True
            self.fields['project'].initial = team_video.project.id
            self.fields['project'].choices = self.fields['project'].choices[1:]
        if video.primary_audio_language_code:
            self.fields['language'].set_options("popular all unset")
        else:
            self.fields['language'].set_options("null popular all dont-set")
        self.fields['language'].initial = video.primary_audio_language_code
        self.fields['language'].required = True

        if can_change_video_titles(self.user, team_video):
            self.fields['title'].widget.attrs['value'] = team_video.video.title
        else:
            del self.fields['title']

    def setup_multiple_selection(self):
        del self.fields['title']
        self.fields['language'].required = False
        self.fields['language'].set_options("null popular all")
        self.fields['language'].set_placeholder(_('No change'))

    def perform_submit(self, qs):
        project = self.cleaned_data.get('project')
        language = self.cleaned_data['language']
        thumbnail = self.cleaned_data['thumbnail']
        if language == '' and not self.single_selection():
            language = None

        for video in qs:
            team_video = video.teamvideo

            new_title = self.cleaned_data.get('title')
            if new_title and new_title != video.title:
                video.update_title(self.user, new_title)

            if project is not None and project != team_video.project:
                team_video.project = project
                team_video.save()
            if (language is not None and
                    language != video.primary_audio_language_code):
                video.primary_audio_language_code = language
                video.save()
            if thumbnail:
                video.s3_thumbnail.save(thumbnail.name, thumbnail)
            elif thumbnail == False:
                video.s3_thumbnail = None
                video.save()

    def message(self):
        msg = ungettext('Video has been edited',
                        '%(count)s videos have been edited',
                        self.count)
        return fmt(msg, count=self.count)

class DeleteVideosForm(VideoManagementForm):
    VERIFY_STRING = _(u'Yes, I want to delete this video')

    name = 'remove'
    label = _('Remove')
    permissions_check = staticmethod(permissions.can_remove_videos)
    css_class = 'cta-reverse'

    DELETE_CHOICES = (
        ('', _('Just remove from team')),
        ('yes', _('Delete entirely')),
    )
    DELETE_HELP_TEXT = (
        ('', _('Remove the video(s) from team into the public area of '
               'Amara.  All existing subtitles will remain on site and '
               'can be edited by any user.')),
        ('yes', mark_safe(_('Permanently delete the video(s) and all associated '
                  'subtitles and subtitle requests from Amara. '
                  '<em>Important: </em> this action is irreversible, so use it '
                  'with care.'))),
    )


    delete = AmaraChoiceField(
        label='', choices=DELETE_CHOICES,
        choice_help_text=DELETE_HELP_TEXT, required=False, initial='',
        widget=AmaraRadioSelect,
    )
    verify = forms.CharField(label=_('Are you sure?'))

    permissions_check = staticmethod(permissions.new_can_remove_videos)

    def setup_fields(self):
        if permissions.can_delete_video_in_team(self.team, self.user):
            self.fields['verify'].help_text = fmt(
                ugettext('Please type: "%(words)s"'),
                words=unicode(self.VERIFY_STRING))
        else:
            del self.fields['delete']
            del self.fields['verify']

    def clean_verify(self):
        verify = self.cleaned_data.get('verify')
        delete = self.cleaned_data.get('delete')
        if delete == 'yes' and verify != unicode(self.VERIFY_STRING):
            raise forms.ValidationError(self.fields['verify'].help_text)

    def perform_submit(self, qs):
        delete = self.cleaned_data.get('delete', False)
        self.public_duplicate_url_errors = 0
        self.other_team_duplicate_url_errors = 0
        self.success_count = 0

        for video in qs:
            team_video = video.teamvideo
            if delete == 'yes':
                team_video.delete()
                video.delete(self.user)
            else:
                try:
                    team_video.remove(self.user)
                except Video.DuplicateUrlError, e:
                    if e.from_prevent_duplicate_public_videos:
                        self.other_team_duplicate_url_errors += 1
                    else:
                        self.public_duplicate_url_errors += 1
                    continue
            self.success_count += 1

    def message(self):
        if self.success_count == 0:
            return None
        if self.cleaned_data.get('delete') == 'yes':
            msg = self.ungettext(
                'Video has been deleted.',
                '%(count)s video has been deleted.',
                '%(count)s videos have been deleted.',
                self.success_count)
        else:
            msg = self.ungettext(
                'Video has been removed.',
                '%(count)s video has been removed.',
                '%(count)s videos have been removed.',
                self.success_count)
        return fmt(msg, count=self.success_count)

    def error_messages(self):
        messages = []
        if self.public_duplicate_url_errors:
            messages.append(fmt(self.ungettext(
                'Video not removed because it already exists in the '
                'public area',
                '%(count)s video not removed because it already exists in the '
                'public area',
                '%(count)s videos not removed because they already exists in '
                'the public area',
                self.public_duplicate_url_errors),
                                count=self.public_duplicate_url_errors))
        if self.other_team_duplicate_url_errors:
            messages.append(fmt(self.ungettext(
                "Video not removed to avoid a conflict with another "
                "team's video policy",
                "%(count) video not removed to avoid a conflict with another "
                "team's video policy",
                "%(count) videso not removed to avoid a conflict with another "
                "team's video policy",
                self.other_team_duplicate_url_errors),
                                count=self.other_team_duplicate_url_errors))
        return messages

class DeleteVideosFormSimple(DeleteVideosForm):
    DELETE_CHOICES = (
        ('', _('Just remove from team')),
        ('yes', _('Delete entirely')),
    )
    DELETE_HELP_TEXT = (
        ('', _('Remove the video(s) from team into the public area of '
               'Amara.  All existing subtitles will remain on site and '
               'can be edited by any user.')),
        ('yes', mark_safe(_('Permanently delete the video(s) and all associated '
                  'subtitles from Amara. '
                  '<em>Important: </em> this action is irreversible, so use it '
                  'with care.'))),
    )


    delete = AmaraChoiceField(
        label='', choices=DELETE_CHOICES,
        choice_help_text=DELETE_HELP_TEXT, required=False, initial='',
        widget=AmaraRadioSelect,
    )

class MoveVideosForm(VideoManagementForm):
    name = 'move'
    label = _('Move')

    new_team = AmaraChoiceField(label=_('New Team'), choices=[])
    project = AmaraChoiceField(label=_('Project'), choices=[],
                               required=False)

    @staticmethod
    def permissions_check(team, user):
        return len(permissions.can_move_videos_to(user, [team])) > 0

    def setup_fields(self):
        dest_teams = permissions.can_move_videos_to(self.user)
        dest_teams.sort(key=lambda t: t.name)
        self.fields['new_team'].choices = [(dest.id, dest.name) for dest in dest_teams]
        self.setup_project_field(dest_teams)

    def setup_project_field(self, dest_teams):
        choices = [ ('', _('None')) ]
        # map team ids to project choices
        self.project_map = {
            team.id: ['']
            for team in dest_teams
        }

        qs = (Project.objects
              .filter(team__in=dest_teams)
              .exclude(name=Project.DEFAULT_NAME))
        for project in qs:
            choices.append((project.id, project.name))
            self.project_map[project.team_id].append(project.id)
        self.fields['project'].choices = choices
        self['project'].field.initial = ''

    def project_map_json(self):
        return json.dumps(self.project_map)

    def clean_project(self):
        try:
            team = self.cleaned_data['new_team']
        except KeyError:
            # No valid team, so we can't validate the project.
            return None

        project_id = self.cleaned_data.get('project', '')

        if project_id == '':
            return team.default_project

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise forms.ValidationError(_("Invalid project"))

        if project.team_id != team.id:
            raise forms.ValidationError(_("Project is not part of team"))
        return project

    def clean_new_team(self):
        if not self.cleaned_data.get('new_team'):
            return None
        return Team.objects.get(id=self.cleaned_data['new_team'])

    def perform_submit(self, qs):
        self.duplicate_url_errors = 0
        self.video_policy_errors = 0
        self.success_count = 0
        for video in qs:
            team_video = video.teamvideo
            try:
                team_video.move_to(self.cleaned_data['new_team'],
                                   self.cleaned_data['project'],
                                   self.user)
            except Video.DuplicateUrlError, e:
                if e.from_prevent_duplicate_public_videos:
                    self.video_policy_errors += 1
                else:
                    self.duplicate_url_errors += 1
            else:
                self.success_count += 1

    def message(self):
        if not self.success_count:
            return None
        new_team = self.cleaned_data['new_team']
        project = self.cleaned_data['project']
        if new_team == self.team:
            if project.is_default_project:
                msg = ungettext(
                    'Video has been removed from project',
                    '%(count)s videos have been removed from projects',
                    self.success_count)
            else:
                msg = ungettext(
                    'Video has been moved to project %(project)s',
                    '%(count)s videos have been moved to project %(project)s',
                    self.success_count)
        else:
            if project.is_default_project:
                msg = ungettext(
                    'Video has been moved to %(team_link)s',
                    '%(count)s videos have been moved to %(team_link)s',
                    self.success_count)
            else:
                msg = ungettext(
                    'Video has been moved to %(team_link)s, '
                    'project %(project)s',
                    '%(count)s videos have been moved to %(team_link)s, '
                    'project %(project)s',
                    self.success_count)
        team_link = '<a href="{}">{}</a>'.format(
            reverse('teams:dashboard', args=(new_team.slug,)),
            new_team)
        return fmt(msg, team_link=team_link, project=project.name,
                   count=self.success_count)

    def error_messages(self):
        """Error message(s) after the form is submitted."""
        messages = []
        if self.duplicate_url_errors:
            messages.append(fmt(
                self.ungettext(
                    "Video already added to %(team)s",
                    "1 video already added to %(team)s",
                    "%(count)s videos already added to %(team)s",
                    self.duplicate_url_errors),
                count=self.duplicate_url_errors,
                team=self.cleaned_data['new_team']))
        if self.video_policy_errors:
            messages.append(fmt(
                self.ungettext(
                    "Video not moved because it would conflict with the "
                    "video policy for %(team)s",
                    "1 video not moved because it would conflict with the "
                    "video policy for %(team)s",
                    "%(count)s videos not moved because they would conflict "
                    "with the video policy for %(team)s",
                    self.video_policy_errors),
                count=self.video_policy_errors,
                team=self.cleaned_data['new_team']))
        return messages
