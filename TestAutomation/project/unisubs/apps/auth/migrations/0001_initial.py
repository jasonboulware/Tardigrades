# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import auth.models
import utils.amazon.fields
from django.conf import settings
import utils.secureid


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AmaraApiKey',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('key', models.CharField(default=auth.models.generate_api_key, max_length=256, blank=True)),
            ],
            options={
                'db_table': 'auth_amaraapikey',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('content', models.CharField(max_length=500)),
                ('created', models.DateTimeField(help_text='This is date when start to display announcement. And only the last will be displayed.')),
                ('hidden', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['-created'],
                'db_table': 'auth_announcement',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Awards',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('points', models.IntegerField()),
                ('type', models.IntegerField(choices=[(1, 'Add comment'), (2, 'Start subtitles'), (3, 'Start translation'), (4, 'Edit subtitles'), (5, 'Edit translation')])),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'auth_awards',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CustomUser',
            fields=[
                ('user_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('homepage', models.URLField(blank=True)),
                ('preferred_language', models.CharField(blank=True, max_length=16, choices=[(b'ar', 'Arabic'), (b'ast', 'Asturian'), (b'az-az', 'Azerbaijani'), (b'be', 'Belarusian'), (b'bg', 'Bulgarian'), (b'bn', 'Bengali'), (b'bs', 'Bosnian'), (b'ca', 'Catalan'), (b'cs', 'Czech'), (b'cy', 'Welsh'), (b'da', 'Danish'), (b'de', 'German'), (b'el', 'Greek'), (b'en', 'English'), (b'en-gb', 'English, British'), (b'eo', 'Esperanto'), (b'es', 'Spanish'), (b'es-ar', 'Spanish, Argentinian'), (b'es-mx', 'Spanish, Mexican'), (b'et', 'Estonian'), (b'eu', 'Basque'), (b'fa', 'Persian'), (b'fi', 'Finnish'), (b'fr', 'French'), (b'fy-nl', 'Frisian'), (b'ga', 'Irish'), (b'gl', 'Galician'), (b'he', 'Hebrew'), (b'hi', 'Hindi'), (b'hr', 'Croatian'), (b'hu', 'Hungarian'), (b'hy', 'Armenian'), (b'ia', 'Interlingua'), (b'id', 'Indonesian'), (b'is', 'Icelandic'), (b'it', 'Italian'), (b'ja', 'Japanese'), (b'ka', 'Georgian'), (b'kk', 'Kazakh'), (b'km', 'Khmer'), (b'kn', 'Kannada'), (b'ko', 'Korean'), (b'ku', 'Kurdish'), (b'ky', 'Kyrgyz'), (b'lt', 'Lithuanian'), (b'lv', 'Latvian'), (b'mk', 'Macedonian'), (b'ml', 'Malayalam'), (b'mn', 'Mongolian'), (b'mr', 'Marathi'), (b'ms', 'Malay'), (b'my', 'Burmese'), (b'nb', 'Norwegian Bokmal'), (b'nl', 'Dutch'), (b'nn', 'Norwegian Nynorsk'), (b'pl', 'Polish'), (b'ps', 'Pashto'), (b'pt', 'Portuguese'), (b'pt-br', 'Portuguese, Brazilian'), (b'ro', 'Romanian'), (b'ru', 'Russian'), (b'sco', 'Scots'), (b'sk', 'Slovak'), (b'sl', 'Slovenian'), (b'sq', 'Albanian'), (b'sr', 'Serbian'), (b'sr-latn', 'Serbian, Latin'), (b'sv', 'Swedish'), (b'ta', 'Tamil'), (b'te', 'Telugu'), (b'th', 'Thai'), (b'tr', 'Turkish'), (b'ug', 'Uyghur'), (b'uk', 'Ukrainian'), (b'ur', 'Urdu'), (b'uz', 'Uzbek'), (b'vi', 'Vietnamese'), (b'zh', 'Chinese, Yue'), (b'zh-cn', 'Chinese, Simplified'), (b'zh-tw', 'Chinese, Traditional')])),
                ('picture', utils.amazon.fields.S3EnabledImageField(upload_to=b'pictures/', blank=True)),
                ('valid_email', models.BooleanField(default=False)),
                ('notify_by_email', models.BooleanField(default=True)),
                ('notify_by_message', models.BooleanField(default=True)),
                ('allow_3rd_party_login', models.BooleanField(default=False)),
                ('biography', models.TextField(verbose_name=b'Bio', blank=True)),
                ('autoplay_preferences', models.IntegerField(default=1, choices=[(1, b'Autoplay subtitles based on browser preferred languages'), (2, b'Autoplay subtitles in languages I know'), (3, b"Don't autoplay subtitles")])),
                ('award_points', models.IntegerField(default=0)),
                ('last_ip', models.IPAddressField(null=True, blank=True)),
                ('full_name', models.CharField(default=b'', max_length=63, blank=True)),
                ('is_partner', models.BooleanField(default=False)),
                ('pay_rate_code', models.CharField(default=b'', max_length=3, blank=True)),
                ('can_send_messages', models.BooleanField(default=True)),
                ('show_tutorial', models.BooleanField(default=True)),
                ('playback_mode', models.IntegerField(default=2, choices=[(1, b'Magical auto-pause'), (2, b'No automatic pausing'), (3, b'Play for 4 seconds, then pause')])),
                ('created_by', models.ForeignKey(related_name='created_users', blank=True, to='amara_auth.CustomUser', null=True)),
            ],
            options={
                'db_table': 'auth_customuser',
                'verbose_name': 'User',
            },
            bases=('auth.user', utils.secureid.SecureIDMixin),
        ),
        migrations.CreateModel(
            name='EmailConfirmation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sent', models.DateTimeField()),
                ('confirmation_key', models.CharField(max_length=40)),
                ('user', models.ForeignKey(to='amara_auth.CustomUser')),
            ],
            options={
                'db_table': 'auth_emailconfirmation',
                'verbose_name': 'e-mail confirmation',
                'verbose_name_plural': 'e-mail confirmations',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LoginToken',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('token', models.CharField(unique=True, max_length=40)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(related_name='login_token', to='amara_auth.CustomUser')),
            ],
            options={
                'db_table': 'auth_logintoken',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SentMessageDate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField()),
                ('user', models.ForeignKey(to='amara_auth.CustomUser')),
            ],
            options={
                'db_table': 'auth_sentmessagedate',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserLanguage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('language', models.CharField(max_length=16, verbose_name=b'languages', choices=[(b'ar', 'Arabic'), (b'ast', 'Asturian'), (b'az-az', 'Azerbaijani'), (b'be', 'Belarusian'), (b'bg', 'Bulgarian'), (b'bn', 'Bengali'), (b'bs', 'Bosnian'), (b'ca', 'Catalan'), (b'cs', 'Czech'), (b'cy', 'Welsh'), (b'da', 'Danish'), (b'de', 'German'), (b'el', 'Greek'), (b'en', 'English'), (b'en-gb', 'English, British'), (b'eo', 'Esperanto'), (b'es', 'Spanish'), (b'es-ar', 'Spanish, Argentinian'), (b'es-mx', 'Spanish, Mexican'), (b'et', 'Estonian'), (b'eu', 'Basque'), (b'fa', 'Persian'), (b'fi', 'Finnish'), (b'fr', 'French'), (b'fy-nl', 'Frisian'), (b'ga', 'Irish'), (b'gl', 'Galician'), (b'he', 'Hebrew'), (b'hi', 'Hindi'), (b'hr', 'Croatian'), (b'hu', 'Hungarian'), (b'hy', 'Armenian'), (b'ia', 'Interlingua'), (b'id', 'Indonesian'), (b'is', 'Icelandic'), (b'it', 'Italian'), (b'ja', 'Japanese'), (b'ka', 'Georgian'), (b'kk', 'Kazakh'), (b'km', 'Khmer'), (b'kn', 'Kannada'), (b'ko', 'Korean'), (b'ku', 'Kurdish'), (b'ky', 'Kyrgyz'), (b'lt', 'Lithuanian'), (b'lv', 'Latvian'), (b'mk', 'Macedonian'), (b'ml', 'Malayalam'), (b'mn', 'Mongolian'), (b'mr', 'Marathi'), (b'ms', 'Malay'), (b'my', 'Burmese'), (b'nb', 'Norwegian Bokmal'), (b'nl', 'Dutch'), (b'nn', 'Norwegian Nynorsk'), (b'pl', 'Polish'), (b'ps', 'Pashto'), (b'pt', 'Portuguese'), (b'pt-br', 'Portuguese, Brazilian'), (b'ro', 'Romanian'), (b'ru', 'Russian'), (b'sco', 'Scots'), (b'sk', 'Slovak'), (b'sl', 'Slovenian'), (b'sq', 'Albanian'), (b'sr', 'Serbian'), (b'sr-latn', 'Serbian, Latin'), (b'sv', 'Swedish'), (b'ta', 'Tamil'), (b'te', 'Telugu'), (b'th', 'Thai'), (b'tr', 'Turkish'), (b'ug', 'Uyghur'), (b'uk', 'Ukrainian'), (b'ur', 'Urdu'), (b'uz', 'Uzbek'), (b'vi', 'Vietnamese'), (b'zh', 'Chinese, Yue'), (b'zh-cn', 'Chinese, Simplified'), (b'zh-tw', 'Chinese, Traditional')])),
                ('proficiency', models.IntegerField(default=1, choices=[(1, 'understand enough'), (2, 'understand 99%'), (3, 'write like a native')])),
                ('priority', models.IntegerField(null=True)),
                ('follow_requests', models.BooleanField(default=False, verbose_name='follow requests in language')),
                ('user', models.ForeignKey(to='amara_auth.CustomUser')),
            ],
            options={
                'db_table': 'auth_userlanguage',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='userlanguage',
            unique_together=set([('user', 'language')]),
        ),
        migrations.AddField(
            model_name='awards',
            name='user',
            field=models.ForeignKey(to='amara_auth.CustomUser', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='amaraapikey',
            name='user',
            field=models.OneToOneField(related_name='api_key', to='amara_auth.CustomUser'),
            preserve_default=True,
        ),
    ]
