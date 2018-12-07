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

import datetime
import string
import sys
import urllib, urllib2
from collections import namedtuple

import json
from babelsubs.storage import diff as diff_subs
from babelsubs.generators.html import HTMLGenerator
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from videos.templatetags.paginator import paginate
from django.urls import reverse
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Sum
from django.http import (HttpResponse, Http404, HttpResponseRedirect,
                         HttpResponseForbidden)
from django.shortcuts import (render, get_object_or_404, redirect)
from django.template import RequestContext
from django.utils.encoding import force_unicode
from django.utils.http import urlquote_plus
from django.utils.translation import ugettext, ugettext_lazy as _
from django.views.decorators.http import require_POST

import widget
from widget import rpc as widget_rpc
from activity.models import ActivityRecord
from auth.models import CustomUser as User
from caching.decorators import cache_page
from comments.models import Comment
from comments.forms import CommentForm
from subtitles.models import SubtitleLanguage, SubtitleVersion
from subtitles.permissions import (user_can_view_private_subtitles,
                                   user_can_edit_subtitles,
                                   user_can_change_subtitle_language)
from subtitles.forms import (SubtitlesUploadForm, DeleteSubtitlesForm,
                             RollbackSubtitlesForm, SubtitlesNotesForm,
                             ResyncSubtitlesForm, ChangeSubtitleLanguageForm)
from subtitles.pipeline import rollback_to
from subtitles.types import SubtitleFormatList
from subtitles.permissions import user_can_access_subtitles_format
from teams.models import Task, Team
from ui.ajax import AJAXResponseRenderer
from utils.behaviors import behavior
from utils.decorators import staff_member_required
from videos import behaviors
from videos import permissions
from videos.decorators import (get_video_revision, get_video_from_code,
                               get_cached_video_from_code)
from videos.forms import (
    VideoForm,
    CreateVideoUrlForm, NewCreateVideoUrlForm, AddFromFeedForm,
    ChangeVideoOriginalLanguageForm, CreateSubtitlesForm, TeamCreateSubtitlesForm
)
from videos.models import (
    Video, VideoUrl, AlreadyEditingException
)
from videos import oldviews
from videos.rpc import VideosApiClass
from videos import share_utils
from videos.tasks import video_changed_tasks
from videos.types import video_type_registrar
from widget.views import base_widget_params
from externalsites.models import can_sync_videourl, get_sync_account, SyncHistory
from utils import send_templated_email
from utils.basexconverter import base62
from utils.decorators import never_in_prod
from utils.objectlist import object_list
from utils.rpc import RpcRouter
from utils.pagination import AmaraPaginator
from utils.text import fmt
from utils.translation import (get_user_languages_from_request,
                               get_language_label)

from teams.permissions import can_edit_video, can_add_version, can_resync
from . import video_size
import teams.permissions

VIDEO_IN_ROW = 6
ACTIVITY_PER_PAGE = 8

rpc_router = RpcRouter('videos:rpc_router', {
    'VideosApi': VideosApiClass()
})


# .e.g json, nor include aliases
AVAILABLE_SUBTITLE_FORMATS_FOR_DISPLAY = [
    'dfxp',  'sbv', 'srt', 'ssa', 'txt', 'vtt',
]

LanguageListItem = namedtuple("LanguageListItem", "name status tags url code")

class LanguageList(object):
    """List of languages for the video pages."""

    def __init__(self, video):
        original_languages = []
        other_languages = []
        for lang in video.all_subtitle_languages():
            public_tip = lang.get_tip(public=False)
            if public_tip is None or public_tip.subtitle_count == 0:
                # no versions in this language yet
                continue
            language_name = get_language_label(lang.language_code)
            code = lang.language_code
            status = self._calc_status(lang)
            tags = self._calc_tags(lang)
            url = lang.get_absolute_url()
            item = LanguageListItem(language_name, status, tags, url, code)
            if lang.language_code == video.primary_audio_language_code:
                original_languages.append(item)
            else:
                other_languages.append(item)
        original_languages.sort(key=lambda li: li.code)
        other_languages.sort(key=lambda li: li.code)
        self.items = original_languages + other_languages

    def _calc_status(self, lang):
        if lang.subtitles_complete:
            if lang.has_public_version():
                return 'complete'
            else:
                return 'needs-review'
        else:
            if lang.is_synced(public=False):
                return 'incomplete'
            else:
                return 'needs-timing'

    def _calc_tags(self, lang):
        tags = []
        if lang.is_primary_audio_language():
            tags.append(ugettext(u'original'))

        team_video = lang.video.get_team_video()

        if not lang.subtitles_complete:
            tags.append(ugettext(u'incomplete'))
        elif team_video is not None:
            # subtitles are complete, check if they are under review/approval.
            incomplete_tasks = (Task.objects.incomplete()
                                            .filter(team_video=team_video,
                                                    language=lang.language_code))
            for t in incomplete_tasks:
                if t.type == Task.TYPE_IDS['Review']:
                    tags.append(ugettext(u'needs review'))
                    break
                elif t.type == Task.TYPE_IDS['Approve']:
                    tags.append(ugettext(u'needs approval'))
                    break
                else:
                    # subtitles are complete, but there's a subtitle/translate
                    # task for them.  They must have gotten sent back.
                    tags.append(ugettext(u'needs editing'))
                    break
        return tags

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

