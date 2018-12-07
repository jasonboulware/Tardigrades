# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0001_initial'),
        ('subtitles', '0001_initial'),
        ('videos', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='action',
            name='member',
            field=models.ForeignKey(blank=True, to='teams.TeamMember', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='action',
            name='new_language',
            field=models.ForeignKey(blank=True, to='subtitles.SubtitleLanguage', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='action',
            name='team',
            field=models.ForeignKey(blank=True, to='teams.Team', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='subtitlelanguage',
            name='new_subtitle_language',
            field=models.ForeignKey(related_name='old_subtitle_version', blank=True, editable=False, to='subtitles.SubtitleLanguage', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='subtitleversion',
            name='new_subtitle_version',
            field=models.OneToOneField(related_name='old_subtitle_version', null=True, blank=True, editable=False, to='subtitles.SubtitleVersion'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='video',
            name='moderated_by',
            field=models.ForeignKey(related_name='moderating', blank=True, to='teams.Team', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='videofeed',
            name='team',
            field=models.ForeignKey(blank=True, to='teams.Team', null=True),
            preserve_default=True,
        ),
    ]
