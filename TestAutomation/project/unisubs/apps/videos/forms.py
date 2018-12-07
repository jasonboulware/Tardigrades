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
import babelsubs
import chardet
import re
from datetime import datetime

from django import forms
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.urls import reverse
from django.core.validators import EMPTY_VALUES
from django.db.models import Q
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode, DjangoUnicodeDecodeError
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext

from videos.feed_parser import FeedParser
from videos.models import Video, VideoFeed, VideoUrl
from videos.permissions import can_user_edit_video_urls
from teams.permissions import can_create_and_edit_subtitles, can_edit_videos
from teams.models import Team
from videos.tasks import import_videos_from_feed
from videos.types import video_type_registrar, VideoTypeError
from ui.forms import AmaraChoiceField
from utils.forms import AjaxForm, EmailListField, UsernameListField, StripRegexField, FeedURLField
from utils import http
from utils.text import fmt
from utils.translation import get_language_choices, get_user_languages_from_request

KB_SIZELIMIT = 512

import logging
logger = logging.getLogger("videos-forms")

def language_choices_with_empty():
    choices = [
        ('', _('--Select language--'))
    ]
    choices.extend(get_language_choices())
    return choices

class VideoDurationField(forms.ChoiceField):
    # Duration choices in the form of (min, max, label)
    DURATION_CHOICE_DATA = [
        (None, 6, _('< 6 min')),
        (6, 12, _('6-12 min')),
        (12, 18, _('12-18 min')),
        (18, 30, _('18-30  min')),
        (30, None, _('> 30 min')),
    ]
    DURATION_CHOICES = [ ('', _('Any length')) ] + [
        (str(i+1), option[2])
        for i, option in enumerate(DURATION_CHOICE_DATA)
    ]
    def __init__(self, *args, **kwargs):
        if 'choices' not in kwargs:
            kwargs['choices'] = self.DURATION_CHOICES
        if 'initial' not in kwargs:
            kwargs['initial'] = ''
        if 'label' not in kwargs:
            kwargs['label'] = _("Video length")
        super(VideoDurationField, self).__init__(*args, **kwargs)

    @classmethod
    def filter(cls, qs, value):
        return qs.filter(**cls.filter_data(value))

    @classmethod
    def filter_data(cls, value):
        filter_data = {}
        if value in EMPTY_VALUES:
            return filter_data
        try:
            min, max, label = cls.DURATION_CHOICE_DATA[int(value)-1]
        except StandardError:
            return filter_data
        if min is not None:
            filter_data['duration__gte'] = min * 60
        if max is not None:
            filter_data['duration__lt'] = max * 60
        return filter_data

class VideoURLField(forms.URLField):
    """Field for inputting URLs for videos.

    This field checks that we can lookup a VideoType for the URL.  If
    successful, we return the VideoType as the cleaned data.
    """
    def clean(self, video_url):
        if not video_url:
            if self.required:
                raise forms.ValidationError(self.error_messages['required'])
            return None
        try:
            video_type = video_type_registrar.video_type_for_url(video_url)
        except VideoTypeError, e:
            raise forms.ValidationError(e)
        if not video_type:
            contact_link = fmt(
                _('<a href="mailto:%(email)s">Contact us</a>'),
                email=settings.FEEDBACK_EMAIL)
            for d in video_type_registrar.domains:
                if d in video_url:
                    raise forms.ValidationError(mark_safe(fmt(
                        _(u"Please try again with a link to a video page.  "
                          "%(contact_link)s if there's a problem."),
                        contact_link=contact_link)))

            raise forms.ValidationError(mark_safe(fmt(
                _(u"You must link to a video on a compatible site "
                  "(like YouTube) or directly to a video file that works "
                  "with HTML5 browsers. For example: "
                  "http://mysite.com/myvideo.ogg or "
                  "http://mysite.com/myipadvideo.m4v "
                  "%(contact_link)s if there's a problem"),
                contact_link=contact_link)))

        return video_type

class CreateVideoUrlForm(forms.Form):
    url = VideoURLField()
    video = forms.ModelChoiceField(queryset=Video.objects.all(),
                                   widget=forms.HiddenInput)

    def __init__(self, user, *args, **kwargs):
        super(CreateVideoUrlForm, self).__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        data = super(CreateVideoUrlForm, self).clean()
        video = data.get('video')
        if video and not can_user_edit_video_urls(video, self.user):
            raise forms.ValidationError(_('You have not permission add video URL for this video'))

        if 'url' in self.cleaned_data:
            self.create_video_url()
        return self.cleaned_data

    def create_video_url(self):
        """Create our VideoUrl object.

        We do this the last part of the clean() method.
        """

        try:
            self.video_url = self.cleaned_data['video'].add_url(
                self.cleaned_data['url'],
                self.user)
        except Video.DuplicateUrlError, e:
            raise forms.ValidationError(self.already_added_message(e.video))

    def already_added_message(self, video):
        if video == self.cleaned_data.get('video'):
            return _('Video URL already added to this video')

        link = '<a href="{}">{}</a>'.format(
            video.get_absolute_url(), ugettext('view video'))
        return mark_safe(fmt(
            _('Video URL already added to a different video (%(link)s)'),
            link=link))

    def save(self):
        return self.video_url

    def get_errors(self):
        output = {}
        for key, value in self.errors.items():
            output[key] = '/n'.join([force_unicode(i) for i in value])
        return output

