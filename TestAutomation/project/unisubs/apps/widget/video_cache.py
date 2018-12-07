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
import datetime
import hashlib

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import (
    ugettext_lazy as _
)

from videos.types import video_type_registrar
from videos.types.base import VideoTypeError
import unilangs

TIMEOUT = 60 * 60 * 24 * 5 # 5 days


def get_video_id(video_url, public_only=False, referer=None):
    """
    Returns the cache video_id for this video
    If public only is
    """
    cache_key = _video_id_key(video_url)
    value = cache.get(cache_key)
    if bool(value):
        return value
    else:
        from videos.models import Video
        try:
            video, _ = Video.add(video_url, None)
        except Video.DuplicateUrlError, e:
            video = e.video

        video_id = video.video_id

        cache.set(cache_key, video_id, TIMEOUT)
        return video_id

def associate_extra_url(video_url, video_id):
    cache_key = _video_id_key(video_url)
    value = cache.get(cache_key)
    if value is None:
        from videos.models import VideoUrl, Video
        vt = video_type_registrar.video_type_for_url(video_url)
        video_url, created = VideoUrl.objects.get_or_create(
            url=vt.convert_to_video_url(),
            defaults={
                'video': Video.objects.get(video_id=video_id),
                'type': vt.abbreviation,
                'videoid': video_id })
        cache.set(cache_key, video_url.videoid, TIMEOUT)


# Invalidation
def invalidate_cache(video_id):
    cache.delete(_video_urls_key(video_id))

    try:
        from videos.models import Video
        video = Video.objects.get(video_id=video_id)
        for l in video.newsubtitlelanguage_set.all():
            cache.delete(_subtitles_dict_key(video_id, l.pk))
    except Video.DoesNotExist:
        pass

    for language in settings.ALL_LANGUAGES:
        cache.delete(_subtitle_language_pk_key(video_id, language[0]))

    cache.delete(_subtitle_language_pk_key(video_id, None))
    cache.delete(_subtitles_dict_key(video_id, None))
    cache.delete(_subtitles_count_key(video_id))
    cache.delete(_video_languages_key(video_id))
    cache.delete(_video_languages_verbose_key(video_id))
    cache.delete(_video_is_moderated_key(video_id))
    cache.delete(_video_visibility_policy_key(video_id))
    cache.delete(_video_filename_key(video_id))

    from videos.models import Video
    try:
        video = Video.objects.get(video_id=video_id)
        for url in video.videourl_set.all():
            cache.delete(_video_id_key(url.url))

        team_video = video.get_team_video()

        if team_video:
            cache.delete(_video_completed_languages(team_video.id))
    except Video.DoesNotExist:
        pass

def invalidate_video_id(video_url):
    cache.delete(_video_id_key(video_url))

def invalidate_video_moderation(video_id):
    cache.delete(_video_is_moderated_key(video_id))

def invalidate_video_visibility(video_id):
    cache.delete(_video_visibility_policy_key(video_id))

def on_video_url_delete(sender, instance, **kwargs):
    if instance.video and instance.video.video_id:
        invalidate_cache(instance.video.video_id)

def _video_id_key(video_url):
    return 'video_id_{0}'.format(hashlib.sha1(video_url).hexdigest())

def _video_urls_key(video_id):
    return 'widget_video_urls_{0}'.format(video_id)

def _subtitles_dict_key(video_id, language_pk, version_no=None):
    return 'widget_subtitles_{0}{1}{2}'.format(video_id, language_pk, version_no)

def _subtitles_count_key(video_id):
    return "subtitle_count_{0}".format(video_id)

def _video_languages_key(video_id):
    return "widget_video_languages_{0}".format(video_id)

def _video_languages_verbose_key(video_id):
    return "widget_video_languages_verbose_{0}".format(video_id)

def _video_completed_languages(video_id):
    return "video_completed_verbose_{0}".format(video_id)

def _video_writelocked_langs_key(video_id):
    return "writelocked_langs_{0}".format(video_id)

def _subtitle_language_pk_key(video_id, language_code):
    return "sl_pk_{0}{1}".format(video_id, language_code)

def _video_is_moderated_key(video_id):
    return 'widget_video_is_moderated_{0}'.format(video_id)

def _video_filename_key(video_id):
    return 'widget_video_filename_{0}'.format(video_id)

def _video_visibility_policy_key(video_id):
    return 'widget_video_vis_key_{0}'.format(video_id)


def pk_for_default_language(video_id, language_code):
    # the widget sends langauge code as an empty dict
    # don't ask me why
    language_code = language_code or None
    cache_key = _subtitle_language_pk_key(video_id, language_code)
    value = cache.get(cache_key)

    if value is None:
        from videos.models import Video
        sl = Video.objects.get(video_id=video_id).subtitle_language(
            language_code)
        value = None if sl is None else sl.pk
        cache.set(cache_key, value, TIMEOUT)

    return value

def get_video_urls(video_id):
    cache_key = _video_urls_key(video_id)
    video_urls = cache.get(cache_key)

    if video_urls is None:
        from videos.models import Video
        video_urls = [vu.url for vu
                 in Video.objects.get(video_id=video_id).videourl_set.all()]
        cache.set(cache_key, video_urls, TIMEOUT)

    return video_urls

