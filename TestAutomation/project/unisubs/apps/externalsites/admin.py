# -*- coding: utf-8 -*-
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
from django.contrib import admin
from django.contrib import messages
from django.utils.translation import ugettext as _

from externalsites import models
from externalsites import tasks
from teams.models import Team

class SyncHistoryAdmin(admin.ModelAdmin):
    fields = (
        'video_url',
        'account_type',
        'account_id',
        'language',
        'datetime',
        'version',
        'result',
        'details',
        'retry',
        'is_latest',
    )
    readonly_fields = (
        'video_url',
        'account_type',
        'account_id',
        'language',
        'datetime',
        'version',
    )
    list_display = (
        'account',
        'video_url',
        'language',
        'retry',
        'datetime',
        'is_latest',
    )
    list_filter = (
        'result',
        'retry',
    )
    list_select_related = True

    class Meta:
        model = models.SyncHistory

    def account(self, sh):
        return sh.get_account()

    def has_add_permission(self, request):
        return False

class OpenIDConnectLinkAdmin(admin.ModelAdmin):
    search_fields = (
        'user__username',
    )
    raw_id_fields = (
        'user',
    )
    readonly_fields = [ 'last_login' ]

class YoutubeAccountForm(forms.ModelForm):
    resync_subtitles = forms.BooleanField(required=False)
    sync_teams = forms.ModelMultipleChoiceField(Team.objects.all(),
                                                required=False)

    def save(self, commit=True):
        account = super(YoutubeAccountForm, self).save(commit=commit)
        if self.cleaned_data.get('resync_subtitles'):
            tasks.update_all_subtitles.delay(account.account_type, account.id)
        return account

    class Meta:
        model = models.YouTubeAccount
        fields = (
            'type',
            'owner_id',
            'channel_id',
            'username',
            'oauth_refresh_token',
            'sync_teams',
            'import_team',
            'resync_subtitles',
            'enable_language_mapping',
            'sync_subtitles',
            'fetch_initial_subtitles',
            'sync_metadata',
        )

class YouTubeAccountAdmin(admin.ModelAdmin):
    form = YoutubeAccountForm

    def save_model(self, request, obj, form, change):
        account = super(YouTubeAccountAdmin, self).save_model(
            request, obj, form, change)
        if form.cleaned_data.get('resync_subtitles'):
            messages.info(request, _(u'Resyncing subtitles'))
        return account

class VimeoAccountForm(forms.ModelForm):
    resync_subtitles = forms.BooleanField(required=False)
    sync_teams = forms.ModelMultipleChoiceField(Team.objects.all(),
                                                required=False)

    def save(self, commit=True):
        account = super(VimeoAccountForm, self).save(commit=commit)
        if self.cleaned_data.get('resync_subtitles'):
            tasks.update_all_subtitles.delay(account.account_type, account.id)
        return account

    class Meta:
        model = models.VimeoSyncAccount
        fields = (
            'type',
            'owner_id',
            'username',
            'access_token',
            'sync_teams',
            'resync_subtitles',
            'sync_subtitles',
            'fetch_initial_subtitles',
        )

class VimeoAccountAdmin(admin.ModelAdmin):
    form = VimeoAccountForm

    def save_model(self, request, obj, form, change):
        account = super(VimeoAccountAdmin, self).save_model(
            request, obj, form, change)
        if form.cleaned_data.get('resync_subtitles'):
            messages.info(request, _(u'Resyncing subtitles'))
        return account

admin.site.register(models.KalturaAccount)
admin.site.register(models.BrightcoveCMSAccount)
admin.site.register(models.YouTubeAccount, YouTubeAccountAdmin)
admin.site.register(models.VimeoSyncAccount, VimeoAccountAdmin)
admin.site.register(models.SyncedSubtitleVersion)
admin.site.register(models.SyncHistory, SyncHistoryAdmin)
admin.site.register(models.OpenIDConnectLink, OpenIDConnectLinkAdmin)
