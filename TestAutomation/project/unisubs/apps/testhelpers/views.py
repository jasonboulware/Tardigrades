import os, json
from random import shuffle
from django.http import HttpResponse
from django.conf import settings
from django.core import serializers
from django.views.decorators.csrf import csrf_exempt

from teams.models import Team, TeamVideo
from videos.models import Video
from auth.models import  CustomUser
from django.db import transaction

from subtitles import pipeline
from subtitles import models as sub_models
from utils.decorators import staff_member_required

import babelsubs
from babelsubs.storage import SubtitleSet

import logging
logger = logging.getLogger("test-fixture-loading")

from utils.decorators import never_in_prod
from utils.factories import *

def _get_fixture_path(model_name):
    return os.path.join(settings.PROJECT_ROOT, "apps", "testhelpers", "fixtures", "%s-fixtures.json" % model_name)

def _get_fixture_file(model_name):
    return file(_get_fixture_path(model_name))


def _add_subtitles(sub_lang, num_subs, video, translated_from=None):
    subtitle_set = SubtitleSet(sub_lang.language_code)

    for i in xrange(0, num_subs):
        start_time=i * 1000
        end_time =i + 800
        subtitle_text = 'hey jude %s' % i
        subtitle_set.append_subtitle(start_time, end_time, subtitle_text)

    parents = []

    if translated_from:
        parents.append(translated_from.get_tip())

    return pipeline.add_subtitles(video, sub_lang.language_code, subtitle_set, parents=parents)

def _add_lang_to_video(video, props,  translated_from=None):
    if props.get('is_original', False):
        video.newsubtitlelanguage_set.all().delete()

    sub_lang = video.subtitle_language(props.get('code', ''))

    if not video.primary_audio_language_code:
        video.primary_audio_language_code = props.get('code', '')
        video.save()

    if not sub_lang:
        sub_lang = sub_models.SubtitleLanguage(
            video=video,
            subtitles_complete=props.get('is_complete', False),
            language_code=props.get('code'),
            is_forked=True,
        )

        sub_lang.save()

    num_subs = props.get("num_subs", 0)

    _add_subtitles(sub_lang, num_subs, video, translated_from)

    for translation_prop in props.get("translations", []):
        _add_lang_to_video(video, translation_prop, translated_from=sub_lang)

    sub_lang.save()

    from videos.tasks import video_changed_tasks
    video_changed_tasks(sub_lang.video.id)
    return sub_lang

def _add_langs_to_video(video, props):
    for prop in props:
        _add_lang_to_video(video, prop)

SRT = u"""1
00:00:00,004 --> 00:00:02,093
We\n started <b>Universal Subtitles</b> <i>because</i> we <u>believe</u>
"""
def _add_language_via_pipeline(video, lang):
    subtitles = babelsubs.load_from(SRT, type='srt', language='en').to_internal()
    return pipeline.add_subtitles(video, lang, subtitles)

def _create_videos(video_data, users):
    videos = []

    for x in video_data:
        shuffle(users)
        def setup_video(video, video_url):
            video.title = x.get('title')
            video.is_subtitled = x['langs'] > 0
        video, video_url = Video.add(x['url'], user[0] if users else None,
                                     setup_video)
        _add_langs_to_video(video, x['langs'])
        videos.append(video)

    return videos

def _hydrate_users(users_data):
    users = []
    for x in serializers.deserialize('json', users_data):
        x.save()
        users.append(x.object)
    return users

# create 30 videos
def _create_team_videos(team, videos, users):
    tvs = []
    for video in videos:
        shuffle(users)
        team_video = TeamVideo(team=team, video=video)
        member, created = CustomUser.objects.get_or_create(user_ptr=users[0])
        team_video.added_by = member
        team_video.save()
        tvs.append(team_video)
    return tvs

@transaction.atomic
def _do_it(video_data_url=None):
    team, created = Team.objects.get_or_create(slug="unisubs-test-team")
    team.name = "Unisubs test"
    team.save()

    team.videos.all().delete()
    users = _hydrate_users(_get_fixture_file("users").read())
    if video_data_url:
        import httplib2
        h = httplib2.Http("/tmp/.httplibcache")
        resp, content = h.request("http://www.emptywhite.com/misc/videos-fixtures.json")
        video_data  = json.loads(content)
    else:
        video_data  = json.load(_get_fixture_file("videos"))

    videos = _create_videos(video_data, [])
    _create_team_videos(team, videos, users)

@staff_member_required
@never_in_prod
def load_team_fixtures(request ):
    load_from = request.GET.get("load_from", None)
    videos = _do_it(load_from)
    return HttpResponse( "created %s videos" % len(videos))

@csrf_exempt
def echo_json(request):
    data   = getattr(request, request.method).copy()
    data["url_path"] = request.path
    return HttpResponse(json.dumps(data, indent=4))
