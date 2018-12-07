# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0003_auto_20180418_0950'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='team',
            name='page_content',
        ),
        migrations.AddField(
            model_name='team',
            name='resources_page_content',
            field=models.TextField(verbose_name='Team resources page text', blank=True),
            preserve_default=True,
        ),
    ]
