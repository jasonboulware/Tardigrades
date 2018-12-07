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

import warnings
from dev_settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

for key in CACHES.keys():
    CACHES[key]['OPTIONS']['REDIS_CLIENT_CLASS'] = "mockredis.client.mock_strict_redis_client"
CACHE_PREFIX = "testcache"
CACHE_TIMEOUT = 60

RUN_JOBS_EAGERLY = True

GOOGLE_CLIENT_ID = 'test-youtube-id'
GOOGLE_CLIENT_SECRET = 'test-youtube-secret'
GOOGLE_API_KEY = 'test-youtube-api-key'

API_ALWAYS_USE_FUTURE = True

# Use MD5 password hashing, other algorithms are purposefully slow to increase
# security.  Also include the SHA1 hasher since some of the tests use it.
PASSWORD_HASHERS = (
        'django.contrib.auth.hashers.MD5PasswordHasher',
        'django.contrib.auth.hashers.SHA1PasswordHasher',
)

MESSAGES_SENT_WINDOW_MINUTES = 1
MESSAGES_SENT_LIMIT = 50

try:
    from dev_settings_test_local import *
except ImportError:
    pass
