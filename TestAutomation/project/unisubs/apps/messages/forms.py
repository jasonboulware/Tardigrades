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
from django.utils.translation import ugettext_lazy as _, ugettext

from auth.models import CustomUser as User
from messages.models import Message
from teams.models import Team
from utils.forms import AjaxForm
from utils.translation import get_language_choices

from utils.translation import (
    get_language_choices, get_language_choices_as_dicts, languages_with_labels, get_user_languages_from_request
)

class SendMessageForm(forms.ModelForm, AjaxForm):
    class Meta:
        model = Message
        fields = ('user', 'subject', 'content', 'thread')

    def __init__(self, author, *args, **kwargs):
        self.author = author
        super(SendMessageForm, self).__init__(*args, **kwargs)
        self.fields['user'].widget = forms.HiddenInput()
        self.fields['thread'].widget = forms.HiddenInput()
        self.fields['user'].queryset = User.objects.exclude(pk=author.pk)

    def clean(self):
        if not self.author.is_authenticated():
            raise forms.ValidationError(_(u'You should be authenticated to write messages'))
        return self.cleaned_data

    def save(self, commit=True):
        obj = super(SendMessageForm, self).save(False)
        obj.author = self.author
        obj.message_type = 'M'
        commit and obj.save()
        return obj


class TeamAdminPageMessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ('subject', 'content')

    def send_to_teams(self, team_ids, author):
        subject = self.cleaned_data['subject']
        content = self.cleaned_data['content']
        content = u''.join([content, '\n\n', ugettext('This message is from site administrator.')])
        users = User.objects.filter(teams__in=team_ids).exclude(pk=author.pk)
        message_list = []
        for user in users:
            m = Message(author=author, user=user)
            m.message_type = 'S'
            m.subject = subject
            m.content = content
            message_list.append(m)
        Message.objects.bulk_create(message_list);
        return users.count()


class NewMessageForm(forms.Form):
    team = forms.ModelChoiceField(queryset=Team.objects.none(), required=False)
    user = forms.ModelChoiceField(queryset=User.objects.none(), required=False)
    content = forms.CharField(widget=forms.Textarea)
    subject = forms.CharField(required=False)
    language = forms.ChoiceField(choices=[], required=False)

    class Meta:
        model = Message
        fields = ('user', 'content', 'subject', 'team', 'language')


    def __init__(self, author, *args, **kwargs):
        super(NewMessageForm, self).__init__(*args, **kwargs)

        self.author = author
        self.message_type = 'M'
        self.fields['user'].queryset = User.objects.all()

        # This isn't the fastest way to do this, but it's the simplest, and
        # performance probably won't be an issue here.
        self.fields['team'].queryset = author.messageable_teams()
        self.fields['language'].choices = get_language_choices(with_any=True)
        # For now we'll add all languages in the dropdown, if users
        # want to limit them, we can re-add this:
        # team_languages = set([('','--- Any language ---')])
        # for team in author.messageable_teams():
        #    users = team.members.values_list('user', flat=True)
        #    user_langs = set(UserLanguage.objects.filter(user__in=users).exclude(user=author).values_list('language', flat=True))
        #    team_languages ^= set(languages_with_labels(user_langs).items())
        # self.fields['language'].choices = sorted(list(team_languages), key=lambda pair: pair[1])

    def clean(self):
        cd = self.cleaned_data

        if cd.get('team') and cd.get('user'):
            raise forms.ValidationError(_(
                u'You cannot send a message to a user and a team at the same time.'))

        if not cd.get('team') and not cd.get('user'):
            raise forms.ValidationError(_(u'You must choose a recipient.'))

        return self.cleaned_data

    def clean_content(self):
        content = self.cleaned_data['content']
        if not content.strip():
            raise forms.ValidationError(_(u'This field is required.'))
        return content
