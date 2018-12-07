# Amara, universalsubtitles.org
#
# Copyright (C) 2015 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

"""utils.test_utils.requests

Mock out calls to the requests library.
"""
from __future__ import absolute_import
import collections
import json
import urlparse
from requests.auth import HTTPBasicAuth

from nose.tools import *
import mock
import requests

REQUEST_CALLBACKS = []

class Response(dict):
    status = 200
    content = ""

    def __getitem__(self, key):
        return getattr(self, key)

def reset_requests():
    global REQUEST_CALLBACKS
    REQUEST_CALLBACKS = []

def store_request_call(url, **kwargs):
    method = kwargs.pop('method', None)
    data = urlparse.parse_qs(kwargs.pop("body", ""))
    for k,v in data.items():
        data[k] = v[0]
    global REQUEST_CALLBACKS
    if not '/solr' in url:
        REQUEST_CALLBACKS.append([url, method, data])
    return Response(), ""

ExpectedRequest = collections.namedtuple(
    "ExpectedRequest",
    "method url params data headers body status_code error auth")

def assert_auth_equal(auth, correct_auth):
    if isinstance(correct_auth, HTTPBasicAuth):
        # We need to check the hard way because HTTPBasicAuth doesn't
        # implemint __equals__
        assert_equal((auth.username, auth.password),
                     (correct_auth.username, correct_auth.password))
    else:
        return assert_equal(auth, correct_auth)

class RequestsMocker(object):
    """Mock code that uses the requests module

    This object patches the various network functions of the requests module
    (get, post, put, delete) with mock functions.  You tell it what requests
    you expect, and what responses to return.

    Example:

    mocker = RequestsMocker()
    mocker.expect_request('get', 'http://example.com/', body="foo")
    mocker.expect_request('post', 'http://example.com/form',
        data={'foo': 'bar'}, body="Form OK")
    with mocker:
        function_to_test()
    """

    def __init__(self):
        self.expected_requests = []

    def expect_request(self, method, url, params=None, data=None,
                       headers=None, body='', status_code=200, error=None,
                       auth=None):
        self.expected_requests.append(
            ExpectedRequest(method, url, params, data, headers, body,
                            status_code, error, auth))

    def __enter__(self):
        self.setup_patchers()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unpatch()
        if exc_type is None:
            self.check_no_more_expected_calls()

    def setup_patchers(self):
        self.patchers = []
        for method in ('get', 'post', 'put', 'delete', 'request'):
            mock_obj = mock.Mock()
            mock_obj.side_effect = getattr(self, 'mock_%s' % method)
            patcher = mock.patch('requests.%s' % method, mock_obj)
            patcher.start()
            self.patchers.append(patcher)

    def unpatch(self):
        for patcher in self.patchers:
            patcher.stop()
        self.patchers = []

    def mock_get(self, url, params=None, data=None, headers=None, auth=None,
                 verify=True):
        return self.check_request('get', url, params, data, headers, auth)

    def mock_post(self, url, params=None, data=None, headers=None, auth=None,
                  verify=True):
        return self.check_request('post', url, params, data, headers, auth)

    def mock_put(self, url, params=None, data=None, headers=None, auth=None,
                 verify=True):
        return self.check_request('put', url, params, data, headers, auth)

    def mock_delete(self, url, params=None, data=None, headers=None,
                    auth=None, verify=True):
        return self.check_request('delete', url, params, data, headers, auth)

    def mock_request(self, method, url, params=None, data=None, headers=None,
                     auth=None, verify=True):
        return self.check_request(method.lower(), url, params, data, headers,
                                  auth)

    def check_request(self, method, url, params, data, headers, auth):
        try:
            expected = self.expected_requests.pop(0)
        except IndexError:
            raise AssertionError("RequestsMocker: No more calls expected, "
                                 "but got %s %s %s %s" % 
                                 (method, url, params, data, headers))

        assert_equal(method, expected.method)
        assert_equal(url, expected.url)
        assert_equal(params, expected.params)
        if (expected.headers is not None and
            expected.headers.get('content-type') == 'application/json'):
            assert_equal(json.loads(data), json.loads(expected.data))
        else:
            assert_equal(data, expected.data)
        assert_equal(headers, expected.headers)
        assert_auth_equal(auth, expected.auth)
        if expected.error:
            raise expected.error
        request = requests.Request(method=method, url=url, params=params,
                                   data=data, headers=headers)
        return self.make_response(request, expected.status_code, expected.body)

    def make_response(self, request, status_code, body):
        response = requests.Response()
        response._content = body
        response.status_code = status_code
        response.request = request
        return response

    def check_no_more_expected_calls(self):
        if self.expected_requests:
            raise AssertionError(
                "leftover expected calls:\n" +
                "\n".join('%s %s %s' % (er.method, er.url, er.params)
                          for er in self.expected_requests))
