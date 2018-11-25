# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations

def create_anonymous_user(apps, schema_editor):
    CustomUser = apps.get_model('amara_auth', 'CustomUser')
    CustomUser.objects.get_or_create(
        pk=settings.ANONYMOUS_USER_ID,
        defaults={'username': settings.ANONYMOUS_DEFAULT_USERNAME})

class Migration(migrations.Migration):

    dependencies = [
        ('amara_auth', '0002_auto_20180215_1232'),
    ]

    operations = [
        migrations.RunPython(create_anonymous_user),
    ]
