# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TeamNotification',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.IntegerField()),
                ('data', models.CharField(max_length=5120)),
                ('url', models.URLField(max_length=512)),
                ('timestamp', models.DateTimeField()),
                ('response_status', models.IntegerField(null=True, blank=True)),
                ('error_message', models.CharField(max_length=256, null=True, blank=True)),
                ('team', models.ForeignKey(to='teams.Team')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TeamNotificationSettings',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=30)),
                ('url', models.URLField(max_length=512)),
                ('auth_username', models.CharField(max_length=128, blank=True)),
                ('auth_password', models.CharField(max_length=128, blank=True)),
                ('header1', models.CharField(max_length=256, blank=True)),
                ('header2', models.CharField(max_length=256, blank=True)),
                ('header3', models.CharField(max_length=256, blank=True)),
                ('extra_teams', models.ManyToManyField(related_name='team_settings_extra', verbose_name='Extra teams to notify', to='teams.Team')),
                ('team', models.OneToOneField(to='teams.Team')),
            ],
            options={
                'verbose_name_plural': 'Team notification settings',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='teamnotification',
            unique_together=set([('team', 'number')]),
        ),
    ]
