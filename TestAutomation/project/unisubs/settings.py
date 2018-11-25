# -*- coding: utf-8 -*-
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

# Django settings for unisubs project.
import os, sys
from datetime import datetime

from unilangs import get_language_name_mapping

import optionalapps

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
DEFAULT_PROTOCOL  = 'http'
HOSTNAME = 'localhost'

LOCALE_PATHS = [
    os.path.join(PROJECT_ROOT, 'locale')
]

def rel(*x):
    return os.path.join(PROJECT_ROOT, *x)

def env_flag_set(name):
    value = os.environ.get(name)
    return bool(value and value != '0')

def calc_locale_choices():
    """Get a list of language (code, label) tuples for each supported locale

    This is the list of languages that we can translate our interface into (at
    least partially)
    """
    localedir = os.path.join(PROJECT_ROOT, 'locale')
    codes = set()
    for name in os.listdir(localedir):
        if not os.path.isdir(os.path.join(localedir, name)):
            continue
        name = name.split('.', 1)[0]
        name = name.replace('_', '-').lower()
        codes.add(name)
    mapping = get_language_name_mapping('gettext')
    return [
        (lc, mapping[lc]) for lc in sorted(codes)
        if lc in mapping
    ]

# Rebuild the language dicts to support more languages.
# ALL_LANGUAGES is a deprecated name for LANGUAGES.
ALL_LANGUAGES = LANGUAGES = calc_locale_choices()

# Languages representing metadata
METADATA_LANGUAGES = (
    ('meta-tw', 'Metadata: Twitter'),
    ('meta-geo', 'Metadata: Geo'),
    ('meta-wiki', 'Metadata: Wikipedia'),
)


DEBUG = True

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

ALARM_EMAIL = None
MANAGERS = ADMINS

P3P_COMPACT = 'CP="CURa ADMa DEVa OUR IND DSP CAO COR"'
SECRET_KEY = 'replace-me-with-an-actual-secret'

DEFAULT_FROM_EMAIL = '"Amara" <feedback@universalsubtitles.org>'
WIDGET_LOG_EMAIL = 'widget-logs@universalsubtitles.org'

BILLING_CUTOFF = datetime(2013, 3, 1, 0, 0, 0)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': rel('unisubs.sqlite3'), # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

CSS_USE_COMPILED = True

COMPRESS_YUI_BINARY = "java -jar ./css-compression/yuicompressor-2.4.6.jar"
COMPRESS_OUTPUT_DIRNAME = "static-cache"


USER_LANGUAGES_COOKIE_NAME = 'unisub-languages-cookie'
LANGUAGE_COOKIE_NAME = 'language'

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
STATIC_ROOT = rel('media')+'/'
MEDIA_ROOT  = rel('user-data')+'/'
CSS_ROOT = os.path.join(STATIC_ROOT, 'amara/css')
LOGO_URL = "https://s3.amazonaws.com/amara/assets/LogoAndWordmark.svg"
PCF_LOGO_URL = "https://s3.amazonaws.com/amara/assets/PCFLogo.png"
# Prefix for assets from the amara-assets repo.  This is currently needed to
# keep them separate from ones from the staticmedia app.  Once everything is
# using futureui, we can get rid of this.
ASSETS_S3_PREFIX = 'assets/'

# List of callables that know how to import templates from various sources.
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            rel('templates'),
        ],
        'OPTIONS': {
            'context_processors': (
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'utils.context_processors.current_site',
                'utils.context_processors.current_commit',
                'utils.context_processors.custom',
                'utils.context_processors.user_languages',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'staticmedia.context_processors.staticmedia',
            ),
            'loaders': (
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader'
            ),
        }

    },
]


MIDDLEWARE_CLASSES = (
    'middleware.AmaraSecurityMiddleware',
    'caching.middleware.AmaraCachingMiddleware',
    'middleware.LogRequest',
    'middleware.StripGoogleAnalyticsCookieMiddleware',
    'utils.ajaxmiddleware.AjaxErrorMiddleware',
    'localeurl.middleware.LocaleURLMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'auth.middleware.AmaraAuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'openid_consumer.middleware.OpenIDMiddleware',
    'middleware.P3PHeaderMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'api.middleware.CORSMiddleware',
)

