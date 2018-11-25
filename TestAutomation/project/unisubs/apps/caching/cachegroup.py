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

"""
Cache Groups
------------

Cache groups are used to manage a group of related cache values.  They add
some extra functionality to the regular django caching system:

- **Key prefixing**: cache keys are prefixed with a string to avoid name
  collisions
- **Invalidation**: all values in the cache group can be invalidated together.
  Optionally, all values can be invalidated on server deploy
- **Optimized fetching**: we can remember cache usage patterns in order to use
  get_many() to fetch all needed keys at once (see :ref:`cache-patterns`)
- **Protection against race conditions**: (see
  :ref:`cache-race-condition-prevention`)

Typically cache groups are associated with objects.  For example we create a
cache group for each user and each video.  The user cache group stores things
like the user menu HTML and message HTML.  The video cache group stores the
language list and other sections of the video/language pages.

Overview
^^^^^^^^

* A CacheGroup is a group of cache values that can all be invalidated together
* You can automatically create a CacheGroup for each model instance
* CacheGroups can be used with a cache pattern.  This makes it so we
  remember which cache keys are requested and fetch them all using
  get_many()

Let's take the video page caching as an example.  To implement caching,
we create cache groups for Team, Video, and User instances.  Here's a few
examples of how we use those cache groups:

* Language list:  we store the rendered HTML in the video cache
* User menu: we store the rendered HTML in the user cache (and we
  actually use that for all pages on the site)
* Add subtitles form: we store the list of existing languages in the
  video cache (needed to set up the selectbox)
* Follow video button: we store a list of user ids that are following
  the videos in the video cache.  To the user is currently following we
  search that list for their user ID.
* Add subtitles permissions: we store a list of member user ids in the
  team cache.  To check if the user can view the tasks/collaboration
  page we search that list of the user ID

When we create the cache groups, we use the video-page cache pattern.
This makes it so we can render the page with 3 cache requests.  One
get_many fetches the Video instance and all cache values related to the video,
and similarly for the Team and User.

Cache invalidation is always tricky.  We use a simple system where if a change
could affect any cache value, we invalidate the entire group of values.
For example if we add/remove a team member then we invalidate the cache for
the team.

.. _cache-patterns:

Cache Patterns
^^^^^^^^^^^^^^

Cache patterns help optimize cache access.  When a cache pattern is set for a
CacheGroup we will do a couple things:

- Remember which keys were fetched from cache.
- On subsequent runs, we will try to use get_many() to fetch all cache
  values at once.

This speeds things up by reducing the number of round trips to the cache.

Behind the scenes
^^^^^^^^^^^^^^^^^

The main trick that CacheGroup uses is to store a "version" value in the
cache, which is simply a random string.  We also pack the version value
together with all of our cache values.  If a cache value's version doesn't
match the version for the cache group, then it's considered invalid.  This
allows us to invalidate the entire cache group by changing the version value
to a different string.

Here's some example data to show how it works.

========  ==============   ==============
key       value in cache   computed value
========  ==============   ==============
version   abc              N/A
X         abc:foo          foo
Y         abc:bar          bar
Z         def:bar          *invalid*
========  ==============   ==============

.. note::

    We also will prefix the all cache keys with the "<prefix>:" using the
    prefix passed into the CacheGroup constructor.

.. note::

    If invalidate_on_deploy is True, then we will append ":<commit-id>" to the
    version key.  This way the version key changes for each deploy, which will
    invalidate all values.

.. _cache-race-condition-prevention:

Race condition prevention
^^^^^^^^^^^^^^^^^^^^^^^^^

The typical cache usage pattern is:

  1. Fetch from the cache
  2. If there is a cache miss then:

      a) calculate the value
      b) store it to cache.

This pattern will often have a race condition if another process updates the
DB between steps 2a and 2b.  Even if the other process invalidates the cache,
the step 2b will overwrite it, storing an outdated value.

This is not a problem with CacheGroup because of the way it handles the
version key.  When we get the value from cache, we also fetch the version
value.  If the version value isn't set, we set it right then.  Then when we
store the value, we also store the version key that we saw when we did the
get.  If the version changes between the get() and set() calls, then the
value stored with set() will not be valid.  This works somewhat similarly to
the memcached GETS and CAS operations.

Cache Groups and DB Models
^^^^^^^^^^^^^^^^^^^^^^^^^^

Cache groups can save and restore django models using get_model() and
set_model().  There is a pretty conservative policy around this.  Only the
actual row data will be stored to cache -- other attributes like cached
related instances are not stored.  Also, restored models can't be saved to the
DB.  All of this is to try to prevent overly aggressive caching from causing
weird/wrong behavior.

To add caching support to your model, add :class:`ModelCacheManager` as an
attribute to your class definition.

.. autoclass:: CacheGroup
.. autoclass:: ModelCacheManager
"""
from __future__ import absolute_import
import collections

from django.conf import settings
from django.core.cache import cache

from utils import codes
from caching.utils import get_or_calc, get_or_calc_many

