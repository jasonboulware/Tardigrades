# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from utils.convertlegacyindextogether import ConvertLegacyIndexTogether

class Migration(migrations.Migration):

    dependencies = [
        ('messages', '0001_initial'),
    ]

    operations = [
        ConvertLegacyIndexTogether(
            name='message',
            index_together=set([('user', 'deleted_for_user', 'has_reply_for_user'), ('user', 'deleted_for_user', 'read', 'id'), ('user', 'deleted_for_author', 'has_reply_for_author')]),
        ),
    ]