HOMEPAGE_VIEW = 'views.home'
ROOT_URLCONF = 'urls'

INSTALLED_APPS = (
    # this needs to be first, yay for app model loading mess
    'auth',
    # django stock apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    # third party apps
    'rest_framework',
    'django_rq',
    # third party apps forked on our repo
    'localeurl',
    'openid_consumer',
    # our apps
    'accountlinker',
    'activity',
    'amara',
    'amaradotorg',
    'api',
    'caching',
    'codefield',
    'comments',
    'externalsites',
    'guitests',
    'messages',
    'mysqltweaks',
    'notifications',
    'profiles',
    'search',
    'staff',
    'staticmedia',
    'styleguide',
    'teams',
    'testhelpers',
    'thirdpartyaccounts',
    'ui',
    'unisubs_compressor',
    'utils',
    'videos',
    'widget',
    'subtitles',
    'captcha',
    'raven.contrib.django.raven_compat',
)

STARTUP_MODULES = [
    'externalsites.signalhandlers',
]

# Queue settings
RQ_QUEUES = {
    'default': {
        'USE_REDIS_CACHE': 'storage',
    },
    'high': {
        'USE_REDIS_CACHE': 'storage',
    },
    'low': {
        'USE_REDIS_CACHE': 'storage',
    }
}
RUN_JOBS_EAGERLY = False

# feedworker management command setup
FEEDWORKER_PASS_DURATION=3600

REST_FRAMEWORK = {
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework_yaml.parsers.YAMLParser',
        'rest_framework_xml.parsers.XMLParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework_yaml.renderers.YAMLRenderer',
        'api.renderers.AmaraBrowsableAPIRenderer',
        'rest_framework_xml.renderers.XMLRenderer',
    ),
    'URL_FORMAT_OVERRIDE': 'format',
    'DEFAULT_CONTENT_NEGOTIATION_CLASS':
        'api.negotiation.AmaraContentNegotiation',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'api.auth.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'api.pagination.AmaraPagination',
    'ORDERING_PARAM': 'order_by',
    'VIEW_NAME_FUNCTION': 'api.viewdocs.amara_get_view_name',
    'VIEW_DESCRIPTION_FUNCTION': 'api.viewdocs.amara_get_view_description',
    'NON_FIELD_ERRORS_KEY': 'general_errors',
}

#################

import re
LOCALE_INDEPENDENT_PATHS = [
    re.compile('^/media/'),
    re.compile('^/assets/'),
    re.compile('^/widget/'),
    re.compile('^/api/'),
    re.compile('^/api2/'),
    re.compile('^/jstest/'),
    re.compile('^/externalsites/youtube-callback'),
    re.compile('^/auth/set-hidden-message-id/'),
    re.compile('^/auth/twitter_login_done'),
    re.compile('^/auth/twitter_login_done_confirm'),
    re.compile('^/crossdomain.xml'),
    re.compile('^/embedder-widget-iframe/'),
    re.compile('^/__debug__/'),
]

OPENID_SREG = {"required": "nickname, email", "optional":"postcode, country", "policy_url": ""}
OPENID_AX = [{"type_uri": "http://axschema.org/contact/email", "count": 1, "required": True, "alias": "email"},
             {"type_uri": "fullname", "count": 1 , "required": False, "alias": "fullname"}]

FACEBOOK_API_KEY = ''
FACEBOOK_SECRET_KEY = ''

VIMEO_API_KEY = None
VIMEO_API_SECRET = None

WUFOO_API_KEY = None
WUFOO_API_BASE_URL = 'https://participatoryculture.wufoo.com/api/v3/'

# NOTE: all of these backends store the User.id value in the session data,
# which we rely on in AmaraAuthenticationMiddleware.  Other backends should
# use the same system.
AUTHENTICATION_BACKENDS = (
   'auth.backends.CustomUserBackend',
   'externalsites.auth_backends.OpenIDConnectBackend',
   'thirdpartyaccounts.auth_backends.TwitterAuthBackend',
   'thirdpartyaccounts.auth_backends.FacebookAuthBackend',
   'django.contrib.auth.backends.ModelBackend',
)

