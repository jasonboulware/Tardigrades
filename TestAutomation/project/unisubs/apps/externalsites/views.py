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

import logging, json

from django.contrib import messages
from django.contrib import auth
from django.contrib.auth.views import redirect_to_login
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponseRedirect, Http404, HttpResponseBadRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import is_safe_url
from django.utils.translation import ugettext as _

from auth.models import CustomUser as User
from externalsites import forms, new_forms
from externalsites import google, vimeo, tasks
from externalsites.auth_backends import OpenIDConnectInfo, OpenIDConnectBackend
from externalsites.exceptions import YouTubeAccountExistsError, VimeoSyncAccountExistsError
from externalsites.models import (get_sync_account, SyncHistory, YouTubeAccount,
                                  VimeoSyncAccount, BrightcoveCMSAccount, KalturaAccount,
                                  SyncedSubtitleVersion, SyncHistory)
from localeurl.utils import universal_url
from subtitles.models import SubtitleLanguage
from teams.models import Team
from teams.permissions import can_change_team_settings, can_resync
from videos import permissions
from teams.views import settings_page
from teams.new_views import team_view
from ui import AJAXResponseRenderer
from utils.breadcrumbs import BreadCrumb
from utils.http import get_url_host
from utils.pagination import AmaraPaginatorFuture
from utils.text import fmt
from videos.models import VideoUrl

logger = logging.getLogger('amara.externalsites.views')

SUBTITLE_EXPORTS_PER_PAGE = 20

class AccountFormHandler(object):
    """Handles a single form for the settings tab

    On the settings tab we show several forms for different accounts.
    AccountFormHandler handles the logic for a single form.
    """
    def __init__(self, form_name, form_class):
        self.form_name = form_name
        self.form_class = form_class
        self.should_redirect = False

    def handle_post(self, post_data, context):
        pass

    def handle_get(self, post_data, context):
        pass

def add_youtube_account_url(owner):
    path = reverse('externalsites:youtube-add-account')
    if isinstance(owner, Team):
        return '%s?team_slug=%s' % (path, owner.slug)
    elif isinstance(owner, User):
        return '%s?username=%s' % (path, owner.username)
    else:
        raise ValueError("Unknown owner type: %s" % owner)

def add_vimeo_account_url(owner):
    path = reverse('externalsites:vimeo-add-account')
    if isinstance(owner, Team):
        return '%s?team_slug=%s' % (path, owner.slug)
    elif isinstance(owner, User):
        return '%s?username=%s' % (path, owner.username)
    else:
        raise ValueError("Unknown owner type: %s" % owner)

@settings_page
def team_settings_tab(request, team):
    if not team.is_old_style():
        return team_externalsites(request, team)

    if request.method == 'POST':
        formset = forms.AccountFormset(request.user, team, request.POST)
    else:
        formset = forms.AccountFormset(request.user, team, None)

    if formset.is_valid():
        formset.save()
        if 'remove-youtube-account' in request.POST:
            account = YouTubeAccount.objects.for_owner(team).get(
                id=request.POST['remove-youtube-account'])
            account.delete()
        elif 'remove-vimeo-account' in request.POST:
            account = VimeoSyncAccount.objects.for_owner(team).get(
                id=request.POST['remove-vimeo-account'])
            account.delete()
        return redirect(settings_page_redirect_url(team, formset))
    
    if team.is_old_style():
        template_name = 'externalsites/team-settings-tab.html'
    else:
        template_name = 'externalsites/new-team-settings-tab.html'

    return render(request, template_name, {
        'team': team,
        'forms': formset,
        'breadcrumbs': [
            BreadCrumb(team, 'teams:dashboard', team.slug),
            BreadCrumb(_('Settings'), 'teams:settings_basic', team.slug),
            BreadCrumb(_('Integrations')),
        ],
    })

