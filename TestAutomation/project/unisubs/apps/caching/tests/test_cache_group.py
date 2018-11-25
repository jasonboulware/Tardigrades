# Amara, universalsubtitles.org
#
# Copyright (C) 2014 Participatory Culture Foundation
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

from __future__ import absolute_import

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.test.utils import override_settings
from nose.tools import *
import mock

from caching.cachegroup import (CacheGroup, _cache_pattern_memory,
                                ModelCacheManager)
from utils import test_utils
from utils.factories import *
from videos.models import Video

def make_cache_group(**kwargs):
    if 'invalidate_on_deploy' not in kwargs:
        kwargs['invalidate_on_deploy'] = False
    return CacheGroup('cache-group-prefix', **kwargs)

class CacheGroupTest(TestCase):
    CACHE_VALUE = 'cached-value'

    def setUp(self):
        self.work_func = mock.Mock(return_value=self.CACHE_VALUE)

    def check_cache_miss(self, key):
        assert_equal(make_cache_group().get(key), None)

    def check_cache_hit(self, key):
        assert_equal(make_cache_group().get(key), self.CACHE_VALUE)

    def populate_key(self, key):
        make_cache_group().set(key, self.CACHE_VALUE)

    def invalidate_group(self):
        make_cache_group().invalidate()

    def test_get(self):
        self.populate_key('key')
        cache_group = make_cache_group()
        assert_equal(cache_group.get('key'), self.CACHE_VALUE)

    def test_get_with_missing_value(self):
        cache_group = make_cache_group()
        assert_equal(cache_group.get('key'), None)

    def test_set(self):
        cache_group = make_cache_group()
        cache_group.set('key', self.CACHE_VALUE)
        self.check_cache_hit('key')

    def test_get_many(self):
        self.populate_key('key1')
        self.populate_key('key2')
        cache_group = make_cache_group()
        assert_equal(cache_group.get_many(['key1', 'key2', 'key3']), {
            'key1': self.CACHE_VALUE,
            'key2': self.CACHE_VALUE,
        })

    def test_set_many(self):
        cache_group = make_cache_group()
        cache_group.set_many({
            'key1': self.CACHE_VALUE,
            'key2': self.CACHE_VALUE,
        })
        self.check_cache_hit('key1')
        self.check_cache_hit('key2')

    def test_invalidate(self):
        self.populate_key('key1')
        self.populate_key('key2')
        self.invalidate_group()

        self.check_cache_miss('key1')
        self.check_cache_miss('key2')

    def patch_get_commit_id(self):
        return mock.patch('caching.cachegroup.get_commit_id')

    def test_invalidate_on_new_commit(self):
        cache_group = make_cache_group(invalidate_on_deploy=True)
        cache_group.set('key', self.CACHE_VALUE)
        with self.patch_get_commit_id() as mock_get_commit_id:
            mock_get_commit_id.return_value = 'new-commit-id'
            cache_group2 = make_cache_group(invalidate_on_deploy=True)
            assert_equal(cache_group2.get('key'), None)

    def test_dont_invalidate_on_new_commit(self):
        cache_group = make_cache_group(invalidate_on_deploy=False)
        cache_group.set('key', self.CACHE_VALUE)
        with self.patch_get_commit_id() as mock_get_commit_id:
            mock_get_commit_id.return_value = 'new-commit-id'
            cache_group2 = make_cache_group(invalidate_on_deploy=False)
            assert_equal(cache_group2.get('key'), self.CACHE_VALUE)

    def test_get_version_missing(self):
        # test a corner case where the version value gets deleted from the
        # cache
        self.populate_key('key')
        cache.delete('cache-group-prefix:{0}'.format(
            make_cache_group().version_key))
        self.check_cache_miss('key')

    def test_get_with_update_version_midway(self):
        # See the documentation for the race condition this is testing
        cache_group = make_cache_group()
        cache_group.get('key')
        self.invalidate_group() # causes the corner case
        cache_group.set('key', self.CACHE_VALUE)

        self.check_cache_miss('key')

    def test_key_prefix(self):
        # we should store values using <prefix>:key
        cache_group = make_cache_group()
        cache_group.set('key', self.CACHE_VALUE)
        assert_not_equal(cache.get('cache-group-prefix:key'), None)

    def test_version_key_prefix(self):
        # we should store versions using <prefix>:version
        cache_group = make_cache_group()
        version_key = 'cache-group-prefix:{0}'.format(cache_group.version_key)
        self.invalidate_group()
        assert_not_equal(cache.get(version_key), None)

