# -*- coding: utf-8 -*-
# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program.  If not, see http://www.gnu.org/licenses/agpl-3.0.html.

import json
from urllib import urlencode

import babelsubs
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, Http404, HttpResponseServerError, HttpResponseForbidden
from django.db.models import Count
from django.conf import settings
from django.contrib import messages
from django.template import RequestContext
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.http import urlencode
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_POST
from django.views.generic import View
from django.shortcuts import render, get_object_or_404, redirect
from django.template.defaultfilters import urlize, linebreaks, force_escape
from django.views.decorators.clickjacking import xframe_options_exempt

from auth.models import CustomUser as User
from subtitles import shims
from subtitles.workflows import get_workflow
from subtitles.models import SubtitleLanguage, SubtitleVersion
from subtitles.permissions import user_can_access_subtitles_format
from subtitles.templatetags.new_subtitles_tags import visibility
from subtitles.forms import SubtitlesUploadForm
from teams.models import Task
from teams.permissions import can_perform_task
from utils.text import fmt
from videos.models import Video
from videos.types import video_type_registrar

def _version_data(version):
    '''
    Creates a dict with version info, suitable for encoding
    into json and bootstrapping the editor.
    '''
    return {
        'metadata': version.get_metadata(),
        'subtitles': version.get_subtitles().to_xml(),
        'title': version.title,
        'description': version.description,
    }

@require_POST
def regain_lock(request, video_id, language_code):
    video = get_object_or_404(Video, video_id=video_id)
    language = video.subtitle_language(language_code)

    if not language.can_writelock(request.user):
        return HttpResponse(json.dumps({'ok': False}))

    language.writelock(request.user, save=True)
    return HttpResponse(json.dumps({'ok': True}))

@require_POST
def release_lock(request, video_id, language_code):
    video = get_object_or_404(Video, video_id=video_id)
    language = video.subtitle_language(language_code)

    if language.can_writelock(request.user):
        language.release_writelock()

    return HttpResponse(json.dumps({'url': reverse('videos:video', args=(video_id,))}))

@login_required
@require_POST
def tutorial_shown(request):
    request.user.tutorial_was_shown()
    return HttpResponse(json.dumps({'success': True}))

@login_required
@require_POST
def set_playback_mode(request):
    request.user.set_playback_mode(request.POST['playback_mode'])
    return HttpResponse(json.dumps({'success': True}))

def old_editor(request, video_id, language_code):
    video = get_object_or_404(Video, video_id=video_id)
    language = get_object_or_404(SubtitleLanguage, video=video,
                                 language_code=language_code)
    url_path = shims.get_widget_url(language,
                                    request.GET.get('mode'),
                                    request.GET.get('task_id'))
    return redirect("{}://{}{}".format(settings.DEFAULT_PROTOCOL, request.get_host(), url_path))

