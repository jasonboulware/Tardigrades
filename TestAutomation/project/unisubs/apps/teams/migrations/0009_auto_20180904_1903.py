# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0008_auto_20180820_1023'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partner',
            name='admins',
            field=models.ManyToManyField(related_name='managed_partners', to='amara_auth.CustomUser', blank=True),
            preserve_default=True,
        ),
    ]
