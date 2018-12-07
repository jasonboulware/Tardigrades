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

from django import forms
from django.core.validators import EMPTY_VALUES
from django.utils.translation import ugettext_lazy as _

from auth.models import CustomUser as User
from teams.models import Project, Invite
from utils.text import fmt
from ui.forms import AmaraChoiceField, AmaraMultipleChoiceField, widgets, MultipleAutoCompleteField

class ProjectFieldMixin(object):
    def __init__(self, *args, **kwargs):
        self.null_label = kwargs.pop('null_label', _('Any'))
        if 'label' not in kwargs:
            kwargs['label'] = _("Project")
        self.futureui = kwargs.pop('futureui', False)
        super(ProjectFieldMixin, self).__init__(*args, **kwargs)
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
            if not isinstance(self, MultipleProjectField):
                choices.append(('none', _('No project')))
            if source_teams and len(source_teams) > 1:
                choices.extend((p.id, p.team.name + ' - ' + p.name) for p in projects)
            else:
                choices.extend((p.id, p.name) for p in projects)
            self.choices = choices

            if isinstance(self, MultipleProjectField):
                self.set_select_data('placeholder', _('Select project'))

            if initial is None:
                initial = self.default_initial(choices)
            self.initial = initial
            if self.futureui:
                self.setup_widget()   
        else:
            self.enabled = False

    def default_initial(self, choices):
        return choices[0][0]

    def setup_widget(self):
        if len(self.choices) < 7:
            self.widget = AmaraRadioSelect()
            self.widget.attrs.update(self.widget_attrs(self.widget))
            self._setup_widget_choices()   
        

    def prepare_value(self, value):
        return value.id if isinstance(value, Project) else value

    def clean(self, value):
        if not self.enabled or self.value_is_empty(value) or not self.team:
            return None
        if value == 'none':
            if getattr(self, 'source_teams', None):
                projects = [p for p in Project.objects.filter(team__in=self.source_teams)
                           if p.slug == Project.DEFAULT_NAME]
            else:
                projects = Project.objects.get(team=self.team, slug=Project.DEFAULT_NAME)
        elif isinstance(value, list):
            projects = Project.objects.filter(id__in=value)
        else:
            projects = Project.objects.get(id=value)

        return projects

    def value_is_empty(self, value):
        if isinstance(value, list):
            return all(v in EMPTY_VALUES for v in value)
        else:
            return value in EMPTY_VALUES

class MultipleProjectField(ProjectFieldMixin, AmaraMultipleChoiceField):
    widget = widgets.AmaraProjectSelectMultiple

    def default_initial(self, choices):
        return []

class TeamMemberRoleSelect(AmaraChoiceField):
    def __init__(self, *args, **kwargs):
        super(TeamMemberRoleSelect, self).__init__(*args, **kwargs)
        widget_classes = self.widget.attrs['class']
        self.widget.attrs['class'] = widget_classes + " teamMemberRoleSelect"

class TeamMemberInput(forms.CharField):
    """Input to select team members.  """

    def set_team(self, team):
        """Set the team to find members for.

        This must be called during form initialization
        """
        self.team = team

    def clean(self, value):
        try:
            team = self.team
        except AttributeError:
            raise AssertionError("team not set")

        try:
            members_qs = team.members.all().select_related('user')
            return members_qs.get(user__username=value)
        except TeamMember.DoesNotExist:
            raise forms.ValidationError(fmt(
                _(u'%(username)s is not a member of the team'),
                username=value))

'''
Don't forget to call this class's set_ajax_autocomplete_url(url)
and set_ajax_multiple_username_url(url) methods

See teams.forms:InviteForm for an example usage of this class
set_ajax_autocomplete_url() and set_ajax_multiple_username_url()
are called in InviteForm's __init__ method
'''
class MultipleUsernameInviteField(MultipleAutoCompleteField):
    '''
    Override MultipleAutoCompleteField's validation since it's not useful
    Instead do validation at the form using this field (e.g. teams.forms.InviteForm)
    '''
    def clean(self, values):
        return values

    def set_initial_selections(self, usernames):
        qs = User.objects.filter(username__in=usernames)
        data = [ user.get_select2_format() for user in qs ]
        self._set_initial_selections(data)

    def set_ajax_multiple_username_url(self, url):
        self.set_select_data('ajax-username-multiple', url)