@cache_page(minutes=60)
def watch_page(request):
    return render(request, 'videos/watch-home.html', {
        'featured_videos': Video.objects.featured()[:VIDEO_IN_ROW],
        'latest_videos': Video.objects.latest()[:VIDEO_IN_ROW*3],
    })

@cache_page(minutes=60)
def video_listing_page(request, subheader, video_qs, query=None,
                       force_pages=None):
    paginator = AmaraPaginator(video_qs, VIDEO_IN_ROW * 3)
    if force_pages:
        paginator._count = paginator.per_page * force_pages
    page = paginator.get_page(request)

    return render(request, 'videos/watch.html', {
        'subheader': subheader,
        'page': page,
        'query': query
    })

def featured_videos(request):
    return video_listing_page(request, _('Featured Videos'),
                              Video.objects.featured(), force_pages=1)

def latest_videos(request):
    return video_listing_page(request, _('Latest Videos'),
                              Video.objects.latest(), force_pages=100)

def search(request):
    query = request.GET.get('q')
    if query:
        subheader = fmt(ugettext('Searching for "%(query)s"'),
                        query=query)
        queryset = Video.objects.public().search(query)
    else:
        subheader = ugettext('Search for videos')
        queryset = Video.objects.none()
    return video_listing_page(request, subheader, queryset, query)

@behavior
def videos_create_template():
    return 'videos/create.html'

@behavior
def videos_create_extra_data(request, create_form):
    return {}

def create(request):
    initial = {
        'video_url': request.GET.get('initial_url'),
    }
    if request.user.is_authenticated():
        if request.method == 'POST':
            create_form = VideoForm(request.user, data=request.POST,
                                   initial=initial)
            if create_form.is_valid():
                video = create_form.video
                messages.info(request, message=_(u'''Here is the subtitle workspace for your video.
                You can share the video with friends, or get an embed code for your site. To start
                new subtitles, click \"Add a new language!\" in the sidebar.'''))

                if create_form.created:
                    messages.info(request, message=_(u'''Existing subtitles will be imported in a few minutes.'''))
                return redirect(video.get_absolute_url())
        else:
            create_form = VideoForm(request.user, initial=initial)
    else:
        create_form = None

    data = { 'create_form': create_form }
    data.update(videos_create_extra_data(request, create_form))
    return render(request, videos_create_template(), data)

def shortlink(request, encoded_pk):
    pk = base62.to_decimal(encoded_pk)
    video = get_object_or_404(Video, pk=pk)
    return redirect(video, video=video, permanent=True)

@get_video_from_code
def redirect_to_video(request, video):
    qs = request.META['QUERY_STRING']
    url = video.get_absolute_url()
    if qs:
        url += '?' + qs
    return redirect(url, permanent=True)

def should_use_old_view(request):
    return 'team' not in request.GET