class SubtitleEditorBase(View):
    def dispatch(self, request, *args, **kwargs):
        self.handle_special_user(request)
        if not request.user.is_authenticated():
            return redirect_to_login(request.build_absolute_uri())
        return super(SubtitleEditorBase, self).dispatch(
            request, *args, **kwargs)

    def handle_special_user(self, request):
        if 'special_user' not in request.GET:
            return
        try:
            special_user = User.objects.get(id=request.session['editor-user-id'])
        except (KeyError, User.DoesNotExist):
            raise PermissionDenied()
        # We use the editor user for this requests, but still don't log them
        # in.  Note that this will also control the auth headers that get sent
        # to the editor, so the API calls will also use this user.
        request.user = special_user

    def get_video_urls(self):
        """Get video URLs to send to the editor."""
        return self.workflow.editor_video_urls(self.language_code)

    def get_redirect_url(self):
        if 'return_url' in self.request.GET:
            return self.request.GET['return_url']
        url = self.editing_language.get_absolute_url()
        if 'team' in self.request.GET:
            url += '?{}'.format(urlencode({
                'team': self.request.GET['team']
            }))
        return url

    def get_custom_css(self):
        return ""

    def get_title(self):
        if self.experimental:
            return _('Amara - Experimental')
        else:
            return _('Amara')

    def calc_base_language(self):
        if (self.video.primary_audio_language_code and 
            SubtitleVersion.objects.extant().filter(
                video=self.video,
                language_code=self.video.primary_audio_language_code)
            .exists()):
            self.base_language = self.video.primary_audio_language_code
        else:
            self.base_language = None

    def calc_editing_language(self):
        self.editing_language = self.video.subtitle_language(self.language_code)
        if self.editing_language is None:
            self.editing_language = SubtitleLanguage(
                video=self.video, language_code=self.language_code)

    def check_can_writelock(self):
        if not self.editing_language.can_writelock(self.request.user):
            msg = _("Sorry, you cannot edit these subtitles now because they are being edited by another user. Please check back later.")
            messages.error(self.request, msg)
            return False
        else:
            return True

    def check_can_edit(self):
        if self.workflow.user_can_edit_subtitles(self.user,
                                                 self.language_code):
            return True
        learn_more_link = u'<a href="{}">{}</a>'.format(
            u'https://support.amara.org/solution/articles/212109-why-do-i-see-a-message-saying-that-i-am-not-permitted-to-edit-subtitles',
            _(u'Learn more'))

        messages.error(self.request,
                       fmt(_('Sorry, you do not have permission to edit '
                             'these subtitles. (%(learn_more_link)s)'),
                           learn_more_link=learn_more_link))
        return False

    def get_editor_data(self):
        editor_data = {
            'canSync': bool(self.request.GET.get('canSync', True)),
            'canAddAndRemove': bool(self.request.GET.get('canAddAndRemove', True)),
            # front end needs this to be able to set the correct
            # api headers for saving subs
            'authHeaders': {
                'x-api-username': self.request.user.username,
                'x-apikey': self.request.user.get_api_key()
            },
            'username': self.request.user.username,
            'user_fullname': unicode(self.request.user),
            'video': {
                'id': self.video.video_id,
                'title': self.video.title,
                'description': self.video.description,
                'duration': self.video.duration,
                'primaryVideoURLType': video_type_registrar.video_type_for_url(self.video.get_video_url()).abbreviation,
                'videoURLs': self.get_video_urls(),
                'metadata': self.video.get_metadata(),
            },
            'editingVersion': {
                'languageCode': self.editing_language.language_code,
                'versionNumber': (self.editing_version.version_number
                                  if self.editing_version else None),
            },
            'softLimits': self.editing_language.get_soft_limits(),
            'baseLanguage': self.base_language,
            'languages': [self.editor_data_for_language(lang)
                          for lang in self.languages],
            'languageCode': self.request.LANGUAGE_CODE,
            'oldEditorURL': reverse('subtitles:old-editor', kwargs={
                'video_id': self.video.video_id,
                'language_code': self.editing_language.language_code,
            }),
            'playbackModes': self.get_editor_data_for_playback_modes(),
            'preferences': {
                'showTutorial': self.request.user.show_tutorial,
                'playbackModeId': self.request.user.playback_mode
            },
            'staticURL': settings.STATIC_URL,
            'notesHeading': 'Editor Notes',
            'notesEnabled': True,
            'redirectUrl': self.get_redirect_url(),
            'customCss': self.get_custom_css(),
        }

        editor_data.update(self.workflow.editor_data(
            self.user, self.language_code))

        team_attributes = self.get_team_editor_data()
        if team_attributes:
            editor_data['teamAttributes'] = team_attributes

        return editor_data

    def editor_data_for_language(self, language):
        versions_data = []

        if self.workflow.user_can_view_private_subtitles(
            self.user, language.language_code):
            language_qs = language.subtitleversion_set.extant()
        else:
            language_qs = language.subtitleversion_set.public()
        for i, version in enumerate(language_qs):
            version_data = {
                'version_no':version.version_number,
                'visibility': visibility(version),
            }
            if self.editing_version == version:
                version_data.update(_version_data(version))
            elif self.translated_from_version == version:
                version_data.update(_version_data(version))
            elif (language.language_code == self.base_language and
                  i == len(language_qs) - 1):
                version_data.update(_version_data(version))

            versions_data.append(version_data)


        return {
            'translatedFrom': self.translated_from_version and {
                'language_code': self.translated_from_version.subtitle_language.language_code,
                'version_number': self.translated_from_version.version_number,
            },
            'editingLanguage': language == self.editing_language,
            'language_code': language.language_code,
            'name': language.get_language_code_display(),
            'pk': language.pk,
            'numVersions': language.num_versions,
            'versions': versions_data,
            'subtitles_complete': language.subtitles_complete,
            'is_rtl': language.is_rtl(),
            'is_original': language.is_primary_audio_language()
        }

    def get_editor_data_for_playback_modes(self):
        return [
            {
                'id': User.PLAYBACK_MODE_MAGIC,
                'idStr': 'magic',
                'name': _('Magic'),
                'desc': _('Recommended: magical auto-pause (just keep typing!)')
            },
            {
                'id': User.PLAYBACK_MODE_STANDARD,
                'idStr': 'standard',
                'name': _('Standard'),
                'desc': _('Standard: no automatic pausing, use TAB key')
            },
            {
                'id': User.PLAYBACK_MODE_BEGINNER,
                'idStr': 'beginner',
                'name': _('Beginner'),
                'desc': _('Beginner: play 4 seconds, then pause')
            }
        ]

    def get_team_editor_data(self):
        if self.team_video:
            team = self.team_video.team
            return dict([('teamName', team.name), ('type', team.workflow_type),
                         ('features', [f.key_name.split('_', 1)[-1] for f in team.settings.features()]),
                         ('guidelines', dict(
                             [(s.key_name.split('_', 1)[-1],
                               linebreaks(urlize(force_escape(s.data))))
                              for s in team.settings.guidelines()
                              if s.data.strip()]))])
        else:
            return None

    def assign_task_for_editor(self):
        """Try to assign any unassigned tasks to our user.

        If we can't assign the task, return False.
        """
        if self.team_video is None:
            return True
        task_set = self.team_video.task_set.incomplete().filter(
            language=self.language_code)
        tasks = list(task_set[:1])
        if tasks:
            task = tasks[0]
            if task.assignee is None and can_perform_task(self.user, task):
                task.assignee = self.user
                task.set_expiration()
                task.save()

            if task.assignee != self.user:
                msg = fmt(_("Another user is currently performing "
                            "the %(task_type)s task for these subtitles"),
                          task_type=task.get_type_display())
                messages.error(self.request, msg)
                return False
        return True

    def handle_task(self, context, editor_data):
        """Does most of the dirty-work to handle tasks.  """
        context['task'] = None
        if self.team_video is None:
            return

        task = self.team_video.get_task_for_editor(self.language_code)
        if not task:
            return
        context['task'] = task
        editor_data['task_id'] = task.id
        editor_data['savedNotes'] = task.body
        editor_data['task_needs_pane'] = task.get_type_display() in ('Review', 'Approve')
        editor_data['team_slug'] = task.team.slug
        editor_data['oldEditorURL'] += '?' + urlencode({
            'mode': Task.TYPE_NAMES[task.type].lower(),
            'task_id': task.id,
        })

    def get(self, request, video_id, language_code):
        self.video = get_object_or_404(Video, video_id=video_id)
        self.team_video = self.video.get_team_video()
        self.language_code = language_code
        self.user = request.user
        self.calc_base_language()
        self.calc_editing_language()
        self.workflow = get_workflow(self.video)

        if (not self.check_can_edit() or
            not self.check_can_writelock() or
            not self.assign_task_for_editor()):
            if 'team' in self.request.GET:
                qs = '?{}'.format(urlencode({
                    'team': self.request.GET['team']
                }))
                return redirect(self.video.get_absolute_url() + qs)
            return redirect(self.video)

        self.editing_language.writelock(self.user,
                                        save=True)
        self.editing_version = self.editing_language.get_tip(public=False)
        # we ignore forking because even if it *is* a fork, we still want to
        # show the user the rererence languages:
        self.translated_from_version = self.editing_language.\
            get_translation_source_version(ignore_forking=True)
        self.languages = self.video.newsubtitlelanguage_set.annotate(
            num_versions=Count('subtitleversion'))
        editor_data = self.get_editor_data()
        self.experimental = 'experimental' in request.GET

        context = {
            'title': self.get_title(),
            'video': self.video,
            'DEBUG': settings.DEBUG,
            'language': self.editing_language,
            'other_languages': self.languages,
            'version': self.editing_version,
            'translated_from_version': self.translated_from_version,
            'experimental': self.experimental,
            'upload_subtitles_form': SubtitlesUploadForm(
                request.user, self.video,
                initial={'language_code':
                         self.editing_language.language_code},
                allow_all_languages=True),
        }
        self.handle_task(context, editor_data)
        context['editor_data'] = json.dumps(editor_data, indent=4)

        if self.experimental:
            return render(request, "experimental-editor/editor.html", context)
        else:
            return render(request, "editor/editor.html", context)

