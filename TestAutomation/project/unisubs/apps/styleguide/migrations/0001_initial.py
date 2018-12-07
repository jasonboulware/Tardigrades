# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import utils.amazon.fields


class Migration(migrations.Migration):

    dependencies = [
        ('amara_auth', '0006_customuser_username_old'),
    ]

    operations = [
        migrations.CreateModel(
            name='StyleguideData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('thumbnail', utils.amazon.fields.S3EnabledImageField(upload_to=b'styleguide/thumbnail/', blank=True)),
                ('user', models.OneToOneField(to='amara_auth.CustomUser')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