def get_subtitles_dict(video_id, language_pk, version_number, 
                       subtitles_dict_fn, is_remote=False):

    cache_key = _subtitles_dict_key(video_id, language_pk, version_number)
    cached_value = cache.get(cache_key)

    if cached_value is None:
        from videos.models import Video
        from subtitles.models import SubtitleLanguage
        video = Video.objects.get(video_id=video_id)

        if language_pk is None:
            language = video.subtitle_language()
        else:
            try:
                language = video.newsubtitlelanguage_set.get(pk=language_pk)
            except SubtitleLanguage.DoesNotExist:
                language = video.subtitle_language()

        if language:
            version = language.version(version_number=version_number, public_only=not is_remote)

            if version:
                cached_value = subtitles_dict_fn(version)
            else:
                cached_value = None

            cache.set(cache_key, cached_value, TIMEOUT)

    return cached_value

def get_video_languages(video_id):
    from widget.rpc import language_summary

    cache_key = _video_languages_key(video_id)
    value = cache.get(cache_key)

    if value is None:
        from videos.models import Video
        video = Video.objects.get(video_id=video_id)
        languages = video.newsubtitlelanguage_set.having_nonempty_versions()

        team_video = video.get_team_video()

        if team_video:
            languages = languages.filter(language_code__in=team_video.team.get_readable_langs())

        value = [language_summary(l) for l in languages]
        cache.set(cache_key, value, TIMEOUT)

    return value

def get_video_completed_languages(team_video_id):
    cache_key = _video_completed_languages(team_video_id)
    languages = cache.get(cache_key)

    if languages is None:
        from videos.models import SubtitleLanguage
        languages = [sl.language for sl in list(SubtitleLanguage.objects.filter(video__teamvideo__id=team_video_id).all())]

        cache.set(cache_key, languages, TIMEOUT)

    # i18n is a pain in the ass
    return [(lang, _(unilangs.INTERNAL_NAMES[lang][0])) for lang in languages]

def get_video_languages_verbose(video_id, max_items=6):
    # FIXME: we should probably merge a better method with get_video_languages
    # maybe accepting a 'verbose' param?
    cache_key = _video_languages_verbose_key(video_id)
    data = cache.get(cache_key)

    if data is None:
        from videos.models import Video
        video = Video.objects.get(video_id=video_id)
        languages_with_version_total = video.subtitlelanguage_set.filter(has_version=True).order_by('-percent_done')
        total_number = languages_with_version_total.count()
        languages_with_version = languages_with_version_total[:max_items]
        data = { "items":[]}
        if total_number > max_items:
            data["total"] = total_number - max_items
        for lang in languages_with_version:
            # show only with some translation
            if lang.is_dependent():
                data["items"].append({
                    'language': lang.language,
                    'percent_done': lang.percent_done ,
                    'language_url': lang.get_absolute_url(),
                    'is_dependent': True,
                })
            else:
                # append to the beggininig of the list as
                # the UI will show this first
                data["items"].insert(0, {
                    'language': lang.language,
                    'is_complete': lang.is_complete,
                    'language_url': lang.get_absolute_url(),
                })
        cache.set(cache_key, data, TIMEOUT)

    return data

def get_is_moderated(video_id):
    cache_key = _video_is_moderated_key(video_id)
    value = cache.get(cache_key)

    if value is None:
        from videos.models import Video
        video = Video.objects.get(video_id=video_id)
        value = video.is_moderated
        cache.set(cache_key, value, TIMEOUT)

    return value

def get_download_filename(video_id):
    cache_key = _video_filename_key(video_id)
    value = cache.get(cache_key)

    if value is None:
        from videos.models import Video
        video = Video.objects.get(video_id=video_id)
        value = video.get_download_filename()
        cache.set(cache_key, value, TIMEOUT)

    return value

def get_visibility_policies(video_id):
    cache_key = _video_visibility_policy_key(video_id)
    value = cache.get(cache_key)

    if value is None:
        from videos.models import Video

        try:
            video = Video.objects.get(video_id=video_id)
        except Video.DoesNotExist:
            return {}

        team_video = video.get_team_video()

        if team_video:
            team = team_video.team
            is_public = team.videos_public()
            team_id = team.id
        else:
            is_public = True
            team_id = None

        value = {
            "is_public": is_public,
            "team_id": team_id
        }

        cache.set(cache_key, value, TIMEOUT)

    return value

# Writelocking
def _writelocked_store_langs(video_id, langs):
    cache_key = _video_writelocked_langs_key(video_id)
    cache.set(cache_key, langs, 5 * 60)
    return langs

def writelocked_langs(video_id):
    from subtitles.models import WRITELOCK_EXPIRATION, Video
    cache_key = _video_writelocked_langs_key(video_id)
    value = cache.get(cache_key)

    if value is None:
        treshold = datetime.datetime.now() - datetime.timedelta(seconds=WRITELOCK_EXPIRATION)
        video = Video.objects.get(video_id=video_id)
        langs = list(video.subtitlelanguage_set.filter(writelock_time__gte=treshold))
        value = _writelocked_store_langs(video_id, [x.language for x in langs])

    return value

def writelock_add_lang(video_id, language_code):
    writelocked_langs_clear(video_id)
    langs = writelocked_langs(video_id)

    if not language_code in langs:
        langs.append(language_code)
        _writelocked_store_langs(video_id, langs)

def writelock_remove_lang(video_id, language_code):
    langs = writelocked_langs(video_id)
    if language_code in langs:
        langs.remove(language_code)
        _writelocked_store_langs(video_id, langs)

def writelocked_langs_clear(video_id):
    cache_key = _video_writelocked_langs_key(video_id)
    cache.delete(cache_key)
