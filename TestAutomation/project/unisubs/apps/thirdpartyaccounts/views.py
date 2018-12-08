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
import base64, hashlib, hmac, json, datetime, requests, urlparse
from urllib2 import URLError

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.core.files.base import ContentFile
from django.urls import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import redirect
from django.utils.http import urlquote
from oauth import oauth
from requests_oauthlib import OAuth1
from auth.models import CustomUser as User
from thirdpartyaccounts.lib.oauth_twitter import TwitterOAuth1
from utils.http import get_url_host
from thirdpartyaccounts.auth_backends import FacebookAccount, FacebookAuthBackend, TwitterAuthBackend, TwitterAccount

import logging
logger = logging.getLogger(__name__)

# Twitter ---------------------------------------------------------------------
def twitter_login(request, next=None, confirmed=True, email=''):
    callback_url = None
    next = request.GET.get('next', next)
    if next is not None:
        callback_view = "thirdpartyaccounts:twitter_login_done"
        if not confirmed:
            callback_view += "_confirm"
        callback_url = '%s%s?next=%s&email=%s' % \
             (get_url_host(request),
             reverse(callback_view),
              urlquote(next),
              urlquote(email))

    twitter = TwitterOAuth1(settings.TWITTER_CONSUMER_KEY, settings.TWITTER_CONSUMER_SECRET)

    try:
        credentials = twitter.fetch_request_token(callback_url=callback_url)
    except:
        messages.error(request, 'Problem connecting to Twitter. Try again.')
        return redirect('auth:login')

    resource_owner_key = credentials.get('oauth_token')[0]
    resource_owner_secret = credentials.get('oauth_token_secret')[0]

    request.session['resource_owner_key'] = resource_owner_key
    request.session['resource_owner_secret'] = resource_owner_secret

    authorize_url = twitter.authorize_token_url(resource_owner_key)
    return HttpResponseRedirect(authorize_url)

def twitter_login_done(request, confirmed=True):

    resource_owner_key = request.session.get('resource_owner_key', None)
    resource_owner_secret = request.session.get('resource_owner_secret', None)
    verifier = request.GET.get("oauth_verifier", None)

    # If there is no token for session, it means we didn't redirect user to twitter
    if not resource_owner_key and resource_owner_secret:
        messages.error(request, "We didn't redirect you to twitter...")
        return redirect('auth:login')

    # If the tokens from the session and twitter don't match, something bad happened to tokens
    if resource_owner_key != request.GET.get('oauth_token', 'no-token'):
        del request.session['resource_owner_key']
        del request.session['resource_owner_secret']

        if request.GET.get('denied', None) is not None:
            messages.info(request, "Twitter authorization cancelled.")
            return redirect('profiles:account')

        messages.error(request, "Something wrong! Tokens do not match...")
        return redirect('auth:login')

    twitter = TwitterOAuth1(settings.TWITTER_CONSUMER_KEY,
                            settings.TWITTER_CONSUMER_SECRET,
                            owner_key=resource_owner_key,
                            owner_secret=resource_owner_secret,
                            verifier=verifier)
    try:
        credentials = twitter.fetch_access_token()
    except URLError:
        messages.error(request, 'Problem connecting to Twitter. Try again.')
        return redirect('auth:login')

    twitter.owner_key = credentials.get('oauth_token')[0]
    twitter.owner_secret = credentials.get('oauth_token_secret')[0]

    if request.session.get('no-login', False):
        if not request.user.is_authenticated():
            messages.error(request, 'You must be logged in.')
            return redirect('auth:login')

        try:
            account = twitter.get_or_create_twitter_account(request.user)
            if request.user.pk != account.user.pk:
                messages.error(request, 'Account already linked')
                return redirect('profiles:account')
        except Exception, e:
            # TODO: Raise something more useful here
            raise e

        del request.session['no-login']
        messages.info(request, 'Successfully linked a Twitter account')
        return redirect('profiles:account')

    if not confirmed:
        try:
            user_info = twitter.get_user_info()
            username = user_info.get('screen_name')
        except Exception, e:
            # TODO: Raise something more useful here
            raise e

        if not username:
            return redirect('auth:confirm_create_user', 'twitter')

    user_info = twitter.get_user_info()
    username, email = user_info.get('screen_name'), user_info.get('email', None)

    # make sure there's a twitter account associated with the user before logging in
    twitter.create_user_from_twitter()
    user = authenticate(username=username)

    # if user is authenticated then login user
    if user:
        auth_login(request, user)
    else:
        # We were not able to authenticate user
        # Redirect to login page
        del request.session['access_token']
        del request.session['request_token']
        return HttpResponseRedirect(reverse('auth:login'))

    # authentication was successful, use is now logged in
    return HttpResponseRedirect(request.GET.get('next') or settings.LOGIN_REDIRECT_URL)

