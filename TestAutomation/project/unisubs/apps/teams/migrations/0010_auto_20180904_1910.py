# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0009_auto_20180904_1903'),
    ]

    operations = [
        migrations.AlterField(
            model_name='teamnotificationsetting',
            name='email',
            field=models.EmailField(max_length=254, null=True, blank=True),
        ),
    ]