class NewCreateVideoUrlForm(forms.Form):
    url = VideoURLField(required=True)

    def __init__(self, video, user, *args, **kwargs):
        super(NewCreateVideoUrlForm, self).__init__(*args, **kwargs)
        self.user = user
        self.video = video

    def clean(self):
        data = super(NewCreateVideoUrlForm, self).clean()
        if self.cleaned_data.get('url'):
            self.create_video_url()
        return self.cleaned_data

    def create_video_url(self):
        """Create our VideoUrl object.

        We do this the last part of the clean() method.
        """
        try:
            self.video_url = self.video.add_url( self.cleaned_data['url'],
                self.user)
        except Video.DuplicateUrlError, e:
            self._errors['url'] = self.error_class([
                self.already_added_message(e.video)
            ])

    def already_added_message(self, video):
        if video == self.video:
            return _('Video URL already added to this video')

        link = '<a href="{}">{}</a>'.format(
            video.get_absolute_url(), ugettext('view video'))
        return mark_safe(fmt(
            _('Video URL already added to a different video (%(link)s)'),
            link=link))

    def save(self):
        return self.video_url

class VideoForm(forms.Form):
    video_url = VideoURLField(
        help_text=_('Acceptable formats include: Vimeo, YouTube, '
                    'MP4, WebM, FLV, OGG, and MP3'))

    def __init__(self, user=None, *args, **kwargs):
        if user and not user.is_authenticated():
            user = None
        self.user = user
        super(VideoForm, self).__init__(*args, **kwargs)

    def clean(self):
        if self._errors:
            return self.cleaned_data

        # Try to create the video and see if any errors happen
        video_url = self.cleaned_data['video_url']
        try:
            self.video, video_url = Video.add(
                self.cleaned_data['video_url'], self.user)
            self.created = True
        except Video.DuplicateUrlError, e:
            self.video = e.video
            self.created = False
        return self.cleaned_data

class AddFromFeedForm(forms.Form, AjaxForm):
    feed_url = FeedURLField(required=False, help_text=_(u'We support: rss 2.0 media feeds including Vimeo, Dailymotion, and more.'))

    def __init__(self, user, *args, **kwargs):
        if not user.is_authenticated():
            user = None
        self.user = user
        super(AddFromFeedForm, self).__init__(*args, **kwargs)

        self.video_limit_routreach = False
        self.urls = []

    def clean_feed_url(self):
        url = self.cleaned_data.get('feed_url', '')

        if url:
            self.parse_feed_url(url)

        return url

    def parse_feed_url(self, url):
        feed_parser = FeedParser(url)

        if not hasattr(feed_parser.feed, 'version') or not feed_parser.feed.version:
            raise forms.ValidationError(_(u'Sorry, we could not find a valid feed at the URL you provided. Please check the URL and try again.'))
        if url in self.urls:
            raise forms.ValidationError(fmt(
                _(u"Duplicate feed URL in form: %(url)s"),
                url=url))
        if VideoFeed.objects.filter(url=url).exists():
            raise forms.ValidationError(fmt(
                _(u'Feed for %(url)s already exists'),
                url=url))

        self.urls.append(url)

    def success_message(self):
        return _(u"The videos are being added in the background. "
                 u"If you are logged in, you will receive a message when it's done")

    def save(self):
        for url in self.urls:
            feed = self.make_feed(url)
            import_videos_from_feed.delay(feed.id)

    def make_feed(self, url):
        return VideoFeed.objects.create(user=self.user, url=url)

class ChangeVideoOriginalLanguageForm(forms.Form):
    language_code = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.fields['language_code'].choices = language_choices_with_empty()

