# Copyright (c) 2008 Joost Cassee
# Licensed under the terms of the MIT License (see LICENSE.txt)

import re
from django import urls
from django.conf import settings
import localeurl.settings

SUPPORTED_LOCALES = dict(settings.LANGUAGES)
LOCALES_RE = '|'.join(SUPPORTED_LOCALES)
PATH_RE = re.compile(r'^/(?P<locale>%s)(?=/)(?P<path>.*)$' % LOCALES_RE)
DOMAIN_RE = re.compile(r'^(?P<locale>%s)(?=/)\.(?P<domain>.*)$' % LOCALES_RE)
DOMAIN_MAP = dict(localeurl.settings.DOMAINS)

import logging
logger = logging.getLogger("localeurl")

def is_locale_independent(path):
    """
    Returns whether the path is locale-independent.

    We only want to prepend the locale part to URLs that we want to localize.
    We don't want to do this for things like static media files, API urls,
    etc.

    We use the LOCALE_INDEPENDENT_PATHS setting to check this.
    LOCALE_INDEPENDENT_PATHS should be a list of regular expressions to match
    against the path.
    """
    for re in settings.LOCALE_INDEPENDENT_PATHS:
        if re.search(path):
            return True
    return False

def strip_path(path):
    """
    Separates the locale prefix from the rest of the path. If the path does not
    begin with a locale it is returned without change.
    """
    if localeurl.settings.URL_TYPE == 'path_prefix':
        check = PATH_RE.match(path)
        if check:
            path_info = check.group('path') or '/'
            if path_info.startswith('/'):
                return check.group('locale'), path_info
    return '', path

def strip_domain(domain):
    """
    Returns the locale component and the domain without the locale component.
    If the domain does not begin with a locale it is returned without change.
    """
    if localeurl.settings.URL_TYPE == 'domain_component':
        check = DOMAIN_RE.match(domain)
        if check:
            return check.group('locale'), check.group('domain')
    return '', domain

def get_locale_from_domain(domain):
    """
    Returns the locale parsed from the domain.
    """
    raise AssertionError("Not implemented")
    if localeurl.settings.URL_TYPE == 'domain':
        if domain in DOMAIN_MAP:
            return DOMAIN_MAP[domain]
    return ''

def supported_language(locale):
    """
    Returns the supported language (from settings.LANGUAGES) for the locale.
    """
    if locale in SUPPORTED_LOCALES:
        return locale
    elif locale[:2] in SUPPORTED_LOCALES:
        return locale[:2]
    else:
        return None

def is_default_locale(locale):
    """
    Returns whether the locale is the default locale.
    """
    return locale == supported_language(settings.LANGUAGE_CODE)

def locale_path(path, locale=''):
    """
    Generate the localeurl-enabled path from a path without locale prefix. If
    the locale is empty settings.LANGUAGE_CODE is used.
    """
    locale = supported_language(locale)
    if localeurl.settings.URL_TYPE != 'path_prefix':
        return path
    if not locale:
        locale = supported_language(settings.LANGUAGE_CODE)
    if is_locale_independent(path):
        return path
    elif is_default_locale(locale) \
            and not localeurl.settings.PREFIX_DEFAULT_LOCALE:
        return path
    else:
        return ''.join([u'/', locale, path])

def locale_url(path, locale=''):
    """
    Generate the localeurl-enabled URL from a path without locale prefix. If
    the locale is empty settings.LANGUAGE_CODE is used.
    """
    path = locale_path(path, locale)
    return ''.join([urls.get_script_prefix(), path[1:]])


def universal_url(*args, **kwargs):
    """
    Returns an absolute path (with protocol + domain) but without the locale set.
    This is useful for email links, for exaple, where the recipient should choose the locale,
    and therefore the url
    """
    if 'protocol_override' in kwargs:
        protocol = kwargs.pop('protocol_override')
    else:
        protocol = None
    try:
        original = urls.reverse(*args, **kwargs)
    except Exception :
        logger.exception("Failed to resolve universal url") 
        return
    return make_universal(original, protocol)

def make_universal(url, protocol=None):
    """
    Convert a relative URL, possibly with a locale in it to a universal URL

    Universal URLS are absolute and don't contain the URL.  They are used when
    we need to use a URL outside of a webpage, for example an email
    """
    if protocol is None:
        protocol = getattr(settings, "DEFAULT_PROTOCOL", 'https')

    return "%s://%s%s" % (protocol, settings.HOSTNAME,
                          strip_path(url)[1])