# Use cookie storage always since it works the best with our caching system
MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'

# We actually use pytest to run our tests, but this settings prevents a
# spurious warning
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'

MINIMUM_PASSWORD_SCORE = 2
PASSWORD_RESET_TIMEOUT_DAYS = 1

AUTH_PROFILE_MODULE = 'profiles.Profile'
ACCOUNT_ACTIVATION_DAYS = 9999  # we are using registration only to verify emails
SESSION_COOKIE_AGE = 2419200    # 4 weeks
SESSION_COOKIE_HTTPONLY = True

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

RECENT_ACTIVITIES_ONPAGE = 10
ACTIVITIES_ONPAGE = 20
REVISIONS_ONPAGE = 20

FEEDBACK_EMAIL = 'socmedia@pculture.org'
FEEDBACK_EMAILS = [FEEDBACK_EMAIL]
FEEDBACK_ERROR_EMAIL = 'universalsubtitles-errors@pculture.org'
FEEDBACK_SUBJECT = 'Amara Feedback'
FEEDBACK_RESPONSE_SUBJECT = 'Thanks for trying Amara'
FEEDBACK_RESPONSE_EMAIL = 'universalsubtitles@pculture.org'
FEEDBACK_RESPONSE_TEMPLATE = 'feedback_response.html'

#teams
TEAMS_ON_PAGE = 12

PROJECT_VERSION = '0.5'

EDIT_END_THRESHOLD = 120

ANONYMOUS_USER_ID = 10000
ANONYMOUS_DEFAULT_USERNAME = u"amara-bot"
ANONYMOUS_FULL_NAME = u"Amara Bot"

#Use on production
GOOGLE_TAG_MANAGER_ID = None
GOOGLE_ANALYTICS_NUMBER = None
GOOGLE_ADWORDS_CODE = None

# API integration settings
GOOGLE_CLIENT_ID = None
GOOGLE_CLIENT_SECRET = None
GOOGLE_API_KEY = None
GOOGLE_SERVICE_ACCOUNT = None
GOOGLE_SERVICE_ACCOUNT_SECRET = None

try:
    from commit import LAST_COMMIT_GUID
except ImportError:
    LAST_COMMIT_GUID = "dev"

AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''
DEFAULT_BUCKET = ''
AWS_USER_DATA_BUCKET_NAME  = ''
STATIC_MEDIA_USES_S3 = USE_AMAZON_S3 = False
STATIC_MEDIA_COMPRESSED = True
STATIC_MEDIA_EXPERIMENTAL_EDITOR_BUCKET = 's3.staging.amara.org'

# django-storages related settings
PRIVATE_STORAGE_BUCKET = os.environ.get('AMARA_PRIVATE_STORAGE_BUCKET')
PRIVATE_STORAGE_PREFIX = os.environ.get('AMARA_PRIVATE_STORAGE_PREFIX')
AWS_DEFAULT_ACL = None

AVATAR_MAX_SIZE = 1024*1024
THUMBNAILS_SIZE = (
    (100, 100),
    (50, 50),
    (30, 30),
    (120, 90),
    (240, 240)
)

EMAIL_BCC_LIST = []

CACHES = {
    'default': {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://{}:{}/{}".format(
            os.environ.get('REDIS_HOST', 'redis'),
            os.environ.get('REDIS_PORT', 6379),
            0),
        "OPTIONS": {
            "PARSER_CLASS": "redis.connection.HiredisParser",
        },
    },
    'storage': {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://{}:{}/{}".format(
            os.environ.get('REDIS_HOST', 'redis'),
            os.environ.get('REDIS_PORT', 6379),
            1),
        "OPTIONS": {
            "PARSER_CLASS": "redis.connection.HiredisParser",
        },
    },
}


#for unisubs.example.com
RECAPTCHA_PUBLIC = '6LdoScUSAAAAANmmrD7ALuV6Gqncu0iJk7ks7jZ0'
RECAPTCHA_SECRET = ' 6LdoScUSAAAAALvQj3aI1dRL9mHgh85Ks2xZH1qc'