# no need to wrap this view function since the calling view is already wrapped
def team_externalsites(request, team):
    form_name = request.GET.get('form', None)
    filters_form = new_forms.AccountFiltersForm(team, request.GET)
    sync_history_filters_form = new_forms.SyncHistoryFiltersForm(request.GET)

    if form_name:
        return team_edit_external_account(request, team, form_name)

    yt_accounts = YouTubeAccount.objects.for_team_or_synced_with_team(team).distinct()
    vimeo_accounts = VimeoSyncAccount.objects.for_team_or_synced_with_team(team).distinct()
    kaltura_accounts = KalturaAccount.objects.for_owner(team)
    brightcove_accounts = BrightcoveCMSAccount.objects.for_owner(team)

    yt_accounts = filters_form.youtube_accounts(yt_accounts)
    vimeo_accounts = filters_form.vimeo_accounts(vimeo_accounts)
    kaltura_accounts = filters_form.kaltura_accounts(kaltura_accounts)
    brightcove_accounts = filters_form.brightcove_accounts(brightcove_accounts)

    sync_history = SyncHistory.objects.for_owner_latest_per_video_and_language(team)
    sync_history_r = sync_history_filters_form.update_results(sync_history)
    sync_history_paginator = AmaraPaginatorFuture(sync_history_r, SUBTITLE_EXPORTS_PER_PAGE)
    sync_history_page = sync_history_paginator.get_page(request)

    context = {
        'team': team,
        'yt_accounts': yt_accounts,
        'vimeo_accounts': vimeo_accounts,
        'kaltura_accounts': kaltura_accounts,
        'brightcove_accounts': brightcove_accounts,
        'filters_form': filters_form,
        'sync_history_filters_form': sync_history_filters_form,
        'team_nav': 'settings',
        'settings_tab': 'integrations',
        'add_youtube_url': add_youtube_account_url(team),
        'add_vimeo_url': add_vimeo_account_url(team),
        'kaltura_form': new_forms.KalturaAccountForm(team),
        'brightcove_form': new_forms.BrightcoveCMSAccountForm(team),

        # sync history pagination -- it's okay to generically name these contexts
        # as `paginator` and `page` since we dont paginate the accounts list
        'paginator': sync_history_paginator,
        'page': sync_history_page,
        'modal_tab': 'youtube',
    }

    if not form_name and request.is_ajax():   
        response_renderer = AJAXResponseRenderer(request)
        response_renderer.replace(
            '#integrations-list', 
            'future/teams/settings/integrations-list.html',
            context)
        response_renderer.replace(
            '#sync-history-list',
            'future/teams/settings/sync-history-list.html',
            context)    
        return response_renderer.render()

    return render(request, 'future/teams/settings/integrations.html', context)

@team_view
def team_edit_external_account(request, team, form_name=None):
    context = {}
    account = None
    template = 'future/teams/settings/forms/integrations-edit.html'

    if request.method == "POST":
        try:
            account_type = request.POST.get('accountType')
            account_pk = request.POST.get('accountPk')
            removing = request.POST.get('remove', False)
        except KeyError:
            return HttpResponseBadRequest()

        if account_type == YouTubeAccount.account_type:
            account = YouTubeAccount.objects.get(pk=account_pk)
            form = forms.YoutubeAccountForm(request.user, account, request.POST)
        elif account_type == VimeoSyncAccount.account_type:
            account = VimeoSyncAccount.objects.get(pk=account_pk)
            form = forms.VimeoAccountForm(request.user, account, request.POST)
        elif account_type == KalturaAccount.account_type:
            account = KalturaAccount.objects.get(pk=account_pk)
            form = new_forms.KalturaAccountForm(team, request.POST)
        elif account_type == BrightcoveCMSAccount.account_type:
            account = BrightcoveCMSAccount.objects.get(pk=account_pk)
            form = new_forms.BrightcoveCMSAccountForm(team, request.POST)

        account_verbose_name = account._meta.verbose_name

        if removing:
            form = new_forms.RemoveAccountForm(account)
            
        if form.is_valid():
            form.save()

            if removing:
                messages.success(request, 
                    _(u'{} removed'.format(account_verbose_name)))
            else:
                messages.success(request, 
                    _(u'{} {} settings updated'.format(account_verbose_name, account.readable_account_name())))
            response_renderer = AJAXResponseRenderer(request)
            response_renderer.reload_page()
            return response_renderer.render()
    else:
        try:
            account_pk = request.GET['selection']
        except KeyError:
            return HttpResponseBadRequest()   

        if form_name == 'edit-youtube':
            account = YouTubeAccount.objects.get(pk=account_pk)
            form = forms.YoutubeAccountForm(request.user, account)
        elif form_name == 'edit-vimeo':
            account = VimeoSyncAccount.objects.get(pk=account_pk)
            form = forms.VimeoAccountForm(request.user, account)
        elif form_name == 'edit-kaltura':
            account = KalturaAccount.objects.get(pk=account_pk)
            form = new_forms.KalturaAccountForm(team)
        elif form_name == 'edit-brightcove':
            account = BrightcoveCMSAccount.objects.get(pk=account_pk)
            form = new_forms.BrightcoveCMSAccountForm(team)

        if form_name == 'remove-youtube':
            account = YouTubeAccount.objects.get(pk=account_pk)
        elif form_name == 'remove-vimeo':
            account = VimeoSyncAccount.objects.get(pk=account_pk)
        elif form_name == 'remove-kaltura':
            account = KalturaAccount.objects.get(pk=account_pk)
        elif form_name == 'remove-brightcove':
            account = BrightcoveCMSAccount.objects.get(pk=account_pk)

        if form_name.startswith('remove'):
            form = new_forms.RemoveAccountForm(account)
            template = 'future/teams/settings/forms/integrations-remove.html'

    context['form'] = form
    context['team'] = team
    context['account'] = account
    context['account_type_display'] = account.readable_account_type()

    response_renderer = AJAXResponseRenderer(request)
    response_renderer.show_modal(template, context)
    return response_renderer.render()

