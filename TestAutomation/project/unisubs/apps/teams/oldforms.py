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

import logging

from django import forms
from django.core.validators import EMPTY_VALUES
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext

from activity.models import ActivityRecord
from teams.behaviors import get_main_project
from teams.models import (
    Team, TeamVideo, Project, Workflow, 
)
from utils.translation import get_language_choices
from videos.forms import VideoURLField
from videos.models import Video
from ui.forms import LanguageField as NewLanguageField
from ui.forms import AmaraChoiceField

logger = logging.getLogger(__name__)

class DeleteLanguageVerifyField(forms.CharField):
    def __init__(self):
        help_text=_('Type "Yes I want to delete this language" if you are '
                    'sure you wish to continue')
        forms.CharField.__init__(self, label=_(u'Are you sure?'),
                                 help_text=help_text)

    def clean(self, value):
        # check text against a translated version of the confirmation string,
        # so when help_text gets translated things still work.
        if value != _(u'Yes I want to delete this language'):
            raise forms.ValidationError(_(u"Confirmation text doesn't match"))

class DeleteLanguageForm(forms.Form):
    verify_text = DeleteLanguageVerifyField()

    def __init__(self, user, team, language, *args, **kwargs):
        super(DeleteLanguageForm, self).__init__(*args, **kwargs)

        self.user = user
        self.team = team
        self.language = language

        # generate boolean fields for deleting languages (rather than forking
        # them).
        for sublanguage in self.language.get_dependent_subtitle_languages():
            key = self.key_for_sublanguage_delete(sublanguage)
            label = sublanguage.get_language_code_display()
            field = forms.BooleanField(label=label, required=False)
            field.widget.attrs['class'] = 'checkbox'
            self.fields[key] = field

    def clean(self):
        team_video = self.language.video.get_team_video()

        if not team_video:
            raise forms.ValidationError(_(
                u"These subtitles are not under a team's control."))

        workflow = self.language.video.get_workflow()
        if not workflow.user_can_delete_subtitles(self.user,
                                                  self.language.language_code):
            raise forms.ValidationError(_(
                u'You do not have permission to delete this language.'))

        return self.cleaned_data

    def key_for_sublanguage_delete(self, sublanguage):
        return 'delete_' + sublanguage.language_code

    def sublanguage_fields(self):
        return [self[key] for key in self.fields.keys()
                if key.startswith('delete_')]

    def languages_to_fork(self):
        assert self.is_bound
        rv = []
        for sublanguage in self.language.get_dependent_subtitle_languages():
            key = self.key_for_sublanguage_delete(sublanguage)
            if not self.cleaned_data.get(key):
                rv.append(sublanguage)
        return rv

class ProjectField(AmaraChoiceField):
    def __init__(self, *args, **kwargs):
        self.null_label = kwargs.pop('null_label', _('Any'))
        if 'label' not in kwargs:
            kwargs['label'] = _("Project")
        super(ProjectField, self).__init__(*args, **kwargs)
        self.enabled = True

    def setup(self, team, promote_main_project=False, initial=None):
        self.team = team
        projects = list(Project.objects.for_team(team))
        if projects:
            if promote_main_project:
                main_project = behaviors.get_main_project(team)
                if main_project:
                    projects.remove(main_project)
                    projects.insert(0, main_project)
                    if initial is None:
                        initial = main_project.slug
            choices = []
            if not self.required:
                choices.append(('', self.null_label))
            choices.append(('none', _('No project')))
            choices.extend((p.id, p.name) for p in projects)
            self.choices = choices
            if initial is None:
                initial = choices[0][0]
            self.initial = initial
        else:
            self.enabled = False

    def prepare_value(self, value):
        return value.id if isinstance(value, Project) else value

    def clean(self, value):
        if not self.enabled or value in EMPTY_VALUES:
            return None
        if value == 'none':
            return Project.objects.get(team=self.team, slug=Project.DEFAULT_NAME)
        else:
            return Project.objects.get(id=value)



class AddTeamVideoForm(forms.ModelForm):
    language = NewLanguageField(label=_(u'Video language'),
                                required=False,
                                options='null popular all',
                                help_text=_(u'It will be saved only if video does not exist in our database.'))

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
            msg = ugettext('This video was already added to your team')
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

class OldActivityFiltersForm(forms.Form):
    SORT_CHOICES = [
        ('-created', _('date, newest')),
        ('created', _('date, oldest')),
    ]
    type = forms.ChoiceField(
        label=_('Activity Type'), required=False,
        choices=[])
    video_language = forms.ChoiceField(
        label=_('Video Language'), required=False,
        choices=[])
    subtitle_language = forms.ChoiceField(
        label=_('Subtitle Language'), required=False,
        choices=[])
    sort = forms.ChoiceField(
        label=_('Sorted by'), required=True,
        choices=SORT_CHOICES)

    def __init__(self, team, get_data):
        super(OldActivityFiltersForm, self).__init__(
                  data=self.calc_data(get_data))
        self.team = team
        self.fields['type'].choices = self.calc_activity_choices()
        language_choices = [
            ('', ('Any language')),
        ]
        language_choices.extend(get_language_choices(flat=True))
        self.fields['video_language'].choices = language_choices
        self.fields['subtitle_language'].choices = language_choices

    def calc_activity_choices(self):
        choices = [
            ('', _('Any type')),
        ]
        choice_map = dict(ActivityRecord.active_type_choices())
        choices.extend(
            (value, choice_map[value])
            for value in self.team.new_workflow.activity_type_filter_options()
        )
        return choices

    def calc_data(self, get_data):
        field_names = set(['type', 'video_language', 'subtitle_language',
                           'sort'])
        data = {
            key: value
            for (key, value) in get_data.items()
            if key in field_names
        }
        return data if data else None

    def get_queryset(self):
        qs = ActivityRecord.objects.for_team(self.team)
        if not (self.is_bound and self.is_valid()):
            return qs
        type = self.cleaned_data.get('type')
        subtitle_language = self.cleaned_data.get('subtitle_language')
        video_language = self.cleaned_data.get('video_language')
        sort = self.cleaned_data.get('sort', '-created')
        if type:
            qs = qs.filter(type=type)
        if subtitle_language:
            qs = qs.filter(language_code=subtitle_language)
        if video_language:
            qs = qs.filter(video_language_code=video_language)
        return qs.order_by(sort)