@behavior
def video(request, video_id, video_url=None, title=None):
    if should_use_old_view(request):
        return oldviews.video(request, video_id, video_url, title)
    if request.is_ajax() and 'form' in request.POST:
        return video_ajax_form(request, video_id)
    request.use_cached_user()
    try:
        video = Video.cache.get_instance_by_video_id(video_id, 'video-page')
    except Video.DoesNotExist:
        raise Http404
    if not video.can_user_see(request.user):
        raise PermissionDenied()

    if video_url:
        video_url = get_object_or_404(video.videourl_set, pk=video_url)
    else:
        video_url = video.get_primary_videourl_obj()

    workflow = video.get_workflow()
    if workflow.user_can_create_new_subtitles(request.user):
        form_name = request.GET.get('form', '')
        if form_name == 'create-subtitles':
            return create_subtitles(request, video_id)
        else:
            # this is the old code for creating the CreateSubtitlesForm
            create_subtitles_form = CreateSubtitlesForm(request,video)
    else:
        create_subtitles_form = None
    if request.user.is_authenticated():
        comment_form = CommentForm(video)
    else:
        comment_form = None
    if permissions.can_user_edit_video_urls(video, request.user):
        create_url_form = NewCreateVideoUrlForm(video, request.user)
        allow_delete = allow_make_primary = True
    else:
        create_url_form = None
        allow_delete = allow_make_primary = False

    customization = behaviors.video_page_customize(request, video)
    all_activities = ActivityRecord.objects.for_video(
        video, customization.team)

    if request.is_ajax() and request.GET.get('show-all', None):
        response_renderer = AJAXResponseRenderer(request)
        response_renderer.replace(
            '#video_activity', "future/videos/tabs/activity.html", {
                'activity': all_activities,
            },
        )
        return response_renderer.render()

    activity = all_activities[:ACTIVITY_PER_PAGE]
    show_all = False if len(activity) >= len(all_activities) else True

    sanity_check_video_urls(request, video)

    return render(request, 'future/videos/video.html', {
        'video': video,
        'player_url': video_url.url,
        'team': video.get_team(),
        'team_video': video.get_team_video(),
        'tab': request.GET.get('tab', 'info'),
        'allow_delete': allow_delete,
        'allow_make_primary': allow_make_primary,
        'create_subtitles_form': create_subtitles_form,
        'comment_form': comment_form,
        'create_url_form': create_url_form,
        'comments': Comment.get_for_object(video),
        'activity': activity,
        'activity_count': 1,
        'show_all': show_all,
        'metadata': video.get_metadata().convert_for_display(),
        'custom_sidebar': customization.sidebar,
        'header': customization.header,
        'use_old_messages': True,
        'video_urls': [
            (vurl, get_sync_account(video, vurl))
            for vurl in video.get_video_urls()
        ],
    })

def create_subtitles(request, video_id):
    try:
        video = Video.cache.get_instance_by_video_id(video_id, 'video-page')
    except Video.DoesNotExist:
        raise Http404

    workflow = video.get_workflow()
    if not workflow.user_can_create_new_subtitles(request.user):
        raise PermissionDenied()

    team_slug = request.GET.get('team', None)
    if request.method == 'POST':
        if team_slug:
            form = TeamCreateSubtitlesForm(request, video, team_slug, request.POST)
        else:
            form = CreateSubtitlesForm(request, video, request.POST)

        if form.is_valid():
            form.set_primary_audio_language()
            response_renderer = AJAXResponseRenderer(request)
            response_renderer.redirect(form.editor_url())
            return response_renderer.render()
    else:
        if team_slug:
            form = TeamCreateSubtitlesForm(request, video, team_slug)
        else:
            form = CreateSubtitlesForm(request, video)

    response_renderer = AJAXResponseRenderer(request)
    response_renderer.show_modal('future/videos/create-subtitles-modal.html', {
        'form': form,
        'video': video,
    })
    return response_renderer.render()

def video_ajax_form(request, video_id):
    form = request.POST.get('form')
    video = get_object_or_404(Video, video_id=video_id)
    if form == 'comment':
        return comments_form(request, video, '#video_comments')
    elif form == 'add-url':
        return video_add_url_form(request, video)
    elif form == 'make-url-primary':
        return video_make_url_primary_form(request, video)
    elif form == 'delete-url':
        return video_delete_url_form(request, video)
    else:
        return redirect(video.get_absolute_url())

def comments_form(request, obj, replace_id):
    if not request.user.is_authenticated():
        raise PermissionDenied()
    comment_form = CommentForm(obj, data=request.POST)
    success = comment_form.is_valid()
    if success:
        comment_form.save(request.user)
        # reset the comment form to a fresh state
        comment_form = CommentForm(obj)

    if request.is_ajax():
        response_renderer = AJAXResponseRenderer(request)
        response_renderer.replace(
            replace_id, 'future/videos/tabs/comments.html', {
                'comments': Comment.get_for_object(obj),
                'comment_form': comment_form,
            })
        return response_renderer.render()
    else:
        return redirect(request.get_full_path())

def video_add_url_form(request, video):
    if not permissions.can_user_edit_video_urls(video, request.user):
        raise PermissionDenied()
    create_url_form = NewCreateVideoUrlForm(video, request.user,
                                            data=request.POST)
    response_renderer = AJAXResponseRenderer(request)
    if create_url_form.is_valid():
        create_url_form.save()
        response_renderer.clear_form('#add-url-form form')
        response_renderer.replace(*urls_tab_replacement_data(request, video))
        response_renderer.hide_modal()
    else:
        response_renderer.replace(
            '#add-url-form', "future/videos/forms/create-url.html", {
                'create_url_form': create_url_form,
            })

    return response_renderer.render()

def video_delete_url_form(request, video):
    if not permissions.can_user_edit_video_urls(video, request.user):
        raise PermissionDenied()
    try:
        video_url = video.videourl_set.get(id=request.POST.get('id', -1))
    except VideoUrl.DoesNotExist:
        success = False
    else:
        video_url.remove(request.user)
        success = True

    response_renderer = AJAXResponseRenderer(request)
    if success:
        response_renderer.replace(*urls_tab_replacement_data(request, video))
        response_renderer.hide_modal()
    return response_renderer.render()