ROSETTA_EXCLUDED_APPLICATIONS = (
    'openid_consumer',
    'rosetta'
)

# List of modules to extract docstrings from for the update_docs management
# command.
API_DOCS_MODULES = [
    'api.views.languages',
    'api.views.videos',
    'api.views.subtitles',
    'api.views.users',
    'api.views.activity',
    'api.views.messages',
    'api.views.teams',
]

MEDIA_BUNDLES = {
    "base.css": {
        "files": (
            "css/jquery.jgrowl.css",
            "css/jquery.alerts.css",
            "css/960.css",
            "css/reset.css",
            "css/html.css",
            "css/about_faq.css",
            "css/breadcrumb.css",
            "css/buttons.css",
            "css/chosen.css",
            "css/classes.css",
            "css/forms.css",
            "css/index.css",
            "css/layout.css",
            "css/profile_pages.css",
            "css/revision_history.css",
            "css/teams.css",
            "css/transcripts.css",
            "css/background.css",
            "css/activity_stream.css",
            "css/settings.css",
            "css/messages.css",
            "css/global.css",
            "css/top_user_panel.css",
            "css/services.css",
            "css/solutions.css",
            "css/watch.css",
            "css/v1.scss",
            "css/bootstrap.css",
            # Hack to make the new headers/footers work
            "amara/css/variables.scss",
            "amara/css/mixins.scss",
            "amara/css/global/dropdowns.scss",
            "amara/css/elements/_page_header.scss",
            "amara/css/elements/_navigation.scss",
            "amara/css/elements/_consolidate-header.scss",
            "amara/css/elements/page_footer.scss",
            "css/marketing-integration.scss",
        ),
    },
    "new-base.css": {
        "files": [
            'src/css/site/colors.scss',
            'src/css/site/layout.scss',
            'src/css/site/type.scss',
            'src/css/site/buttons.scss',
            'src/css/site/forms.scss',
            'src/css/site/links.scss',
            'src/css/site/lists.scss',
            'src/css/site/cards.scss',
            'src/css/site/tables.scss',
            'src/css/site/graphs.scss',
            'src/css/site/header.scss',
            'src/css/site/tabs.scss',
            'src/css/site/split-view.scss',
            'src/css/site/bottom-sheet.scss',
            'src/css/site/pagination.scss',
            'src/css/site/menus.scss',
            'src/css/site/modals.scss',
            'src/css/site/tooltips.scss',
            'src/css/site/banner.scss',
            'src/css/site/messages.scss',
            'src/css/site/footer.scss',
            'src/css/site/teams.scss',
            'src/css/third-party/jquery-ui-1.11.4.custom.css',
            'src/css/third-party/jquery-ui.theme-1.11.4.custom.css',
            'src/css/third-party/jquery-ui.structure-1.11.4.custom.css',
        ],
        "include_path": 'src/css/site',
    },
    "home.css": {
        "files": (
            "css/new_index.css",
        ),
    },
    "hands_home.css": {
        "files": (
            "css/hands-static.css",
            "css/hands-main.css",
            # Hack to make the new headers/footers work
            "amara/css/variables.scss",
            "amara/css/mixins.scss",
            "amara/css/global/grid.scss",
            "amara/css/global/dropdowns.scss",
            "amara/css/elements/_navigation.scss",
            "amara/css/elements/_page_header.scss",
            "amara/css/elements/_consolidate-header.scss",
            "amara/css/elements/page_footer.scss",
            "css/marketing-integration.scss",
         )
    },
    "api.css": {
        "files": (
            "src/css/api.css",
        ),
    },
    "hands_home.js": {
        "files": (
            "js/hands-plugins.js",
            "js/hands-modernizr-2.6.2.min.js",
         )
    },
    "site.js": {
        "files": (
            "js/jquery-1.4.3.js",
            "js/jquery-ui-1.8.16.custom.min.js",
            "js/jgrowl/jquery.jgrowl.js",
            "js/jalerts/jquery.alerts.js",
            "js/jquery.form.js",
            "js/jquery.metadata.js",
            "js/jquery.mod.js",
            "js/jquery.rpc.js",
            "js/jquery.input_replacement.min.js",
            "js/messages.js",
            "js/escape.js",
            "js/dropdown-hack.js",
            "js/libs/chosen.jquery.min.js",
            "js/libs/chosen.ajax.jquery.js",
            "js/libs/jquery.cookie.js",
            "src/js/third-party/js.cookie.js",
            "js/unisubs.site.js",
            "src/js/unisubs.variations.js",
        ),
    },
    "new-site.js": {
        "files": [
            'src/js/third-party/jquery-2.1.3.js',
            'src/js/third-party/jquery-ui-1.11.4.custom.js',
            'src/js/third-party/jquery.form.js',
            'src/js/third-party/jquery.formset.js',
            'src/js/third-party/behaviors.js',
            "src/js/third-party/js.cookie.js",
            'src/js/site/announcements.js',
            'src/js/site/copytext.js',
            'src/js/site/menus.js',
            'src/js/site/modals.js',
            'src/js/site/querystring.js',
            'src/js/site/tooltips.js',
            'src/js/site/pagination.js',
            'src/js/site/autocomplete.js',
            'src/js/site/thumb-lists.js',
            'src/js/site/bottom-sheet.js',
            'src/js/site/team-videos.js',
            'src/js/site/team-bulk-move.js',
            'src/js/site/team-members.js',
            'src/js/site/team-integration-settings.js',
            'src/js/site/dates.js',
            'src/js/site/formsets.js',
        ],
    },
    "api.js": {
        "files": (
            "js/jquery-1.4.3.js",
            "src/js/api.js",
        ),
    },
    "teams.js": {
        "files": (
            "js/libs/ICanHaz.js",
            "js/libs/classy.js",
            "js/libs/underscore.js",
            "js/libs/chosen.jquery.min.js",
            "js/libs/chosen.ajax.jquery.js",
            "js/jquery.mod.js",
            "js/teams/create-task.js",
         ),
    },
    'editor.js':  {
        'files': (
            'src/js/third-party/jquery-1.12.4.js',
            'js/jquery.form.js',
            'src/js/third-party/jquery.autosize.js',
            'src/js/third-party/angular.1.2.9.js',
            'src/js/third-party/angular-cookies.js',
            'src/js/third-party/underscore.1.8.3.js',
            'src/js/third-party/popcorn.js',
            'src/js/third-party/Blob.js',
            'src/js/third-party/FileSaver.js',
            'src/js/popcorn/popcorn.amara.js',
            'src/js/third-party/modal-helper.js',
            'src/js/third-party/json2.min.js',
            'src/js/dfxp/dfxp.js',
            'src/js/uri.js',
            'src/js/popcorn/popcorn.flash-fallback.js',
            #'src/js/popcorn/popcorn.netflix.js',
            'src/js/subtitle-editor/app.js',
            'src/js/subtitle-editor/dom.js',
            'src/js/subtitle-editor/durationpicker.js',
            'src/js/subtitle-editor/gettext.js',
            'src/js/subtitle-editor/help.js',
            'src/js/subtitle-editor/lock.js',
            'src/js/subtitle-editor/preferences.js',
            'src/js/subtitle-editor/modal.js',
            'src/js/subtitle-editor/notes.js',
            'src/js/subtitle-editor/blob.js',
            'src/js/subtitle-editor/session.js',
            'src/js/subtitle-editor/shifttime.js',
            'src/js/subtitle-editor/toolbar.js',
            'src/js/subtitle-editor/workflow.js',
            'src/js/subtitle-editor/subtitles/controllers.js',
            'src/js/subtitle-editor/subtitles/directives.js',
            'src/js/subtitle-editor/subtitles/filters.js',
            'src/js/subtitle-editor/subtitles/models.js',
            'src/js/subtitle-editor/subtitles/services.js',
            'src/js/subtitle-editor/timeline/controllers.js',
            'src/js/subtitle-editor/timeline/directives.js',
            'src/js/subtitle-editor/video/controllers.js',
            'src/js/subtitle-editor/video/directives.js',
            'src/js/subtitle-editor/video/services.js',
        ),
    },
    'editor.css':  {
        'files': (
            'src/css/third-party/reset.css',
            'src/css/subtitle-editor/subtitle-editor.scss',
        ),
    },
    "embedder.js":{
        "files": (
            "src/js/third-party/json2.min.js",
            'src/js/third-party/underscore.min.js',
            'src/js/third-party/jquery-1.8.3.min.js',
            'src/js/third-party/backbone.min.js',
            'src/js/third-party/popcorn.js',
            'src/js/popcorn/popcorn.flash-fallback.js',
            'src/js/third-party/jquery.mCustomScrollbar.concat.min.js',
            'src/js/popcorn/popcorn.amaratranscript.js',
            'src/js/popcorn/popcorn.amarasubtitle.js',
            'src/js/popcorn/popcorn.amara.js',
            'src/js/embedder/embedder.js'
        ),
        'add_amara_conf': True,
    },
    "embedder.css": {
        "files": (
            "src/css/embedder/jquery.mCustomScrollbar.css",
            "src/css/embedder/embedder.scss",
        ),
    },
    'ie8.css': {
        'files': (
            'css/ie8.css',
        ),
    },
    'ajax-paginator.js': {
        'files': (
            'js/jquery.address-1.4.fixed.js',
            'js/escape.js',
            'js/jquery.ajax-paginator.js',
        ),
    },
    'prepopulate.js': {
        'files': (
            'js/urlify.js',
            'js/prepopulate.min.js',
        ),
    },
    # used by the old editor
    'unisubs-api.js': {
        'files': (
            'legacy-js/unisubs-api.js',
        ),
    },
    # used by the old embedder -- hopefully going away soon
    'unisubs-offsite-compiled.js': {
        'files': (
            'legacy-js/unisubs-offsite-compiled.js',
        ),
    },
    # used by both the old embedder and old editor
    "widget.css": {
        "files": (
            "css/unisubs-widget.css",
        ),
    },
    'login.js': {
        'files': (
            'src/js/site/login.js',
            'src/js/site/facebook.js',
        ),
    },
}

