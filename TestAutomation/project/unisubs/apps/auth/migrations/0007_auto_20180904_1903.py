# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('amara_auth', '0006_customuser_username_old'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='last_ip',
            field=models.GenericIPAddressField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
