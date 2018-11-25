from datetime import datetime
import logging

logger = logging.getLogger('teams.tasks')

from django.conf import settings
from django.db.models import F
from django.utils.translation import ugettext_lazy as _
import requests

from utils import send_templated_email
from utils.panslugify import pan_slugify
from utils.translation import SUPPORTED_LANGUAGE_CODES
from widget.video_cache import (
    invalidate_cache as invalidate_video_cache,
    invalidate_video_moderation,
    invalidate_video_visibility
)

from utils.taskqueue import job
from utils.text import fmt
from videos.tasks import video_changed_tasks

@job
def invalidate_video_caches(team_id):
    """Invalidate all TeamVideo caches for all the given team's videos."""
    from teams.models import Team
    team = Team.objects.get(pk=team_id)
    for video_id in team.teamvideo_set.values_list('video__video_id', flat=True):
        invalidate_video_cache(video_id)

@job
def invalidate_video_moderation_caches(team):
    """Invalidate the moderation status caches for all the given team's videos."""
    for video_id in team.teamvideo_set.values_list('video__video_id', flat=True):
        invalidate_video_moderation(video_id)

@job
def update_video_moderation(team):
    """Set the moderated_by field for all the given team's videos."""
    from videos.models import Video

    moderated_by = team if team.moderates_videos() else None
    Video.objects.filter(teamvideo__team=team).update(moderated_by=moderated_by)

@job
def invalidate_video_visibility_caches(team):
    for video_id in team.teamvideo_set.values_list("video__video_id", flat=True):
        invalidate_video_visibility(video_id)

@job
def update_video_public_field(team_id):
    from teams.models import Team

    team = Team.objects.get(pk=team_id)

    for team_video in team.teamvideo_set.all():
        video = team_video.video
        video.is_public = team.videos_public()
        video.save()
        video_changed_tasks(video.id)

@job
def expire_tasks():
    """Find any tasks that are past their expiration date and unassign them.

    We currently run this once per day (at 7 AM server time).

    """
    from teams.models import Task

    expired_tasks = Task.objects.incomplete().filter(
        expiration_date__isnull=False,
        expiration_date__lt=datetime.now(),
    )
    for task in expired_tasks:
        task.assignee = task.expiration_date = None
        # run each inside a try/except so that one
        # rotten apple doesn't make a huge mess
        try:
            task.save()
        except Exception as e:
            logger.error('Error on expiring tasks', extra={
            'task': task,
            'exception': e,
        })

@job(timeout=600)
def add_videos_notification_daily(*args, **kwargs):
    from teams.models import Team
    team_qs = Team.objects.needs_new_video_notification(Team.NOTIFY_DAILY)
    _notify_teams_of_new_videos(team_qs)

@job(timeout=600)
def add_videos_notification_hourly(*args, **kwargs):
    from teams.models import Team
    team_qs = Team.objects.needs_new_video_notification(Team.NOTIFY_HOURLY)
    _notify_teams_of_new_videos(team_qs)

def _notify_teams_of_new_videos(team_qs):
    from messages.tasks import team_sends_notification
    from teams.models import TeamVideo
    domain = settings.HOSTNAME

    for team in team_qs:
        if not team_sends_notification(team, 'block_new_video_message'):
            continue
        team_videos = TeamVideo.objects.filter(team=team, created__gt=team.last_notification_time)

        team.last_notification_time = datetime.now()
        team.save()
        members = team.users.filter( notify_by_email=True, is_active=True) \
            .distinct()

        subject = fmt(_(u'New %(team)s videos ready for subtitling!'),
                      team=team)

        for user in members:
            if not user.email:
                continue

            context = {
                'domain': domain,
                'user': user,
                'team': team,
                'team_videos': team_videos,
                "STATIC_URL": settings.STATIC_URL,
            }

            send_templated_email(user, subject,
                                 'teams/email_new_videos.html',
                                 context, fail_silently=not settings.DEBUG)


@job
def api_notify_on_subtitles_activity(team_pk, event_name, version_pk):
    from teams.models import TeamNotificationSetting
    from subtitles.models import SubtitleVersion
    version = SubtitleVersion.objects.select_related("subtitle_language", "video").get(pk=version_pk)
    TeamNotificationSetting.objects.notify_team(team_pk, event_name,
            video_id=version.video.video_id,
            language_pk=version.subtitle_language.pk, version_pk=version_pk)

