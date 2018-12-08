# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import messages.models


class Migration(migrations.Migration):

    dependencies = [
        ('amara_auth', '0002_auto_20180215_1232'),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('subject', models.CharField(max_length=100, blank=True)),
                ('content', models.TextField(max_length=1000, blank=True)),
                ('read', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('deleted_for_user', models.BooleanField(default=False)),
                ('deleted_for_author', models.BooleanField(default=False)),
                ('object_pk', models.TextField(null=True, verbose_name=b'object ID', blank=True)),
                ('thread', models.PositiveIntegerField(db_index=True, null=True, blank=True)),
                ('has_reply_for_author', models.BooleanField(default=False)),
                ('has_reply_for_user', models.BooleanField(default=False)),
                ('message_type', models.CharField(max_length=1, choices=[(b'S', b'System Notification'), (b'M', b'Personal Message'), (b'O', b'Old Type Message')], validators=[messages.models.validate_message_type])),
                ('author', models.ForeignKey(related_name='sent_messages', blank=True, to='amara_auth.CustomUser', null=True)),
                ('content_type', models.ForeignKey(related_name='content_type_set_for_message', blank=True, to='contenttypes.ContentType', null=True)),
                ('user', models.ForeignKey(to='amara_auth.CustomUser')),
            ],
            options={
                'ordering': ['-id'],
            },
            bases=(models.Model,),
        ),
    ]
