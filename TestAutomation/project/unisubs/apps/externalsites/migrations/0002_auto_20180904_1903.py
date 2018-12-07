# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('externalsites', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='creditedvideourl',
            name='video_url',
            field=models.OneToOneField(primary_key=True, serialize=False, to='videos.VideoUrl'),
            preserve_default=True,
        ),
    ]
