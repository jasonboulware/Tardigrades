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

import json
from django import forms
from django.core import validators
from django.urls import reverse
from django.forms.utils import ErrorDict
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy

from auth.models import CustomUser as User
from teams.models import Team
from externalsites import models
from utils.forms import SubmitButtonField, SubmitButtonWidget
from utils.text import fmt
import videos.tasks
import logging
logger = logging.getLogger("forms")
class AccountForm(forms.ModelForm):
    """Base class for forms on the teams or user profile tab."""

    enabled = forms.BooleanField(required=False)

    def __init__(self, owner, data=None, **kwargs):
        super(AccountForm, self).__init__(data=data,
                                          instance=self.get_account(owner),
                                          **kwargs)
        self.owner = owner
        # set initial to be True if an account already exists
        self.fields['enabled'].initial = (self.instance.pk is not None)

    @classmethod
    def get_account(cls, owner):
        ModelClass = cls._meta.model
        try:
            return ModelClass.objects.for_owner(owner).get()
        except ModelClass.DoesNotExist:
            return None

    def full_clean(self):
        if not self.find_enabled_value():
            self.cleaned_data = {
                'enabled': False,
            }
            self._errors = ErrorDict()
        else:
            return super(AccountForm, self).full_clean()

    def find_enabled_value(self):
        widget = self.fields['enabled'].widget
        return widget.value_from_datadict(self.data, self.files,
                                          self.add_prefix('enabled'))

    def save(self):
        if not self.is_valid():
            raise ValueError("form has errors: %s" % self.errors.as_text())
        if not self.cleaned_data['enabled']:
            self.delete_account()
            return
        account = forms.ModelForm.save(self, commit=False)
        if isinstance(self.owner, Team):
            account.type = models.ExternalAccount.TYPE_TEAM
            account.owner_id = self.owner.id
        elif isinstance(self.owner, User):
            account.type = models.ExternalAccount.TYPE_USER
            account.owner_id = self.owner.id
        else:
            raise TypeError("Invalid owner type: %s" % self.owner)
        account.save()
        return account

    def delete_account(self):
        if self.instance.id is not None:
            self.instance.delete()

class KalturaAccountForm(AccountForm):
    partner_id = forms.IntegerField()

    class Meta:
        model = models.KalturaAccount
        fields = ['partner_id', 'secret']

class BrightcoveCMSAccountForm(AccountForm):
    publisher_id = forms.IntegerField(label=ugettext_lazy("Publisher ID"))
    client_id = forms.CharField(label=ugettext_lazy("Client ID"))
    client_secret = forms.CharField(label=ugettext_lazy("Client Secret"))


    class Meta:
        model = models.BrightcoveCMSAccount
        fields = ['publisher_id', 'client_id', 'client_secret' ]

    def add_error(self, field_name, msg):
        self._errors[field_name] = self.error_class([msg])
        if field_name in self.cleaned_data:
            del self.cleaned_data[field_name]

    def save(self):
        account = AccountForm.save(self)
        if not self.cleaned_data['enabled']:
            return None
        return account

class AddVimeoAccountForm(forms.Form):
    add_button = SubmitButtonField(
        label=ugettext_lazy('Add Vimeo account'),
        required=False,
        widget=SubmitButtonWidget(attrs={'class': 'small'}))

    def __init__(self, owner, data=None, **kwargs):
        super(AddVimeoAccountForm, self).__init__(data=data, **kwargs)
        self.owner = owner

    def save(self):
        pass

    def redirect_path(self):
        if self.cleaned_data['add_button']:
            path = reverse('externalsites:vimeo-add-account')
            if isinstance(self.owner, Team):
                return '%s?team_slug=%s' % (path, self.owner.slug)
            elif isinstance(self.owner, User):
                return '%s?username=%s' % (path, self.owner.username)
            else:
                raise ValueError("Unknown owner type: %s" % self.owner)
        else:
            return None

