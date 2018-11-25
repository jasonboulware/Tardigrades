# -*- coding: utf-8 -*-
import copy
import json
import os
import time

from django.conf import settings
from django.core.cache import cache
from django.utils.http import cookie_date
from django.utils.translation import (
    get_language, get_language_info, ugettext as _
)
from django.utils.translation.trans_real import parse_accept_lang_header
import babel

from unilangs import get_language_name_mapping, LanguageCode

# A set of all language codes we support.
_supported_languages_map = get_language_name_mapping('unisubs')
_all_languages_map = get_language_name_mapping('internal')
SUPPORTED_LANGUAGE_CODES = set(_supported_languages_map.keys())
ALL_LANGUAGE_CODES = set(_all_languages_map.keys())

SUPPORTED_LANGUAGE_CHOICES = list(sorted(_supported_languages_map.items(),
                                         key=lambda c: c[1]))
ALL_LANGUAGE_CHOICES = list(sorted(_all_languages_map.items(),
                                   key=lambda c: c[1]))

# Top 24 popular languages, taken from:
# https://en.wikipedia.org/wiki/Languages_used_on_the_Internet
POPULAR_LANGUAGES_ORDERED = [
    'en',
    'ru',
    'de',
    'ja',
    'es',
    'fr',
    # "Chinese" and "Portuguese" have 2 main variants.  Include them both.
    'zh-cn',
    'zh-tw',
    'pt',
    'pt-br',
    'it',
    'pl',
    'tr',
    'nl',
    'fa',
    'ar',
    'ko',
    'cs',
    'sv',
    'vi',
    'id',
    'el',
    'ro',
    'hu',
    'da',
    'th',
]
POPULAR_LANGUAGES = sorted(POPULAR_LANGUAGES_ORDERED)
POPULAR_LANGUAGE_SET = set(POPULAR_LANGUAGES)

def _only_supported_languages(language_codes):
    """Filter the given list of language codes to contain only codes we support."""
    # TODO: Figure out the codec issue here.
    return [code for code in language_codes if code in SUPPORTED_LANGUAGE_CODES]

_get_language_choices_cache = {}
def get_language_choices(with_empty=False, with_any=False, flat=False,
                         top_section=None, limit_to=None, exclude=None):
    """Get a list of language choices

    We display languages as "<native_name> [code]", where native
    name is the how native speakers of the language would write it.

    We use the babel library to lookup the native name, however not all of our
    languages are handled by babel.  As a fallback we use the translations
    from gettext.

    Args:
        with_empty: Should we include a null choice?
        with_any: Should we include a choice for any language?
        flat: Make all items in the list (code, name), instead of using the
           django optgroup style for some
        top_section: (code, choices) tuple to use for the top section, instead
           of the popular languages
        limit_to: limit choices to a list of language codes
        exclude: exclude choices from the list of language codes
    """

    language_code = get_language()
    try:
        languages = _get_language_choices_cache[language_code]
    except KeyError:
        languages = calc_language_choices(language_code)
        _get_language_choices_cache[language_code] = languages

    # make a copy of languages before we alter it
    languages = copy.deepcopy(languages)
    if top_section:
        languages[0] = top_section
    if limit_to or exclude:
        if limit_to is not None:
            limit_to = set(limit_to)
        else:
            limit_to = set(SUPPORTED_LANGUAGE_CODES)
        if exclude is not None:
            limit_to = limit_to.difference(exclude)
        def filter_optgroup(og):
            return (og[0], [item for item in og[1] if item[0] in limit_to])
        languages = [filter_optgroup(o) for o in languages]
    if flat:
        languages = languages[1][1]
    if with_any:
        languages.insert(0, ('', _('--- Any Language ---')))
    if with_empty:
        languages.insert(0, ('', '---------'))
    return languages

def calc_language_choices(language_code):
    """Do the work for get_language_choices() """
    languages = []
    translation_locale = lookup_babel_locale(language_code)
    languages.append((_('Popular'), [
        (code, choice_label(code)) for code in POPULAR_LANGUAGES
    ]))
    languages.append((_('All'), [
        (code, choice_label(code)) for code in sorted(SUPPORTED_LANGUAGE_CODES)
    ]))
    return languages