# Where we should tell OAuth providers to redirect the user to.  We want to
# use https for production to prevent attackers from seeing the access token.
# For development, we care less about that so we typically use http
OAUTH_CALLBACK_PROTOCOL = 'https'
ENABLE_LOGIN_CAPTCHA = not os.environ.get('DISABLE_LOGIN_CAPTCHA')

EMAIL_BACKEND = "utils.safemail.InternalOnlyBackend"
EMAIL_FILE_PATH = '/tmp/unisubs-messages'
# on staging and dev only the emails listed bellow will receive actual mail
EMAIL_NOTIFICATION_RECEIVERS = ("arthur@stimuli.com.br", "steve@stevelosh.com", "@pculture.org")

def log_handler_info():
    rv = {
        'formatter': 'standard' ,
    }
    if env_flag_set('DB_LOGGING'):
        rv['level'] = 'DEBUG'
    else:
        rv['level'] = 'INFO'
    if env_flag_set('JSON_LOGGING'):
        rv['class'] = 'utils.jsonlogging.JSONHandler'
    else:
        rv['class'] = 'logging.StreamHandler'
    return rv

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'root': {
        'level': 'INFO',
        'handlers': ['main'],
    },
    'formatters': {
        'standard': {
            'format': '%(levelname)s %(asctime)s %(name)s %(message)s'
        },
    },
    'handlers': {
        'main': log_handler_info(),
    },
    'loggers': {
        "rq.worker": {
            "level": "INFO"
        },
        'requests.packages.urllib3.connectionpool': {
            'level': 'WARNING',
        }
    },
}
if env_flag_set('DB_LOGGING'):
    LOGGING['loggers']['django.db'] = { 'level': 'DEBUG' }

TMP_FOLDER = "/tmp/"

SOUTH_MIGRATION_MODULES = {
    'captcha': 'captcha.south_migrations',
}

from task_settings import *


optionalapps.exec_repository_scripts('settings_extra.py', globals(), locals())
