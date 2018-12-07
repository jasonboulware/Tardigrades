from django.contrib.contenttypes.models import ContentType
from subtitles.models import SubtitleLanguage
from subtitles.signals import subtitles_published
from teams.signals import api_subtitles_approved
from utils.csv_parser import UnicodeReader
from videos.tasks import video_changed_tasks

def complete_approve_tasks(tasks):
    lang_ct = ContentType.objects.get_for_model(SubtitleLanguage)
    video_ids = set()
    for task in tasks:
        task.do_complete_approve(lang_ct=lang_ct)
        version = task.get_subtitle_version()
        api_subtitles_approved.send(version)
        if version.is_public():
            subtitles_published.send(version.subtitle_language, version=version)
        video_ids.add(task.team_video.video_id)
    for video_id in video_ids:
        video_changed_tasks.delay(video_id)

def add_videos_from_csv(team, user, csv_file):
    from .tasks import add_team_videos
    videos = []
    fields = ['project', 'url', 'title', 'description', 'duration', 'language', 'transcript']
    num_fields = len(fields)
    try:
        reader = UnicodeReader(csv_file)
        header = reader.next()
        if len(header) != num_fields:
            raise Exception()
    except:
        raise ValueError(u'CSV format is not valid')
    for row in reader:
        videos.append(dict(zip(fields, row)))
    add_team_videos.delay(team.pk, user.pk, videos)