class SubtitleEditor(SubtitleEditorBase):
    @method_decorator(xframe_options_exempt)
    def dispatch(self, request, *args, **kwargs):
        if 'legacy' in request.GET:
            return old_editor(request, *args, **kwargs)
        return super(SubtitleEditor, self).dispatch(
            request, *args, **kwargs)

def _user_for_download_permissions(request):
    if request.user.is_authenticated():
        return request.user
    username = request.META.get('HTTP_X_API_USERNAME', None)
    api_key = request.META.get('HTTP_X_API_KEY',
                               request.META.get('HTTP_X_APIKEY', None))
    if not username or not api_key:
        return request.user
    try:
        api_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return request.user
    if api_user.check_api_key(api_key):
        return api_user
    return request.user

def download(request, video_id, language_code, filename, format,
             version_number=None):
    user = _user_for_download_permissions(request)
    if not user_can_access_subtitles_format(user, format):
        raise HttpResponseForbidden(_(u'You are not allowed to download this subtitle format.'))
    video = get_object_or_404(Video, video_id=video_id)
    workflow = video.get_workflow()
    if not workflow.user_can_view_video(user):
        raise PermissionDenied()

    language = video.subtitle_language(language_code)
    if language is None:
        raise PermissionDenied()

    public_only = workflow.user_can_view_private_subtitles(user,
                                                           language_code)
    version = language.version(public_only=not public_only,
                               version_number=version_number)
    if not version:
        raise Http404()
    if not format in babelsubs.get_available_formats():
        raise HttpResponseServerError("Format not found")

    subs_text = babelsubs.to(version.get_subtitles(), format,
                             language=version.language_code)
    # since this is a download, we can afford not to escape tags, specially
    # true since speaker change is denoted by '>>' and that would get entirely
    # stripped out
    response = HttpResponse(subs_text, content_type="text/plain")
    response['Content-Disposition'] = 'attachment'
    return response


def download_all(request, video_id, filename):
    video = get_object_or_404(Video, video_id=video_id)
    merged_dfxp = video.get_merged_dfxp()

    if merged_dfxp is None:
        raise Http404()

    response = HttpResponse(merged_dfxp, content_type="text/plain")
    response['Content-Disposition'] = 'attachment'
    return response
