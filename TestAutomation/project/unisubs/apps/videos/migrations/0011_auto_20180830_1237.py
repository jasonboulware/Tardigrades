# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0010_merge_20181012_1358'),
    ]

    operations = [
        migrations.RunSQL([
            'UPDATE videos_video '
            'SET search_text = '
            '(SELECT text FROM videos_videoindex '
            'WHERE videos_video.id = videos_videoindex.video_id)'
        ])
    ]
