# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import codefield


class Migration(migrations.Migration):

    dependencies = [
        ('activity', '0006_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activityrecord',
            name='type',
            field=codefield.CodeField(),
            preserve_default=True,
        ),
    ]
