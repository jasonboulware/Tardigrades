# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('amara_auth', '0005_auto_20180405_1519'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='username_old',
            field=models.CharField(default=b'', max_length=30, null=True, blank=True),
            preserve_default=True,
        ),
    ]