# Facebook --------------------------------------------------------------------

def base64_url_decode(inp):
    padding_factor = (4 - len(inp) % 4) % 4
    inp += "="*padding_factor
    return base64.b64decode(unicode(inp).translate(dict(zip(map(ord, u'-_'), u'+/'))))

def parse_signed_request(signed_request, secret):
    l = signed_request.split('.', 2)
    encoded_sig = l[0]
    payload = l[1]

    sig = base64_url_decode(encoded_sig)
    data = json.loads(base64_url_decode(payload))

    if data.get('algorithm').upper() != 'HMAC-SHA256':
        logger.error('Unknown algorithm')
        return None
    else:
        expected_sig = hmac.new(secret, msg=payload, digestmod=hashlib.sha256).digest()

    if sig != expected_sig:
        return None
    return data

def facebook_login(request, next=None, confirmed=False, email=None, form_data=None):
    data = parse_signed_request(request.COOKIES['fbsr_' + settings.FACEBOOK_APP_ID], settings.FACEBOOK_SECRET_KEY)
    if data is None or \
       datetime.datetime.now() - datetime.datetime.fromtimestamp(data['issued_at']) > datetime.timedelta(minutes=2):
        return redirect('auth:login')
    next = request.GET.get('next', settings.LOGIN_REDIRECT_URL)
    try:
        account = FacebookAccount.objects.get(uid=data['user_id'])
        user = account.user
        if user.is_active:
            user = authenticate(facebook=True, user=user)
            auth_login(request, user)
            return redirect(next)
        else:
            account.delete()
            raise FacebookAccount.DoesNotExist
    except FacebookAccount.DoesNotExist:
        if confirmed:
            if form_data is not None and \
               'avatar' in form_data and \
               'first_name' in form_data and \
               'last_name' in form_data and \
               len(form_data['first_name'] + form_data['last_name']) > 0:
                user_created = False
                first_name = form_data['first_name']
                last_name = form_data['last_name']
                facebook_uid = data['user_id']
                img_url = form_data['avatar']
                email = email
                username_to_try = username_base = form_data['first_name']
                index = 1
                temp_password = User.objects.make_random_password(length=24)
                while not user_created:
                    try:
                        user = User(username=username_to_try, email=email, first_name=first_name,
                                    last_name=last_name)
                        user.set_password(temp_password)
                        user.save()
                        user_created = True
                    except:
                        username_to_try = '%s%d' % (username_base, index)
                        index += 1
                if img_url:
                    img = ContentFile(requests.get(img_url).content)
                    name = img_url.split('/')[-1]
                    user.picture.save(name, img, False)
                    FacebookAccount.objects.create(uid=facebook_uid, user=user,
                                                   avatar=img_url)
                user = authenticate(facebook=True, user=user)
                auth_login(request, user)
                return redirect('/')
        else:
            return redirect('auth:confirm_create_user', 'facebook', email)
    return redirect('auth:login')
