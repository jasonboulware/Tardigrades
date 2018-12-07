# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import videos.metadata
import utils.amazon.fields


class Migration(migrations.Migration):

    dependencies = [
        ('amara_auth', '0001_initial'),
        ('comments', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Action',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('action_type', models.IntegerField(choices=[(1, 'add video'), (2, 'change title'), (3, 'comment'), (4, 'add version'), (6, 'add translation'), (5, 'add video url'), (7, 'request subtitles'), (8, 'approve version'), (9, 'add contributor'), (11, 'remove contributor'), (10, 'reject version'), (12, 'review version'), (13, 'accept version'), (14, 'decline version'), (15, 'delete video'), (16, 'edit url'), (17, 'delete url')])),
                ('new_video_title', models.CharField(max_length=2048, blank=True)),
                ('created', models.DateTimeField(db_index=True)),
                ('comment', models.ForeignKey(blank=True, to='comments.Comment', null=True)),
            ],
            options={
                'ordering': ['-created'],
                'get_latest_by': 'created',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ImportedVideo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
                'ordering': ('-id',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Subtitle',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('subtitle_id', models.CharField(max_length=32, blank=True)),
                ('subtitle_order', models.FloatField(null=True)),
                ('subtitle_text', models.CharField(max_length=1024, blank=True)),
                ('start_time_seconds', models.FloatField(null=True, db_column=b'start_time')),
                ('start_time', models.IntegerField(default=None, null=True, db_column=b'start_time_ms')),
                ('end_time_seconds', models.FloatField(null=True, db_column=b'end_time')),
                ('end_time', models.IntegerField(default=None, null=True, db_column=b'end_time_ms')),
                ('start_of_paragraph', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['subtitle_order'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SubtitleLanguage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_original', models.BooleanField(default=False)),
                ('language', models.CharField(blank=True, max_length=16, choices=[(b'ar', 'Arabic'), (b'ast', 'Asturian'), (b'az-az', 'Azerbaijani'), (b'be', 'Belarusian'), (b'bg', 'Bulgarian'), (b'bn', 'Bengali'), (b'bs', 'Bosnian'), (b'ca', 'Catalan'), (b'cs', 'Czech'), (b'cy', 'Welsh'), (b'da', 'Danish'), (b'de', 'German'), (b'el', 'Greek'), (b'en', 'English'), (b'en-gb', 'English, British'), (b'eo', 'Esperanto'), (b'es', 'Spanish'), (b'es-ar', 'Spanish, Argentinian'), (b'es-mx', 'Spanish, Mexican'), (b'et', 'Estonian'), (b'eu', 'Basque'), (b'fa', 'Persian'), (b'fi', 'Finnish'), (b'fr', 'French'), (b'fy-nl', 'Frisian'), (b'ga', 'Irish'), (b'gl', 'Galician'), (b'he', 'Hebrew'), (b'hi', 'Hindi'), (b'hr', 'Croatian'), (b'hu', 'Hungarian'), (b'hy', 'Armenian'), (b'ia', 'Interlingua'), (b'id', 'Indonesian'), (b'is', 'Icelandic'), (b'it', 'Italian'), (b'ja', 'Japanese'), (b'ka', 'Georgian'), (b'kk', 'Kazakh'), (b'km', 'Khmer'), (b'kn', 'Kannada'), (b'ko', 'Korean'), (b'ku', 'Kurdish'), (b'ky', 'Kyrgyz'), (b'lt', 'Lithuanian'), (b'lv', 'Latvian'), (b'mk', 'Macedonian'), (b'ml', 'Malayalam'), (b'mn', 'Mongolian'), (b'mr', 'Marathi'), (b'ms', 'Malay'), (b'my', 'Burmese'), (b'nb', 'Norwegian Bokmal'), (b'nl', 'Dutch'), (b'nn', 'Norwegian Nynorsk'), (b'pl', 'Polish'), (b'ps', 'Pashto'), (b'pt', 'Portuguese'), (b'pt-br', 'Portuguese, Brazilian'), (b'ro', 'Romanian'), (b'ru', 'Russian'), (b'sco', 'Scots'), (b'sk', 'Slovak'), (b'sl', 'Slovenian'), (b'sq', 'Albanian'), (b'sr', 'Serbian'), (b'sr-latn', 'Serbian, Latin'), (b'sv', 'Swedish'), (b'ta', 'Tamil'), (b'te', 'Telugu'), (b'th', 'Thai'), (b'tr', 'Turkish'), (b'ug', 'Uyghur'), (b'uk', 'Ukrainian'), (b'ur', 'Urdu'), (b'uz', 'Uzbek'), (b'vi', 'Vietnamese'), (b'zh', 'Chinese, Yue'), (b'zh-cn', 'Chinese, Simplified'), (b'zh-tw', 'Chinese, Traditional')])),
                ('writelock_time', models.DateTimeField(null=True, editable=False)),
                ('writelock_session_key', models.CharField(max_length=255, editable=False, blank=True)),
                ('is_complete', models.BooleanField(default=False)),
                ('subtitle_count', models.IntegerField(default=0, editable=False)),
                ('has_version', models.BooleanField(default=False, db_index=True, editable=False)),
                ('had_version', models.BooleanField(default=False, editable=False)),
                ('is_forked', models.BooleanField(default=False, editable=False)),
                ('created', models.DateTimeField()),
                ('percent_done', models.IntegerField(default=0, editable=False)),
                ('needs_sync', models.BooleanField(default=True, editable=False)),
                ('followers', models.ManyToManyField(related_name='followed_languages', editable=False, to='amara_auth.CustomUser', blank=True)),
                ('standard_language', models.ForeignKey(blank=True, editable=False, to='videos.SubtitleLanguage', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SubtitleMetadata',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.PositiveIntegerField(choices=[(1, b'Start of pargraph')])),
                ('data', models.CharField(max_length=255)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('subtitle', models.ForeignKey(to='videos.Subtitle')),
            ],
            options={
                'ordering': ('created',),
                'verbose_name_plural': 'subtitles metadata',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SubtitleVersion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('version_no', models.PositiveIntegerField(default=0)),
                ('datetime_started', models.DateTimeField(editable=False)),
                ('note', models.CharField(max_length=512, blank=True)),
                ('time_change', models.FloatField(null=True, editable=False, blank=True)),
                ('text_change', models.FloatField(null=True, editable=False, blank=True)),
                ('notification_sent', models.BooleanField(default=False)),
                ('result_of_rollback', models.BooleanField(default=False)),
                ('is_forked', models.BooleanField(default=False)),
                ('moderation_status', models.CharField(default=b'not__under_moderation', max_length=32, db_index=True, choices=[(b'not__under_moderation', b'not__under_moderation'), (b'waiting_moderation', b'waiting_moderation'), (b'approved', b'approved'), (b'rejected', b'rejected')])),
                ('title', models.CharField(max_length=2048, blank=True)),
                ('description', models.TextField(null=True, blank=True)),
                ('needs_sync', models.BooleanField(default=True, editable=False)),
                ('forked_from', models.ForeignKey(blank=True, to='videos.SubtitleVersion', null=True)),
                ('language', models.ForeignKey(to='videos.SubtitleLanguage')),
                ('user', models.ForeignKey(default=None, to='amara_auth.CustomUser')),
            ],
            options={
                'ordering': ['-version_no'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SubtitleVersionMetadata',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.PositiveIntegerField(choices=[(100, b'reviewed_by'), (101, b'approved_by'), (200, b'workflow_origin')])),
                ('data', models.TextField(blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('subtitle_version', models.ForeignKey(related_name='metadata', to='videos.SubtitleVersion')),
            ],
            options={
                'verbose_name_plural': 'subtitle version metadata',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Video',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('video_id', models.CharField(unique=True, max_length=255)),
                ('title', models.CharField(max_length=2048, blank=True)),
                ('description', models.TextField(blank=True)),
                ('duration', models.PositiveIntegerField(help_text='in seconds', null=True, blank=True)),
                ('allow_community_edits', models.BooleanField(default=False)),
                ('allow_video_urls_edit', models.BooleanField(default=True)),
                ('writelock_time', models.DateTimeField(null=True, editable=False)),
                ('writelock_session_key', models.CharField(max_length=255, editable=False)),
                ('is_subtitled', models.BooleanField(default=False)),
                ('was_subtitled', models.BooleanField(default=False, db_index=True)),
                ('thumbnail', models.CharField(max_length=500, blank=True)),
                ('small_thumbnail', models.CharField(max_length=500, blank=True)),
                ('s3_thumbnail', utils.amazon.fields.S3EnabledImageField(upload_to=b'video/thumbnail/', blank=True)),
                ('edited', models.DateTimeField(null=True, editable=False)),
                ('created', models.DateTimeField()),
                ('complete_date', models.DateTimeField(null=True, editable=False, blank=True)),
                ('featured', models.DateTimeField(null=True, blank=True)),
                ('meta_1_type', videos.metadata.MetadataTypeField(blank=True, null=True, choices=[(0, b'Speaker'), (1, b'Location')])),
                ('meta_1_content', videos.metadata.MetadataContentField(default=b'', max_length=255, blank=True)),
                ('meta_2_type', videos.metadata.MetadataTypeField(blank=True, null=True, choices=[(0, b'Speaker'), (1, b'Location')])),
                ('meta_2_content', videos.metadata.MetadataContentField(default=b'', max_length=255, blank=True)),
                ('meta_3_type', videos.metadata.MetadataTypeField(blank=True, null=True, choices=[(0, b'Speaker'), (1, b'Location')])),
                ('meta_3_content', videos.metadata.MetadataContentField(default=b'', max_length=255, blank=True)),
                ('view_count', models.PositiveIntegerField(default=0, verbose_name='Views', editable=False, db_index=True)),
                ('languages_count', models.PositiveIntegerField(default=0, editable=False, db_index=True)),
                ('is_public', models.BooleanField(default=True)),
                ('primary_audio_language_code', models.CharField(default=b'', max_length=16, blank=True, choices=[(b'ab', 'Abkhazian'), (b'ace', 'Acehnese'), (b'aa', 'Afar'), (b'af', 'Afrikaans'), (b'aka', 'Akan'), (b'sq', 'Albanian'), (b'arq', 'Algerian Arabic'), (b'ase', 'American Sign Language'), (b'amh', 'Amharic'), (b'am', 'Amharic'), (b'ami', 'Amis'), (b'ar', 'Arabic'), (b'an', 'Aragonese'), (b'arc', 'Aramaic'), (b'hy', 'Armenian'), (b'as', 'Assamese'), (b'ast', 'Asturian'), (b'av', 'Avaric'), (b'ae', 'Avestan'), (b'ay', 'Aymara'), (b'az', 'Azerbaijani'), (b'bam', 'Bambara'), (b'ba', 'Bashkir'), (b'eu', 'Basque'), (b'be', 'Belarusian'), (b'bem', 'Bemba (Zambia)'), (b'bn', 'Bengali'), (b'ber', 'Berber'), (b'bh', 'Bihari'), (b'bi', 'Bislama'), (b'bs', 'Bosnian'), (b'br', 'Breton'), (b'bug', 'Buginese'), (b'bg', 'Bulgarian'), (b'my', 'Burmese'), (b'cak', 'Cakchiquel, Central'), (b'ca', 'Catalan'), (b'ceb', 'Cebuano'), (b'ch', 'Chamorro'), (b'ce', 'Chechen'), (b'chr', 'Cherokee'), (b'nya', 'Chewa'), (b'ctd', 'Chin, Tedim'), (b'zh-hans', b'Chinese (Simplified Han)'), (b'zh-hant', b'Chinese (Traditional Han)'), (b'zh-cn', 'Chinese, Simplified'), (b'zh-sg', 'Chinese, Simplified (Singaporean)'), (b'zh-tw', 'Chinese, Traditional'), (b'zh-hk', 'Chinese, Traditional (Hong Kong)'), (b'zh', 'Chinese, Yue'), (b'cho', 'Choctaw'), (b'ctu', 'Chol, Tumbal\xe1'), (b'cu', 'Church Slavic'), (b'cv', 'Chuvash'), (b'ksh', 'Colognian'), (b'rar', 'Cook Islands M\u0101ori'), (b'kw', 'Cornish'), (b'co', 'Corsican'), (b'cr', 'Cree'), (b'ht', 'Creole, Haitian'), (b'hr', 'Croatian'), (b'cs', 'Czech'), (b'da', 'Danish'), (b'prs', 'Dari'), (b'din', 'Dinka'), (b'dv', 'Divehi'), (b'nl', 'Dutch'), (b'nl-be', 'Dutch (Belgium)'), (b'dz', 'Dzongkha'), (b'cly', 'Eastern Chatino'), (b'efi', 'Efik'), (b'arz', 'Egyptian Arabic'), (b'en', 'English'), (b'en-au', 'English (Australia)'), (b'en-ca', 'English (Canada)'), (b'en-in', 'English (India)'), (b'en-ie', 'English (Ireland)'), (b'en-us', 'English (United States)'), (b'en-gb', 'English, British'), (b'eo', 'Esperanto'), (b'et', 'Estonian'), (b'ee', 'Ewe'), (b'fo', 'Faroese'), (b'fj', 'Fijian'), (b'fil', 'Filipino'), (b'fi', 'Finnish'), (b'vls', 'Flemish'), (b'fr', 'French'), (b'fr-be', 'French (Belgium)'), (b'fr-ca', 'French (Canada)'), (b'fr-ch', 'French (Switzerland)'), (b'fy-nl', 'Frisian'), (b'ful', 'Fula'), (b'ff', 'Fulah'), (b'gl', 'Galician'), (b'lg', 'Ganda'), (b'ka', 'Georgian'), (b'de', 'German'), (b'de-at', 'German (Austria)'), (b'de-ch', 'German (Switzerland)'), (b'kik', 'Gikuyu'), (b'got', 'Gothic'), (b'el', 'Greek'), (b'kl', 'Greenlandic'), (b'gn', 'Guaran'), (b'gu', 'Gujarati'), (b'hai', 'Haida'), (b'cnh', 'Hakha Chin'), (b'hb', 'HamariBoli (Roman Hindi-Urdu)'), (b'hau', 'Hausa'), (b'ha', b'Hausa'), (b'hwc', "Hawai'i Creole English"), (b'haw', 'Hawaiian'), (b'haz', 'Hazaragi'), (b'iw', b'Hebrew'), (b'he', 'Hebrew'), (b'hz', 'Herero'), (b'hi', 'Hindi'), (b'ho', 'Hiri Motu'), (b'hmn', 'Hmong'), (b'nan', 'Hokkien'), (b'hus', 'Huastec, Veracruz'), (b'hch', 'Huichol'), (b'hu', 'Hungarian'), (b'hup', 'Hupa'), (b'bnt', 'Ibibio'), (b'is', 'Icelandic'), (b'io', 'Ido'), (b'ibo', 'Igbo'), (b'ilo', 'Ilocano'), (b'id', 'Indonesian'), (b'inh', 'Ingush'), (b'ia', 'Interlingua'), (b'ie', 'Interlingue'), (b'iu', 'Inuktitut'), (b'ik', 'Inupia'), (b'ga', 'Irish'), (b'iro', 'Iroquoian languages'), (b'it', 'Italian'), (b'ja', 'Japanese'), (b'jv', 'Javanese'), (b'kn', 'Kannada'), (b'kau', 'Kanuri'), (b'pam', 'Kapampangan'), (b'kaa', 'Karakalpak'), (b'kar', 'Karen'), (b'ks', 'Kashmiri'), (b'kk', 'Kazakh'), (b'km', 'Khmer'), (b'rw', b'Kinyarwanda'), (b'tlh', 'Klingon'), (b'cku', 'Koasati'), (b'kv', 'Komi'), (b'kon', 'Kongo'), (b'ko', 'Korean'), (b'kj', 'Kuanyama, Kwanyama'), (b'ku', 'Kurdish'), (b'ckb', 'Kurdish (Central)'), (b'ky', 'Kyrgyz'), (b'lld', 'Ladin'), (b'lkt', 'Lakota'), (b'lo', 'Lao'), (b'ltg', 'Latgalian'), (b'la', 'Latin'), (b'lv', 'Latvian'), (b'li', 'Limburgish'), (b'ln', b'Lingala'), (b'lin', 'Lingala'), (b'lt', 'Lithuanian'), (b'dsb', b'Lower Sorbian'), (b'loz', 'Lozi'), (b'lua', 'Luba-Kasai'), (b'lu', 'Luba-Katagana'), (b'luy', 'Luhya'), (b'luo', 'Luo'), (b'lut', 'Lushootseed'), (b'lb', 'Luxembourgish'), (b'rup', 'Macedo'), (b'mk', 'Macedonian'), (b'mad', 'Madurese'), (b'mg', b'Malagasy'), (b'mlg', 'Malagasy'), (b'ms', 'Malay'), (b'ml', 'Malayalam'), (b'mt', 'Maltese'), (b'mnk', 'Mandinka'), (b'mni', 'Manipuri'), (b'gv', 'Manx'), (b'mi', 'Maori'), (b'mr', 'Marathi'), (b'mh', 'Marshallese'), (b'mfe', b'Mauritian Creole'), (b'yua', 'Maya, Yucat\xe1n'), (b'meta-audio', 'Metadata: Audio Description'), (b'meta-geo', 'Metadata: Geo'), (b'meta-tw', 'Metadata: Twitter'), (b'meta-video', 'Metadata: Video Description'), (b'meta-wiki', 'Metadata: Wikipedia'), (b'lus', 'Mizo'), (b'moh', 'Mohawk'), (b'mo', 'Moldavian, Moldovan'), (b'mn', 'Mongolian'), (b'srp', 'Montenegrin'), (b'mos', 'Mossi'), (b'mus', 'Muscogee'), (b'nci', 'Nahuatl, Classical'), (b'ncj', 'Nahuatl, Northern Puebla'), (b'na', 'Naurunan'), (b'nv', 'Navajo'), (b'ng', 'Ndonga'), (b'ne', 'Nepali'), (b'pcm', 'Nigerian Pidgin'), (b'nd', 'North Ndebele'), (b'se', 'Northern Sami'), (b'nso', 'Northern Sotho'), (b'no', 'Norwegian'), (b'nb', 'Norwegian Bokmal'), (b'nn', 'Norwegian Nynorsk'), (b'oc', 'Occitan'), (b'oji', 'Ojibwe'), (b'or', 'Oriya'), (b'orm', 'Oromo'), (b'om', b'Oromo'), (b'os', 'Ossetian, Ossetic'), (b'x-other', 'Other'), (b'pi', 'Pali'), (b'pap', 'Papiamento'), (b'ps', 'Pashto'), (b'fa', 'Persian'), (b'fa-af', 'Persian (Afghanistan)'), (b'pcd', 'Picard'), (b'pl', 'Polish'), (b'pt', 'Portuguese'), (b'pt-pt', b'Portuguese (Portugal)'), (b'pt-br', 'Portuguese, Brazilian'), (b'pa', b'Punjabi'), (b'pan', 'Punjabi'), (b'tsz', 'Purepecha'), (b'tob', b'Qom (Toba)'), (b'que', 'Quechua'), (b'qu', b'Quechua'), (b'qvi', 'Quichua, Imbabura Highland'), (b'raj', 'Rajasthani'), (b'ro', 'Romanian'), (b'rm', 'Romansh'), (b'rn', b'Rundi'), (b'run', 'Rundi'), (b'ru', 'Russian'), (b'ry', 'Rusyn'), (b'kin', 'Rwandi'), (b'sm', 'Samoan'), (b'sg', 'Sango'), (b'sa', 'Sanskrit'), (b'sc', 'Sardinian'), (b'sco', 'Scots'), (b'gd', 'Scottish Gaelic'), (b'trv', 'Seediq'), (b'skx', 'Seko Padang'), (b'sr', 'Serbian'), (b'sr-latn', 'Serbian, Latin'), (b'sh', 'Serbo-Croatian'), (b'crs', 'Seselwa Creole French'), (b'shp', 'Shipibo-Conibo'), (b'sna', 'Shona'), (b'sn', b'Shona'), (b'ii', 'Sichuan Yi'), (b'scn', 'Sicilian'), (b'sgn', 'Sign Languages'), (b'szl', 'Silesian'), (b'sd', 'Sindhi'), (b'si', 'Sinhala'), (b'sk', 'Slovak'), (b'sl', 'Slovenian'), (b'sby', 'Soli'), (b'so', b'Somali'), (b'som', 'Somali'), (b'sot', 'Sotho'), (b'nr', 'Southern Ndebele'), (b'st', 'Southern Sotho'), (b'es', 'Spanish'), (b'es-ec', 'Spanish (Ecuador)'), (b'es-419', 'Spanish (Latin America)'), (b'es-es', b'Spanish (Spain)'), (b'es-ar', 'Spanish, Argentinian'), (b'es-mx', 'Spanish, Mexican'), (b'es-ni', 'Spanish, Nicaraguan'), (b'su', 'Sundanese'), (b'sw', b'Swahili'), (b'swa', 'Swahili'), (b'ss', 'Swati'), (b'sv', 'Swedish'), (b'gsw', 'Swiss German'), (b'tl', 'Tagalog'), (b'ty', 'Tahitian'), (b'tg', 'Tajik'), (b'ta', 'Tamil'), (b'tar', 'Tarahumara, Central'), (b'cta', 'Tataltepec Chatino'), (b'tt', 'Tatar'), (b'te', 'Telugu'), (b'tet', 'Tetum'), (b'th', 'Thai'), (b'bo', 'Tibetan'), (b'ti', b'Tigrinya'), (b'tir', 'Tigrinya'), (b'toj', 'Tojolabal'), (b'to', 'Tonga'), (b'ts', 'Tsonga'), (b'tn', b'Tswana'), (b'tsn', 'Tswana'), (b'aeb', 'Tunisian Arabic'), (b'tr', 'Turkish'), (b'tk', 'Turkmen'), (b'tw', 'Twi'), (b'tzh', 'Tzeltal, Oxchuc'), (b'tzo', 'Tzotzil, Venustiano Carranza'), (b'uk', 'Ukrainian'), (b'umb', 'Umbundu'), (b'hsb', b'Upper Sorbian'), (b'ur', 'Urdu'), (b'ug', 'Uyghur'), (b'uz', 'Uzbek'), (b've', 'Venda'), (b'vi', 'Vietnamese'), (b'vo', 'Volapuk'), (b'wbl', 'Wakhi'), (b'wa', 'Walloon'), (b'wau', 'Wauja'), (b'cy', 'Welsh'), (b'fy', b'Western Frisian'), (b'pnb', 'Western Punjabi'), (b'wol', 'Wolof'), (b'wo', b'Wolof'), (b'xho', 'Xhosa'), (b'xh', b'Xhosa'), (b'tao', 'Yami (Tao)'), (b'yaq', 'Yaqui'), (b'yi', 'Yiddish'), (b'yo', b'Yoruba'), (b'yor', 'Yoruba'), (b'zam', 'Zapotec, Miahuatl\xe1n'), (b'zza', 'Zazaki'), (b'czn', 'Zenzontepec Chatino'), (b'za', 'Zhuang, Chuang'), (b'zu', b'Zulu'), (b'zul', 'Zulu')])),
            ],
            options={
                'permissions': (('can_moderate_version', 'Can moderate version'),),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VideoFeed',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.URLField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('last_update', models.DateTimeField(null=True)),
                ('user', models.ForeignKey(blank=True, to='amara_auth.CustomUser', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VideoIndex',
            fields=[
                ('video', models.OneToOneField(related_name='index', primary_key=True, serialize=False, to='videos.Video')),
                ('text', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VideoMetadata',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.PositiveIntegerField(choices=[(1, b'Author'), (2, b'Creation Date'), (100, b'ted_id')])),
                ('data', models.CharField(max_length=255)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('video', models.ForeignKey(to='videos.Video')),
            ],
            options={
                'ordering': ('created',),
                'verbose_name_plural': 'video metadata',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VideoTypeUrlPattern',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=2)),
                ('url_pattern', models.URLField(unique=True, max_length=255)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VideoUrl',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=2)),
                ('url', models.URLField(max_length=2048)),
                ('url_hash', models.CharField(max_length=32)),
                ('videoid', models.CharField(max_length=50, blank=True)),
                ('primary', models.BooleanField(default=False)),
                ('original', models.BooleanField(default=False)),
                ('created', models.DateTimeField()),
                ('owner_username', models.CharField(max_length=255, null=True, blank=True)),
                ('team_id', models.IntegerField(default=0, blank=True)),
                ('added_by', models.ForeignKey(blank=True, to='amara_auth.CustomUser', null=True)),
                ('video', models.ForeignKey(to='videos.Video')),
            ],
            options={
                'ordering': ('video', '-primary'),
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='videourl',
            unique_together=set([('url_hash', 'team_id', 'type')]),
        ),
        migrations.AddField(
            model_name='video',
            name='followers',
            field=models.ManyToManyField(related_name='followed_videos', editable=False, to='amara_auth.CustomUser', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='video',
            name='user',
            field=models.ForeignKey(blank=True, to='amara_auth.CustomUser', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='video',
            name='writelock_owner',
            field=models.ForeignKey(related_name='writelock_owners', editable=False, to='amara_auth.CustomUser', null=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='subtitleversionmetadata',
            unique_together=set([('key', 'subtitle_version')]),
        ),
        migrations.AlterUniqueTogether(
            name='subtitleversion',
            unique_together=set([('language', 'version_no')]),
        ),
        migrations.AddField(
            model_name='subtitlelanguage',
            name='video',
            field=models.ForeignKey(to='videos.Video'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='subtitlelanguage',
            name='writelock_owner',
            field=models.ForeignKey(blank=True, editable=False, to='amara_auth.CustomUser', null=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='subtitlelanguage',
            unique_together=set([('video', 'language', 'standard_language')]),
        ),
        migrations.AddField(
            model_name='subtitle',
            name='version',
            field=models.ForeignKey(to='videos.SubtitleVersion', null=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='subtitle',
            unique_together=set([('version', 'subtitle_id')]),
        ),
        migrations.AddField(
            model_name='importedvideo',
            name='feed',
            field=models.ForeignKey(to='videos.VideoFeed'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='importedvideo',
            name='video',
            field=models.OneToOneField(to='videos.Video'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='action',
            name='language',
            field=models.ForeignKey(blank=True, to='videos.SubtitleLanguage', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='action',
            name='user',
            field=models.ForeignKey(blank=True, to='amara_auth.CustomUser', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='action',
            name='video',
            field=models.ForeignKey(blank=True, to='videos.Video', null=True),
            preserve_default=True,
        ),
    ]
