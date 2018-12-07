# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('amara_auth', '0002_auto_20180215_1232'),
        ('subtitles', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SubtitlingSession',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('browser_id', models.CharField(max_length=128, blank=True)),
                ('datetime_started', models.DateTimeField(auto_now_add=True)),
                ('base_language', models.ForeignKey(related_name='based_subtitling_sessions', to='subtitles.SubtitleLanguage', null=True)),
                ('language', models.ForeignKey(related_name='subtitling_sessions', to='subtitles.SubtitleLanguage')),
                ('parent_version', models.ForeignKey(to='subtitles.SubtitleVersion', null=True)),
                ('user', models.ForeignKey(to='amara_auth.CustomUser', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
