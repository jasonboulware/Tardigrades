from django import template
from django.conf import settings

from unilangs import get_language_name_mapping
from utils.translation import get_language_label

import logging
logger = logging.getLogger('utils.languagetags')

LANGUAGE_NAMES = get_language_name_mapping('unisubs')
register = template.Library()

@register.filter()
def to_localized_display(language_code):
    '''
    Translates from a language code to the language name
    in the locale the user is viewing the site. For example:
    en -> Anglaise (if user is viewing with 'fr'
    en -> English
    It uses the django internal machinery to figure out what
    language the request cicle is in, currently set on the
    localurl middleware.
    IF anything is wrong, will log the missing error and
    will return a '?'.
    '''
    try:
        return get_language_label(language_code)
    except KeyError:
        logger.error('Unknown language code to be translated', extra={
            'language_code': unicode(language_code),
        })
    return '?'

@register.filter()
def to_language_display(language_code):
    return  LANGUAGE_NAMES[language_code]

@register.filter()
def to_localized_display_list(language_codes):
    display = []
    for lc in language_codes:
        display.append(to_localized_display(lc))
    return ', '.join(display)
