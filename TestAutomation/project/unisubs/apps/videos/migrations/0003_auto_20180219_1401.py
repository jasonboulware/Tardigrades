# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ('amara_auth', '0003_auto_20180219_1501'),
        ('videos', '0002_auto_20180215_1232'),
    ]

    operations = [
        migrations.AlterField(
            model_name='video',
            name='user',
            field=models.ForeignKey(default=settings.ANONYMOUS_USER_ID, blank=True, to='amara_auth.CustomUser', null=True),
            preserve_default=True,
        ),
    ]