def video_make_url_primary_form(request, video):
    if not permissions.can_user_edit_video_urls(video, request.user):
        raise PermissionDenied()
    try:
        video_url = video.videourl_set.get(id=request.POST.get('id', -1))
    except VideoUrl.DoesNotExist:
        success = False
    else:
        video_url.make_primary(request.user)
        success = True

    response_renderer = AJAXResponseRenderer(request)
    if success:
        response_renderer.replace(*urls_tab_replacement_data(request, video))
        response_renderer.hide_modal()
    return response_renderer.render()

def urls_tab_replacement_data(request, video):
    return ('#video_urls', 'future/videos/tabs/urls.html', {
            'video': video,
            'allow_delete': True,
            'allow_make_primary': True,
            'video_urls': [
                (vurl, get_sync_account(video, vurl))
                for vurl in video.get_video_urls()
            ],
            'create_url_form': NewCreateVideoUrlForm(video, request.user),
        })

def sanity_check_video_urls(request, video):
    team = video.get_team()
    team_id = team.id if team else 0
    for video_url in video.get_video_urls():
        if video_url.team_id != team_id:
            video_url.team_id = team_id
            video_url.save()
            if request.user.is_staff:
                messages.warning(request, "Updated team for {} to {}".format(
                                     video_url.url, team))

def _get_related_task(request):
    """
    Checks if request has t=[task-id], and if so checks if the current
    user can perform it, in case all goes well, return the task to be
    performed.
    """
    task_pk = request.GET.get('t', None)
    if task_pk:
        from teams.permissions import can_perform_task
        try:
            task = Task.objects.get(pk=task_pk)
            if can_perform_task(request.user, task):
                return task
        except Task.DoesNotExist:
            return


def activity(request, video_id):
    video = get_object_or_404(Video, video_id=video_id)
    qs = ActivityRecord.objects.for_video(video)

    extra_context = {
        'video': video,
        'use_old_messages': True
    }

    return object_list(request, queryset=qs, allow_empty=True,
                       paginate_by=settings.ACTIVITIES_ONPAGE,
                       template_name='videos/activity.html',
                       template_object_name='action',
                       extra_context=extra_context)

def check_upload_subtitles_permissions(request):
    return request.user.is_authenticated()

def upload_subtitles(request):
    if not check_upload_subtitles_permissions(request):
        path = request.get_full_path()
        return redirect_to_login(path)

    output = {'success': False}
    video = Video.objects.get(id=request.POST['video'])
    form = SubtitlesUploadForm(request.user, video, True, request.POST,
                               request.FILES,
                               initial={'primary_audio_language_code':video.primary_audio_language_code},
                               allow_all_languages=True)

    try:
        if form.is_valid():
            version = form.save()
            output['success'] = True
            output['next'] = version.subtitle_language.get_absolute_url()
            output['msg'] = ugettext(
                u'Thank you for uploading. '
                u'It may take a minute or so for your subtitles to appear.')
        else:
            output['errors'] = form.get_errors()
    except AlreadyEditingException, e:
        output['errors'] = {'__all__': [force_unicode(e.msg)]}
    except Exception, e:
        import traceback
        traceback.print_exc()
        output['errors'] = {'__all__': [force_unicode(e)]}

    return HttpResponse(json.dumps(output))

@get_video_from_code
def legacy_history(request, video, lang):
    """
    In the old days we allowed only one translation per video.
    Therefore video urls looked like /vfjdh2/en/
    Now that this constraint is removed we need to redirect old urls
    to the new view, that needs
    """
    language, created = SubtitleLanguage.objects.get_or_create(
        video=video, language_code=lang)

    url = reverse("videos:translation_history", kwargs={
        'video_id': video.video_id,
        'lang_id': language.pk,
        'lang': language.language_code,
    })
    if request.META['QUERY_STRING']:
        url = '{}?{}'.format(url, request.META['QUERY_STRING'])

    return HttpResponseRedirect(url)