@job
def api_notify_on_language_activity(team_pk, event_name, language_pk):
    from teams.models import TeamNotificationSetting
    from subtitles.models import SubtitleLanguage
    language = SubtitleLanguage.objects.select_related("video").get(pk=language_pk)
    TeamNotificationSetting.objects.notify_team(
        team_pk, event_name, language_pk=language_pk, video_id=language.video.video_id)

@job
def api_notify_on_video_activity(team_pk, event_name, video_id):
    from teams.models import TeamNotificationSetting
    TeamNotificationSetting.objects.notify_team(team_pk, event_name, video_id=video_id)

@job
def api_notify_on_application_activity(team_pk, event_name, application_pk):
    from teams.models import TeamNotificationSetting
    TeamNotificationSetting.objects.notify_team(
        team_pk, event_name, application_pk=application_pk)

@job
def process_billing_report(billing_report_pk):
    from teams.models import BillingReport
    report = BillingReport.objects.get(pk=billing_report_pk)
    report.process()

@job
def add_team_videos(team_pk, user_pk, videos):
    from .permissions import can_add_videos_bulk
    from teams.models import Team, Project, TeamVideo
    from videos.models import Video
    from videos.types import video_type_registrar
    from auth.models import CustomUser as User
    from utils.subtitles import load_subtitles
    from subtitles.pipeline import add_subtitles
    user = User.objects.get(pk=int(user_pk))
    team = Team.objects.get(pk=int(team_pk))
    num_successful_videos = 0
    messages = []
    if can_add_videos_bulk(user):
        for video_item in videos:
            video_url = video_item['url']
            try:
                video_type = video_type_registrar.video_type_for_url(video_url)
                video_url = video_type.convert_to_video_url()
            except:
                messages.append(fmt(_(u"Unknown video type: %(url)s\n"), url=video_url))
                continue

            def setup_video(video, video_url):
                video.is_public = team.videos_public()
                if video_item.get('title'):
                    video.title = video_item['title']
                if video_item.get('description'):
                    video.description = video_item['description']
                if video_item.get('language'):
                    language = video_item['language'].lower()
                    if language in SUPPORTED_LANGUAGE_CODES:
                        video.primary_audio_language_code = language
                    else:
                        messages.append(fmt(_(u"Badly formated language for %(url)s: %(language)s, ignoring it."), url=video_url, language=video_item['language']))
                if video_item.get('duration') and not video.duration:
                    try:
                        video.duration = int(video_item['duration'])
                    except:
                        messages.append(fmt(_(u"Badly formated duration for %(url)s: %(duration)s, ignoring it."), url=video_url, duration=video_item['duration']))
                if video_item.get('project'):
                    project, created = Project.objects.get_or_create(team=team, slug=pan_slugify(video_item['project']), defaults={'name': video_item['project']})
                else:
                    project = team.default_project
                team_video = TeamVideo.objects.create(video=video, team=team,
                                                      project=project, added_by=user)

            try:
                video, video_url = Video.add(video_type, user, setup_video, team)
            except Video.DuplicateUrlError, e:
                messages.append(fmt(
                    _(u"Video is already added to team: %(url)s\n"),
                    url=e.video_url))
                continue

            if 'transcript' in video_item and len(video_item['transcript']) > 0 and video.primary_audio_language_code:
                try:
                    sub_type = video_item['transcript'].split(".")[-1]
                    r = requests.get(video_item['transcript'])
                    if r.ok:
                        subs = load_subtitles(video.primary_audio_language_code, r.text, sub_type)
                        version = add_subtitles(video, video.primary_audio_language_code, subs)
                    else:
                        raise Exception("Request not successful")
                except Exception, e:
                    logger.error("Error while importing transcript file: {}".format(str(e)))
                    messages.append(fmt(_(u"Invalid transcript file or language code for video %(url)s\n"), url=video_url))
            num_successful_videos += 1
    else:
        messages.append(fmt(_(u'You are not authorized to perform such action\n')))
    messages.append(fmt(_(u"Number of videos added to team: %(num)i\n"), num=num_successful_videos))
    domain = settings.HOSTNAME
    context = {
        'domain': domain,
        'user': user,
        'team': team,
        'messages': messages,
        "STATIC_URL": settings.STATIC_URL,
    }
    send_templated_email(user, "Summary of videos added to team on Amara",
                         'teams/email_videos_added.html',
                         context, fail_silently=not settings.DEBUG)
