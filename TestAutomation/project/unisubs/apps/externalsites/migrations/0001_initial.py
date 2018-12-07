# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0001_initial'),
        ('videos', '0002_auto_20180215_1232'),
        ('amara_auth', '0002_auto_20180215_1232'),
        ('subtitles', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BrightcoveAccount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=1, choices=[(b'U', 'User'), (b'T', 'Team')])),
                ('owner_id', models.IntegerField()),
                ('publisher_id', models.CharField(max_length=100, verbose_name='Publisher ID')),
                ('write_token', models.CharField(max_length=100)),
                ('import_feed', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, to='videos.VideoFeed')),
            ],
            options={
                'verbose_name': 'Brightcove account',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BrightcoveCMSAccount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=1, choices=[(b'U', 'User'), (b'T', 'Team')])),
                ('owner_id', models.IntegerField()),
                ('publisher_id', models.CharField(max_length=100, verbose_name='Publisher ID')),
                ('client_id', models.CharField(max_length=100, verbose_name='Client ID')),
                ('client_secret', models.CharField(max_length=100, verbose_name='Client Secret')),
            ],
            options={
                'verbose_name': 'Brightcove CMS account',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CreditedVideoUrl',
            fields=[
                ('video_url', models.ForeignKey(primary_key=True, serialize=False, to='videos.VideoUrl')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='KalturaAccount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=1, choices=[(b'U', 'User'), (b'T', 'Team')])),
                ('owner_id', models.IntegerField()),
                ('partner_id', models.CharField(max_length=100, verbose_name='Partner ID')),
                ('secret', models.CharField(help_text='Administrator secret found in Settings -> Integration on your Kaltura control panel', max_length=100, verbose_name='Secret')),
            ],
            options={
                'verbose_name': 'Kaltura account',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OpenIDConnectLink',
            fields=[
                ('sub', models.CharField(max_length=255, serialize=False, primary_key=True)),
                ('user', models.OneToOneField(related_name='openid_connect_link', to='amara_auth.CustomUser')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SyncedSubtitleVersion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('account_type', models.CharField(max_length=1, choices=[(b'K', 'Kaltura account'), (b'C', 'Brightcove CMS account'), (b'Y', 'YouTube account'), (b'V', 'Vimeo account')])),
                ('account_id', models.PositiveIntegerField()),
                ('language', models.ForeignKey(to='subtitles.SubtitleLanguage')),
                ('version', models.ForeignKey(to='subtitles.SubtitleVersion')),
                ('video_url', models.ForeignKey(to='videos.VideoUrl')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SyncHistory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('account_type', models.CharField(max_length=1, choices=[(b'K', 'Kaltura account'), (b'C', 'Brightcove CMS account'), (b'Y', 'YouTube account'), (b'V', 'Vimeo account')])),
                ('account_id', models.PositiveIntegerField()),
                ('action', models.CharField(max_length=1, choices=[(b'U', b'Update Subtitles'), (b'D', b'Delete Subtitles')])),
                ('datetime', models.DateTimeField()),
                ('result', models.CharField(max_length=1, choices=[(b'S', 'Success'), (b'E', 'Error')])),
                ('details', models.CharField(default=b'', max_length=255, blank=True)),
                ('retry', models.BooleanField(default=False)),
                ('language', models.ForeignKey(to='subtitles.SubtitleLanguage')),
                ('version', models.ForeignKey(blank=True, to='subtitles.SubtitleVersion', null=True)),
                ('video_url', models.ForeignKey(to='videos.VideoUrl')),
            ],
            options={
                'verbose_name': 'Sync history',
                'verbose_name_plural': 'Sync history',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VimeoSyncAccount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=1, choices=[(b'U', 'User'), (b'T', 'Team')])),
                ('owner_id', models.IntegerField()),
                ('username', models.CharField(max_length=255)),
                ('access_token', models.CharField(max_length=255)),
                ('sync_subtitles', models.BooleanField(default=True)),
                ('fetch_initial_subtitles', models.BooleanField(default=True)),
                ('import_team', models.ForeignKey(blank=True, to='teams.Team', null=True)),
                ('sync_teams', models.ManyToManyField(related_name='vimeo_sync_accounts', to='teams.Team')),
            ],
            options={
                'verbose_name': 'Vimeo account',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='YouTubeAccount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=1, choices=[(b'U', 'User'), (b'T', 'Team')])),
                ('owner_id', models.IntegerField()),
                ('channel_id', models.CharField(unique=True, max_length=255)),
                ('username', models.CharField(max_length=255)),
                ('oauth_refresh_token', models.CharField(max_length=255)),
                ('last_import_video_id', models.CharField(default=b'', max_length=100, blank=True)),
                ('enable_language_mapping', models.BooleanField(default=True)),
                ('sync_subtitles', models.BooleanField(default=True)),
                ('fetch_initial_subtitles', models.BooleanField(default=True)),
                ('import_team', models.ForeignKey(blank=True, to='teams.Team', null=True)),
                ('sync_teams', models.ManyToManyField(related_name='youtube_sync_accounts', to='teams.Team')),
            ],
            options={
                'verbose_name': 'YouTube account',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='youtubeaccount',
            unique_together=set([('type', 'owner_id', 'channel_id')]),
        ),
        migrations.AlterUniqueTogether(
            name='vimeosyncaccount',
            unique_together=set([('type', 'owner_id', 'username')]),
        ),
        migrations.AlterUniqueTogether(
            name='syncedsubtitleversion',
            unique_together=set([('account_type', 'account_id', 'video_url', 'language')]),
        ),
        migrations.AlterUniqueTogether(
            name='kalturaaccount',
            unique_together=set([('type', 'owner_id')]),
        ),
        migrations.AlterUniqueTogether(
            name='brightcovecmsaccount',
            unique_together=set([('type', 'owner_id')]),
        ),
        migrations.AlterUniqueTogether(
            name='brightcoveaccount',
            unique_together=set([('type', 'owner_id')]),
        ),
    ]
