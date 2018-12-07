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
import logging
from datetime import datetime, timedelta
from itertools import groupby

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponseBadRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_unicode

from activity.models import ActivityRecord
from auth.models import CustomUser as User, AmaraApiKey
from profiles.forms import (EditUserForm, EditAccountForm, SendMessageForm,
                            EditAvatarForm, AdminProfileForm, EditNotificationsForm)
from profiles.rpc import ProfileApiClass
import externalsites.models
from utils.objectlist import object_list
from utils.orm import LoadRelatedQuerySet
from utils.rpc import RpcRouter
from utils.text import fmt
from teams.models import Task
from subtitles.models import SubtitleLanguage
from videos.models import (
    VideoUrl, Video, VIDEO_TYPE_YOUTUBE, VideoFeed
)

logger = logging.getLogger(__name__)


rpc_router = RpcRouter('profiles:rpc_router', {
    'ProfileApi': ProfileApiClass()
})

VIDEOS_ON_PAGE = getattr(settings, 'VIDEOS_ON_PAGE', 30)
LINKABLE_ACCOUNTS = ['youtube', 'twitter', 'facebook']


class OptimizedQuerySet(LoadRelatedQuerySet):

    def update_result_cache(self):
        videos = dict((v.id, v) for v in self._result_cache if not hasattr(v, 'langs_cache'))

        if videos:
            for v in videos.values():
                v.langs_cache = []

            langs_qs = SubtitleLanguage.objects.select_related('video').filter(video__id__in=videos.keys())

            for l in langs_qs:
                videos[l.video_id].langs_cache.append(l)


def profile(request, user_id):
    try:
        user = User.objects.get(username=user_id)
        if not user.is_active:
            raise Http404
    except User.DoesNotExist:
        try:
            user = User.objects.get(id=user_id)
            if not user.is_active:
                raise Http404
        except (User.DoesNotExist, ValueError):
            raise Http404    

    if request.user.is_staff:
        if request.method == 'POST':
            form = AdminProfileForm(instance=user, data=request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, _('Your profile has been updated.'))
                return redirect('profiles:profile', user_id=user.username)
        else:
            form = AdminProfileForm(instance=user)
    else:
        form = None
    qs = (ActivityRecord.objects.for_user(user)
          .select_related('video', 'team', 'user'))
    if request.user != user:
        qs = qs.viewable_by_user(request.user)

    extra_context = {
        'user_info': user,
        'form': form,
    }

    return object_list(request, queryset=qs, allow_empty=True,
                       paginate_by=settings.ACTIVITIES_ONPAGE,
                       template_name='profiles/view.html',
                       template_object_name='activity',
                       extra_context=extra_context)


@login_required
def dashboard(request):
    user = request.user

    tasks = user.open_tasks()
    since = datetime.now() - timedelta(days=30)

    # MySQL optimazies the team activity query very poorly if the user is not
    # part of any teams
    user_dashboard_extra = []
    user_dashboard_extra_list = []
    more_items = int(request.GET.get('more_extra_items', 0))
    if user.teams.all().exists():
        team_activity = (ActivityRecord.objects
                         .filter(team__in=user.teams.all(), created__gt=since)
                         .exclude(user=user)
                         .original())
        user_dashboard_extra_teams = []
        for team in user.teams.all():
            if not team.is_old_style() and team.new_workflow.user_dashboard_extra:
                user_dashboard_extra_teams.append(team)
        if user_dashboard_extra_teams:
            for extra, teams in groupby(user_dashboard_extra_teams, lambda x: x.new_workflow.user_dashboard_extra):
                head, bodies = extra(request, teams, more_items=more_items)
                if bodies:
                    user_dashboard_extra_list.append({'head': head, 'bodies': bodies})
    else:
        team_activity = ActivityRecord.objects.none()
    # Ditto for video activity
    if user.videos.all().exists():
        video_activity = (ActivityRecord.objects
                          .filter(video__in=user.videos.all(), created__gt=since)
                          .exclude(user=user)
                          .original())
    else:
        video_activity = ActivityRecord.objects.none()
    context = {
        'user_info': user,
        'team_activity': team_activity[:8],
        'video_activity': video_activity[:8],
        'tasks': tasks,
        'user_dashboard_extra': user_dashboard_extra_list,
        'more_items': (more_items + 10) if user_dashboard_extra_list else None
    }

    return render(request, 'profiles/dashboard.html', context)

def videos(request, user_id):
    try:
        user = User.objects.get(username=user_id)
        if not user.is_active:
            raise Http404
    except User.DoesNotExist:
        try:
            user = User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError):
            raise Http404    

    qs = Video.objects.filter(user=user).order_by('-edited')
    if not (request.user == user or request.user.is_superuser):
        qs = qs.filter(is_public=True)
    q = request.GET.get('q')

    if q:
        qs = qs.filter(Q(title__icontains=q)|Q(description__icontains=q))

    context = {
        'user_info': user,
        'query': q
    }

    qs = qs._clone()

    return object_list(request, queryset=qs,
                       paginate_by=VIDEOS_ON_PAGE,
                       template_name='profiles/videos.html',
                       extra_context=context,
                       template_object_name='user_video')


@login_required
def edit(request):
    if request.method == 'POST':
        # the form requires username and email
        # however, letting the user set it here isn't safe
        # (let the account view handle it)
        data = request.POST.copy()
        data['username'] = request.user.username
        data['email'] = request.user.email
        form = EditUserForm(data,
                            instance=request.user,
                            files=request.FILES, label_suffix="")
        if form.is_valid():
            form.save()
            messages.success(request, _('Your profile has been updated.'))
            return redirect('profiles:edit')
    else:
        form = EditUserForm(instance=request.user, label_suffix="")

    context = {
        'form': form,
        'user_info': request.user,
        'edit_profile_page': True
    }
    return render(request, 'profiles/edit.html', context)

