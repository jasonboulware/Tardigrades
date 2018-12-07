# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0011_auto_20180830_1237'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='videoindex',
            name='video',
        ),
        migrations.DeleteModel(
            name='VideoIndex',
        ),
    ]
