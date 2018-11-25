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
from datetime import datetime

from django import forms
from django.contrib import admin
from django.contrib.admin import widgets
from django.contrib.admin.views.main import ChangeList
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from models import CustomUser, Announcement

class UserChangeList(ChangeList):
    def get_ordering(self, request, queryset):
        # The default ChangeList code adds CustomUser.id to the list of
        # ordering fields to make things deterministic.  However this kills
        # performance because the ORDER BY clause includes columns from 2
        # different tables (auth_user.username, auth_customuser.id).
        #
        # Also, sorting by any column other than user also kills performance
        # since our user table is quite large at this point.
        #
        # So we just override everything and force the sort to be username.
        # Username is a unique key so the sort will be fast and deterministic.
        return ['username']

class CustomUserForm(forms.ModelForm):
    password = forms.CharField(
        label=_("Raw Password"), required=False,
        widget=forms.TextInput(attrs={
            'readonly': True,
            'style': 'width: 500px',
        }))
    password1 = forms.CharField(label=_("Password"), required=False,
                                widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password confirmation"),
                                required=False, widget=forms.PasswordInput)

    def clean(self):
        data = super(CustomUserForm, self).clean()
        if ((data.get('password1') or data.get('password2')) and
            data.get('password1') != data.get('password2')):
            raise ValidationError("Passwords don't match")
        return data

    def save(self, commit=True):
        user = super(CustomUserForm, self).save(commit=False)
        if self.cleaned_data.get('password1'):
            user.set_password(self.cleaned_data.get('password1'))
        if commit:
            user.save()
        return user


    class Meta:
        model = CustomUser
        fields = [
            'username', 'password', 'password1', 'password2', 'first_name',
            'last_name', 'email', 'username_old', 'is_active', 'is_staff', 'is_superuser',
            'groups', 'user_permissions', 'last_login', 'date_joined',
            'is_partner', 'allow_3rd_party_login', 'created_by',
            'last_hidden_message_id',
        ]

class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'username_old', 'is_staff',
                    'is_superuser', 'last_ip', 'partner', 'secure_id')
    search_fields = ('username', 'username_old', 'first_name', 'last_name', 'email', 'id')
    raw_id_fields = ('created_by',)
    form = CustomUserForm

    fieldsets = (
        (None, {'fields': ('username', 'password', 'password1', 'password2')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {'fields': ('username_old', 'is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Amara'), {'fields': ('is_partner', 'allow_3rd_party_login',
                                 'created_by', 'last_hidden_message_id')}),
    )

    actions = ['remove_staff_access']

    def get_changelist(self, request, **kwargs):
        return UserChangeList

    def remove_staff_access(self, request, queryset):
        queryset.update(is_staff=False, is_superuser=False)
    remove_staff_access.short_description = _(u'Remove Staff Access')

class AnnouncementAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.CharField: {'widget': widgets.AdminTextareaWidget}
    }
    list_display = ('content', 'created', 'visible')
    actions = ['make_hidden']

    def get_form(self, request, obj=None, **kwargs):
        form = super(AnnouncementAdmin, self).get_form(request, obj=None, **kwargs)

        default_help_text = form.base_fields['created'].help_text
        now = datetime.now()
        form.base_fields['created'].help_text = default_help_text+\
            u'</br>Current server time is %s. Value is saved without timezone converting.' % now.strftime('%m/%d/%Y %H:%M:%S')
        return form

    def visible(self, obj):
        return not obj.hidden
    visible.boolean = True

    def make_hidden(self, request, queryset):
        Announcement.clear_cache()
        queryset.update(hidden=True)
    make_hidden.short_description = _(u'Hide')

admin.site.register(Announcement, AnnouncementAdmin)
admin.site.register(CustomUser, CustomUserAdmin)

import django.contrib.auth.admin
admin.site.unregister(User)