class AddYoutubeAccountForm(forms.Form):
    add_button = SubmitButtonField(
        label=ugettext_lazy('Add YouTube account'),
        required=False,
        widget=SubmitButtonWidget(attrs={'class': 'small'}))

    def __init__(self, owner, data=None, **kwargs):
        super(AddYoutubeAccountForm, self).__init__(data=data, **kwargs)
        self.owner = owner

    def save(self):
        pass

    def redirect_path(self):
        if self.cleaned_data['add_button']:
            path = reverse('externalsites:youtube-add-account')
            if isinstance(self.owner, Team):
                return '%s?team_slug=%s' % (path, self.owner.slug)
            elif isinstance(self.owner, User):
                return '%s?username=%s' % (path, self.owner.username)
            else:
                raise ValueError("Unknown owner type: %s" % self.owner)
        else:
            return None

class YoutubeAccountForm(forms.Form):
    remove_button = SubmitButtonField(label=ugettext_lazy('Remove account'),
                                      required=False)
    sync_teams = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False)
    import_team = forms.ChoiceField(label='', required=False)
    sync_subtitles = forms.BooleanField(label=ugettext_lazy('Sync subtitles from Amara to YouTube'), required=False)
    fetch_initial_subtitles = forms.BooleanField(label=ugettext_lazy('Fetch initial subtitles from YouTube when videos are submitted to Amara'), required=False)

    def __init__(self, admin_user, account, data=None, **kwargs):
        super(YoutubeAccountForm, self).__init__(data=data, **kwargs)
        self.account = account
        self.admin_user = admin_user
        self.setup_sync_team()
        self.setup_import_team()
        self.setup_account_options()

    def setup_account_options(self):
        self['sync_subtitles'].field.initial = self.account.sync_subtitles
        self['fetch_initial_subtitles'].field.initial = self.account.fetch_initial_subtitles

    def setup_sync_team(self):
        choices = []
        initial = []
        # allow the admin to uncheck any of the current sync teams
        current_sync_teams = list(self.account.sync_teams.get_queryset())
        for team in current_sync_teams:
            choices.append((team.id, team.name))
            initial.append(team.id)
        # allow the admin to check any of the other teams they're an admin for
        exclude_team_ids = [t.id for t in current_sync_teams]
        exclude_team_ids.append(self.account.owner_id)
        member_qs = (self.admin_user.team_members.admins()
                     .exclude(team_id__in=exclude_team_ids)
                     .select_related('team'))
        choices.extend((member.team.id, member.team.name)
                       for member in member_qs if not member.team.deleted)
        self['sync_teams'].field.choices = choices
        self['sync_teams'].field.initial = initial

    def setup_import_team(self):
        # Setup the import team field.  The choices are:
        #   - None to disable import
        #   - Any valid sync team
        #   - The account team it self
        #   - The current import_team
        label_template = _('Import Videos into %(team)s')

        choices = [('', _("Disable Video Import"))]
        choices.append((self.account.team.id,
                        fmt(label_template, team=self.account.team.name)))
        choices.extend(
            (team_id, fmt(label_template, team=team_name))
            for team_id, team_name in self.fields['sync_teams'].choices
        )
        if (self.account.import_team_id and
            self.account.import_team_id not in [c[0] for c in choices]):
            choices.append((self.account.import_team_id,
                            fmt(label_template,
                                team=self.account.import_team.name)))

        self.fields['import_team'].choices = choices
        self.fields['import_team'].initial = self.account.import_team_id

    def save(self):
        if not self.is_valid():
            raise ValueError("Form not valid")
        if self.cleaned_data['remove_button']:
            self.account.delete()
        else:
            self.account.sync_teams = Team.objects.filter(
                id__in=self.cleaned_data['sync_teams']
            )
            if self.cleaned_data['import_team'] == '':
                self.account.import_team = None
            else:
                self.account.import_team_id = self.cleaned_data['import_team']
            self.account.sync_subtitles = self.cleaned_data['sync_subtitles']
            self.account.fetch_initial_subtitles = self.cleaned_data['fetch_initial_subtitles']
            self.account.save()

    def show_sync_teams(self):
        return len(self['sync_teams'].field.choices) > 0