def subtitles(request, video_id, lang, lang_id, version_id=None):
    if should_use_old_view(request):
        return oldviews.language_subtitles(request, video_id, lang, lang_id,
                                           version_id)
    request.use_cached_user()
    try:
        video, subtitle_language, version = get_objects_for_subtitles_page(
            request.user, video_id, lang, lang_id, version_id)
    except ObjectDoesNotExist:
        raise Http404()

    # Fetch the comments now.  We only support posting new comments if the
    # subtitles already have comments on them
    comments = Comment.get_for_object(subtitle_language)

    if 'form' in request.GET:
        return subtitles_ajax_form(request, video, subtitle_language, version)
    elif request.POST.get('form') == 'comment' and comments:
        # Handle the comments form specially, and only handle it if there are
        # already comments on the video
        return comments_form(request, subtitle_language,
                             '#subtitles_comments')
    workflow = video.get_workflow()
    if request.user.is_authenticated() and comments:
        comment_form = CommentForm(subtitle_language)
    else:
        comment_form = None

    customization = behaviors.subtitles_page_customize(request, video, subtitle_language)
    all_activities = (ActivityRecord.objects.for_video(video, customization.team)
                .filter(language_code=lang))

    if request.is_ajax() and request.GET.get('show-all', None):
        response_renderer = AJAXResponseRenderer(request)
        response_renderer.replace(
            '#subtitles_activity', "future/videos/tabs/activity.html", {
                'activity': all_activities,
            },
        )
        return response_renderer.render()

    if request.is_ajax() and request.GET.get('update-sync-history', None):
        response_renderer = AJAXResponseRenderer(request)
        response_renderer.replace(
            '#subtitles_sync_history', "future/videos/tabs/sync-history.html",
            sync_history_context(video, subtitle_language),
        )
        return response_renderer.render()

    all_subtitle_versions = subtitle_language.versions_for_user(
            request.user).order_by('-version_number')
    team_video = video.get_team_video()
    activity = all_activities[:ACTIVITY_PER_PAGE]
    show_all = False if len(activity) >= len(all_activities) else True
    context = {
        'video': video,
        'team_video': team_video,
        'metadata': video.get_metadata().convert_for_display(),
        'subtitle_language': subtitle_language,
        'subtitle_version': version,
        'enable_delete_subtitles': workflow.user_can_delete_subtitles(
                request.user, subtitle_language.language_code),
        'enable_change_language': user_can_change_subtitle_language(request.user, video),
        'show_rollback': version and not version.is_tip(public=False),
        'all_subtitle_versions': all_subtitle_versions,
        'enabled_compare': len(all_subtitle_versions) >= 2,
        'has_private_version': any(v.is_private() for v in
                                   all_subtitle_versions),
        'downloadable_formats': downloadable_formats(request.user),
        'activity': activity,
        'activity_count': 1,
        'show_all': show_all,
        'comments': comments,
        'comment_form': comment_form,
        'enable_edit_in_admin': request.user.is_superuser,
        'steps': customization.steps,
        'cta': customization.cta,
        'due_date': customization.due_date,
        'can_edit': workflow.user_can_edit_subtitles(
            request.user, subtitle_language.language_code),
        'header': customization.header,
        'extra_page_controls': customization.extra_page_controls,
    }
    if workflow.user_can_view_notes(request.user, subtitle_language.language_code):
        editor_notes = workflow.get_editor_notes(request.user, subtitle_language.language_code)
        if editor_notes:
            context['show_notes'] = True
            context['notes'] = editor_notes.fetch_notes()
            if workflow.user_can_post_notes(request.user, subtitle_language.language_code):
                context['notes_form'] = SubtitlesNotesForm(
                    request.user, video, subtitle_language, version)
        else:
            context['show_notes'] = False
    else:
        context['show_notes'] = False
    if team_video and can_resync(team_video.team, request.user):
        context.update(sync_history_context(video, subtitle_language))
        context['show_sync_history'] = True
    else:
        context['show_sync_history'] = False
        context['can_resync'] = False

    sanity_check_video_urls(request, video)

    return render(request, 'future/videos/subtitles.html', context)

def get_objects_for_subtitles_page(user, video_id, language_code, lang_id,
                                   version_id):
    """Fetch the Video and SubtitleVersion objects for the subtitles page.
    """

    video = Video.cache.get_instance_by_video_id(video_id, 'subtitles-page')

    workflow = video.get_workflow()
    if not workflow.user_can_view_video(user):
        raise PermissionDenied()

    language, _ = SubtitleLanguage.objects.get_or_create(
        video=video, language_code=language_code)

    public_only = not workflow.user_can_view_private_subtitles(user,
                                                               language_code)

    if version_id is None:
        version = language.get_tip(public=public_only)
    else:
        version = language.get_version_by_id(version_id, public=public_only)

    if version is not None:
        # Set up some relationships that we know to avoid an extra DB fetch
        version.subtitle_language = language
        version.video = language.video = video

    return video, language, version

