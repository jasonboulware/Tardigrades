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
from django.db.models import Q
from django.utils.translation import ugettext as _, ugettext_lazy

from auth.models import CustomUser as User
from teams.models import Team
from externalsites import models
from ui.forms import SearchField, ContentHeaderSearchBar, AmaraChoiceField

import logging
logger = logging.getLogger("forms")

class AccountForm(forms.ModelForm):
    def __init__(self, owner, data=None, **kwargs):
        super(AccountForm, self).__init__(data=data,
                                          instance=self.get_account(owner),
                                          **kwargs)
        self.owner = owner

    @classmethod
    def get_account(cls, owner):
        ModelClass = cls._meta.model
        try:
            return ModelClass.objects.for_owner(owner).get()
        except ModelClass.DoesNotExist:
            return None

    def save(self):
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

    @property
    def has_existing_account(self):
        return self.instance.pk is not None

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

class RemoveAccountForm(forms.Form):
    def __init__(self, account=None, data=None, **kwargs):
        self.account = account

    def save(self):
        self.account.delete()

    def is_valid(self):
        return not self.account is None

class AccountFiltersForm(forms.Form):
    q = SearchField(label=_('Search'), required=False,
                    widget=ContentHeaderSearchBar)

    def __init__(self, owner, get_data=None):
        super(AccountFiltersForm, self).__init__(get_data)
        self.owner = owner

    def youtube_accounts(self, qs):
        if self.is_bound and self.is_valid():
            q = self.cleaned_data.get('q', '')
            qs = qs.filter(Q(channel_id__icontains=q) | Q(username__icontains=q))
        return qs

    def vimeo_accounts(self, qs):
        if self.is_bound and self.is_valid():
            q = self.cleaned_data.get('q', '')
            qs = qs.filter(username__icontains=q)
        return qs

    def kaltura_accounts(self, qs):
        if self.is_bound and self.is_valid():
            q = self.cleaned_data.get('q', '')
            qs = qs.filter(partner_id__icontains=q)
        return qs

    def brightcove_accounts(self, qs):
        if self.is_bound and self.is_valid():
            q = self.cleaned_data.get('q', '')
            qs = qs.filter(Q(publisher_id__icontains=q) | Q(client_id__icontains=q))
        return qs

class SyncHistoryFiltersForm(forms.Form):
    q2 = SearchField(label=_('Search'), required=False,
                    widget=ContentHeaderSearchBar)

    result = AmaraChoiceField(label=_('Select export result'), choices=[
            ('any', _('Any')),
            ('S', _('Success')),
            ('E', _('Error')),
        ], filter=True, required=False, initial='any')

    # this is quite different from how we usually process search queries
    # since we are not actually dealing with a queryset result
    def update_results(self, sync_histories):
        ret_val = []
        ret_val2 = []
        if self.is_bound and self.is_valid():
            q = self.cleaned_data.get('q2', '')
            if q:
                q = q.lower()
                for i in sync_histories:
                    if q in i.video_url.video.title.lower():
                        ret_val.append(i)
            else:
                ret_val = sync_histories

            q_result = self.cleaned_data.get('result', 'any')
            if q_result and q_result != 'any':
                for i in ret_val:
                    if i.result == q_result:
                        ret_val2.append(i)
            else:
                ret_val2 = ret_val

            return ret_val2
        else:
            return sync_histories