class CacheGroupTest2(CacheGroupTest):
    # test non-string values, which go through a slightly different codepath
    CACHE_VALUE = {'value': 'test'}

class CachePatternTest(TestCase):
    def tearDown(self):
        _cache_pattern_memory.clear()

    def test_remember_keys(self):
        # test that we remember fetched keys
        cache_group = make_cache_group(cache_pattern='foo')
        cache_group.get('a')
        cache_group.get_many(['b', 'c'])
        assert_items_equal(_cache_pattern_memory['foo'], ['a', 'b', 'c'])

    def test_remember_keys_two_runs(self):
        # test remembering fetched keys after multiple runs
        cache_group = make_cache_group(cache_pattern='foo')
        cache_group.get('a')
        cache_group2 = make_cache_group(cache_pattern='foo')
        cache_group2.get_many(['b', 'c'])
        assert_items_equal(_cache_pattern_memory['foo'], ['a', 'b', 'c'])

    def make_mocked_cache_group(self):
        cache_group = make_cache_group(cache_pattern='foo')
        def mock_get_many(keys):
            return dict((k, None) for k in keys)
        cache_group.cache_wrapper = mock.Mock()
        cache_group.cache_wrapper.get_many.side_effect = mock_get_many
        return cache_group

    def test_get_with_previous_key(self):
        # test calling get() with previously seen keys.  We should use
        # get_many() to fetch them all at once
        _cache_pattern_memory['foo'] = set(['a', 'b'])
        cache_group = self.make_mocked_cache_group()
        cache_group.get('a')
        assert_equal(cache_group.cache_wrapper.get_many.call_args,
                     mock.call(set(['a', 'b', cache_group.version_key])))

    def test_get_twice(self):
        # test calling get() twice.  On the first call we should fetch the
        # previous keys, but on the second one we should just fetch the new
        # value
        _cache_pattern_memory['foo'] = set(['a', 'b'])
        cache_group = self.make_mocked_cache_group()
        cache_group.get('a')
        cache_group.cache_wrapper.get_many.reset_mock()
        cache_group.get('d')
        assert_equal(cache_group.cache_wrapper.get_many.call_args,
                     mock.call(set(['d'])))

    def test_get_with_new_key(self):
        # test calling get() with a key not previously seen.  We should fetch
        # that value plus the previously seen ones
        _cache_pattern_memory['foo'] = set(['a', 'b'])
        cache_group = self.make_mocked_cache_group()
        cache_group.get('c')
        assert_equal(cache_group.cache_wrapper.get_many.call_args,
                     mock.call(set(['a', 'b', 'c', cache_group.version_key])))

    def test_get_many(self):
        # test calling get_many() with some previous keys and some new keys.
        # We should fetch all the previous keys and also any new keys passed
        # to get_many()
        _cache_pattern_memory['foo'] = set(['a', 'b'])
        cache_group = self.make_mocked_cache_group()
        cache_group.get_many(['b', 'c'])
        assert_equal(cache_group.cache_wrapper.get_many.call_args,
                     mock.call(set(['a', 'b', 'c', cache_group.version_key])))

