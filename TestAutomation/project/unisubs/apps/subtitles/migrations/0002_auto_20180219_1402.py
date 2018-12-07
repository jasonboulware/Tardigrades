# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ('amara_auth', '0003_auto_20180219_1501'),
        ('subtitles', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subtitleversion',
            name='author',
            field=models.ForeignKey(related_name='newsubtitleversion_set', default=settings.ANONYMOUS_USER_ID, to='amara_auth.CustomUser'),
            preserve_default=True,
        ),
    ]
