# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import auth.models


class Migration(migrations.Migration):

    dependencies = [
        ('amara_auth', '0007_auto_20180904_1903'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='customuser',
            managers=[
                ('objects', auth.models.CustomUserManager()),
            ],
        ),
    ]