def get_commit_id():
    return settings.LAST_COMMIT_GUID

class _CacheWrapper(object):
    """Wrap cache access for CacheGroup.

    This class helps CacheGroup access the cache.  It does 2 things:
        - adds the key prefix
        - remembers previously fetched values and avoids fetching them again
        - handles prefetching keys for a cache pattern
    """
    def __init__(self, prefix):
        self.prefix = prefix
        self._cache_data = {}

    def get(self, key):
        value = cache.get(self._prefix_key(key))
        self._cache_data[key] = value
        return value

    def get_many(self, keys):
        unfetched_keys = [key for key in keys if key not in self._cache_data]
        if unfetched_keys:
            self._run_get_many(unfetched_keys)
        return dict((key, self._cache_data.get(key)) for key in keys)

    def _run_get_many(self, keys):
        result = cache.get_many([self._prefix_key(key) for key in keys])
        for key in keys:
            self._cache_data[key] = result.get(self._prefix_key(key))

    def set(self, key, value, timeout=None):
        cache.set(self._prefix_key(key), value)
        self._cache_data[key] = value

    def set_many(self, values, timeout=None):
        raw_values = dict((self._prefix_key(key), value)
                          for (key, value) in values.items())
        cache.set_many(raw_values, timeout)
        self._cache_data.update(values)

    def _prefix_key(self, key):
        return '{0}:{1}'.format(self.prefix, key)

# map cache pattern IDs to the keys we've seen used
_cache_pattern_memory = collections.defaultdict(set)

class CacheGroup(object):
    """Manage a group of cached values

    Args:
        prefix(str): prefix keys with this
        cache_pattern(str): :ref:`cache pattern <cache-patterns>` identifier
        invalidate_on_deploy(bool): Invalidate values when we redeploy

    .. automethod:: get
    .. automethod:: get_many
    .. automethod:: set
    .. automethod:: set_many
    .. automethod:: get_or_calc
    .. automethod:: get_or_calc_many
    .. automethod:: get_model
    .. automethod:: set_model
    .. automethod:: invalidate

    """

    def __init__(self, prefix, cache_pattern=None, invalidate_on_deploy=True):
        self.prefix = prefix
        self.cache_wrapper = _CacheWrapper(prefix)
        if cache_pattern:
            # copy the values from _cache_pattern_memory now.  It's going to
            # change as we fetch keys and for sanity sake we should not care
            # about that
            self._cache_pattern_keys = \
                    set(_cache_pattern_memory[cache_pattern])
        else:
            self._cache_pattern_keys = None
        self.cache_pattern = cache_pattern
        self.current_version = None
        if invalidate_on_deploy:
            self.version_key = 'version:{0}'.format(get_commit_id())
        else:
            self.version_key = 'version'
        self.invalidate_on_deploy = invalidate_on_deploy

    def invalidate(self):
        """Invalidate all values in this CacheGroup."""
        self.current_version = codes.make_code()
        self.cache_wrapper.set(self.version_key, self.current_version)

    def ensure_version(self):
        if self.current_version is not None:
            return
        version = self.cache_wrapper.get(self.version_key)
        if version is None:
            self.invalidate()
        else:
            self.current_version = version

    def get(self, key):
        """Get a value from the cache

        This method also checks that the version of the value stored matches
        the version in our version key.

        If there is no value set for our version key, we set it now.
        """
        # Delegate to get_many().  This function is just for convenience.
        return self.get_many([key]).get(key)

    def get_many(self, keys):
        """Get multiple keys at once

        If there is no value set for our version key, we set it now.
        """
        if self.cache_pattern:
            _cache_pattern_memory[self.cache_pattern].update(keys)
        keys_to_fetch = set(keys)
        if self.current_version is None:
            keys_to_fetch.add(self.version_key)
        if self._cache_pattern_keys:
            keys_to_fetch.update(self._cache_pattern_keys)
            self._cache_pattern_keys = None
        get_many_result = self.cache_wrapper.get_many(keys_to_fetch)
        # first of all, handle the version.
        if self.current_version is None:
            if get_many_result[self.version_key] is None:
                self.invalidate()
                return {}
            else:
                self.current_version = get_many_result[self.version_key]
        result = {}
        for key in keys:
            cache_value = get_many_result.get(key)
            version, value = self._unpack_cache_value(cache_value)
            if version == self.current_version:
                result[key] = value
        return result

    def set(self, key, value, timeout=None):
        """Set a value in the cache """
        self.ensure_version()
        self.cache_wrapper.set(key, self._pack_cache_value(value), timeout)

    def set_many(self, values, timeout=None):
        """Set multiple values in the cache """
        self.ensure_version()
        values_to_set = dict(
            (key, self._pack_cache_value(value))
            for key, value in values.items()
        )
        self.cache_wrapper.set_many(values_to_set, timeout)

    def get_or_calc(self, key, work_func):
        """See utils.get_or_calc """
        return get_or_calc(key, work_func, cache=self)

    def get_or_calc_many(self, keys, work_func):
        """See utils.get_or_calc_many """
        return get_or_calc_many(keys, work_func, cache=self)

    def get_model(self, ModelClass, key):
        """Get a model stored with set_model()

        .. note::

            To be catious, models fetched from the cache don't allow saving.
            If the cache data is out of date, we don't want to saave it to
            disk.
        """
        value = self.get(key)
        if value is None:
            return None
        if value == 'does-not-exist':
            raise ModelClass.DoesNotExist()
        try:
            instance = self._tuple_to_model(ModelClass, value)
        except StandardError:
            # invalid data stored or we're fetching the wrong cache key, don't
            # return anything.
            return None
        instance.save = self._model_save_override
        return instance

    def _model_save_override(model, *args, **kwargs):
        raise TypeError("Saving cached models is prohibitted")

    def set_model(self, key, instance, timeout=None):
        """Store a model instance in the cache

        Storing a model is a tricky thing.  This method works by storing a
        tuple containing the values of the DB row.  We store it like that for
        2 reasons:

        - It's space efficient
        - It drops things like cached related objects.  This is probably good
          since it makes it so we don't also cache those objects, which can
          lead to unexpected behavior and bugs.

        Args:
            key: key to store the instance with
            instance: Django model instance, or None to indicate the model
                      does not exist in the DB.  This will make get_model()
                      raise a ObjectDoesNotExist exception.
        """
        if instance is not None:
            value = self._model_to_tuple(instance)
        else:
            value = 'does-not-exist'
        self.set(key, value, timeout)

    def _pack_cache_value(self, value):
        """Combine our version and value together to get a value to store in
        the cache.
        """
        if isinstance(value, basestring):
            # if the value is a string, let's not create a tuple.  This avoids
            # having to pickle the data
            return ':'.join((self.current_version, value))
        else:
            return (self.current_version, value)

    def _unpack_cache_value(self, cache_value):
        """Unpack a value stored in the cache to a (version, value) tuple
        """
        if isinstance(cache_value, basestring):
            split = cache_value.split(':', 1)
            if len(split) == 2:
                return split
        elif isinstance(cache_value, tuple):
            if len(cache_value) == 2:
                return cache_value
        return (None, None)

    @staticmethod
    def _model_to_tuple(instance):
        return tuple(getattr(instance, f.column, None)
                     for f in instance._meta.fields)

    @staticmethod
    def _tuple_to_model(ModelClass, tup):
        value_dict = dict(
            (f.column, tup[i])
            for i, f in enumerate(ModelClass._meta.fields))
        return ModelClass(**value_dict)

