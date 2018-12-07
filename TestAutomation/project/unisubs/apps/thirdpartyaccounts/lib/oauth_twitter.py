import httplib
import json
import requests
import time
import urllib2
import urllib
import urlparse

from requests_oauthlib import OAuth1
from urllib2 import URLError, HTTPError

from django.conf import settings

from auth.models import CustomUser as User
from thirdpartyaccounts.models import TwitterAccount

REQUEST_TOKEN_URL = 'https://twitter.com/oauth/request_token'
AUTHORIZATION_URL = 'http://twitter.com/oauth/authorize'
ACCESS_TOKEN_URL = 'https://twitter.com/oauth/access_token'
VERIFY_CREDENTIALS_URL = 'https://api.twitter.com/1.1/account/verify_credentials.json'

class TwitterOAuth1(object):
    """A helper class containing all of the Twitter OAuth session requests.
    """

    def __init__(self, consumer_key, consumer_secret, owner_key=None, owner_secret=None, verifier=None):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.owner_key = owner_key
        self.owner_secret = owner_secret
        self.verifier = verifier

    def _get_session(self, callback_url=None):
        session = OAuth1(self.consumer_key,
                         client_secret=self.consumer_secret,
                         resource_owner_key=self.owner_key,
                         resource_owner_secret=self.owner_secret,
                         verifier=self.verifier,
                         callback_uri=callback_url)
        return session

    def fetch_request_token(self, callback_url=None):
        session = self._get_session(callback_url=callback_url)
        try:
            r = requests.post(url=REQUEST_TOKEN_URL, auth=session)
            r.raise_for_status()
        except (URLError, HTTPError, requests.exceptions.RequestException) as e:
            raise e

        credentials = urlparse.parse_qs(r.content)
        return credentials
    
    def authorize_token_url(self, oauth_token):
        return AUTHORIZATION_URL + '?oauth_token=' + oauth_token

    def fetch_access_token(self):
        session = self._get_session()
        try:
            r = requests.post(url=ACCESS_TOKEN_URL, auth=session)
            r.raise_for_status()
        except (URLError, HTTPError, requests.exception.RequestException) as e:
            raise e

        credentials = urlparse.parse_qs(r.content)
        return credentials

    def get_user_info(self, get_email=True):
        session = self._get_session()
        params = {'include_email': True} if get_email else None

        try:
            r = requests.get(url=VERIFY_CREDENTIALS_URL, auth=session, params=params)
            r.raise_for_status()
        except (HTTPError, Exception) as e:
            raise e
        return json.loads(r.content)

    def _get_name_from_user_info(self, user_info):
        name_data = user_info.get('name').split()
        try:
            first, last = name_data[0], ' '.join(name_data[1:])
        except:
            first, last = user_info.get('screen_name'), ''
        return first, last

    def get_or_create_twitter_account(self, amara_user):
        user_info = self.get_user_info()
        # get username and email
        username = user_info.get('screen_name')
        email = user_info.get('email', None)

        # check for TwitterAccount with existing username
        try:
            account = TwitterAccount.objects.get(username=username)
        except TwitterAccount.DoesNotExist:
            account = TwitterAccount.objects.create(user=amara_user,
                                                    username=username,
                                                    access_token=self.owner_key)

        return account

    def create_user_from_twitter(self):
        user_info = self.get_user_info()
        username = user_info.get('screen_name')
        try:
            account = TwitterAccount.objects.get(username=username)
            user = User.objects.get(pk=account.user_id)
        except (TwitterAccount.DoesNotExist, User.DoesNotExist):
            first_name, last_name = self._get_name_from_user_info(user_info)
            avatar = user_info.get('profile_image_url_https')
            email = user_info.get('email', '')
            user = User.objects.create_with_unique_username(username=username,
                        email=email, first_name=first_name, last_name=last_name)
            temp_password = User.objects.make_random_password(length=24)
            user.set_password(temp_password)
            user.save()

            account = TwitterAccount.objects.create(user=user, username=username,
                                      access_token=self.owner_key, avatar=avatar)

    def access_resource(self, oauth_request):
        # via post body
        # -> some protected resources
        headers = {'Content-Type' :'application/x-www-form-urlencoded'}
        self.connection.request('POST', RESOURCE_URL, body=oauth_request.to_postdata(), headers=headers)
        response = self.connection.getresponse()
        return response.read()
