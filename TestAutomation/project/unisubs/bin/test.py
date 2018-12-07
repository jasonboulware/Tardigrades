#!/usr/bin/python

"""
Amara testing script

Some notes about testing:

  - Before running this cd to a directory to put tests in.  The user running
    the script needs to be able to write to it.  In our docker file, we use
    /var/run/tests.

  - Pass as the first argument the directory that holds the test code (either
    "tests", or "guitests").

  - The test directory will be cleared out, then we will symlink all files
    found in the the tests/guitests directories (both from the unisubs repo,
    and any submodules)

"""

from __future__ import absolute_import

import os
import shutil
import sys
import tempfile

from django.apps import apps
from django.conf import settings
from django_redis import get_redis_connection
import mock
import py.path
import pytest

from amara.signals import before_tests
import startup

def is_one_path_a_parent_of_another(path1, path2):
    return path1.startswith(path2) or path2.startswith(path1)

class AmaraPlugin(object):
    def __init__(self):
        self.test_paths = [
            config.path for config in apps.get_app_configs()
            if 'guitests' not in config.name
        ]
        self.test_paths.extend(
            os.path.abspath(p) for p in ['libs/babelsubs', 'libs/unilangs']
        )

    def pytest_ignore_collect(self, path, config):
        for test_path in self.test_paths:
            if is_one_path_a_parent_of_another(path.strpath, test_path):
                return False
        return True

    @pytest.mark.trylast
    def pytest_configure(self, config):
        from utils.test_utils import monkeypatch
        self.patcher = monkeypatch.MonkeyPatcher()
        self.patcher.patch_functions()
        self.patch_mockredis()

        settings.MEDIA_ROOT = tempfile.mkdtemp(prefix='amara-test-media-root')

        reporter = config.pluginmanager.getplugin('terminalreporter')
        reporter.startdir = py.path.local('/run/pytest/')

        before_tests.send(config)

    def patch_mockredis(self):
        from mockredis.client import MockRedis
        # Patch for mockredis returning a boolean when it should return 1 or 0.
        # (See https://github.com/locationlabs/mockredis/issues/147)
        def exists(self, key):
            if self._encode(key) in self.redis:
                return 1
            else:
                return 0
        MockRedis.exists = exists

        # Emulate PERSIST
        def persist(self, key):
            key = self._encode(key)
            if key in self.redis and key in self.timeouts:
                del self.timeouts[key]
                return 1
            else:
                return 0
        MockRedis.persist = persist

    def pytest_runtest_teardown(self, item, nextitem):
        self.patcher.reset_mocks()
        get_redis_connection("default").flushdb()
        get_redis_connection("storage").flushdb()

    def pytest_unconfigure(self, config):
        self.patcher.unpatch_functions()
        shutil.rmtree(settings.MEDIA_ROOT)

    @pytest.fixture(autouse=True)
    def setup_amara_db(self, db):
        from auth.models import CustomUser
        CustomUser.get_amara_anonymous()

    @pytest.fixture(autouse=True)
    def undo_set_debug_to_false(self, db):
        # pytest-django sets this to False, undo it.
        settings.DEBUG = True

    @pytest.fixture
    def patch_for_test(self):
        """
        Call mock.patch to monkeypatch a function, then undo it at the end of
        the test
        """
        patchers = []
        def func(*args, **kwargs):
            patcher = mock.patch(*args, **kwargs)
            obj = patcher.start()
            patchers.append(patcher)
            return obj
        yield func
        for patcher in patchers:
            patcher.stop()

    @pytest.fixture
    def redis_connection(self):
        return get_redis_connection('storage')

class AmaraGUITestsPlugin(object):
    def __init__(self):
        self.test_paths = [
            config.path for config in apps.get_app_configs()
            if 'guitests' in config.name
        ]

    def pytest_ignore_collect(self, path, config):
        for test_path in self.test_paths:
            if is_one_path_a_parent_of_another(path.strpath, test_path):
                return False
        return True

    @pytest.mark.trylast
    def pytest_configure(self, config):
        reporter = config.pluginmanager.getplugin('terminalreporter')
        reporter.startdir = py.path.local('/run/pytest/')

if __name__ == '__main__':
    startup.startup()
    test_type = sys.argv[1] # run type, either 'tests' or 'guitests'
    pytest_args = sys.argv[2:] # send all args after that to pytest

    if test_type == 'tests':
        plugin = AmaraPlugin()
    elif test_type == 'guitests':
        plugin = AmaraGUITestsPlugin()
    else:
        print "Unknown test type: {}".format(test_type)
        sys.exit(1)
    sys.exit(pytest.main(pytest_args, plugins=[plugin]))
