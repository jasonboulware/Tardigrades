# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('amara_auth', '0002_auto_20180215_1232'),
    ]

    operations = [
        migrations.CreateModel(
            name='FacebookAccount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(editable=False)),
                ('modified', models.DateTimeField(editable=False)),
                ('uid', models.CharField(unique=True, max_length=200)),
                ('avatar', models.URLField(null=True, blank=True)),
                ('user', models.ForeignKey(to='amara_auth.CustomUser')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TwitterAccount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(editable=False)),
                ('modified', models.DateTimeField(editable=False)),
                ('username', models.CharField(unique=True, max_length=200)),
                ('access_token', models.CharField(max_length=255, null=True, editable=False, blank=True)),
                ('avatar', models.URLField(null=True, blank=True)),
                ('user', models.ForeignKey(to='amara_auth.CustomUser')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VimeoExternalAccount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(editable=False)),
                ('modified', models.DateTimeField(editable=False)),
                ('username', models.CharField(unique=True, max_length=200)),
                ('access_code', models.CharField(max_length=255, null=True, editable=False, blank=True)),
                ('user', models.ForeignKey(to='amara_auth.CustomUser')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]