def choice_label(code):
    english_name = _supported_languages_map[code]
    translated_name = _(english_name)
    return u'{} [{}]'.format(translated_name, code)

babel_locale_blacklist = set(['tw'])
def lookup_babel_locale(language_code):
    if language_code == 'tw':
        # babel parses the Twi language as Akan, but this doesn't work for us
        # because "aka" is also Akan and we need to use a unique Locale for
        # each language code.
        return None
    try:
        return babel.Locale.parse(language_code, '-')
    except (babel.UnknownLocaleError, ValueError):
        return None

def get_language_choices_as_dicts(with_empty=False):
    """Return a list of language code choices labeled appropriately."""
    return [
        {'code': code, 'name': name}
        for (code, name) in get_language_choices(with_empty, flat=True)
    ]

def get_language_label(code):
    """Return the translated, human-readable label for the given language code."""
    lc = LanguageCode(code, 'internal')
    return u'%s' % _(lc.name())

def get_user_languages_from_request(request, readable=False, guess=True):
    """Return a list of our best guess at languages that request.user speaks."""
    languages = []

    if hasattr(request, 'user') and request.user.is_authenticated():
        languages = request.user.get_languages()

    if guess and not languages:
        languages = languages_from_request(request)

    if readable:
        return map(get_language_label, _only_supported_languages(languages))
    else:
        return _only_supported_languages(languages)

def set_user_languages_to_cookie(response, languages):
    max_age = 60*60*24
    response.set_cookie(
        settings.USER_LANGUAGES_COOKIE_NAME,
        json.dumps(languages),
        max_age=max_age,
        expires=cookie_date(time.time() + max_age))

def get_user_languages_from_cookie(request):
    try:
        langs = json.loads(request.COOKIES.get(settings.USER_LANGUAGES_COOKIE_NAME, '[]'))
        return _only_supported_languages(langs)
    except (TypeError, ValueError):
        return []


def languages_from_request(request):
    languages = []

    for l in get_user_languages_from_cookie(request):
        if not l in languages:
            languages.append(l)

    if not languages:
        trans_lang = get_language()
        if not trans_lang in languages:
            languages.append(trans_lang)

        if hasattr(request, 'session'):
            lang_code = request.session.get('django_language', None)
            if lang_code is not None and not lang_code in languages:
                languages.append(lang_code)

        cookie_lang_code = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        if cookie_lang_code and not cookie_lang_code in languages:
            languages.append(cookie_lang_code)

        accept = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        for lang, val in parse_accept_lang_header(accept):
            if lang and lang != '*' and not lang in languages:
                languages.append(lang)

    return _only_supported_languages(languages)

def languages_with_labels(langs):
    """Return a dict of language codes to language labels for the given seq of codes.

    These codes must be in the internal unisubs format.

    The labels will be in the standard label format.

    """
    return dict([code, get_language_label(code)] for code in langs)

# This handles RTL info for languages where get_language_info() is not correct
_RTL_OVERRIDE_MAP = {
    # there are languages on our system that are not on django.
    'arq': True,
    'arz': True,
    'pnb': True,
    # Forcing Azerbaijani to be a left-to-right language.
    # For: https://unisubs.sifterapp.com/projects/12298/issues/753035/comments 
    'az': False,
    # Force Urdu to be RTL (see gh-722)
    'ur': True,
    # Force Uyghur to be RTL (see gh-1411)
    'ug': True,
    # Force Aramaic to be RTL (gh-1073)
    'arc': True,
    # Force Dari to be RTL (gh-3307)
    'prs': True,
}

def is_rtl(language_code):
    if language_code in _RTL_OVERRIDE_MAP:
        return _RTL_OVERRIDE_MAP[language_code]
    try:
        return get_language_info(language_code)['bidi']
    except KeyError:
        return False
