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
import base64
from urllib2 import URLError

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    REDIRECT_FIELD_NAME, get_backends, login as stock_login, authenticate,
    logout, login as auth_login
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import password_reset as contrib_password_reset
from django.core.cache import cache
from django.urls import reverse
from django.forms import ValidationError
from django.forms.utils import ErrorList
from django.http import (HttpResponseRedirect, HttpResponseForbidden,
                         HttpResponse, HttpResponseBadRequest)
from django.shortcuts import render, redirect, resolve_url
from django.template import RequestContext
from django.template.response import TemplateResponse
from django.utils.encoding import force_text
from django.utils.http import urlquote, urlsafe_base64_decode
from django.utils.translation import ugettext_lazy as _, get_language
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from oauth import oauth
from auth.forms import CustomUserCreationForm, ChooseUserForm, SecureAuthenticationForm, \
    DeleteUserForm, CustomPasswordResetForm, SecureCustomPasswordResetForm, EmailForm, \
    CustomSetPasswordForm
from openid_consumer.views import begin as begin_openid
from auth.models import (
    CustomUser, UserLanguage, EmailConfirmation, LoginToken
)
from auth.providers import get_authentication_provider
from ipware.ip import get_real_ip, get_ip
from thirdpartyaccounts.views import facebook_login, twitter_login
from externalsites.views import google_login
from utils import post_or_get_value
from utils.http import get_url_host
from utils.translation import get_user_languages_from_cookie

LOGIN_CACHE_TIMEOUT = 60

import logging
logger = logging.getLogger(__name__)

def login(request):
    redirect_to = post_or_get_value(request, REDIRECT_FIELD_NAME, '')
    if login_form_needs_captcha(request):
        form = SecureAuthenticationForm(label_suffix="")
    else:
        form = AuthenticationForm(label_suffix="")
    return render_login(request, CustomUserCreationForm(label_suffix=""),
                        form, redirect_to)

def logout(request):
    """Log the user out

    This method differs from the standard django one in a couple ways:

    - We delete the session and unset the session cookie (better for caching)
    - We redirect to a language-specific homepage URL
    """
    request.session.delete()
    response = HttpResponseRedirect("/{}/".format(get_language()))
    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    return response

def confirm_create_user(request, account_type, email):
    redirect_to = post_or_get_value(request, REDIRECT_FIELD_NAME, '')
    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            if account_type == 'facebook':
                return facebook_login(request, next=redirect_to, confirmed=True, email=email, form_data=form.cleaned_data)
            if account_type == 'google':
                return google_login(request, next=redirect_to, confirmed=True, email=email)
            if account_type == 'twitter':
                return twitter_login(request, next=redirect_to, confirmed=True, email=email)
            if account_type == 'ted':
                provider = get_authentication_provider('ted')
                return provider.view(request, confirmed=True, email=email)
    else:
        initial = {}
        if email:
            initial['email'] = email
        openid_url = request.GET.get('openid_url', '')
        if openid_url:
            initial['url'] = openid_url
        form = EmailForm(initial=initial)
    return render_login(request, CustomUserCreationForm(label_suffix=""),
                        AuthenticationForm(label_suffix=""), redirect_to, email_form=form, confirm_type=account_type)

def confirm_email(request, confirmation_key):
    confirmation_key = confirmation_key.lower()
    user = EmailConfirmation.objects.confirm_email(confirmation_key)
    if not user:
        messages.error(request, _(u'Confirmation key expired.'))
    else:
        messages.success(request, _(u'Email is confirmed.'))

    if request.user.is_authenticated():
        return redirect('profiles:dashboard')

    return redirect('/')

@login_required
def resend_confirmation_email(request):
    user = request.user
    if user.email and not user.valid_email:
        EmailConfirmation.objects.send_confirmation(user)
        messages.success(request, _(u'Confirmation email was sent.'))
    else:
        messages.error(request, _(u'You email is empty or already confirmed.'))
    return redirect(request.META.get('HTTP_REFERER') or request.user)