def sync_history_context(video, subtitle_language):
    context = {}
    sync_history = SyncHistory.objects.get_sync_history_for_subtitle_language(subtitle_language)
    context['sync_history'] = sync_history
    context['can_resync'] = (len(sync_history) > 0) and not sync_history[0]['account'].should_skip_syncing()
    context['current_version'] = subtitle_language.get_public_tip()
    synced_versions = []
    for video_url in video.get_video_urls():
        if not can_sync_videourl(video_url):
            continue
        try:
            version = (subtitle_language.syncedsubtitleversion_set.
                       select_related('version').
                       get(video_url=video_url)).version
        except ObjectDoesNotExist:
            version = None
        synced_versions.append({
            'video_url': video_url,
            'version': version,
            'syncable': get_sync_account(video, video_url),
        })
    context['synced_versions'] = synced_versions
    return context

def downloadable_formats(user):
    downloadable_formats = AVAILABLE_SUBTITLE_FORMATS_FOR_DISPLAY
    downloadable_formats_set = set(downloadable_formats)
    for format in SubtitleFormatList.for_staff():
        if user_can_access_subtitles_format(user, format):
            downloadable_formats_set.add(format)
    return list(downloadable_formats_set)

subtitles_form_map = {
    'delete': DeleteSubtitlesForm,
    'language': ChangeSubtitleLanguageForm,
    'rollback': RollbackSubtitlesForm,
    'notes': SubtitlesNotesForm,
    'resync': ResyncSubtitlesForm,
}

def subtitles_ajax_form(request, video, subtitle_language, version):
    try:
        form_name = request.GET['form']
        FormClass = subtitles_form_map[form_name]
    except KeyError:
        raise Http404()
    if form_name == 'notes' and request.POST['body'] == '':
        return AJAXResponseRenderer(request).render()
    form = FormClass(request.user, video, subtitle_language, version,
                     data=request.POST if request.method == 'POST' else None)
    if not form.check_permissions():
        raise PermissionDenied()

    if form.is_bound and form.is_valid() and form_name == 'language':
        form.submit(request)
        redirect_url = subtitle_language.get_absolute_url() + '?team=' + request.GET['team']
        return redirect(redirect_url)
    elif request.is_ajax():
        if form.is_bound and form.is_valid():
            form.submit(request)
            return handle_subtitles_ajax_form_success(
                request, video, subtitle_language, version, form_name, form)
        response_renderer = AJAXResponseRenderer(request)
        template = 'future/videos/subtitles-forms/{}.html'.format(
            form_name)
        response_renderer.show_modal(template, {
            'video': video,
            'subtitle_language': subtitle_language,
            'version': version,
            'form': form,
        })
        return response_renderer.render()
    else:
        # TODO implement the not-AJAX case
        return redirect(request.get_full_path())

def handle_subtitles_ajax_form_success(request, video, subtitle_language,
                                       version, form_name, form):
    response_renderer = AJAXResponseRenderer(request)
    if form_name == 'notes':
        notes = (video.get_workflow()
                 .get_editor_notes(request.user, subtitle_language.language_code)
                 .fetch_notes())
        response_renderer.replace(
            '#subtitles_notes', 'future/videos/tabs/notes.html', {
                'notes': notes,
                'notes_form': SubtitlesNotesForm(
                    request.user, video, subtitle_language, version)
            })
    else:
        response_renderer.reload_page()
    return response_renderer.render()

def _widget_params(request, video, version_no=None, language=None, video_url=None, size=None):
    primary_url = video_url or video.get_video_url()
    alternate_urls = [vu.url for vu in video.videourl_set.all()
                      if vu.url != primary_url]
    params = {'video_url': primary_url,
              'alternate_video_urls': alternate_urls,
              'base_state': {}}

    if version_no:
        params['base_state']['revision'] = version_no

    if language:
        params['base_state']['language_code'] = language.language_code
        params['base_state']['language_pk'] = language.pk
    if size:
        params['video_config'] = {"width":size[0], "height":size[1]}

    return base_widget_params(request, params)

@login_required
@get_video_revision
def rollback(request, version):
    # Normally, we only accept POST methods, but the old template code uses
    # GET, so we allow that too.
    if should_use_old_view(request) or request.method == 'POST':
        is_writelocked = version.subtitle_language.is_writelocked
        if not user_can_edit_subtitles(request.user, version.video,
                                       version.subtitle_language.language_code):
            messages.error(request, _(u"You don't have permission to rollback "
                                      "this language"))
        elif is_writelocked:
            messages.error(request, u'Can not rollback now, because someone is editing subtitles.')
        elif not version.next_version():
            messages.error(request, message=u'Can not rollback to the last version')
        else:
            messages.success(request, message=u'Rollback successful')
            version = rollback_to(version.video,
                    version.subtitle_language.language_code,
                    version_number=version.version_number,
                    rollback_author=request.user)
            video_changed_tasks.delay(version.video.id, version.id)
            return redirect(version.subtitle_language.get_absolute_url()+'#revisions')
    return redirect(version)

