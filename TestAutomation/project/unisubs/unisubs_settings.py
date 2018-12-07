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

from datetime import timedelta
from settings import *
from server_local_settings import *

DEBUG = False

ADMINS = (
)

if INSTALLATION == DEV:
    REDIS_DB = "3"
    EMAIL_SUBJECT_PREFIX = '[usubs-dev]'
    GOOGLE_TAG_MANAGER_ID = 'GTM-WDHD7XK'
elif INSTALLATION == STAGING:
    REDIS_DB = "2"
    SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
    EMAIL_SUBJECT_PREFIX = '[usubs-staging]'
    GOOGLE_TAG_MANAGER_ID = 'GTM-WDHD7XK'
elif INSTALLATION == PRODUCTION:
    REDIS_DB = "1"
    SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
    EMAIL_SUBJECT_PREFIX = '[usubs-production]'
    # only send actual email on the production server
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    GOOGLE_ANALYTICS_NUMBER = 'UA-163840-22'
    GOOGLE_TAG_MANAGER_ID = 'GTM-WDHD7XK'
    GOOGLE_ADWORDS_CODE = 'AW-806413593'
elif INSTALLATION == BETA:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
elif INSTALLATION == DEMO:
    DEBUG = True
    REDIS_DB = "4"

if INSTALLATION == STAGING or INSTALLATION == PRODUCTION or INSTALLATION == LOCAL:
    AWS_STORAGE_BUCKET_NAME = DEFAULT_BUCKET

TEMPLATE_DEBUG = DEBUG

RECAPTCHA_PUBLIC = '6LftU8USAAAAADia-hmK1RTJyqXjFf_T5QzqLE9o'

IGNORE_REDIS = True

ALARM_EMAIL = FEEDBACK_EMAILS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': DATABASE_NAME,
        'USER': DATABASE_USER,
        'PASSWORD': DATABASE_PASSWORD,
        'HOST': DATABASE_HOST,
        'PORT': '3306',
        'OPTIONS': {
            'init_command': 'SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED',
        },
    }
}

USE_AMAZON_S3 = True

try:
    from settings_local import *
except ImportError:
    pass

AWS_BUCKET_NAME = AWS_STORAGE_BUCKET_NAME
COMPRESS_MEDIA = not DEBUG

#  the keyd cache apps need this:
CACHE_TIMEOUT  = 60
CACHE_PREFIX  = "unisubscache"

# Grab the SENTRY_DSN for django_rq if we can
try:
    SENTRY_DSN = RAVEN_CONFIG['dsn']
except KeyError, AttributeError:
    pass