def create_user(request):
    redirect_to = make_redirect_to(request)
    form = CustomUserCreationForm(request.POST, label_suffix="")
    if form.is_valid():
        new_user = form.save()
        user = authenticate(username=new_user,
                            password=form.cleaned_data['password1'])
        langs = get_user_languages_from_cookie(request)
        for l in langs:
            UserLanguage.objects.get_or_create(user=user, language=l)
        auth_login(request, user)
        return HttpResponseRedirect(redirect_to)
    else:
        return render_login(request, form, AuthenticationForm(label_suffix=""), redirect_to)

@login_required
def delete_user(request):
    if not request.user.has_valid_password():
        return render(request, 'auth/delete_user.html', {})
    if request.method == 'POST':
        form = DeleteUserForm(request.POST)
        if form.is_valid():
             username = request.user.username
             password = form.cleaned_data['password']
             user = authenticate(username=username, password=password)
             if user:
                 user.deactivate_account()
                 if form.cleaned_data['delete_account_data']:
                    user.delete_account_data()
                 if form.cleaned_data['delete_videos_and_subtitles']:
                    user.delete_self_subtitled_videos()
                 logout(request)
                 messages.success(request, _(u'Your account was deleted.'))
                 return HttpResponseRedirect('/')
             else:
                 errors = form._errors.setdefault("password", ErrorList())
                 errors.append(_(u"Incorrect Password"))
    else:
        form = DeleteUserForm()
    return render(request, 'auth/delete_user.html', {
        'form': form
    })

def cache_key(request):
    ip = get_real_ip(request)
    if ip is None:
        ip = get_ip(request)
        if ip is None:
            ip = ""
    return "failed_attempt_{}".format(ip)

def cache_set(request):
    cache.set(cache_key(request), True, LOGIN_CACHE_TIMEOUT)

def cache_delete(request):
    cache.delete(cache_key(request))

def login_form_needs_captcha(request):
    return settings.ENABLE_LOGIN_CAPTCHA and cache.get(cache_key(request))

def login_post(request):
    redirect_to = make_redirect_to(request)
    form_has_no_captcha = False
    if 'captcha_0' in request.POST or login_form_needs_captcha(request):
        form = SecureAuthenticationForm(data=request.POST, label_suffix="")
    else:
        form_has_no_captcha = True
        form = AuthenticationForm(data=request.POST, label_suffix="")
    try:
        if form.is_valid():
            cache_delete(request)
            auth_login(request, form.get_user())
            if request.session.test_cookie_worked():
                request.session.delete_test_cookie()
            return HttpResponseRedirect(redirect_to)
        else:
            cache_set(request)
            if form_has_no_captcha and settings.ENABLE_LOGIN_CAPTCHA:
                form = SecureAuthenticationForm(data=request.POST, label_suffix="")
            return render_login(request, CustomUserCreationForm(label_suffix=""), form, redirect_to)
    except ValueError:
        cache_set(request)
        if form_has_no_captcha and settings.ENABLE_LOGIN_CAPTCHA:
            form = SecureAuthenticationForm(data=request.POST, label_suffix="")
        return render_login(request, CustomUserCreationForm(label_suffix=""), form, redirect_to)


def token_login(request, token):
    """
    Automagically logs a user in from a secret token.
    Will only work for the CustomUser backend, and will not
    let staff or admin users login.
    Receives a '?next=' parameter of where to redirect the user into
    If the token has expired or is not found, a 403 is returned.
    """
    # we return 403 even from not found tokens, just being a bit more
    # strict about not leaking valid tokens
    success = False
    try:
        lt = LoginToken.objects.get(token=token)
        if lt.is_valid():
            user = lt.user
            # this will only work if user has the CustoUser backend
            # not a third party provider
            backend = get_backends()[0]
            user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)
            stock_login(request, user)
            next_url = make_redirect_to(request, reverse("profiles:edit"))
            success = True
        lt.delete()
    except LoginToken.DoesNotExist:
        pass
    if success:
        return HttpResponseRedirect(next_url)
    else:
        return HttpResponseForbidden("Invalid user token")

