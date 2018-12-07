# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('amara_auth', '0003_auto_20180219_1501'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='last_hidden_message_id',
            field=models.PositiveIntegerField(default=0, blank=True),
            preserve_default=True,
        ),
    ]
