# Amara, universalsubtitles.org
#
# Copyright (C) 2017 Participatory Culture Foundation
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

from django.test import TestCase
from nose.tools import *
import mock

from utils.memoize import memoize

class MemoizedFunctionTest(TestCase):
    def make_func(self):
        def func(*args, **kwargs):
            self.last_call = mock.call(*args, **kwargs)
        return func

    def make_memoized_function(self, key_func=None):
        func = self.make_func()
        if key_func:
            return memoize(key_func=key_func)(func)
        else:
            return memoize(func)

    def check_call_not_cached(self, *args, **kwargs):
        self.last_call = None
        self.memoized_func(*args, **kwargs)
        assert_equal(self.last_call, mock.call(*args, **kwargs))

    def check_call_cached(self, *args, **kwargs):
        self.last_call = None
        self.memoized_func(*args, **kwargs)
        assert_equal(self.last_call, None)

    def test_function(self):
        self.memoized_func = self.make_memoized_function()

        self.check_call_not_cached(1)
        # calling again with the same args, shouldn't generate a new call
        self.check_call_cached(1)
        # but different args should
        self.check_call_not_cached('foo', 'bar')
        # different args that compare equal should be cached
        self.check_call_cached(u'foo', u'bar')

    def test_clear_cache(self):
        self.memoized_func = self.make_memoized_function()
        self.check_call_not_cached(1)
        self.memoized_func.clear_cache()
        self.check_call_not_cached(1)

    def test_key_function(self):
        # dicts are not hashable by default.  The key_func must be used to
        # hash them
        def key_func(dct):
            return dct['val']
        self.memoized_func = self.make_memoized_function(key_func)
        obj = { 'val': 1 }
        self.check_call_not_cached(obj)
        self.check_call_cached(obj)

class MemoizedMethodTest(MemoizedFunctionTest):
    def make_func(self):
        test_self = self
        class TestObject(object):
            def method(self, *args, **kwargs):
                assert_equal(self, test_self.obj)
                test_self.last_call = mock.call(*args,**kwargs)
        self.obj = TestObject()
        return self.obj.method

class MemoizedStaticMethodTest(MemoizedFunctionTest):
    def make_func(self):
        test_self = self
        class TestObject(object):
            @staticmethod
            def method(*args, **kwargs):
                test_self.last_call = mock.call(*args,**kwargs)

        self.obj = TestObject()
        return self.obj.method

class MemoizedClassMethodTest(MemoizedFunctionTest):
    def make_func(self):
        test_self = self
        class TestObject(object):
            @classmethod
            def method(cls, *args, **kwargs):
                assert_equal(cls, TestObject)
                test_self.last_call = mock.call(*args,**kwargs)

        self.obj = TestObject()
        return self.obj.method