@get_video_revision
def diffing(request, first_version, second_pk):
    language = first_version.subtitle_language
    second_version = get_object_or_404(
        SubtitleVersion.objects.extant(),
        pk=second_pk, subtitle_language=language)

    if first_version.video != second_version.video:
        # this is either a bad bug, or someone evil
        raise "Revisions for diff videos"

    if first_version.pk < second_version.pk:
        # this is just stupid Instead of first, second meaning
        # chronological order (first cames before second)
        # it means  the opposite, so make sure the first version
        # has a larger version no than the second
        first_version, second_version = second_version, first_version

    video = first_version.subtitle_language.video
    diff_data = diff_subs(first_version.get_subtitles(), second_version.get_subtitles(), mappings=HTMLGenerator.MAPPINGS)
    team_video = video.get_team_video()
    first_version_previous = first_version.previous_version()
    first_version_next = first_version.next_version()
    second_version_previous = second_version.previous_version()
    second_version_next = second_version.next_version()
    context = {
        'video': video,
        'diff_data': diff_data,
        'language': language,
        'first_version': first_version,
        'second_version': second_version,
        'latest_version': language.get_tip(),
        'first_version_previous': first_version_previous if (first_version_previous != second_version) else None,
        'first_version_next': first_version_next,
        'second_version_previous': second_version_previous,
        'second_version_next': second_version_next if (second_version_next != first_version) else None,
        'rollback_allowed': user_can_edit_subtitles(request.user, video,
                                                    language.language_code),
        'width': video_size["small"]["width"],
        'height': video_size["small"]["height"],
        'video_url': video.get_video_url(),
    }

    return render(request, 'videos/diffing.html', context)

@login_required
def stop_notification(request, video_id):
    user_id = request.GET.get('u')
    hash = request.GET.get('h')

    if not user_id or not hash:
        raise Http404

    video = get_object_or_404(Video, video_id=video_id)
    user = get_object_or_404(User, id=user_id)
    context = dict(video=video, u=user)

    if hash and user.hash_for_video(video_id) == hash:
        video.followers.remove(user)
        for l in video.subtitlelanguage_set.all():
            l.followers.remove(user)
        if request.user.is_authenticated() and not request.user == user:
            logout(request)
    else:
        context['error'] = u'Incorrect secret hash'
    return render(request, 'videos/stop_notification.html', context)

@login_required
@require_POST
def video_url_make_primary(request):
    output = {}
    id = request.POST.get('id')
    status = 200
    if id:
        try:
            obj = VideoUrl.objects.get(id=id)
            tv = obj.video.get_team_video()
            if tv and not permissions.can_user_edit_video_urls(obj.video, request.user):
                output['error'] = ugettext('You have not permission change this URL')
                status = 403
            else:
                obj.make_primary(user=request.user)
        except VideoUrl.DoesNotExist:
            output['error'] = ugettext('Object does not exist')
            status = 404
    return HttpResponse(json.dumps(output), status=status)

@login_required
@require_POST
def video_url_remove(request):
    output = {}
    id = request.POST.get('id')
    status = 200
    if id:
        try:
            obj = VideoUrl.objects.get(id=id)
            tv = obj.video.get_team_video()
            if tv and not permissions.can_user_edit_video_urls(obj.video, request.user):
                output['error'] = ugettext('You have not permission delete this URL')
                status = 403
            else:
                try:
                    obj.remove(request.user)
                except IntegrityError, e:
                    output['error'] = str(e)
                    status = 403
        except VideoUrl.DoesNotExist:
            output['error'] = ugettext('Object does not exist')
            status = 404
    return HttpResponse(json.dumps(output), status=status)

@login_required
def video_url_create(request):
    output = {}

    form = CreateVideoUrlForm(request.user, request.POST)
    if form.is_valid():
        obj = form.save()
        video = form.cleaned_data['video']
        users = video.notification_list(request.user)

        for user in users:
            subject = u'New video URL added by %(username)s to "%(video_title)s" on amara.org'
            subject = subject % {'url': obj.url, 'username': obj.added_by, 'video_title': video}
            context = {
                'video': video,
                'video_url': obj,
                'user': user,
                'domain': settings.HOSTNAME,
                'hash': user.hash_for_video(video.video_id)
            }
            send_templated_email(user, subject,
                                 'videos/email_video_url_add.html',
                                 context, fail_silently=not settings.DEBUG)
    else:
        output['errors'] = form.get_errors()

    return HttpResponse(json.dumps(output))

@staff_member_required
def reindex_video(request, video_id):
    video = get_object_or_404(Video, video_id=video_id)
    video.update_search_index()