@team_view
def team_add_external_account(request, team):
    modal_tab = ''
    if request.method == "POST":
        modal_tab = request.POST.get('modalTab')
        if modal_tab == 'kaltura':
            form = new_forms.KalturaAccountForm(team, request.POST)
            kaltura_form = form
            brightcove_form = new_forms.BrightcoveCMSAccountForm(team)
            account_str = _('Kaltura')
        elif modal_tab == 'brightcove':
            form = new_forms.BrightcoveCMSAccountForm(team, request.POST)
            brightcove_form = form
            kaltura_form = new_forms.KalturaAccountForm(team)
            account_str = _('Brightcove')

        if form.is_valid():
            form.save()
            messages.success(request, 
                             _(u'{} account information has been succesfully saved!'.format(account_str)))
            response_renderer = AJAXResponseRenderer(request)
            response_renderer.reload_page()
            return response_renderer.render()
    else:
        return HttpResponseBadRequest()

    response_renderer = AJAXResponseRenderer(request)
    response_renderer.show_modal('future/teams/settings/forms/integrations-add.html', 
        { 'team': team, 
          'add_youtube_url': add_youtube_account_url(team),
          'add_vimeo_url': add_vimeo_account_url(team),
          'kaltura_form': kaltura_form,
          'brightcove_form': brightcove_form,
          'modal_tab': modal_tab,
        })
    return response_renderer.render()

@settings_page
@login_required
def team_settings_sync_errors_tab(request, team):
    if not can_resync(team, request.user):
        return redirect_to_login(request.build_absolute_uri())
    if request.POST:        
        sh = SyncHistory.objects.get_attempts_to_resync(team=team)
        if sh:
            sync_items = sh
        else:
            sync_items = []
        form = forms.ResyncForm(request.POST, sync_items=sync_items)
        if form.is_valid():
            for (key, val) in form.sync_items():
                if val:
                    SyncHistory.objects.force_retry(key, team=team)
        
    sh = SyncHistory.objects.get_attempts_to_resync(team=team)
    if sh:
        sync_items = sh
    else:
        sync_items = []
        
    form = forms.ResyncForm(sync_items=sync_items)
    context = {
        'team': team,
        'form': form,
    }

    if team.is_old_style():
        template_name = 'externalsites/team-settings-sync-errors.html'
    else:
        context['nobulk'] = True
        template_name = 'externalsites/new-team-settings-sync-errors.html'

    return render(request, template_name, context)

# we pass the pk of the SyncHistory object to be exported inside the request
def export_subtitles(request):
    try:
        sync_history_pk = request.GET.get('pk')
    except KeyError:
        return HttpResponseBadRequest()

    try:
        sh = SyncHistory.objects.get(pk=sync_history_pk)
    except SyncHistory.DoesNotExist:
        return HttpResponse(status=500)

    account = sh.get_account()

    if account.update_subtitles(sh.video_url, sh.language):
        return HttpResponse(status=200)
    else:
        return HttpResponse(status=500)        

