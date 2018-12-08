# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from utils.convertlegacyindextogether import ConvertLegacyIndexTogether


class Migration(migrations.Migration):

    dependencies = [
        ('activity', '0004_auto_20180426_1006'),
    ]

    operations = [
        ConvertLegacyIndexTogether(
            name='activityrecord',
            index_together=set([('user', 'copied_from', 'created'), ('team', 'type', 'created'), ('team', 'language_code', 'created'), ('video', 'copied_from', 'created'), ('team', 'type', 'video_language_code', 'created'), ('team', 'created')]),
        ),
    ]