def subscribe_to_updates(request):
    email_address = request.POST.get('email_address', '')
    data = urllib.urlencode({'email': email_address})
    req = urllib2.Request(
        'http://pcf8.pculture.org/interspire/form.php?form=3', data)
    urllib2.urlopen(req)
    return HttpResponse('ok', 'text/plain')

@never_in_prod
@staff_member_required
def video_staff_delete(request, video_id):
    video = get_object_or_404(Video, video_id=video_id)
    video.delete()
    return HttpResponse("ok")

def video_debug(request, video_id):
    from widget import video_cache as vc
    from django.core.cache import cache
    from videos.models import VIDEO_TYPE_YOUTUBE

    video = get_object_or_404(Video, video_id=video_id)
    vid = video.video_id
    get_subtitles_dict = {}

    for l in video.newsubtitlelanguage_set.all():
        cache_key = vc._subtitles_dict_key(vid, l.pk, None)
        get_subtitles_dict[l.language_code] = cache.get(cache_key)

    cache = {
        "get_video_urls": cache.get(vc._video_urls_key(vid)),
        "get_subtitles_dict": get_subtitles_dict,
        "get_video_languages": cache.get(vc._video_languages_key(vid)),

        "get_video_languages_verbose": cache.get(vc._video_languages_verbose_key(vid)),
        "writelocked_langs": cache.get(vc._video_writelocked_langs_key(vid)),
    }

    tasks = Task.objects.filter(team_video=video)

    is_youtube = video.videourl_set.filter(type=VIDEO_TYPE_YOUTUBE).count() != 0

    return render(request, "videos/video_debug.html", {
            'video': video,
            'is_youtube': is_youtube,
            'tasks': tasks,
            "cache": cache
    })

def reset_metadata(request, video_id):
    video = get_object_or_404(Video, video_id=video_id)
    video_changed_tasks.delay(video.id)
    return HttpResponse('ok')

def set_original_language(request, video_id):
    """
    We only allow if a video is own a team, or the video owner is the
    logged in user
    """
    video = get_object_or_404(Video, video_id=video_id)
    if not (can_edit_video(video.get_team_video(), request.user) or video.user == request.user):
        return HttpResponseForbidden("Can't touch this.")
    form = ChangeVideoOriginalLanguageForm(request.POST or None, initial={
        'language_code': video.primary_audio_language_code
    })
    if request.method == "POST" and form.is_valid():
        video.primary_audio_language_code = form.cleaned_data['language_code']
        video.save()
        messages.success(request, fmt(
            _(u'The language for %(video)s has been changed'),
            video=video))
        return HttpResponseRedirect(reverse("videos:set_original_language", args=(video_id,)))
    return render(request, "videos/set-original-language.html", {
        "video": video,
        'form': form
    })

@staff_member_required
def url_search(request):
    if request.POST:
        return url_search_move(request)
    if 'urls' in request.GET:
        return url_search_results(request)
    return render(request, "future/videos/url-search.html")

def url_search_results(request):
    urls = []
    for url in request.GET['urls'].split():
        if not url:
            continue
        vt = video_type_registrar.video_type_for_url(url)
        if vt:
            urls.append(vt.convert_to_video_url())
    video_urls = list(
        VideoUrl.objects
        .filter(url__in=urls)
        .select_related('video', 'video__teamvideo')
    )
    found_urls = set(vurl.url for vurl in video_urls)
    not_found = [
        url for url in urls
        if url not in found_urls
    ]
    video_urls.sort(key=lambda vurl: urls.index(vurl.url))
    videos = [vurl.video for vurl in video_urls]
    return render(request, "future/videos/url-search-results.html", {
        'videos': videos,
        'not_found': not_found,
        'move_to_options': teams.permissions.can_move_videos_to(request.user),
    })

def url_search_move(request):
    team = Team.objects.get(slug=request.POST['team'])
    if not teams.permissions.can_move_videos_to_team(request.user, team):
        raise PermissionDenied()
    videos = Video.objects.filter(video_id__in=request.POST.getlist('videos'))
    moved_a_video = False
    with transaction.atomic():
        for video in videos:
            try:
                team_video = video.get_team_video()
                if team_video:
                    team_video.move_to(team, user=request.user)
                else:
                    team.add_existing_video(video, request.user)
            except Video.DuplicateUrlError, e:
                if e.from_prevent_duplicate_public_videos:
                    msg = ugettext(
                        u"%(video)s not moved to %(team)s because it "
                        "would conflict with the team policy")
                else:
                    msg = ugettext(u"%(video)s already added to %(team)s")

                msg = fmt(msg, team=team, video=video.title_display())
                messages.error(request, msg)
            else:
                moved_a_video = True
    if moved_a_video:
        messages.success(request, fmt(ugettext(u'Videos moved to %(team)s'),
                                      team=team))
    return redirect(request.get_full_path())