class ModelCachingTest(TestCase):
    def test_model_to_tuple(self):
        video = VideoFactory()
        pickled = CacheGroup._model_to_tuple(video)
        assert_equal(video, CacheGroup._tuple_to_model(Video, pickled))

    def test_get_model_cache_miss(self):
        cache_group = make_cache_group()
        assert_equal(cache_group.get_model(Video, 'video'), None)

    def test_set(self):
        video = VideoFactory()
        cache_group = make_cache_group()
        cache_group.set_model('video', video)
        cache_group = make_cache_group()
        assert_equal(cache_group.get_model(Video, 'video'), video)

    def test_save_throws_error(self):
        make_cache_group().set_model('video', VideoFactory())
        video = make_cache_group().get_model(Video, 'video')
        with assert_raises(TypeError):
            video.save()

    def test_get_with_invalid_data(self):
        cache_group = make_cache_group()
        cache_group.set('video', 'foo')
        cache_group = make_cache_group()
        assert_equal(cache_group.get_model(Video, 'video'), None)

    def test_does_not_exist(self):
        make_cache_group().set_model('video', None)
        with assert_raises(Video.DoesNotExist):
            make_cache_group().get_model(Video, 'video')

class ModelCacheManagerTest(TestCase):
    def setUp(self):
        # test ModelCacheManager using the User model.  To do this, we
        # simulate User having cache = ModelCacheManager() in its class
        # definition.
        User.cache = ModelCacheManager()
        self.model_cache_manager = User.cache
        self.instance = User.objects.create_user('test-user')
        self.pk = self.instance.pk
    
    def tearDown(self):
        del User.cache

    def test_get_cache_group(self):
        cache_group = self.model_cache_manager.get_cache_group(self.pk)
        assert_is_instance(cache_group, CacheGroup)
        assert_equal(cache_group.prefix, 'user:{0}'.format(self.pk))

    def test_default_cache_pattern(self):
        # setting default_cache_pattern should set the cache pattern for cache
        # groups
        self.model_cache_manager.default_cache_pattern = 'foo'
        cache_group = self.model_cache_manager.get_cache_group(self.pk)
        assert_equal(cache_group.cache_pattern, 'foo')

    def test_override_default_cache_pattern(self):
        self.model_cache_manager.default_cache_pattern = 'foo'
        cache_group = self.model_cache_manager.get_cache_group(self.pk, 'bar')
        assert_equal(cache_group.cache_pattern, 'bar')

    def test_invalidate_by_pk(self):
        cache_group = self.model_cache_manager.get_cache_group(self.pk)
        cache_group.set('key', 'value')
        self.model_cache_manager.invalidate_by_pk(self.pk)
        cache_group2 = self.model_cache_manager.get_cache_group(self.pk)
        assert_equal(cache_group2.get('key'), None)

    def test_get_instance(self):
        # Since the instance is not cached at this point, calling
        # get_instance() should fetch it from the DB
        with self.assertNumQueries(1):
            instance = self.model_cache_manager.get_instance(self.pk)
        assert_equal(instance, self.instance)

    def test_get_instance_cache_hit(self):
        self.model_cache_manager.get_instance(self.pk)
        # calling get_instance should save the result in cache.  This time
        # around we shouldn't need a DB query
        with self.assertNumQueries(0):
            instance = self.model_cache_manager.get_instance(self.pk)
        assert_equal(instance, self.instance)

    def test_get_instance_saves_cache_group(self):
        instance = self.model_cache_manager.get_instance(self.pk)
        # We should re-use the cache group that we created the instance from.
        # Check this by seeing if current_version is set
        assert_not_equal(instance._cache_group.current_version, None)

    # Test implementation of the python descriptor protocol (AKA __get__)
    def test_descriptor_class_access(self):
        # When accessed via a class, the descriptor should just return the
        # ModelCacheManager
        assert_equal(User.cache, self.model_cache_manager)

    def test_descriptor_instance_access(self):
        # When accessed via an instance, the description should return a cache
        # group for that instance
        user = User.objects.create_user(username='test-user2')
        assert_is_instance(user.cache, CacheGroup)
        assert_equal(user.cache.prefix, 'user:{0}'.format(user.pk))