@login_required
def account(request):
    if request.method == 'POST':
        if 'editaccount' in request.POST:
            editaccountform = EditAccountForm(request.POST,
                                              instance=request.user,
                                              files=request.FILES, label_suffix="",
                                              prefix='account')
            if editaccountform.is_valid():
                editaccountform.save()
                messages.success(request, _('Your account has been updated.'))
                return redirect('profiles:account')
            editnotificationsform = EditNotificationsForm(instance=request.user, label_suffix="", prefix='notifications')
        elif 'editnotifications' in request.POST:
            editnotificationsform = EditNotificationsForm(request.POST,
                                                          instance=request.user,
                                                          files=request.FILES, label_suffix="", prefix='notifications')
            if editnotificationsform.is_valid():
                editnotificationsform.save()
                messages.success(request, _('Your account has been updated.'))
                return redirect('profiles:account')
            editaccountform = EditAccountForm(instance=request.user, label_suffix="", prefix='account')
        else:
            return HttpResponseBadRequest()
    else:
        editnotificationsform = EditNotificationsForm(instance=request.user, label_suffix="", prefix='notifications')
        editaccountform = EditAccountForm(instance=request.user, label_suffix="", prefix='account')
    twitters = request.user.twitteraccount_set.all()
    facebooks = request.user.facebookaccount_set.all()

    context = {
        'editnotificationsform': editnotificationsform,
        'editaccountform': editaccountform,
        'user_info': request.user,
        'edit_profile_page': True,
        'youtube_accounts': (externalsites.models.YouTubeAccount
                             .objects.for_owner(request.user)),
        'vimeo_accounts': (externalsites.models.VimeoSyncAccount
                             .objects.for_owner(request.user)),
        'twitters': twitters,
        'facebooks': facebooks,
        'hide_prompt': True
    }

    return render(request, 'profiles/account.html', context)


@login_required
def send_message(request):
    output = dict(success=False)
    form = SendMessageForm(request.user, request.POST)
    if form.is_valid():
        form.send()
        output['success'] = True
    else:
        output['errors'] = form.get_errors()
    return HttpResponse(json.dumps(output), "text/javascript")


@login_required
def generate_api_key(request):
    key, created = AmaraApiKey.objects.get_or_create(user=request.user)
    if not created:
        key.generate_new_key()
    return HttpResponse(json.dumps({"key":key.key}))


@login_required
def edit_avatar(request):
    form = EditAvatarForm(request.POST, instance=request.user, files=request.FILES)
    if form.is_valid():
        form.save()
        result = {
            'status': 'success',
            'message': force_unicode(_('Your photo has been updated.'))
        }
    else:
        errors = []
        [errors.append(force_unicode(e)) for e in form.errors['picture']]
        result = {
            'status': 'error',
            'message': ''.join(errors)
        }
    result['avatar'] = request.user._get_avatar_by_size(240)
    return HttpResponse(json.dumps(result))


@login_required
def remove_avatar(request):
    if request.POST.get('remove'):
        request.user.picture = ''
        request.user.save()
        result = {
            'status': 'success',
            'message': force_unicode(_('Your photo has been removed.')),
            'avatar': request.user._get_avatar_by_size(240)
        }
    return HttpResponse(json.dumps(result))


@login_required
def add_third_party(request):
    account_type = request.GET.get('account_type', None)
    if not account_type:
        raise Http404

    if account_type not in LINKABLE_ACCOUNTS:
        raise Http404

    if account_type == 'twitter':
        request.session['no-login'] = True
        url = reverse('thirdpartyaccounts:twitter_login')

    if account_type == 'vimeo':
        request.session['vimeo-no-login'] = True
        url = reverse('thirdpartyaccounts:vimeo_login')

    if account_type == 'facebook':
        request.session['fb-no-login'] = True
        url = reverse('thirdpartyaccounts:facebook_login')

    return redirect(url)


@login_required
def remove_third_party(request, account_type, account_id):
    from thirdpartyaccounts.models import TwitterAccount, FacebookAccount

    if account_type == 'twitter':
        account = get_object_or_404(request.user.twitteraccount_set.all(),
                                    pk=account_id)
        account_type_name = _('Twitter account')
        account_owner = account.username
    elif account_type == 'facebook':
        account = get_object_or_404(request.user.facebookaccount_set.all(),
                                    pk=account_id)
        account_type_name = _('Facebook account')
        account_owner = account.uid
    elif account_type == 'vimeo':
        # map the account type string from the URL to the externalsites
        # model
        account_type_map = {
            'vimeo': externalsites.models.VimeoSyncAccount
        }
        qs = account_type_map[account_type].objects.for_owner(request.user)
        account = get_object_or_404(qs, id=account_id)
        account_type_name = account._meta.verbose_name
        account_owner = account.get_owner_display()
    else:
        # map the account type string from the URL to the externalsites
        # model
        account_type_map = {
            'youtube': externalsites.models.YouTubeAccount
        }
        qs = account_type_map[account_type].objects.for_owner(request.user)
        account = get_object_or_404(qs, id=account_id)
        account_type_name = account._meta.verbose_name
        account_owner = account.get_owner_display()
    if request.method == 'POST':
        account.delete()
        msg = _('Account deleted.')
        messages.success(request, msg)
        return redirect('profiles:account')

    context = {
        'user_info': request.user,
        'account_type_name': account_type_name,
        'account_owner': account_owner,
    }
    return render(request, 'profiles/remove-third-party.html', context)
