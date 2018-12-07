import json
from django.conf import settings
from django.template.defaulttags import register
from django.utils.safestring import mark_safe
from django.urls import reverse

ALL_LANGUAGES_DICT = dict(settings.ALL_LANGUAGES)

@register.filter
def get_fields(dictionary):
    output = []
    dict = json.loads(dictionary)
    output.append(mark_safe('<a target="blank" href="' +
                            dict['video_url']
                             +
                            '">' + dict['account_type'] + '</a>'))
    video_url = reverse("videos:translation_history_legacy",
                        kwargs={"video_id": dict['video_id'],
                                "lang": dict['language_code']})
    output.append(mark_safe('<a href="' +
                            video_url
                             +
                            '">' + dict['video_id'] + '</a>'))
    language = language_code = dict['language_code']
    if language_code in ALL_LANGUAGES_DICT:
        language = ALL_LANGUAGES_DICT[language_code]
    output.append(language)
    output.append(dict['details'])
    return output