class CreateSubtitlesFormBase(forms.Form):
    """Base class for forms to create new subtitle languages."""
    subtitle_language_code = forms.ChoiceField(label=_('Subtitle into:'))
    primary_audio_language_code = forms.ChoiceField(
                label=_('This video is in:'),
                help_text=_('Please double check the primary spoken '
                            'language. This step cannot be undone.'))

    def __init__(self, request, data=None):
        super(CreateSubtitlesFormBase, self).__init__(data=data)
        self.request = request
        self.user = request.user
        self.setup_subtitle_language_code()
        self.fields['primary_audio_language_code'].choices = language_choices_with_empty()

    def setup_subtitle_language_code(self):
        if self.user.is_authenticated():
            user_langs = self.user.get_languages()
        else:
            user_langs = get_user_languages_from_request(self.request)
        if not user_langs:
            user_langs = ['en']
        def sort_key(choice):
            code, label = choice
            if code in user_langs:
                return user_langs.index(code)
            else:
                return len(user_langs)
        field = self.fields['subtitle_language_code']
        field.choices = sorted(self.get_language_choices(), key=sort_key)

    def get_language_choices(self):
        return get_language_choices()

    def set_primary_audio_language(self):
        # Sometimes we are passed in a cached video, which can't be saved.
        # Make sure we have one from the DB.
        video = Video.objects.get(pk=self.get_video().pk)
        lang = self.cleaned_data['primary_audio_language_code']
        video.primary_audio_language_code = lang
        video.save()

    def editor_url(self):
        return reverse('subtitles:subtitle-editor', kwargs={
            'video_id': self.get_video().video_id,
            'language_code': self.cleaned_data['subtitle_language_code'],
        })

    def handle_post(self):
        self.set_primary_audio_language()
        return redirect(self.editor_url())

    def get_video(self):
        """Get the video that the user wants to create subtiltes for."""
        raise NotImplementedError()

    def clean(self):
        cleaned_data = super(CreateSubtitlesFormBase, self).clean()
        team_video = self.get_video().get_team_video()
        language_code = cleaned_data.get('subtitle_language_code')
        if (team_video is not None and
            not can_create_and_edit_subtitles(self.user, team_video,
                                              language_code)):
            raise forms.ValidationError("You don't have permissions to "
                                        "edit that video")
        return cleaned_data

class CreateSubtitlesForm(CreateSubtitlesFormBase):
    """Form to create subtitles for pages that display a single video.

    This form is generally put in a modal dialog.  See
    the video page for an example.
    """

    subtitle_language_code = forms.ChoiceField(label=_('Subtitle into:'))

    def __init__(self, request, video, data=None):
        self.video = video
        super(CreateSubtitlesForm, self).__init__(request, data=data)
        if not self.needs_primary_audio_language:
            del self.fields['primary_audio_language_code']

    def get_language_choices(self):
        # remove languages that already have subtitles
        current_langs = set(self.video.languages_with_versions())
        if self.user.is_authenticated():
            user_language_choices = self.user.get_language_codes_and_names()
        else:
            user_language_choices = []
        if user_language_choices:
            top_section = (_('Your Languages'), user_language_choices)
        else:
            top_section = None
        return get_language_choices(top_section=top_section,
                                    exclude=current_langs)

    def set_primary_audio_language(self):
        if self.needs_primary_audio_language:
            super(CreateSubtitlesForm, self).set_primary_audio_language()

    @property
    def needs_primary_audio_language(self):
        return not bool(self.video.primary_audio_language_code)

    def get_video(self):
        return self.video

class TeamCreateSubtitlesForm(CreateSubtitlesForm):

    subtitle_language_code = AmaraChoiceField(label=_('Subtitle into:'))
    primary_audio_language_code = AmaraChoiceField(
                label=_('Video language'))

    def __init__(self, request, video, team_slug, data=None):
        super(TeamCreateSubtitlesForm, self).__init__(request, video, data=data)
        team = Team.objects.get(slug=team_slug)

        if self.needs_primary_audio_language:
            if can_edit_videos(team, request.user):
                self.fields['primary_audio_language_code'].help_text = ''
            else:
                self.fields['primary_audio_language_code'].help_text = 'Please double check the video language. Only team admins and above can change the video language once it is set.'

        self.team_url_arg = '?team={}'.format(team_slug)
        self.action_url = reverse('videos:create_subtitles', kwargs={
                'video_id': self.video.video_id
            }) + self.team_url_arg

    def editor_url(self):
        return super(TeamCreateSubtitlesForm, self).editor_url() + self.team_url_arg

class MultiVideoCreateSubtitlesForm(CreateSubtitlesFormBase):
    """Form to create subtitles for pages that display multiple videos.

    This form is normally used with some javascript that alters the form
    for a specific video.  This is done with a couple special things on the
    <A> tag:
        * Adding both the open-modal and multi-video-create-subtitles classes
        * The multi_video_create_subtitles_data_attrs template filter, which
          fills in a bunch of data attributes

    See the team dashboard page for an example.
    """
    video = forms.ModelChoiceField(queryset=Video.objects.none(),
                                   widget=forms.HiddenInput)

    def __init__(self, request, video_queryset, data=None):
        super(MultiVideoCreateSubtitlesForm, self).__init__(request, data=data)
        self.fields['video'].queryset = video_queryset

    def get_video(self):
        return self.cleaned_data['video']

    def clean(self):
        cleaned_data = super(MultiVideoCreateSubtitlesForm, self).clean()
        video = cleaned_data['video']
        lang_code = cleaned_data['subtitle_language_code']
        if video.subtitle_language(lang_code) is not None:
            lang = video.subtitle_language(lang_code)
            self._errors['subtitle_language_code'] = [
                forms.ValidationError('%s subtitles already created',
                                      params=lang.get_language_code_display())
            ]
            del cleaned_data['subtitle_language_code']
        return cleaned_data
