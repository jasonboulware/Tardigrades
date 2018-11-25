# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0002_auto_20180405_0626'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailinvite',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2018, 4, 6, 7, 55, 14, 643217), auto_now_add=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='emailinvite',
            name='email',
            field=models.EmailField(max_length=254),
            preserve_default=True,
        ),
    ]