class VimeoAccountForm(forms.Form):
    remove_button = SubmitButtonField(label=ugettext_lazy('Remove account'),
                                      required=False)
    sync_teams = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False)
    sync_subtitles = forms.BooleanField(label=ugettext_lazy('Sync subtitles from Amara to Vimeo'), required=False)
    fetch_initial_subtitles = forms.BooleanField(label=ugettext_lazy('Fetch initial subtitles from Vimeo when videos are submitted to Amara'), required=False)

    def __init__(self, admin_user, account, data=None, **kwargs):
        super(VimeoAccountForm, self).__init__(data=data, **kwargs)
        self.account = account
        self.admin_user = admin_user
        self.setup_sync_team()
        self.setup_account_options()

    def setup_account_options(self):
        self['sync_subtitles'].field.initial = self.account.sync_subtitles
        self['fetch_initial_subtitles'].field.initial = self.account.fetch_initial_subtitles

    def setup_sync_team(self):
        choices = []
        initial = []
        # allow the admin to uncheck any of the current sync teams
        current_sync_teams = list(self.account.sync_teams.all())
        for team in current_sync_teams:
            choices.append((team.id, team.name))
            initial.append(team.id)
        # allow the admin to check any of the other teams they're an admin for
        exclude_team_ids = [t.id for t in current_sync_teams]
        exclude_team_ids.append(self.account.owner_id)
        member_qs = (self.admin_user.team_members.admins()
                     .exclude(team_id__in=exclude_team_ids)
                     .select_related('team'))
        choices.extend((member.team.id, member.team.name)
                       for member in member_qs)
        self['sync_teams'].field.choices = choices
        self['sync_teams'].field.initial = initial

    def save(self):
        if not self.is_valid():
            raise ValueError("Form not valid")
        if self.cleaned_data['remove_button']:
            self.account.delete()
        else:
            self.account.sync_teams = Team.objects.filter(
                id__in=self.cleaned_data['sync_teams']
            )
            self.account.sync_subtitles = self.cleaned_data['sync_subtitles']
            self.account.fetch_initial_subtitles = self.cleaned_data['fetch_initial_subtitles']
            self.account.save()

    def show_sync_teams(self):
        return len(self['sync_teams'].field.choices) > 0

class AccountFormset(dict):
    """Container for multiple account forms.

    For each form in form classes we will instatiate it with a unique prefix
    to avoid name collisions.
    """
    def __init__(self, admin_user, owner, data=None):
        super(AccountFormset, self).__init__()
        self.admin_user = admin_user
        self.data = data
        self.make_forms(owner)

    def make_forms(self, owner):
        self.make_form('kaltura', KalturaAccountForm, owner)
        self.make_form('brightcovecms', BrightcoveCMSAccountForm, owner)
        self.make_form('add_youtube', AddYoutubeAccountForm, owner)
        self.make_form('add_vimeo', AddVimeoAccountForm, owner)
        for account in models.YouTubeAccount.objects.for_owner(owner):
            name = 'youtube_%s' % account.id
            self.make_form(name, YoutubeAccountForm, self.admin_user, account)
        for account in models.VimeoSyncAccount.objects.for_owner(owner):
            name = 'vimeo_%s' % account.id
            self.make_form(name, VimeoAccountForm, self.admin_user, account)

    def make_form(self, name, form_class, *args, **kwargs):
        kwargs['prefix'] = name.replace('_', '-')
        kwargs['data'] = self.data
        self[name] = form_class(*args, **kwargs)

    def youtube_forms(self):
        return [form for name, form in self.items()
                if name.startswith('youtube_')]

    def vimeo_forms(self):
        return [form for name, form in self.items()
                if name.startswith('vimeo_')]

    def is_valid(self):
        return all(form.is_valid() for form in self.values())

    def save(self):
        for form in self.values():
            form.save()

    def redirect_path(self):
        for form in self.values():
            if hasattr(form, 'redirect_path'):
                redirect_path = form.redirect_path()
                if redirect_path is not None:
                    return redirect_path

class ResyncForm(forms.Form):
    def __init__(self, *args, **kwargs):
        sync_items = kwargs.pop('sync_items')
        super(ResyncForm, self).__init__(*args, **kwargs)
        for i, sync_item in enumerate(sync_items):
            item_id = sync_item.pop('id')
            self.fields['custom_%s' % item_id] = forms.BooleanField(label=json.dumps(sync_item), required = False, widget=forms.CheckboxInput(attrs={'class': 'bulkable'}))
    def sync_items(self):
        for name, value in self.cleaned_data.items():
            if name.startswith('custom_'):
                yield (name.replace('custom_','',1), value)