@never_cache
def password_reset_confirm(request, uidb64=None, token=None,
                           template_name='registration/password_reset_confirm.html',
                           post_reset_redirect=None,
                           current_app=None, extra_context=None):
    """
    View that checks the hash in a password reset link and presents a
    form for entering a new password.
    """
    assert uidb64 is not None and token is not None  # checked by URLconf
    if post_reset_redirect is None:
        post_reset_redirect = reverse('password_reset_complete')
    else:
        post_reset_redirect = resolve_url(post_reset_redirect)
    try:
        # urlsafe_base64_decode() decodes to bytestring on Python 3
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = CustomUser._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        validlink = True
        # move to submit form function
        title = _('Enter new password')
        if request.method == 'POST':
            form = CustomSetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(post_reset_redirect)
        else:
            form = CustomSetPasswordForm(user)
    else:
        validlink = False
        form = None
        title = _('Password reset unsuccessful')

    context = {
        'form': form,
        'title': title,
        'validlink': validlink,
    }
    if extra_context is not None:
        context.update(extra_context)

    if current_app is not None:
        request.current_app = current_app

    return TemplateResponse(request, template_name, context)

def password_reset_complete(request,
                            template_name='registration/password_reset_complete.html',
                            current_app=None, extra_context=None):
    """
    The difference with the complete view from the contrib package
    is that is logs out the user.
    """
    context = {
        'login_url': settings.LOGIN_URL
    }
    if extra_context is not None:
        context.update(extra_context)
    logout(request)
    if current_app is not None:
        request.current_app = current_app

    return TemplateResponse(request, template_name, context)


@user_passes_test(lambda u: u.is_superuser)
def login_trap(request):
    if request.method == 'POST':
        form = ChooseUserForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['username']
            user.backend = getattr(settings, 'AUTHENTICATION_BACKENDS')[0]
            auth_login(request, user)
            return redirect('/')
    else:
        form = ChooseUserForm()
    return render(request, 'auth/login_trap.html', {
        'form': form
    })


# Helpers

def render_login(request, user_creation_form, login_form, redirect_to, email_form=None, confirm_type=None):
    redirect_to = redirect_to or '/'
    context = {
        REDIRECT_FIELD_NAME: redirect_to,
        'app_id': settings.FACEBOOK_APP_ID,
    }
    if confirm_type is None:
        context['creation_form'] = user_creation_form
        context['login_form'] = login_form
        context['ted_auth'] = get_authentication_provider('ted')
        context['facebook_login_confirm'] = reverse('thirdpartyaccounts:facebook_login_confirm');
        template = 'auth/login.html'
    else:
        if email_form:
            context['email_form'] = email_form
        template = 'auth/login_create.html'
        if confirm_type == 'ted':
            context['ted_auth'] = get_authentication_provider('ted')
        if confirm_type == 'facebook':
            context['submit_facebook'] = "submit-proceed-to-create-facebook"
    return render(request, template, context)

def make_redirect_to(request, default=''):
    """Get the URL to redirect to after logging a user in.

    This method has a simply check against open redirects to prevent attackers
    from putting their sites into the next GET param (see 1253)
    """
    redirect_to = post_or_get_value(request, REDIRECT_FIELD_NAME, default)
    if not redirect_to or '//' in redirect_to:
        return '/'
    else:
        return redirect_to

@csrf_protect
def password_reset(request):
    extra_context = {}
    if request.user.is_authenticated():
        extra_context = {'email_address': request.user.email}
        form = CustomPasswordResetForm
    else:
        form = SecureCustomPasswordResetForm
    return contrib_password_reset(request, password_reset_form=form, extra_context=extra_context)

@login_required
def set_hidden_message_id(request):
    try:
        message_id = request.POST['message_id']
    except KeyError:
        return HttpResponseBadRequest()
    request.user.set_last_hidden_message_id(request, message_id)
    return HttpResponse()