@login_required
def user_profile_sync_errors_tab(request):
    if request.POST:
        sh = SyncHistory.objects.get_attempts_to_resync(user=request.user)
        if sh:
            sync_items = sh
        else:
            sync_items = []
        form = forms.ResyncForm(request.POST, sync_items=sync_items)
        if form.is_valid():
            for (key, val) in form.sync_items():
                if val:
                    SyncHistory.objects.force_retry(key, user=request.user)

    sh = SyncHistory.objects.get_attempts_to_resync(user=request.user)
    if sh:
        sync_items = sh
    else:
        sync_items = []

    form = forms.ResyncForm(sync_items=sync_items)
    template_name = 'externalsites/user-profile-sync-errors.html'

    return render(request, template_name, {
        'user_info': request.user,
        'form': form,
    })

def settings_page_redirect_url(team, formset):
    redirect_path = formset.redirect_path()
    if redirect_path is not None:
        return redirect_path
    else:
        return reverse('teams:settings_externalsites', kwargs={
            'slug': team.slug,
        })

def google_callback_url():
    return universal_url(
        'externalsites:google-callback',
        protocol_override=settings.OAUTH_CALLBACK_PROTOCOL)

def google_login(request, next=None, confirmed=True, email=None):
    state_type = 'login'
    if confirmed:
        state_type += '-confirmed'
    state = {
        'type': state_type,
        'next': next or request.GET.get('next'),
    }
    if email is not None:
        state['email'] = email
    return redirect(google.request_token_url(
        google_callback_url(), 'online', state, ['profile', 'email']))

def handle_login_callback(request, auth_info, confirmed=True):
    profile_info = google.get_openid_profile(auth_info.access_token)
    openid_connect_info = OpenIDConnectInfo(
        auth_info.sub, profile_info.email, auth_info.openid_id, {
            'full_name': profile_info.full_name,
            'first_name': profile_info.first_name,
            'last_name': profile_info.last_name
        }
    )
    (existing_user, email) = OpenIDConnectBackend.pre_authenticate(openid_connect_info=openid_connect_info)
    if not confirmed and not existing_user:
        return redirect('auth:confirm_create_user', 'google', email)
    if 'email' in auth_info.state:
        email = auth_info.state['email']
    else:
        email = None
    user = auth.authenticate(openid_connect_info=openid_connect_info, email=email)
    if not user:
        messages.error(request, _("OpenID Connect error"))
        return redirect('home')
    auth.login(request, user)
    next_url = auth_info.state.get('next')
    if next_url and is_safe_url(next_url):
        return HttpResponseRedirect(next_url)
    else:
        return redirect('home')

def youtube_add_account(request):
    if 'team_slug' in request.GET:
        state = {'team_slug': request.GET['team_slug']}
    elif 'username' in request.GET:
        state = {'username': request.GET['username']}
    else:
        logging.error("youtube_add_account: Unknown owner")
        raise Http404()
    state['type'] = 'add-account'
    return redirect(google.request_token_url(
        google_callback_url(), 'offline', state,
        google.youtube_scopes()))

def vimeo_add_account(request):
    if 'team_slug' in request.GET:
        state = json.dumps({'team_slug': request.GET['team_slug']})
    elif 'username' in request.GET:
        state = json.dumps({'username': request.GET['username']})
    else:
        logging.error("vimeo_add_account: Unknown owner")
        raise Http404()
    auth_url = vimeo.get_auth_url(get_url_host(request), state)
    return HttpResponseRedirect(auth_url)


def vimeo_login_done(request):
    state = json.loads(request.GET.get('state'))
    code = request.GET.get('code')
    account_data = {}
    if 'error' in state:
        logger.error("vimeo_callback: invalid state data: %s" %
                     state)
        messages.error(request, _("Error in auth callback"))
        return redirect('home')
    if 'team_slug' in state:
        team = get_object_or_404(Team, slug=state['team_slug'])
        account_data['team'] = team
        redirect_url = reverse('teams:settings_externalsites', kwargs={
            'slug': team.slug,
        })
    elif 'username' in state:
        user = get_object_or_404(User, username=state['username'])
        account_data['user'] = user
        redirect_url = reverse('profiles:account')
    else:
        logger.error("vimeo_callback: invalid state data: %s" %
                     state)
        messages.error(request, _("Error in auth callback"))
        redirect_url = reverse('home')
    if 'code' is not None and request.GET.get('error') is None:
        try:
            token_message = vimeo.get_token(code)
            username = token_message['user']['name']
            account = VimeoSyncAccount.objects.create_or_update(username, token_message['access_token'], **account_data)
        except VimeoSyncAccountExistsError, e:
            messages.error(request,
                           already_linked_message(request.user, e.other_account))
    return HttpResponseRedirect(redirect_url)