class ModelCacheManager(object):
    """Manage CacheGroups for a django model.

    ModelCacheManager is meant to be added as an attribute to a class.  It
    does 2 things: manages CacheGroups for the model class and implements the
    python descriptor protocol to create a CacheGroup for each instance.  If
    you add ``cache = ModelCacheManager()`` to your class definition,
    then:

    - At the class level, MyModel.cache will be the ModelCacheManager instance
    - At the instance level, my_model.cache will be a :class:`CacheGroup`
      specific to that instance

    .. automethod:: get_cache_group
    .. automethod:: invalidate_by_pk
    .. automethod:: get_instance

    """
    def __init__(self, default_cache_pattern=None):
        self.default_cache_pattern = default_cache_pattern
        # we will set in __get__ once the attribute is accessed
        self.model_class = None

    def _make_prefix(self, pk):
        return '{0}:{1}'.format(self.model_class.__name__.lower(), pk)

    def get_cache_group(self, pk, cache_pattern=None):
        """Create a CacheGroup for an instance of this model

        Args:
            pk: primary key value for the instance
            cache_pattern: cache pattern to use or None to use the default
                           cache pattern for this ModelCacheManager
        """
        if cache_pattern is None:
            cache_pattern = self.default_cache_pattern
        return CacheGroup(self._make_prefix(pk), cache_pattern)

    def invalidate_by_pk(self, pk):
        """Invalidate a CacheGroup for an instance

        This is a shortcut for get_cache_group(pk).invalidate() and can be
        used to invalidate without having to load the instance from the DB.
        """
        return self.get_cache_group(pk).invalidate()

    def get_instance(self, pk, cache_pattern=None):
        """Get a cached instance from it's cache group

        This will create a CacheGroup, get the instance from it or load it
        from the DB, then reuse the CacheGroup for the instance's cache.  If a
        cache pattern is used this means we can load the instance and all of
        the needed cache values with one get_many() call.
        """
        cache_group = self.get_cache_group(pk, cache_pattern)
        instance = cache_group.get_model(self.model_class, 'self')
        if instance is None:
            instance = self.model_class.objects.get(pk=pk)
            cache_group.set_model('self', instance)
        # re-use the cache group that we just created for the instance
        instance._cache_group = cache_group
        return instance

    def __get__(self, instance, owner):
        self.model_class = owner
        if instance is None:
            # class-level access
            return self
        # instance-level access
        if not hasattr(instance, '_cache_group'):
            instance._cache_group = self.get_cache_group(instance.pk)
        return instance._cache_group
