# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0001_initial'),
        ('videos', '0002_auto_20180215_1232'),
        ('amara_auth', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='partner',
            field=models.ForeignKey(blank=True, to='teams.Partner', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='customuser',
            name='videos',
            field=models.ManyToManyField(to='videos.Video', blank=True),
            preserve_default=True,
        ),
    ]