def handle_add_account_callback(request, auth_info):
    try:
        user_info = google.get_youtube_user_info(auth_info.access_token)
    except google.APIError, e:
        logging.error("handle_add_account_callback: %s" % e)
        messages.error(request, e.message)
        # there's no good place to redirect the user to since we don't know
        # what team/user they were trying to add the account for.  I guess the
        # homepage is as good as any.
        return redirect('home')
    account_data = {
        'username': user_info.username,
        'channel_id': user_info.channel_id,
        'oauth_refresh_token': auth_info.refresh_token,
    }
    if 'team_slug' in auth_info.state:
        team = get_object_or_404(Team, slug=auth_info.state['team_slug'])
        account_data['team'] = team
        redirect_url = reverse('teams:settings_externalsites', kwargs={
            'slug': team.slug,
        })
    elif 'username' in auth_info.state:
        user = get_object_or_404(User, username=auth_info.state['username'])
        account_data['user'] = user
        redirect_url = reverse('profiles:account')
    else:
        logger.error("google_callback: invalid state data: %s" %
                     auth_info.state)
        messages.error(request, _("Error in auth callback"))
        return redirect('home')

    try:
        account = YouTubeAccount.objects.create_or_update(**account_data)
    except YouTubeAccountExistsError, e:
        messages.error(request,
                       already_linked_message(request.user, e.other_account))
        return HttpResponseRedirect(redirect_url)

    tasks.import_video_from_youtube_account.delay(account.id)
    return HttpResponseRedirect(redirect_url)

def google_callback(request):
    try:
        auth_info = google.handle_callback(request, google_callback_url())
    except google.APIError, e:
        logging.error("google_callback: %s" % e)
        messages.error(request, e.message)
        # there's no good place to redirect the user to since we don't know
        # what team/user they were trying to add the account for.  I guess the
        # homepage is as good as any.
        return redirect('home')

    callback_type = auth_info.state.get('type')
    if callback_type == 'login-confirmed':
        return handle_login_callback(request, auth_info, confirmed=True)
    elif callback_type == 'login':
        return handle_login_callback(request, auth_info, confirmed=False)
    elif callback_type == 'add-account':
        return handle_add_account_callback(request, auth_info)
    else:
        messages.warning(request,
                         _("Google Login Complete, but no next step"))
        return redirect('home')

def already_linked_message(user, other_account):
    if other_account.user is not None:
        return fmt(_('That account has already been linked '
                     'to the user %(username)s.'),
                   username=other_account.user.username)

    if can_change_team_settings(other_account.team, user):
        settings_link = reverse('teams:settings_externalsites', kwargs={
            'slug': other_account.team.slug,
        })
        return fmt(_('That account has already been linked '
                     'to the %(team)s team '
                     '(<a href="%(link)s">view settings page</a>).'),
                   team=other_account.team,
                   link=settings_link)
    else:
        return fmt(_('That account has already been linked '
                     'to the %(team)s team.'),
                   team=other_account.team)

@login_required
def resync(request, video_url_id, language_code):
    video_url = get_object_or_404(VideoUrl, id=video_url_id)
    video = video_url.video
    if not permissions.can_user_resync(video, request.user):
        return redirect_to_login(request.build_absolute_uri())
    language = video.subtitle_language(language_code)

    if request.method == 'POST':
        logger.info("resyncing subtitles: %s (%s)", video, video_url)
        _resync_video(video, video_url, language)

    redirect_url = reverse('videos:translation_history', kwargs={
        'video_id': video.video_id,
        'lang': language_code,
        'lang_id': language.id
    })
    return HttpResponseRedirect(redirect_url + '?tab=sync-history')

def _resync_video(video, video_url, language):
    account = get_sync_account(video, video_url)
    if account is None:
        return
    tip = language.get_public_tip()
    if tip is not None:
        account.update_subtitles(video_url, language)
    else:
        account.delete_subtitles(video_url, language)
