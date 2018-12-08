# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0009_auto_20180913_1441'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='tags',
            field=models.ManyToManyField(related_name='teams', to='teams.TeamTag'),
            preserve_default=True,
        ),
    ]
