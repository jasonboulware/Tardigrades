# Amara, universalsubtitles.org
#
# Copyright (C) 2015 Participatory Culture Foundation
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

from __future__ import absolute_import

from django.test import TestCase
from nose.tools import *
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.reverse import reverse
from rest_framework.serializers import Serializer
from rest_framework.test import APIClient, APIRequestFactory
import mock

from api.fields import UserField
from api.tests.utils import user_field_data
from auth.models import CustomUser as User, LoginToken
from utils import test_utils
from utils.factories import *

class UserAPITest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.user.ensure_api_key_created()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.list_url = reverse('api:users-list')

    def detail_url(self, user):
        return reverse('api:users-detail', args=('id$' + user.secure_id(),))

    def assert_response_data_correct(self, response, user, method):
        for field in ('username', 'full_name', 'first_name', 'last_name',
                      'biography', 'homepage'):
            value = getattr(user, field)
            response_value = response.data[field]
            assert_equal(response_value, value,
                         '{} != {} (field: {})'.format(
                             response_value, value, field))

        if user.created_by:
            assert_equal(response.data['created_by'],
                         user.created_by.username)
        else:
            assert_equal(response.data['created_by'], None)
        assert_equal(response.data['id'], user.secure_id())
        assert_equal(response.data['avatar'], user.avatar())
        assert_equal(response.data['num_videos'], user.videos.count())
        assert_items_equal(response.data['languages'], user.get_languages())
        assert_equal(response.data['resource_uri'],
                     'http://testserver' + self.detail_url(user))

        if method == 'get':
            assert_not_in('email', response.data)
            assert_not_in('api_key', response.data)
        elif method == 'put':
            assert_equal(response.data['email'], user.email)
            assert_not_in('api_key', response.data)
        else:
            assert_equal(response.data['email'], user.email)
            assert_equal(response.data['api_key'], user.api_key.key)

    def test_get_details(self):
        user = UserFactory(
            username='test-username',
            full_name='Test Name',
            first_name='Test',
            last_name='Name',
            biography='test bio',
            homepage='http://example.com/homepage.html',
            languages=['en', 'fr', 'pt-br'],
        )
        for i in range(3):
            VideoFactory(user=self.user)
        response = self.client.get(self.detail_url(user))
        assert_equal(response.status_code, status.HTTP_200_OK,
                     response.content)
        self.assert_response_data_correct(response, user, 'get')

    def test_get_with_username(self):
        user = UserFactory()
        url =reverse('api:users-detail', args=(user.username,))
        response = self.client.get(url)
        assert_equal(response.status_code, status.HTTP_200_OK,
                     response.content)
        self.assert_response_data_correct(response, user, 'get')

    def check_user_data(self, user, data, orig_user_data=None):
        if orig_user_data is None:
            orig_user_data = {
                'first_name': '',
                'last_name': '',
                'password': '',
            }
        for name in ('email', 'first_name', 'last_name'):
            if name in data:
                assert_equal(getattr(user, name), data[name])
            else:
                assert_equal(getattr(user, name), orig_user_data[name])
        if 'password' in data:
            assert_true(user.check_password(data['password']))
        elif 'password':
            assert_equal(user.password, orig_user_data['password'])

    def check_post(self, data):
        response = self.client.post(self.list_url, data=data)
        assert_equal(response.status_code, status.HTTP_201_CREATED,
                     response.content)
        user = User.objects.get(username=response.data['username'])
        self.check_user_data(user, data)
        assert_equal(user.created_by, self.user)
        self.assert_response_data_correct(response, user, 'post')
        return user, response

    def check_post_permission_denied(self, data):
        response = self.client.post(self.list_url, data=data)
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN,
                     response.content)
        return response

    def test_create_user(self):
        self.user.is_partner = True
        self.check_post({
            'username': 'test-user',
            'email': 'test@example.com',
            'password': 'test-password',
            'first_name': 'Test',
            'last_name': 'User',
            'full_name': 'Test User',
            'bio': 'test-bio',
            'homepage': 'http://example.com/test/'
        })

    def test_create_user_denied(self):
        self.user.is_partner = False
        response = self.check_post_permission_denied({
            'username': 'test-user',
            'email': 'test@example.com',
            'password': 'test-password',
            'first_name': 'Test',
            'last_name': 'User',
            'full_name': 'Test User',
            'bio': 'test-bio',
            'homepage': 'http://example.com/test/'
        })
        assert_equal(response.content, """{"detail":"Permission denied."}""")

    def test_create_user_with_unique_username(self):
        UserFactory(username='test-user')
        self.user.is_partner = True
        user, response = self.check_post({
            'username': 'test-user',
            'find_unique_username': 1,
            'email': 'test@example.com',
            'password': 'test-password',
            'first_name': 'Test',
            'last_name': 'User',
            'full_name': 'Test User',
            'bio': 'test-bio',
            'homepage': 'http://example.com/test/'
        })
        assert_equal(user.username, 'test-user00')

    def test_create_partner(self):
        self.user.is_partner = True
        user, response = self.check_post({
            'username': 'test-user',
            'email': 'test@example.com',
            'password': 'test-password',
            'is_partner': True,
        })
        assert_true(user.is_partner)

    def test_only_partners_can_create_users(self):
        self.user.is_partner = False
        response = self.client.post(self.list_url, {
            'username': 'test-user',
            'email': 'test@example.com',
            'password': 'test-password',
        })
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_with_dollar_sign(self):
        # The dollar sign is reserved for identifiers, so we should prevent
        # creating users with this.
        response = self.client.post(self.list_url, {
            'username': 'test$user',
        })
        assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_username_max_length(self):
        # we should only allow 30 chars for the username length
        response = self.client.post(self.list_url, {
            'username': 'a' * 31,
            'find_unique_username': 1,
            'email': 'test@example.com',
        })
        assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unique_username_max_length(self):
        # we should only allow 24 chars for the username length, since we may
        # add up to 6 extra to make it unique
        response = self.client.post(self.list_url, {
            'username': 'a' * 25,
            'find_unique_username': 1,
            'email': 'test@example.com',
        })
        assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_user_partial_data(self):
        self.user.is_partner = True
        self.check_post({
            'username': 'test-user',
            'email': 'test@example.com',
        })

    def test_create_user_blank_data(self):
        self.user.is_partner = True
        self.check_post({
            'username': 'test-user',
            'email': 'test@example.com',
            'first_name': '',
            'last_name': '',
            'full_name': '',
            'bio': '',
            'homepage': '',
        })

    def test_create_user_non_unique_username(self):
        UserFactory(username='test-user')
        self.user.is_partner = True
        response = self.client.post(self.list_url, {
            'username': 'test-user',
            'email': 'test@example.com',
        })
        assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_user_non_ascii_username(self):
        response = self.client.post(self.list_url, {
            'username': '\xc4\x8devap\xc4\x8di\xc4\x87i',
            'email': 'test@example.com',
        }, format='json')
        assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_token(self):
        self.user.is_partner = True
        user, response = self.check_post({
            'username': 'test-user',
            'email': 'test@example.com',
            'create_login_token': True,
        })
        token = LoginToken.objects.get(user=user)
        self.check_login_token(response, token)

    def check_login_token(self, response, token):
        assert_equal(response.data['auto_login_url'],
                     'http://testserver' + reverse("auth:token-login",
                                                   args=(token.token,)))

    def check_put(self, data):
        orig_user_data = self.user.__dict__.copy()
        response = self.client.put(self.detail_url(self.user), data=data)
        assert_equal(response.status_code, status.HTTP_200_OK,
                     response.content)
        user = test_utils.reload_obj(self.user)
        self.check_user_data(user, data, orig_user_data)
        assert_equals(user.created_by, None)
        self.assert_response_data_correct(response, user, 'put')
        return response

    def test_update_user(self):
        self.check_put({
            'email': 'new-email@example.com',
            'first_name': 'New',
            'last_name': 'Newson',
        })

    def test_update_user_partial_data(self):
        self.check_put({
            'email': 'new-email@example.com',
        })

    def test_delete_user(self):
        response = self.client.delete(self.detail_url(self.user))
        assert_equal(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED,
                     response.content)

    def test_update_with_create_login_token(self):
        response = self.check_put({
            'create_login_token': True,
        })
        token = LoginToken.objects.get(user=self.user)
        self.check_login_token(response, token)
        # test a second update, we should create a new token
        response = self.check_put({
            'create_login_token': True,
        })
        token2 = LoginToken.objects.get(user=self.user)
        assert_not_equal(token.token, token2.token)
        self.check_login_token(response, token2)

    def test_cant_change_other_user(self):
        other_user = UserFactory()
        response = self.client.put(self.detail_url(other_user), data={
            'first_name': 'New',
        })
        assert_equal(response.status_code, status.HTTP_403_FORBIDDEN,
                     response.content)

    def test_cant_change_username(self):
        orig_username = self.user.username
        response = self.client.put(self.detail_url(self.user), data={
            'username': 'new-username',
        })
        assert_equal(response.status_code, status.HTTP_200_OK)
        assert_equal(test_utils.reload_obj(self.user).username, orig_username)

class UserFieldTest(TestCase):
    def setUp(self):
        self.field = UserField()
        self.serializer = Serializer(context={
            'request': APIRequestFactory().get('/'),
        })
        self.field.bind('user', self.serializer)
        self.user = UserFactory()

    def test_output(self):
        assert_equal(self.field.to_representation(self.user),
                     user_field_data(self.user))

    @test_utils.patch_for_test('api.userlookup.lookup_user')
    def test_input(self, lookup_user):
        # Input should be done using the userlookup module.  This allows us to
        # input users using usernames, user ids, or partner ids
        lookup_user.return_value = self.user
        assert_equal(self.field.to_internal_value('test-user-id'),
                     self.user)
        assert_equal(lookup_user.call_args, mock.call('test-user-id'))

    @test_utils.patch_for_test('api.userlookup.lookup_user')
    def test_user_not_found(self, lookup_user):
        # If lookup_user raises a User.DoesNotExist error, we should turn it
        # into a validation error
        lookup_user.side_effect = User.DoesNotExist
        with assert_raises(ValidationError):
            self.field.to_internal_value('test-user-id')
