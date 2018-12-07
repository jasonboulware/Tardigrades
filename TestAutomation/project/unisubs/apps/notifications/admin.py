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

from django import forms
from django.contrib import admin

from notifications import handlers
from notifications.models import TeamNotificationSettings, TeamNotification

class ExtraTeamsInline(admin.TabularInline):
    model = TeamNotificationSettings.extra_teams.through
    verbose_name_plural = 'Extra teams to notify:'

class TeamNotificationSettingsForm(forms.ModelForm):
    type = forms.ChoiceField(required=True)

    def __init__(self, *args, **kwargs):
        super(TeamNotificationSettingsForm, self).__init__(*args, **kwargs)
        self.fields['type'].choices = handlers.get_type_choices()

    class Meta:
        model = TeamNotificationSettings
        fields = ['team', 'type', 'url', 'auth_username', 'auth_password',
                  'header1', 'header2', 'header3',]

class TeamNotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ('team', 'type', 'url',)
    form = TeamNotificationSettingsForm
    inlines = [
        ExtraTeamsInline,
    ]

class TeamNotificationAdmin(admin.ModelAdmin):
    list_display = ('team', 'number', 'url', 'timestamp', 'error_message')
    ordering = ('team', '-number')


admin.site.register(TeamNotificationSettings, TeamNotificationSettingsAdmin)
admin.site.register(TeamNotification, TeamNotificationAdmin)
