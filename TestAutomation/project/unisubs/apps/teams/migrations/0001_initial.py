# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import utils.enum
import datetime
import django.db.models.deletion
import utils.amazon.fields


class Migration(migrations.Migration):

    dependencies = [
        ('amara_auth', '0001_initial'),
        ('videos', '0001_initial'),
        ('subtitles', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Application',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('note', models.TextField(blank=True)),
                ('status', models.PositiveIntegerField(default=0, choices=[(0, 'Pending'), (1, 'Approved'), (2, 'Denied'), (3, 'Member Removed'), (4, 'Member Left')])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(null=True, blank=True)),
                ('history', models.TextField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BillingRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('minutes', models.FloatField(null=True, blank=True)),
                ('is_original', models.BooleanField(default=False)),
                ('created', models.DateTimeField()),
                ('source', models.CharField(max_length=255)),
                ('new_subtitle_language', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='subtitles.SubtitleLanguage', null=True)),
                ('new_subtitle_version', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='subtitles.SubtitleVersion', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BillingReport',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('csv_file', utils.amazon.fields.S3EnabledFileField(null=True, upload_to=b'teams/billing/', blank=True)),
                ('processed', models.DateTimeField(null=True, blank=True)),
                ('type', models.IntegerField(default=2, choices=[(2, b'Crowd sourced'), (3, b'Professional services'), (4, b'On-demand translators')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BillToClient',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('client', models.CharField(unique=True, max_length=255)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Invite',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('note', models.TextField(max_length=200, blank=True)),
                ('role', models.CharField(default=b'contributor', max_length=16, choices=[(b'owner', 'Owner'), (b'manager', 'Manager'), (b'admin', 'Admin'), (b'contributor', 'Contributor')])),
                ('approved', models.NullBooleanField(default=None)),
                ('author', models.ForeignKey(to='amara_auth.CustomUser')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LanguageManager',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(max_length=16, choices=[(b'ab', 'Abkhazian'), (b'ace', 'Acehnese'), (b'aa', 'Afar'), (b'af', 'Afrikaans'), (b'aka', 'Akan'), (b'sq', 'Albanian'), (b'arq', 'Algerian Arabic'), (b'ase', 'American Sign Language'), (b'amh', 'Amharic'), (b'am', 'Amharic'), (b'ami', 'Amis'), (b'ar', 'Arabic'), (b'an', 'Aragonese'), (b'arc', 'Aramaic'), (b'hy', 'Armenian'), (b'as', 'Assamese'), (b'ast', 'Asturian'), (b'av', 'Avaric'), (b'ae', 'Avestan'), (b'ay', 'Aymara'), (b'az', 'Azerbaijani'), (b'bam', 'Bambara'), (b'ba', 'Bashkir'), (b'eu', 'Basque'), (b'be', 'Belarusian'), (b'bem', 'Bemba (Zambia)'), (b'bn', 'Bengali'), (b'ber', 'Berber'), (b'bh', 'Bihari'), (b'bi', 'Bislama'), (b'bs', 'Bosnian'), (b'br', 'Breton'), (b'bug', 'Buginese'), (b'bg', 'Bulgarian'), (b'my', 'Burmese'), (b'cak', 'Cakchiquel, Central'), (b'ca', 'Catalan'), (b'ceb', 'Cebuano'), (b'ch', 'Chamorro'), (b'ce', 'Chechen'), (b'chr', 'Cherokee'), (b'nya', 'Chewa'), (b'ctd', 'Chin, Tedim'), (b'zh-hans', b'Chinese (Simplified Han)'), (b'zh-hant', b'Chinese (Traditional Han)'), (b'zh-cn', 'Chinese, Simplified'), (b'zh-sg', 'Chinese, Simplified (Singaporean)'), (b'zh-tw', 'Chinese, Traditional'), (b'zh-hk', 'Chinese, Traditional (Hong Kong)'), (b'zh', 'Chinese, Yue'), (b'cho', 'Choctaw'), (b'ctu', 'Chol, Tumbal\xe1'), (b'cu', 'Church Slavic'), (b'cv', 'Chuvash'), (b'ksh', 'Colognian'), (b'rar', 'Cook Islands M\u0101ori'), (b'kw', 'Cornish'), (b'co', 'Corsican'), (b'cr', 'Cree'), (b'ht', 'Creole, Haitian'), (b'hr', 'Croatian'), (b'cs', 'Czech'), (b'da', 'Danish'), (b'prs', 'Dari'), (b'din', 'Dinka'), (b'dv', 'Divehi'), (b'nl', 'Dutch'), (b'nl-be', 'Dutch (Belgium)'), (b'dz', 'Dzongkha'), (b'cly', 'Eastern Chatino'), (b'efi', 'Efik'), (b'arz', 'Egyptian Arabic'), (b'en', 'English'), (b'en-au', 'English (Australia)'), (b'en-ca', 'English (Canada)'), (b'en-in', 'English (India)'), (b'en-ie', 'English (Ireland)'), (b'en-us', 'English (United States)'), (b'en-gb', 'English, British'), (b'eo', 'Esperanto'), (b'et', 'Estonian'), (b'ee', 'Ewe'), (b'fo', 'Faroese'), (b'fj', 'Fijian'), (b'fil', 'Filipino'), (b'fi', 'Finnish'), (b'vls', 'Flemish'), (b'fr', 'French'), (b'fr-be', 'French (Belgium)'), (b'fr-ca', 'French (Canada)'), (b'fr-ch', 'French (Switzerland)'), (b'fy-nl', 'Frisian'), (b'ful', 'Fula'), (b'ff', 'Fulah'), (b'gl', 'Galician'), (b'lg', 'Ganda'), (b'ka', 'Georgian'), (b'de', 'German'), (b'de-at', 'German (Austria)'), (b'de-ch', 'German (Switzerland)'), (b'kik', 'Gikuyu'), (b'got', 'Gothic'), (b'el', 'Greek'), (b'kl', 'Greenlandic'), (b'gn', 'Guaran'), (b'gu', 'Gujarati'), (b'hai', 'Haida'), (b'cnh', 'Hakha Chin'), (b'hb', 'HamariBoli (Roman Hindi-Urdu)'), (b'hau', 'Hausa'), (b'ha', b'Hausa'), (b'hwc', "Hawai'i Creole English"), (b'haw', 'Hawaiian'), (b'haz', 'Hazaragi'), (b'iw', b'Hebrew'), (b'he', 'Hebrew'), (b'hz', 'Herero'), (b'hi', 'Hindi'), (b'ho', 'Hiri Motu'), (b'hmn', 'Hmong'), (b'nan', 'Hokkien'), (b'hus', 'Huastec, Veracruz'), (b'hch', 'Huichol'), (b'hu', 'Hungarian'), (b'hup', 'Hupa'), (b'bnt', 'Ibibio'), (b'is', 'Icelandic'), (b'io', 'Ido'), (b'ibo', 'Igbo'), (b'ilo', 'Ilocano'), (b'id', 'Indonesian'), (b'inh', 'Ingush'), (b'ia', 'Interlingua'), (b'ie', 'Interlingue'), (b'iu', 'Inuktitut'), (b'ik', 'Inupia'), (b'ga', 'Irish'), (b'iro', 'Iroquoian languages'), (b'it', 'Italian'), (b'ja', 'Japanese'), (b'jv', 'Javanese'), (b'kn', 'Kannada'), (b'kau', 'Kanuri'), (b'pam', 'Kapampangan'), (b'kaa', 'Karakalpak'), (b'kar', 'Karen'), (b'ks', 'Kashmiri'), (b'kk', 'Kazakh'), (b'km', 'Khmer'), (b'rw', b'Kinyarwanda'), (b'tlh', 'Klingon'), (b'cku', 'Koasati'), (b'kv', 'Komi'), (b'kon', 'Kongo'), (b'ko', 'Korean'), (b'kj', 'Kuanyama, Kwanyama'), (b'ku', 'Kurdish'), (b'ckb', 'Kurdish (Central)'), (b'ky', 'Kyrgyz'), (b'lld', 'Ladin'), (b'lkt', 'Lakota'), (b'lo', 'Lao'), (b'ltg', 'Latgalian'), (b'la', 'Latin'), (b'lv', 'Latvian'), (b'li', 'Limburgish'), (b'ln', b'Lingala'), (b'lin', 'Lingala'), (b'lt', 'Lithuanian'), (b'dsb', b'Lower Sorbian'), (b'loz', 'Lozi'), (b'lua', 'Luba-Kasai'), (b'lu', 'Luba-Katagana'), (b'luy', 'Luhya'), (b'luo', 'Luo'), (b'lut', 'Lushootseed'), (b'lb', 'Luxembourgish'), (b'rup', 'Macedo'), (b'mk', 'Macedonian'), (b'mad', 'Madurese'), (b'mg', b'Malagasy'), (b'mlg', 'Malagasy'), (b'ms', 'Malay'), (b'ml', 'Malayalam'), (b'mt', 'Maltese'), (b'mnk', 'Mandinka'), (b'mni', 'Manipuri'), (b'gv', 'Manx'), (b'mi', 'Maori'), (b'mr', 'Marathi'), (b'mh', 'Marshallese'), (b'mfe', b'Mauritian Creole'), (b'yua', 'Maya, Yucat\xe1n'), (b'meta-audio', 'Metadata: Audio Description'), (b'meta-geo', 'Metadata: Geo'), (b'meta-tw', 'Metadata: Twitter'), (b'meta-video', 'Metadata: Video Description'), (b'meta-wiki', 'Metadata: Wikipedia'), (b'lus', 'Mizo'), (b'moh', 'Mohawk'), (b'mo', 'Moldavian, Moldovan'), (b'mn', 'Mongolian'), (b'srp', 'Montenegrin'), (b'mos', 'Mossi'), (b'mus', 'Muscogee'), (b'nci', 'Nahuatl, Classical'), (b'ncj', 'Nahuatl, Northern Puebla'), (b'na', 'Naurunan'), (b'nv', 'Navajo'), (b'ng', 'Ndonga'), (b'ne', 'Nepali'), (b'pcm', 'Nigerian Pidgin'), (b'nd', 'North Ndebele'), (b'se', 'Northern Sami'), (b'nso', 'Northern Sotho'), (b'no', 'Norwegian'), (b'nb', 'Norwegian Bokmal'), (b'nn', 'Norwegian Nynorsk'), (b'oc', 'Occitan'), (b'oji', 'Ojibwe'), (b'or', 'Oriya'), (b'orm', 'Oromo'), (b'om', b'Oromo'), (b'os', 'Ossetian, Ossetic'), (b'x-other', 'Other'), (b'pi', 'Pali'), (b'pap', 'Papiamento'), (b'ps', 'Pashto'), (b'fa', 'Persian'), (b'fa-af', 'Persian (Afghanistan)'), (b'pcd', 'Picard'), (b'pl', 'Polish'), (b'pt', 'Portuguese'), (b'pt-pt', b'Portuguese (Portugal)'), (b'pt-br', 'Portuguese, Brazilian'), (b'pa', b'Punjabi'), (b'pan', 'Punjabi'), (b'tsz', 'Purepecha'), (b'tob', b'Qom (Toba)'), (b'que', 'Quechua'), (b'qu', b'Quechua'), (b'qvi', 'Quichua, Imbabura Highland'), (b'raj', 'Rajasthani'), (b'ro', 'Romanian'), (b'rm', 'Romansh'), (b'rn', b'Rundi'), (b'run', 'Rundi'), (b'ru', 'Russian'), (b'ry', 'Rusyn'), (b'kin', 'Rwandi'), (b'sm', 'Samoan'), (b'sg', 'Sango'), (b'sa', 'Sanskrit'), (b'sc', 'Sardinian'), (b'sco', 'Scots'), (b'gd', 'Scottish Gaelic'), (b'trv', 'Seediq'), (b'skx', 'Seko Padang'), (b'sr', 'Serbian'), (b'sr-latn', 'Serbian, Latin'), (b'sh', 'Serbo-Croatian'), (b'crs', 'Seselwa Creole French'), (b'shp', 'Shipibo-Conibo'), (b'sna', 'Shona'), (b'sn', b'Shona'), (b'ii', 'Sichuan Yi'), (b'scn', 'Sicilian'), (b'sgn', 'Sign Languages'), (b'szl', 'Silesian'), (b'sd', 'Sindhi'), (b'si', 'Sinhala'), (b'sk', 'Slovak'), (b'sl', 'Slovenian'), (b'sby', 'Soli'), (b'so', b'Somali'), (b'som', 'Somali'), (b'sot', 'Sotho'), (b'nr', 'Southern Ndebele'), (b'st', 'Southern Sotho'), (b'es', 'Spanish'), (b'es-ec', 'Spanish (Ecuador)'), (b'es-419', 'Spanish (Latin America)'), (b'es-es', b'Spanish (Spain)'), (b'es-ar', 'Spanish, Argentinian'), (b'es-mx', 'Spanish, Mexican'), (b'es-ni', 'Spanish, Nicaraguan'), (b'su', 'Sundanese'), (b'sw', b'Swahili'), (b'swa', 'Swahili'), (b'ss', 'Swati'), (b'sv', 'Swedish'), (b'gsw', 'Swiss German'), (b'tl', 'Tagalog'), (b'ty', 'Tahitian'), (b'tg', 'Tajik'), (b'ta', 'Tamil'), (b'tar', 'Tarahumara, Central'), (b'cta', 'Tataltepec Chatino'), (b'tt', 'Tatar'), (b'te', 'Telugu'), (b'tet', 'Tetum'), (b'th', 'Thai'), (b'bo', 'Tibetan'), (b'ti', b'Tigrinya'), (b'tir', 'Tigrinya'), (b'toj', 'Tojolabal'), (b'to', 'Tonga'), (b'ts', 'Tsonga'), (b'tn', b'Tswana'), (b'tsn', 'Tswana'), (b'aeb', 'Tunisian Arabic'), (b'tr', 'Turkish'), (b'tk', 'Turkmen'), (b'tw', 'Twi'), (b'tzh', 'Tzeltal, Oxchuc'), (b'tzo', 'Tzotzil, Venustiano Carranza'), (b'uk', 'Ukrainian'), (b'umb', 'Umbundu'), (b'hsb', b'Upper Sorbian'), (b'ur', 'Urdu'), (b'ug', 'Uyghur'), (b'uz', 'Uzbek'), (b've', 'Venda'), (b'vi', 'Vietnamese'), (b'vo', 'Volapuk'), (b'wbl', 'Wakhi'), (b'wa', 'Walloon'), (b'wau', 'Wauja'), (b'cy', 'Welsh'), (b'fy', b'Western Frisian'), (b'pnb', 'Western Punjabi'), (b'wol', 'Wolof'), (b'wo', b'Wolof'), (b'xho', 'Xhosa'), (b'xh', b'Xhosa'), (b'tao', 'Yami (Tao)'), (b'yaq', 'Yaqui'), (b'yi', 'Yiddish'), (b'yo', b'Yoruba'), (b'yor', 'Yoruba'), (b'zam', 'Zapotec, Miahuatl\xe1n'), (b'zza', 'Zazaki'), (b'czn', 'Zenzontepec Chatino'), (b'za', 'Zhuang, Chuang'), (b'zu', b'Zulu'), (b'zul', 'Zulu')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MembershipNarrowing',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('language', models.CharField(blank=True, max_length=24, choices=[(b'ab', 'Abkhazian'), (b'ace', 'Acehnese'), (b'aa', 'Afar'), (b'af', 'Afrikaans'), (b'aka', 'Akan'), (b'sq', 'Albanian'), (b'arq', 'Algerian Arabic'), (b'ase', 'American Sign Language'), (b'amh', 'Amharic'), (b'am', 'Amharic'), (b'ami', 'Amis'), (b'ar', 'Arabic'), (b'an', 'Aragonese'), (b'arc', 'Aramaic'), (b'hy', 'Armenian'), (b'as', 'Assamese'), (b'ast', 'Asturian'), (b'av', 'Avaric'), (b'ae', 'Avestan'), (b'ay', 'Aymara'), (b'az', 'Azerbaijani'), (b'bam', 'Bambara'), (b'ba', 'Bashkir'), (b'eu', 'Basque'), (b'be', 'Belarusian'), (b'bem', 'Bemba (Zambia)'), (b'bn', 'Bengali'), (b'ber', 'Berber'), (b'bh', 'Bihari'), (b'bi', 'Bislama'), (b'bs', 'Bosnian'), (b'br', 'Breton'), (b'bug', 'Buginese'), (b'bg', 'Bulgarian'), (b'my', 'Burmese'), (b'cak', 'Cakchiquel, Central'), (b'ca', 'Catalan'), (b'ceb', 'Cebuano'), (b'ch', 'Chamorro'), (b'ce', 'Chechen'), (b'chr', 'Cherokee'), (b'nya', 'Chewa'), (b'ctd', 'Chin, Tedim'), (b'zh-hans', b'Chinese (Simplified Han)'), (b'zh-hant', b'Chinese (Traditional Han)'), (b'zh-cn', 'Chinese, Simplified'), (b'zh-sg', 'Chinese, Simplified (Singaporean)'), (b'zh-tw', 'Chinese, Traditional'), (b'zh-hk', 'Chinese, Traditional (Hong Kong)'), (b'zh', 'Chinese, Yue'), (b'cho', 'Choctaw'), (b'ctu', 'Chol, Tumbal\xe1'), (b'cu', 'Church Slavic'), (b'cv', 'Chuvash'), (b'ksh', 'Colognian'), (b'rar', 'Cook Islands M\u0101ori'), (b'kw', 'Cornish'), (b'co', 'Corsican'), (b'cr', 'Cree'), (b'ht', 'Creole, Haitian'), (b'hr', 'Croatian'), (b'cs', 'Czech'), (b'da', 'Danish'), (b'prs', 'Dari'), (b'din', 'Dinka'), (b'dv', 'Divehi'), (b'nl', 'Dutch'), (b'nl-be', 'Dutch (Belgium)'), (b'dz', 'Dzongkha'), (b'cly', 'Eastern Chatino'), (b'efi', 'Efik'), (b'arz', 'Egyptian Arabic'), (b'en', 'English'), (b'en-au', 'English (Australia)'), (b'en-ca', 'English (Canada)'), (b'en-in', 'English (India)'), (b'en-ie', 'English (Ireland)'), (b'en-us', 'English (United States)'), (b'en-gb', 'English, British'), (b'eo', 'Esperanto'), (b'et', 'Estonian'), (b'ee', 'Ewe'), (b'fo', 'Faroese'), (b'fj', 'Fijian'), (b'fil', 'Filipino'), (b'fi', 'Finnish'), (b'vls', 'Flemish'), (b'fr', 'French'), (b'fr-be', 'French (Belgium)'), (b'fr-ca', 'French (Canada)'), (b'fr-ch', 'French (Switzerland)'), (b'fy-nl', 'Frisian'), (b'ful', 'Fula'), (b'ff', 'Fulah'), (b'gl', 'Galician'), (b'lg', 'Ganda'), (b'ka', 'Georgian'), (b'de', 'German'), (b'de-at', 'German (Austria)'), (b'de-ch', 'German (Switzerland)'), (b'kik', 'Gikuyu'), (b'got', 'Gothic'), (b'el', 'Greek'), (b'kl', 'Greenlandic'), (b'gn', 'Guaran'), (b'gu', 'Gujarati'), (b'hai', 'Haida'), (b'cnh', 'Hakha Chin'), (b'hb', 'HamariBoli (Roman Hindi-Urdu)'), (b'hau', 'Hausa'), (b'ha', b'Hausa'), (b'hwc', "Hawai'i Creole English"), (b'haw', 'Hawaiian'), (b'haz', 'Hazaragi'), (b'iw', b'Hebrew'), (b'he', 'Hebrew'), (b'hz', 'Herero'), (b'hi', 'Hindi'), (b'ho', 'Hiri Motu'), (b'hmn', 'Hmong'), (b'nan', 'Hokkien'), (b'hus', 'Huastec, Veracruz'), (b'hch', 'Huichol'), (b'hu', 'Hungarian'), (b'hup', 'Hupa'), (b'bnt', 'Ibibio'), (b'is', 'Icelandic'), (b'io', 'Ido'), (b'ibo', 'Igbo'), (b'ilo', 'Ilocano'), (b'id', 'Indonesian'), (b'inh', 'Ingush'), (b'ia', 'Interlingua'), (b'ie', 'Interlingue'), (b'iu', 'Inuktitut'), (b'ik', 'Inupia'), (b'ga', 'Irish'), (b'iro', 'Iroquoian languages'), (b'it', 'Italian'), (b'ja', 'Japanese'), (b'jv', 'Javanese'), (b'kn', 'Kannada'), (b'kau', 'Kanuri'), (b'pam', 'Kapampangan'), (b'kaa', 'Karakalpak'), (b'kar', 'Karen'), (b'ks', 'Kashmiri'), (b'kk', 'Kazakh'), (b'km', 'Khmer'), (b'rw', b'Kinyarwanda'), (b'tlh', 'Klingon'), (b'cku', 'Koasati'), (b'kv', 'Komi'), (b'kon', 'Kongo'), (b'ko', 'Korean'), (b'kj', 'Kuanyama, Kwanyama'), (b'ku', 'Kurdish'), (b'ckb', 'Kurdish (Central)'), (b'ky', 'Kyrgyz'), (b'lld', 'Ladin'), (b'lkt', 'Lakota'), (b'lo', 'Lao'), (b'ltg', 'Latgalian'), (b'la', 'Latin'), (b'lv', 'Latvian'), (b'li', 'Limburgish'), (b'ln', b'Lingala'), (b'lin', 'Lingala'), (b'lt', 'Lithuanian'), (b'dsb', b'Lower Sorbian'), (b'loz', 'Lozi'), (b'lua', 'Luba-Kasai'), (b'lu', 'Luba-Katagana'), (b'luy', 'Luhya'), (b'luo', 'Luo'), (b'lut', 'Lushootseed'), (b'lb', 'Luxembourgish'), (b'rup', 'Macedo'), (b'mk', 'Macedonian'), (b'mad', 'Madurese'), (b'mg', b'Malagasy'), (b'mlg', 'Malagasy'), (b'ms', 'Malay'), (b'ml', 'Malayalam'), (b'mt', 'Maltese'), (b'mnk', 'Mandinka'), (b'mni', 'Manipuri'), (b'gv', 'Manx'), (b'mi', 'Maori'), (b'mr', 'Marathi'), (b'mh', 'Marshallese'), (b'mfe', b'Mauritian Creole'), (b'yua', 'Maya, Yucat\xe1n'), (b'meta-audio', 'Metadata: Audio Description'), (b'meta-geo', 'Metadata: Geo'), (b'meta-tw', 'Metadata: Twitter'), (b'meta-video', 'Metadata: Video Description'), (b'meta-wiki', 'Metadata: Wikipedia'), (b'lus', 'Mizo'), (b'moh', 'Mohawk'), (b'mo', 'Moldavian, Moldovan'), (b'mn', 'Mongolian'), (b'srp', 'Montenegrin'), (b'mos', 'Mossi'), (b'mus', 'Muscogee'), (b'nci', 'Nahuatl, Classical'), (b'ncj', 'Nahuatl, Northern Puebla'), (b'na', 'Naurunan'), (b'nv', 'Navajo'), (b'ng', 'Ndonga'), (b'ne', 'Nepali'), (b'pcm', 'Nigerian Pidgin'), (b'nd', 'North Ndebele'), (b'se', 'Northern Sami'), (b'nso', 'Northern Sotho'), (b'no', 'Norwegian'), (b'nb', 'Norwegian Bokmal'), (b'nn', 'Norwegian Nynorsk'), (b'oc', 'Occitan'), (b'oji', 'Ojibwe'), (b'or', 'Oriya'), (b'orm', 'Oromo'), (b'om', b'Oromo'), (b'os', 'Ossetian, Ossetic'), (b'x-other', 'Other'), (b'pi', 'Pali'), (b'pap', 'Papiamento'), (b'ps', 'Pashto'), (b'fa', 'Persian'), (b'fa-af', 'Persian (Afghanistan)'), (b'pcd', 'Picard'), (b'pl', 'Polish'), (b'pt', 'Portuguese'), (b'pt-pt', b'Portuguese (Portugal)'), (b'pt-br', 'Portuguese, Brazilian'), (b'pa', b'Punjabi'), (b'pan', 'Punjabi'), (b'tsz', 'Purepecha'), (b'tob', b'Qom (Toba)'), (b'que', 'Quechua'), (b'qu', b'Quechua'), (b'qvi', 'Quichua, Imbabura Highland'), (b'raj', 'Rajasthani'), (b'ro', 'Romanian'), (b'rm', 'Romansh'), (b'rn', b'Rundi'), (b'run', 'Rundi'), (b'ru', 'Russian'), (b'ry', 'Rusyn'), (b'kin', 'Rwandi'), (b'sm', 'Samoan'), (b'sg', 'Sango'), (b'sa', 'Sanskrit'), (b'sc', 'Sardinian'), (b'sco', 'Scots'), (b'gd', 'Scottish Gaelic'), (b'trv', 'Seediq'), (b'skx', 'Seko Padang'), (b'sr', 'Serbian'), (b'sr-latn', 'Serbian, Latin'), (b'sh', 'Serbo-Croatian'), (b'crs', 'Seselwa Creole French'), (b'shp', 'Shipibo-Conibo'), (b'sna', 'Shona'), (b'sn', b'Shona'), (b'ii', 'Sichuan Yi'), (b'scn', 'Sicilian'), (b'sgn', 'Sign Languages'), (b'szl', 'Silesian'), (b'sd', 'Sindhi'), (b'si', 'Sinhala'), (b'sk', 'Slovak'), (b'sl', 'Slovenian'), (b'sby', 'Soli'), (b'so', b'Somali'), (b'som', 'Somali'), (b'sot', 'Sotho'), (b'nr', 'Southern Ndebele'), (b'st', 'Southern Sotho'), (b'es', 'Spanish'), (b'es-ec', 'Spanish (Ecuador)'), (b'es-419', 'Spanish (Latin America)'), (b'es-es', b'Spanish (Spain)'), (b'es-ar', 'Spanish, Argentinian'), (b'es-mx', 'Spanish, Mexican'), (b'es-ni', 'Spanish, Nicaraguan'), (b'su', 'Sundanese'), (b'sw', b'Swahili'), (b'swa', 'Swahili'), (b'ss', 'Swati'), (b'sv', 'Swedish'), (b'gsw', 'Swiss German'), (b'tl', 'Tagalog'), (b'ty', 'Tahitian'), (b'tg', 'Tajik'), (b'ta', 'Tamil'), (b'tar', 'Tarahumara, Central'), (b'cta', 'Tataltepec Chatino'), (b'tt', 'Tatar'), (b'te', 'Telugu'), (b'tet', 'Tetum'), (b'th', 'Thai'), (b'bo', 'Tibetan'), (b'ti', b'Tigrinya'), (b'tir', 'Tigrinya'), (b'toj', 'Tojolabal'), (b'to', 'Tonga'), (b'ts', 'Tsonga'), (b'tn', b'Tswana'), (b'tsn', 'Tswana'), (b'aeb', 'Tunisian Arabic'), (b'tr', 'Turkish'), (b'tk', 'Turkmen'), (b'tw', 'Twi'), (b'tzh', 'Tzeltal, Oxchuc'), (b'tzo', 'Tzotzil, Venustiano Carranza'), (b'uk', 'Ukrainian'), (b'umb', 'Umbundu'), (b'hsb', b'Upper Sorbian'), (b'ur', 'Urdu'), (b'ug', 'Uyghur'), (b'uz', 'Uzbek'), (b've', 'Venda'), (b'vi', 'Vietnamese'), (b'vo', 'Volapuk'), (b'wbl', 'Wakhi'), (b'wa', 'Walloon'), (b'wau', 'Wauja'), (b'cy', 'Welsh'), (b'fy', b'Western Frisian'), (b'pnb', 'Western Punjabi'), (b'wol', 'Wolof'), (b'wo', b'Wolof'), (b'xho', 'Xhosa'), (b'xh', b'Xhosa'), (b'tao', 'Yami (Tao)'), (b'yaq', 'Yaqui'), (b'yi', 'Yiddish'), (b'yo', b'Yoruba'), (b'yor', 'Yoruba'), (b'zam', 'Zapotec, Miahuatl\xe1n'), (b'zza', 'Zazaki'), (b'czn', 'Zenzontepec Chatino'), (b'za', 'Zhuang, Chuang'), (b'zu', b'Zulu'), (b'zul', 'Zulu')])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Partner',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=250, verbose_name='name')),
                ('slug', models.SlugField(unique=True, verbose_name='slug')),
                ('can_request_paid_captions', models.BooleanField(default=False)),
                ('admins', models.ManyToManyField(related_name='managed_partners', null=True, to='amara_auth.CustomUser', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(blank=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(max_length=2048, null=True, blank=True)),
                ('guidelines', models.TextField(max_length=2048, null=True, blank=True)),
                ('slug', models.SlugField(blank=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('workflow_enabled', models.BooleanField(default=False)),
                ('bill_to', models.ForeignKey(blank=True, to='teams.BillToClient', null=True)),
            ],
            options={
                'permissions': (('assign_roles', 'Assign Roles'), ('assign_tasks', 'Assign Tasks'), ('create_tasks', 'Create Tasks'), ('add_videos', 'Add videos'), ('edit_project_settings', 'Edit project settings'), ('edit_video_settings', 'Edit video settings'), ('accept_assignment', 'Accept assignment'), ('perform_manager_review', 'Perform manager review'), ('perform_peer_review', 'Perform peer review'), ('edit_subs', 'Edit subs'), ('message_all_members', 'Message all members')),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Setting',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.PositiveIntegerField(choices=[(100, b'messages_invite'), (101, b'messages_manager'), (102, b'messages_admin'), (103, b'messages_application'), (104, b'messages_joins'), (105, b'messages_joins_localized'), (200, b'guidelines_subtitle'), (201, b'guidelines_translate'), (202, b'guidelines_review'), (300, b'block_invitation_sent_message'), (301, b'block_application_sent_message'), (302, b'block_application_denided_message'), (303, b'block_team_member_new_message'), (304, b'block_team_member_leave_message'), (305, b'block_task_assigned_message'), (306, b'block_reviewed_and_published_message'), (307, b'block_reviewed_and_pending_approval_message'), (308, b'block_reviewed_and_sent_back_message'), (309, b'block_approved_message'), (310, b'block_new_video_message'), (311, b'block_new_collab_assignments_message'), (312, b'block_collab_auto_unassignments_message'), (401, b'pagetext_welcome_heading'), (402, b'pagetext_warning_tasks'), (501, b'enable_require_translated_metadata')])),
                ('data', models.TextField(blank=True)),
                ('language_code', models.CharField(default=b'', max_length=16, blank=True, choices=[(b'ab', 'Abkhazian'), (b'ace', 'Acehnese'), (b'aa', 'Afar'), (b'af', 'Afrikaans'), (b'aka', 'Akan'), (b'sq', 'Albanian'), (b'arq', 'Algerian Arabic'), (b'ase', 'American Sign Language'), (b'amh', 'Amharic'), (b'am', 'Amharic'), (b'ami', 'Amis'), (b'ar', 'Arabic'), (b'an', 'Aragonese'), (b'arc', 'Aramaic'), (b'hy', 'Armenian'), (b'as', 'Assamese'), (b'ast', 'Asturian'), (b'av', 'Avaric'), (b'ae', 'Avestan'), (b'ay', 'Aymara'), (b'az', 'Azerbaijani'), (b'bam', 'Bambara'), (b'ba', 'Bashkir'), (b'eu', 'Basque'), (b'be', 'Belarusian'), (b'bem', 'Bemba (Zambia)'), (b'bn', 'Bengali'), (b'ber', 'Berber'), (b'bh', 'Bihari'), (b'bi', 'Bislama'), (b'bs', 'Bosnian'), (b'br', 'Breton'), (b'bug', 'Buginese'), (b'bg', 'Bulgarian'), (b'my', 'Burmese'), (b'cak', 'Cakchiquel, Central'), (b'ca', 'Catalan'), (b'ceb', 'Cebuano'), (b'ch', 'Chamorro'), (b'ce', 'Chechen'), (b'chr', 'Cherokee'), (b'nya', 'Chewa'), (b'ctd', 'Chin, Tedim'), (b'zh-hans', b'Chinese (Simplified Han)'), (b'zh-hant', b'Chinese (Traditional Han)'), (b'zh-cn', 'Chinese, Simplified'), (b'zh-sg', 'Chinese, Simplified (Singaporean)'), (b'zh-tw', 'Chinese, Traditional'), (b'zh-hk', 'Chinese, Traditional (Hong Kong)'), (b'zh', 'Chinese, Yue'), (b'cho', 'Choctaw'), (b'ctu', 'Chol, Tumbal\xe1'), (b'cu', 'Church Slavic'), (b'cv', 'Chuvash'), (b'ksh', 'Colognian'), (b'rar', 'Cook Islands M\u0101ori'), (b'kw', 'Cornish'), (b'co', 'Corsican'), (b'cr', 'Cree'), (b'ht', 'Creole, Haitian'), (b'hr', 'Croatian'), (b'cs', 'Czech'), (b'da', 'Danish'), (b'prs', 'Dari'), (b'din', 'Dinka'), (b'dv', 'Divehi'), (b'nl', 'Dutch'), (b'nl-be', 'Dutch (Belgium)'), (b'dz', 'Dzongkha'), (b'cly', 'Eastern Chatino'), (b'efi', 'Efik'), (b'arz', 'Egyptian Arabic'), (b'en', 'English'), (b'en-au', 'English (Australia)'), (b'en-ca', 'English (Canada)'), (b'en-in', 'English (India)'), (b'en-ie', 'English (Ireland)'), (b'en-us', 'English (United States)'), (b'en-gb', 'English, British'), (b'eo', 'Esperanto'), (b'et', 'Estonian'), (b'ee', 'Ewe'), (b'fo', 'Faroese'), (b'fj', 'Fijian'), (b'fil', 'Filipino'), (b'fi', 'Finnish'), (b'vls', 'Flemish'), (b'fr', 'French'), (b'fr-be', 'French (Belgium)'), (b'fr-ca', 'French (Canada)'), (b'fr-ch', 'French (Switzerland)'), (b'fy-nl', 'Frisian'), (b'ful', 'Fula'), (b'ff', 'Fulah'), (b'gl', 'Galician'), (b'lg', 'Ganda'), (b'ka', 'Georgian'), (b'de', 'German'), (b'de-at', 'German (Austria)'), (b'de-ch', 'German (Switzerland)'), (b'kik', 'Gikuyu'), (b'got', 'Gothic'), (b'el', 'Greek'), (b'kl', 'Greenlandic'), (b'gn', 'Guaran'), (b'gu', 'Gujarati'), (b'hai', 'Haida'), (b'cnh', 'Hakha Chin'), (b'hb', 'HamariBoli (Roman Hindi-Urdu)'), (b'hau', 'Hausa'), (b'ha', b'Hausa'), (b'hwc', "Hawai'i Creole English"), (b'haw', 'Hawaiian'), (b'haz', 'Hazaragi'), (b'iw', b'Hebrew'), (b'he', 'Hebrew'), (b'hz', 'Herero'), (b'hi', 'Hindi'), (b'ho', 'Hiri Motu'), (b'hmn', 'Hmong'), (b'nan', 'Hokkien'), (b'hus', 'Huastec, Veracruz'), (b'hch', 'Huichol'), (b'hu', 'Hungarian'), (b'hup', 'Hupa'), (b'bnt', 'Ibibio'), (b'is', 'Icelandic'), (b'io', 'Ido'), (b'ibo', 'Igbo'), (b'ilo', 'Ilocano'), (b'id', 'Indonesian'), (b'inh', 'Ingush'), (b'ia', 'Interlingua'), (b'ie', 'Interlingue'), (b'iu', 'Inuktitut'), (b'ik', 'Inupia'), (b'ga', 'Irish'), (b'iro', 'Iroquoian languages'), (b'it', 'Italian'), (b'ja', 'Japanese'), (b'jv', 'Javanese'), (b'kn', 'Kannada'), (b'kau', 'Kanuri'), (b'pam', 'Kapampangan'), (b'kaa', 'Karakalpak'), (b'kar', 'Karen'), (b'ks', 'Kashmiri'), (b'kk', 'Kazakh'), (b'km', 'Khmer'), (b'rw', b'Kinyarwanda'), (b'tlh', 'Klingon'), (b'cku', 'Koasati'), (b'kv', 'Komi'), (b'kon', 'Kongo'), (b'ko', 'Korean'), (b'kj', 'Kuanyama, Kwanyama'), (b'ku', 'Kurdish'), (b'ckb', 'Kurdish (Central)'), (b'ky', 'Kyrgyz'), (b'lld', 'Ladin'), (b'lkt', 'Lakota'), (b'lo', 'Lao'), (b'ltg', 'Latgalian'), (b'la', 'Latin'), (b'lv', 'Latvian'), (b'li', 'Limburgish'), (b'ln', b'Lingala'), (b'lin', 'Lingala'), (b'lt', 'Lithuanian'), (b'dsb', b'Lower Sorbian'), (b'loz', 'Lozi'), (b'lua', 'Luba-Kasai'), (b'lu', 'Luba-Katagana'), (b'luy', 'Luhya'), (b'luo', 'Luo'), (b'lut', 'Lushootseed'), (b'lb', 'Luxembourgish'), (b'rup', 'Macedo'), (b'mk', 'Macedonian'), (b'mad', 'Madurese'), (b'mg', b'Malagasy'), (b'mlg', 'Malagasy'), (b'ms', 'Malay'), (b'ml', 'Malayalam'), (b'mt', 'Maltese'), (b'mnk', 'Mandinka'), (b'mni', 'Manipuri'), (b'gv', 'Manx'), (b'mi', 'Maori'), (b'mr', 'Marathi'), (b'mh', 'Marshallese'), (b'mfe', b'Mauritian Creole'), (b'yua', 'Maya, Yucat\xe1n'), (b'meta-audio', 'Metadata: Audio Description'), (b'meta-geo', 'Metadata: Geo'), (b'meta-tw', 'Metadata: Twitter'), (b'meta-video', 'Metadata: Video Description'), (b'meta-wiki', 'Metadata: Wikipedia'), (b'lus', 'Mizo'), (b'moh', 'Mohawk'), (b'mo', 'Moldavian, Moldovan'), (b'mn', 'Mongolian'), (b'srp', 'Montenegrin'), (b'mos', 'Mossi'), (b'mus', 'Muscogee'), (b'nci', 'Nahuatl, Classical'), (b'ncj', 'Nahuatl, Northern Puebla'), (b'na', 'Naurunan'), (b'nv', 'Navajo'), (b'ng', 'Ndonga'), (b'ne', 'Nepali'), (b'pcm', 'Nigerian Pidgin'), (b'nd', 'North Ndebele'), (b'se', 'Northern Sami'), (b'nso', 'Northern Sotho'), (b'no', 'Norwegian'), (b'nb', 'Norwegian Bokmal'), (b'nn', 'Norwegian Nynorsk'), (b'oc', 'Occitan'), (b'oji', 'Ojibwe'), (b'or', 'Oriya'), (b'orm', 'Oromo'), (b'om', b'Oromo'), (b'os', 'Ossetian, Ossetic'), (b'x-other', 'Other'), (b'pi', 'Pali'), (b'pap', 'Papiamento'), (b'ps', 'Pashto'), (b'fa', 'Persian'), (b'fa-af', 'Persian (Afghanistan)'), (b'pcd', 'Picard'), (b'pl', 'Polish'), (b'pt', 'Portuguese'), (b'pt-pt', b'Portuguese (Portugal)'), (b'pt-br', 'Portuguese, Brazilian'), (b'pa', b'Punjabi'), (b'pan', 'Punjabi'), (b'tsz', 'Purepecha'), (b'tob', b'Qom (Toba)'), (b'que', 'Quechua'), (b'qu', b'Quechua'), (b'qvi', 'Quichua, Imbabura Highland'), (b'raj', 'Rajasthani'), (b'ro', 'Romanian'), (b'rm', 'Romansh'), (b'rn', b'Rundi'), (b'run', 'Rundi'), (b'ru', 'Russian'), (b'ry', 'Rusyn'), (b'kin', 'Rwandi'), (b'sm', 'Samoan'), (b'sg', 'Sango'), (b'sa', 'Sanskrit'), (b'sc', 'Sardinian'), (b'sco', 'Scots'), (b'gd', 'Scottish Gaelic'), (b'trv', 'Seediq'), (b'skx', 'Seko Padang'), (b'sr', 'Serbian'), (b'sr-latn', 'Serbian, Latin'), (b'sh', 'Serbo-Croatian'), (b'crs', 'Seselwa Creole French'), (b'shp', 'Shipibo-Conibo'), (b'sna', 'Shona'), (b'sn', b'Shona'), (b'ii', 'Sichuan Yi'), (b'scn', 'Sicilian'), (b'sgn', 'Sign Languages'), (b'szl', 'Silesian'), (b'sd', 'Sindhi'), (b'si', 'Sinhala'), (b'sk', 'Slovak'), (b'sl', 'Slovenian'), (b'sby', 'Soli'), (b'so', b'Somali'), (b'som', 'Somali'), (b'sot', 'Sotho'), (b'nr', 'Southern Ndebele'), (b'st', 'Southern Sotho'), (b'es', 'Spanish'), (b'es-ec', 'Spanish (Ecuador)'), (b'es-419', 'Spanish (Latin America)'), (b'es-es', b'Spanish (Spain)'), (b'es-ar', 'Spanish, Argentinian'), (b'es-mx', 'Spanish, Mexican'), (b'es-ni', 'Spanish, Nicaraguan'), (b'su', 'Sundanese'), (b'sw', b'Swahili'), (b'swa', 'Swahili'), (b'ss', 'Swati'), (b'sv', 'Swedish'), (b'gsw', 'Swiss German'), (b'tl', 'Tagalog'), (b'ty', 'Tahitian'), (b'tg', 'Tajik'), (b'ta', 'Tamil'), (b'tar', 'Tarahumara, Central'), (b'cta', 'Tataltepec Chatino'), (b'tt', 'Tatar'), (b'te', 'Telugu'), (b'tet', 'Tetum'), (b'th', 'Thai'), (b'bo', 'Tibetan'), (b'ti', b'Tigrinya'), (b'tir', 'Tigrinya'), (b'toj', 'Tojolabal'), (b'to', 'Tonga'), (b'ts', 'Tsonga'), (b'tn', b'Tswana'), (b'tsn', 'Tswana'), (b'aeb', 'Tunisian Arabic'), (b'tr', 'Turkish'), (b'tk', 'Turkmen'), (b'tw', 'Twi'), (b'tzh', 'Tzeltal, Oxchuc'), (b'tzo', 'Tzotzil, Venustiano Carranza'), (b'uk', 'Ukrainian'), (b'umb', 'Umbundu'), (b'hsb', b'Upper Sorbian'), (b'ur', 'Urdu'), (b'ug', 'Uyghur'), (b'uz', 'Uzbek'), (b've', 'Venda'), (b'vi', 'Vietnamese'), (b'vo', 'Volapuk'), (b'wbl', 'Wakhi'), (b'wa', 'Walloon'), (b'wau', 'Wauja'), (b'cy', 'Welsh'), (b'fy', b'Western Frisian'), (b'pnb', 'Western Punjabi'), (b'wol', 'Wolof'), (b'wo', b'Wolof'), (b'xho', 'Xhosa'), (b'xh', b'Xhosa'), (b'tao', 'Yami (Tao)'), (b'yaq', 'Yaqui'), (b'yi', 'Yiddish'), (b'yo', b'Yoruba'), (b'yor', 'Yoruba'), (b'zam', 'Zapotec, Miahuatl\xe1n'), (b'zza', 'Zazaki'), (b'czn', 'Zenzontepec Chatino'), (b'za', 'Zhuang, Chuang'), (b'zu', b'Zulu'), (b'zul', 'Zulu')])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.PositiveIntegerField(choices=[(10, b'Subtitle'), (20, b'Translate'), (30, b'Review'), (40, b'Approve')])),
                ('language', models.CharField(blank=True, max_length=16, db_index=True, choices=[(b'ab', 'Abkhazian'), (b'ace', 'Acehnese'), (b'aa', 'Afar'), (b'af', 'Afrikaans'), (b'aka', 'Akan'), (b'sq', 'Albanian'), (b'arq', 'Algerian Arabic'), (b'ase', 'American Sign Language'), (b'amh', 'Amharic'), (b'am', 'Amharic'), (b'ami', 'Amis'), (b'ar', 'Arabic'), (b'an', 'Aragonese'), (b'arc', 'Aramaic'), (b'hy', 'Armenian'), (b'as', 'Assamese'), (b'ast', 'Asturian'), (b'av', 'Avaric'), (b'ae', 'Avestan'), (b'ay', 'Aymara'), (b'az', 'Azerbaijani'), (b'bam', 'Bambara'), (b'ba', 'Bashkir'), (b'eu', 'Basque'), (b'be', 'Belarusian'), (b'bem', 'Bemba (Zambia)'), (b'bn', 'Bengali'), (b'ber', 'Berber'), (b'bh', 'Bihari'), (b'bi', 'Bislama'), (b'bs', 'Bosnian'), (b'br', 'Breton'), (b'bug', 'Buginese'), (b'bg', 'Bulgarian'), (b'my', 'Burmese'), (b'cak', 'Cakchiquel, Central'), (b'ca', 'Catalan'), (b'ceb', 'Cebuano'), (b'ch', 'Chamorro'), (b'ce', 'Chechen'), (b'chr', 'Cherokee'), (b'nya', 'Chewa'), (b'ctd', 'Chin, Tedim'), (b'zh-hans', b'Chinese (Simplified Han)'), (b'zh-hant', b'Chinese (Traditional Han)'), (b'zh-cn', 'Chinese, Simplified'), (b'zh-sg', 'Chinese, Simplified (Singaporean)'), (b'zh-tw', 'Chinese, Traditional'), (b'zh-hk', 'Chinese, Traditional (Hong Kong)'), (b'zh', 'Chinese, Yue'), (b'cho', 'Choctaw'), (b'ctu', 'Chol, Tumbal\xe1'), (b'cu', 'Church Slavic'), (b'cv', 'Chuvash'), (b'ksh', 'Colognian'), (b'rar', 'Cook Islands M\u0101ori'), (b'kw', 'Cornish'), (b'co', 'Corsican'), (b'cr', 'Cree'), (b'ht', 'Creole, Haitian'), (b'hr', 'Croatian'), (b'cs', 'Czech'), (b'da', 'Danish'), (b'prs', 'Dari'), (b'din', 'Dinka'), (b'dv', 'Divehi'), (b'nl', 'Dutch'), (b'nl-be', 'Dutch (Belgium)'), (b'dz', 'Dzongkha'), (b'cly', 'Eastern Chatino'), (b'efi', 'Efik'), (b'arz', 'Egyptian Arabic'), (b'en', 'English'), (b'en-au', 'English (Australia)'), (b'en-ca', 'English (Canada)'), (b'en-in', 'English (India)'), (b'en-ie', 'English (Ireland)'), (b'en-us', 'English (United States)'), (b'en-gb', 'English, British'), (b'eo', 'Esperanto'), (b'et', 'Estonian'), (b'ee', 'Ewe'), (b'fo', 'Faroese'), (b'fj', 'Fijian'), (b'fil', 'Filipino'), (b'fi', 'Finnish'), (b'vls', 'Flemish'), (b'fr', 'French'), (b'fr-be', 'French (Belgium)'), (b'fr-ca', 'French (Canada)'), (b'fr-ch', 'French (Switzerland)'), (b'fy-nl', 'Frisian'), (b'ful', 'Fula'), (b'ff', 'Fulah'), (b'gl', 'Galician'), (b'lg', 'Ganda'), (b'ka', 'Georgian'), (b'de', 'German'), (b'de-at', 'German (Austria)'), (b'de-ch', 'German (Switzerland)'), (b'kik', 'Gikuyu'), (b'got', 'Gothic'), (b'el', 'Greek'), (b'kl', 'Greenlandic'), (b'gn', 'Guaran'), (b'gu', 'Gujarati'), (b'hai', 'Haida'), (b'cnh', 'Hakha Chin'), (b'hb', 'HamariBoli (Roman Hindi-Urdu)'), (b'hau', 'Hausa'), (b'ha', b'Hausa'), (b'hwc', "Hawai'i Creole English"), (b'haw', 'Hawaiian'), (b'haz', 'Hazaragi'), (b'iw', b'Hebrew'), (b'he', 'Hebrew'), (b'hz', 'Herero'), (b'hi', 'Hindi'), (b'ho', 'Hiri Motu'), (b'hmn', 'Hmong'), (b'nan', 'Hokkien'), (b'hus', 'Huastec, Veracruz'), (b'hch', 'Huichol'), (b'hu', 'Hungarian'), (b'hup', 'Hupa'), (b'bnt', 'Ibibio'), (b'is', 'Icelandic'), (b'io', 'Ido'), (b'ibo', 'Igbo'), (b'ilo', 'Ilocano'), (b'id', 'Indonesian'), (b'inh', 'Ingush'), (b'ia', 'Interlingua'), (b'ie', 'Interlingue'), (b'iu', 'Inuktitut'), (b'ik', 'Inupia'), (b'ga', 'Irish'), (b'iro', 'Iroquoian languages'), (b'it', 'Italian'), (b'ja', 'Japanese'), (b'jv', 'Javanese'), (b'kn', 'Kannada'), (b'kau', 'Kanuri'), (b'pam', 'Kapampangan'), (b'kaa', 'Karakalpak'), (b'kar', 'Karen'), (b'ks', 'Kashmiri'), (b'kk', 'Kazakh'), (b'km', 'Khmer'), (b'rw', b'Kinyarwanda'), (b'tlh', 'Klingon'), (b'cku', 'Koasati'), (b'kv', 'Komi'), (b'kon', 'Kongo'), (b'ko', 'Korean'), (b'kj', 'Kuanyama, Kwanyama'), (b'ku', 'Kurdish'), (b'ckb', 'Kurdish (Central)'), (b'ky', 'Kyrgyz'), (b'lld', 'Ladin'), (b'lkt', 'Lakota'), (b'lo', 'Lao'), (b'ltg', 'Latgalian'), (b'la', 'Latin'), (b'lv', 'Latvian'), (b'li', 'Limburgish'), (b'ln', b'Lingala'), (b'lin', 'Lingala'), (b'lt', 'Lithuanian'), (b'dsb', b'Lower Sorbian'), (b'loz', 'Lozi'), (b'lua', 'Luba-Kasai'), (b'lu', 'Luba-Katagana'), (b'luy', 'Luhya'), (b'luo', 'Luo'), (b'lut', 'Lushootseed'), (b'lb', 'Luxembourgish'), (b'rup', 'Macedo'), (b'mk', 'Macedonian'), (b'mad', 'Madurese'), (b'mg', b'Malagasy'), (b'mlg', 'Malagasy'), (b'ms', 'Malay'), (b'ml', 'Malayalam'), (b'mt', 'Maltese'), (b'mnk', 'Mandinka'), (b'mni', 'Manipuri'), (b'gv', 'Manx'), (b'mi', 'Maori'), (b'mr', 'Marathi'), (b'mh', 'Marshallese'), (b'mfe', b'Mauritian Creole'), (b'yua', 'Maya, Yucat\xe1n'), (b'meta-audio', 'Metadata: Audio Description'), (b'meta-geo', 'Metadata: Geo'), (b'meta-tw', 'Metadata: Twitter'), (b'meta-video', 'Metadata: Video Description'), (b'meta-wiki', 'Metadata: Wikipedia'), (b'lus', 'Mizo'), (b'moh', 'Mohawk'), (b'mo', 'Moldavian, Moldovan'), (b'mn', 'Mongolian'), (b'srp', 'Montenegrin'), (b'mos', 'Mossi'), (b'mus', 'Muscogee'), (b'nci', 'Nahuatl, Classical'), (b'ncj', 'Nahuatl, Northern Puebla'), (b'na', 'Naurunan'), (b'nv', 'Navajo'), (b'ng', 'Ndonga'), (b'ne', 'Nepali'), (b'pcm', 'Nigerian Pidgin'), (b'nd', 'North Ndebele'), (b'se', 'Northern Sami'), (b'nso', 'Northern Sotho'), (b'no', 'Norwegian'), (b'nb', 'Norwegian Bokmal'), (b'nn', 'Norwegian Nynorsk'), (b'oc', 'Occitan'), (b'oji', 'Ojibwe'), (b'or', 'Oriya'), (b'orm', 'Oromo'), (b'om', b'Oromo'), (b'os', 'Ossetian, Ossetic'), (b'x-other', 'Other'), (b'pi', 'Pali'), (b'pap', 'Papiamento'), (b'ps', 'Pashto'), (b'fa', 'Persian'), (b'fa-af', 'Persian (Afghanistan)'), (b'pcd', 'Picard'), (b'pl', 'Polish'), (b'pt', 'Portuguese'), (b'pt-pt', b'Portuguese (Portugal)'), (b'pt-br', 'Portuguese, Brazilian'), (b'pa', b'Punjabi'), (b'pan', 'Punjabi'), (b'tsz', 'Purepecha'), (b'tob', b'Qom (Toba)'), (b'que', 'Quechua'), (b'qu', b'Quechua'), (b'qvi', 'Quichua, Imbabura Highland'), (b'raj', 'Rajasthani'), (b'ro', 'Romanian'), (b'rm', 'Romansh'), (b'rn', b'Rundi'), (b'run', 'Rundi'), (b'ru', 'Russian'), (b'ry', 'Rusyn'), (b'kin', 'Rwandi'), (b'sm', 'Samoan'), (b'sg', 'Sango'), (b'sa', 'Sanskrit'), (b'sc', 'Sardinian'), (b'sco', 'Scots'), (b'gd', 'Scottish Gaelic'), (b'trv', 'Seediq'), (b'skx', 'Seko Padang'), (b'sr', 'Serbian'), (b'sr-latn', 'Serbian, Latin'), (b'sh', 'Serbo-Croatian'), (b'crs', 'Seselwa Creole French'), (b'shp', 'Shipibo-Conibo'), (b'sna', 'Shona'), (b'sn', b'Shona'), (b'ii', 'Sichuan Yi'), (b'scn', 'Sicilian'), (b'sgn', 'Sign Languages'), (b'szl', 'Silesian'), (b'sd', 'Sindhi'), (b'si', 'Sinhala'), (b'sk', 'Slovak'), (b'sl', 'Slovenian'), (b'sby', 'Soli'), (b'so', b'Somali'), (b'som', 'Somali'), (b'sot', 'Sotho'), (b'nr', 'Southern Ndebele'), (b'st', 'Southern Sotho'), (b'es', 'Spanish'), (b'es-ec', 'Spanish (Ecuador)'), (b'es-419', 'Spanish (Latin America)'), (b'es-es', b'Spanish (Spain)'), (b'es-ar', 'Spanish, Argentinian'), (b'es-mx', 'Spanish, Mexican'), (b'es-ni', 'Spanish, Nicaraguan'), (b'su', 'Sundanese'), (b'sw', b'Swahili'), (b'swa', 'Swahili'), (b'ss', 'Swati'), (b'sv', 'Swedish'), (b'gsw', 'Swiss German'), (b'tl', 'Tagalog'), (b'ty', 'Tahitian'), (b'tg', 'Tajik'), (b'ta', 'Tamil'), (b'tar', 'Tarahumara, Central'), (b'cta', 'Tataltepec Chatino'), (b'tt', 'Tatar'), (b'te', 'Telugu'), (b'tet', 'Tetum'), (b'th', 'Thai'), (b'bo', 'Tibetan'), (b'ti', b'Tigrinya'), (b'tir', 'Tigrinya'), (b'toj', 'Tojolabal'), (b'to', 'Tonga'), (b'ts', 'Tsonga'), (b'tn', b'Tswana'), (b'tsn', 'Tswana'), (b'aeb', 'Tunisian Arabic'), (b'tr', 'Turkish'), (b'tk', 'Turkmen'), (b'tw', 'Twi'), (b'tzh', 'Tzeltal, Oxchuc'), (b'tzo', 'Tzotzil, Venustiano Carranza'), (b'uk', 'Ukrainian'), (b'umb', 'Umbundu'), (b'hsb', b'Upper Sorbian'), (b'ur', 'Urdu'), (b'ug', 'Uyghur'), (b'uz', 'Uzbek'), (b've', 'Venda'), (b'vi', 'Vietnamese'), (b'vo', 'Volapuk'), (b'wbl', 'Wakhi'), (b'wa', 'Walloon'), (b'wau', 'Wauja'), (b'cy', 'Welsh'), (b'fy', b'Western Frisian'), (b'pnb', 'Western Punjabi'), (b'wol', 'Wolof'), (b'wo', b'Wolof'), (b'xho', 'Xhosa'), (b'xh', b'Xhosa'), (b'tao', 'Yami (Tao)'), (b'yaq', 'Yaqui'), (b'yi', 'Yiddish'), (b'yo', b'Yoruba'), (b'yor', 'Yoruba'), (b'zam', 'Zapotec, Miahuatl\xe1n'), (b'zza', 'Zazaki'), (b'czn', 'Zenzontepec Chatino'), (b'za', 'Zhuang, Chuang'), (b'zu', b'Zulu'), (b'zul', 'Zulu')])),
                ('deleted', models.BooleanField(default=False)),
                ('public', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('completed', models.DateTimeField(null=True, blank=True)),
                ('expiration_date', models.DateTimeField(null=True, blank=True)),
                ('priority', models.PositiveIntegerField(default=0, db_index=True, blank=True)),
                ('approved', models.PositiveIntegerField(blank=True, null=True, choices=[(10, b'In Progress'), (20, b'Approved'), (30, b'Rejected')])),
                ('body', models.TextField(default=b'', blank=True)),
                ('assignee', models.ForeignKey(blank=True, to='amara_auth.CustomUser', null=True)),
                ('new_review_base_version', models.ForeignKey(related_name='tasks_based_on_new', blank=True, to='subtitles.SubtitleVersion', null=True)),
                ('new_subtitle_version', models.ForeignKey(blank=True, to='subtitles.SubtitleVersion', null=True)),
                ('review_base_version', models.ForeignKey(related_name='tasks_based_on', blank=True, to='videos.SubtitleVersion', null=True)),
                ('subtitle_version', models.ForeignKey(blank=True, to='videos.SubtitleVersion', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=250, verbose_name='name')),
                ('slug', models.SlugField(unique=True, verbose_name='slug')),
                ('description', models.TextField(help_text='All urls will be converted to links. Line breaks and HTML not supported.', verbose_name='description', blank=True)),
                ('logo', utils.amazon.fields.S3EnabledImageField(default=b'', upload_to=b'teams/logo/', verbose_name='logo', blank=True)),
                ('square_logo', utils.amazon.fields.S3EnabledImageField(default=b'', upload_to=b'teams/square-logo/', verbose_name='square logo', blank=True)),
                ('team_visibility', utils.enum.EnumField(default=utils.enum.EnumMember(b'TeamVisibility', b'PRIVATE', 'Private', 3))),
                ('video_visibility', utils.enum.EnumField(default=utils.enum.EnumMember(b'VideoVisibility', b'PRIVATE', 'Private', 3))),
                ('sync_metadata', models.BooleanField(default=False, verbose_name='Sync metadata when available (Youtube)?')),
                ('points', models.IntegerField(default=0, editable=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('highlight', models.BooleanField(default=False)),
                ('application_text', models.TextField(blank=True)),
                ('page_content', models.TextField(help_text='You can use markdown. This will replace Description.', verbose_name='Page content', blank=True)),
                ('is_moderated', models.BooleanField(default=False)),
                ('header_html_text', models.TextField(default=b'', help_text='HTML that appears at the top of the teams page.', blank=True)),
                ('last_notification_time', models.DateTimeField(default=datetime.datetime.now, editable=False)),
                ('notify_interval', models.CharField(default=b'D', max_length=1, choices=[(b'D', 'Daily'), (b'H', 'Hourly')])),
                ('prevent_duplicate_public_videos', models.BooleanField(default=False)),
                ('auth_provider_code', models.CharField(default=b'', max_length=24, verbose_name='authentication provider code', blank=True)),
                ('workflow_type', models.CharField(default=b'O', max_length=2)),
                ('projects_enabled', models.BooleanField(default=False)),
                ('workflow_enabled', models.BooleanField(default=False)),
                ('membership_policy', models.IntegerField(default=4, verbose_name='membership policy', choices=[(4, 'Open'), (1, 'Application'), (3, 'Invitation by any team member'), (2, 'Invitation by manager'), (5, 'Invitation by admin')])),
                ('video_policy', models.IntegerField(default=1, verbose_name='video policy', choices=[(1, 'Any team member'), (2, 'Managers and admins'), (3, 'Admins only')])),
                ('task_assign_policy', models.IntegerField(default=10, verbose_name='task assignment policy', choices=[(10, b'Any team member'), (20, b'Managers and admins'), (30, b'Admins only')])),
                ('subtitle_policy', models.IntegerField(default=10, verbose_name='subtitling policy', choices=[(10, b'Anyone'), (20, b'Any team member'), (30, b'Only managers and admins'), (40, b'Only admins')])),
                ('translate_policy', models.IntegerField(default=10, verbose_name='translation policy', choices=[(10, b'Anyone'), (20, b'Any team member'), (30, b'Only managers and admins'), (40, b'Only admins')])),
                ('max_tasks_per_member', models.PositiveIntegerField(default=None, null=True, verbose_name='maximum tasks per member', blank=True)),
                ('task_expiration', models.PositiveIntegerField(default=None, null=True, verbose_name='task expiration (days)', blank=True)),
                ('deleted', models.BooleanField(default=False)),
                ('applicants', models.ManyToManyField(related_name='applicated_teams', verbose_name='applicants', through='teams.Application', to='amara_auth.CustomUser')),
                ('bill_to', models.ForeignKey(blank=True, to='teams.BillToClient', null=True)),
                ('partner', models.ForeignKey(related_name='teams', blank=True, to='teams.Partner', null=True)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Team',
                'verbose_name_plural': 'Teams',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TeamLanguagePreference',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('language_code', models.CharField(max_length=16)),
                ('allow_reads', models.BooleanField(default=False)),
                ('allow_writes', models.BooleanField(default=False)),
                ('preferred', models.BooleanField(default=False)),
                ('team', models.ForeignKey(related_name='lang_preferences', to='teams.Team')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TeamMember',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('role', models.CharField(default=b'contributor', max_length=16, db_index=True, choices=[(b'owner', 'Owner'), (b'manager', 'Manager'), (b'admin', 'Admin'), (b'contributor', 'Contributor')])),
                ('created', models.DateTimeField(default=datetime.datetime.now, null=True, blank=True)),
                ('projects_managed', models.ManyToManyField(related_name='managers', to='teams.Project')),
                ('team', models.ForeignKey(related_name='members', to='teams.Team')),
                ('user', models.ForeignKey(related_name='team_members', to='amara_auth.CustomUser')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TeamNotificationSetting',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('request_url', models.URLField(null=True, blank=True)),
                ('basic_auth_username', models.CharField(max_length=255, null=True, blank=True)),
                ('basic_auth_password', models.CharField(max_length=255, null=True, blank=True)),
                ('email', models.EmailField(max_length=75, null=True, blank=True)),
                ('notification_class', models.IntegerField(default=1)),
                ('partner', models.OneToOneField(related_name='notification_settings', null=True, blank=True, to='teams.Partner')),
                ('team', models.OneToOneField(related_name='notification_settings', null=True, blank=True, to='teams.Team')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TeamSubtitleNote',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('language_code', models.CharField(max_length=16, choices=[(b'ab', 'Abkhazian'), (b'ace', 'Acehnese'), (b'aa', 'Afar'), (b'af', 'Afrikaans'), (b'aka', 'Akan'), (b'sq', 'Albanian'), (b'arq', 'Algerian Arabic'), (b'ase', 'American Sign Language'), (b'amh', 'Amharic'), (b'am', 'Amharic'), (b'ami', 'Amis'), (b'ar', 'Arabic'), (b'an', 'Aragonese'), (b'arc', 'Aramaic'), (b'hy', 'Armenian'), (b'as', 'Assamese'), (b'ast', 'Asturian'), (b'av', 'Avaric'), (b'ae', 'Avestan'), (b'ay', 'Aymara'), (b'az', 'Azerbaijani'), (b'bam', 'Bambara'), (b'ba', 'Bashkir'), (b'eu', 'Basque'), (b'be', 'Belarusian'), (b'bem', 'Bemba (Zambia)'), (b'bn', 'Bengali'), (b'ber', 'Berber'), (b'bh', 'Bihari'), (b'bi', 'Bislama'), (b'bs', 'Bosnian'), (b'br', 'Breton'), (b'bug', 'Buginese'), (b'bg', 'Bulgarian'), (b'my', 'Burmese'), (b'cak', 'Cakchiquel, Central'), (b'ca', 'Catalan'), (b'ceb', 'Cebuano'), (b'ch', 'Chamorro'), (b'ce', 'Chechen'), (b'chr', 'Cherokee'), (b'nya', 'Chewa'), (b'ctd', 'Chin, Tedim'), (b'zh-hans', b'Chinese (Simplified Han)'), (b'zh-hant', b'Chinese (Traditional Han)'), (b'zh-cn', 'Chinese, Simplified'), (b'zh-sg', 'Chinese, Simplified (Singaporean)'), (b'zh-tw', 'Chinese, Traditional'), (b'zh-hk', 'Chinese, Traditional (Hong Kong)'), (b'zh', 'Chinese, Yue'), (b'cho', 'Choctaw'), (b'ctu', 'Chol, Tumbal\xe1'), (b'cu', 'Church Slavic'), (b'cv', 'Chuvash'), (b'ksh', 'Colognian'), (b'rar', 'Cook Islands M\u0101ori'), (b'kw', 'Cornish'), (b'co', 'Corsican'), (b'cr', 'Cree'), (b'ht', 'Creole, Haitian'), (b'hr', 'Croatian'), (b'cs', 'Czech'), (b'da', 'Danish'), (b'prs', 'Dari'), (b'din', 'Dinka'), (b'dv', 'Divehi'), (b'nl', 'Dutch'), (b'nl-be', 'Dutch (Belgium)'), (b'dz', 'Dzongkha'), (b'cly', 'Eastern Chatino'), (b'efi', 'Efik'), (b'arz', 'Egyptian Arabic'), (b'en', 'English'), (b'en-au', 'English (Australia)'), (b'en-ca', 'English (Canada)'), (b'en-in', 'English (India)'), (b'en-ie', 'English (Ireland)'), (b'en-us', 'English (United States)'), (b'en-gb', 'English, British'), (b'eo', 'Esperanto'), (b'et', 'Estonian'), (b'ee', 'Ewe'), (b'fo', 'Faroese'), (b'fj', 'Fijian'), (b'fil', 'Filipino'), (b'fi', 'Finnish'), (b'vls', 'Flemish'), (b'fr', 'French'), (b'fr-be', 'French (Belgium)'), (b'fr-ca', 'French (Canada)'), (b'fr-ch', 'French (Switzerland)'), (b'fy-nl', 'Frisian'), (b'ful', 'Fula'), (b'ff', 'Fulah'), (b'gl', 'Galician'), (b'lg', 'Ganda'), (b'ka', 'Georgian'), (b'de', 'German'), (b'de-at', 'German (Austria)'), (b'de-ch', 'German (Switzerland)'), (b'kik', 'Gikuyu'), (b'got', 'Gothic'), (b'el', 'Greek'), (b'kl', 'Greenlandic'), (b'gn', 'Guaran'), (b'gu', 'Gujarati'), (b'hai', 'Haida'), (b'cnh', 'Hakha Chin'), (b'hb', 'HamariBoli (Roman Hindi-Urdu)'), (b'hau', 'Hausa'), (b'ha', b'Hausa'), (b'hwc', "Hawai'i Creole English"), (b'haw', 'Hawaiian'), (b'haz', 'Hazaragi'), (b'iw', b'Hebrew'), (b'he', 'Hebrew'), (b'hz', 'Herero'), (b'hi', 'Hindi'), (b'ho', 'Hiri Motu'), (b'hmn', 'Hmong'), (b'nan', 'Hokkien'), (b'hus', 'Huastec, Veracruz'), (b'hch', 'Huichol'), (b'hu', 'Hungarian'), (b'hup', 'Hupa'), (b'bnt', 'Ibibio'), (b'is', 'Icelandic'), (b'io', 'Ido'), (b'ibo', 'Igbo'), (b'ilo', 'Ilocano'), (b'id', 'Indonesian'), (b'inh', 'Ingush'), (b'ia', 'Interlingua'), (b'ie', 'Interlingue'), (b'iu', 'Inuktitut'), (b'ik', 'Inupia'), (b'ga', 'Irish'), (b'iro', 'Iroquoian languages'), (b'it', 'Italian'), (b'ja', 'Japanese'), (b'jv', 'Javanese'), (b'kn', 'Kannada'), (b'kau', 'Kanuri'), (b'pam', 'Kapampangan'), (b'kaa', 'Karakalpak'), (b'kar', 'Karen'), (b'ks', 'Kashmiri'), (b'kk', 'Kazakh'), (b'km', 'Khmer'), (b'rw', b'Kinyarwanda'), (b'tlh', 'Klingon'), (b'cku', 'Koasati'), (b'kv', 'Komi'), (b'kon', 'Kongo'), (b'ko', 'Korean'), (b'kj', 'Kuanyama, Kwanyama'), (b'ku', 'Kurdish'), (b'ckb', 'Kurdish (Central)'), (b'ky', 'Kyrgyz'), (b'lld', 'Ladin'), (b'lkt', 'Lakota'), (b'lo', 'Lao'), (b'ltg', 'Latgalian'), (b'la', 'Latin'), (b'lv', 'Latvian'), (b'li', 'Limburgish'), (b'ln', b'Lingala'), (b'lin', 'Lingala'), (b'lt', 'Lithuanian'), (b'dsb', b'Lower Sorbian'), (b'loz', 'Lozi'), (b'lua', 'Luba-Kasai'), (b'lu', 'Luba-Katagana'), (b'luy', 'Luhya'), (b'luo', 'Luo'), (b'lut', 'Lushootseed'), (b'lb', 'Luxembourgish'), (b'rup', 'Macedo'), (b'mk', 'Macedonian'), (b'mad', 'Madurese'), (b'mg', b'Malagasy'), (b'mlg', 'Malagasy'), (b'ms', 'Malay'), (b'ml', 'Malayalam'), (b'mt', 'Maltese'), (b'mnk', 'Mandinka'), (b'mni', 'Manipuri'), (b'gv', 'Manx'), (b'mi', 'Maori'), (b'mr', 'Marathi'), (b'mh', 'Marshallese'), (b'mfe', b'Mauritian Creole'), (b'yua', 'Maya, Yucat\xe1n'), (b'meta-audio', 'Metadata: Audio Description'), (b'meta-geo', 'Metadata: Geo'), (b'meta-tw', 'Metadata: Twitter'), (b'meta-video', 'Metadata: Video Description'), (b'meta-wiki', 'Metadata: Wikipedia'), (b'lus', 'Mizo'), (b'moh', 'Mohawk'), (b'mo', 'Moldavian, Moldovan'), (b'mn', 'Mongolian'), (b'srp', 'Montenegrin'), (b'mos', 'Mossi'), (b'mus', 'Muscogee'), (b'nci', 'Nahuatl, Classical'), (b'ncj', 'Nahuatl, Northern Puebla'), (b'na', 'Naurunan'), (b'nv', 'Navajo'), (b'ng', 'Ndonga'), (b'ne', 'Nepali'), (b'pcm', 'Nigerian Pidgin'), (b'nd', 'North Ndebele'), (b'se', 'Northern Sami'), (b'nso', 'Northern Sotho'), (b'no', 'Norwegian'), (b'nb', 'Norwegian Bokmal'), (b'nn', 'Norwegian Nynorsk'), (b'oc', 'Occitan'), (b'oji', 'Ojibwe'), (b'or', 'Oriya'), (b'orm', 'Oromo'), (b'om', b'Oromo'), (b'os', 'Ossetian, Ossetic'), (b'x-other', 'Other'), (b'pi', 'Pali'), (b'pap', 'Papiamento'), (b'ps', 'Pashto'), (b'fa', 'Persian'), (b'fa-af', 'Persian (Afghanistan)'), (b'pcd', 'Picard'), (b'pl', 'Polish'), (b'pt', 'Portuguese'), (b'pt-pt', b'Portuguese (Portugal)'), (b'pt-br', 'Portuguese, Brazilian'), (b'pa', b'Punjabi'), (b'pan', 'Punjabi'), (b'tsz', 'Purepecha'), (b'tob', b'Qom (Toba)'), (b'que', 'Quechua'), (b'qu', b'Quechua'), (b'qvi', 'Quichua, Imbabura Highland'), (b'raj', 'Rajasthani'), (b'ro', 'Romanian'), (b'rm', 'Romansh'), (b'rn', b'Rundi'), (b'run', 'Rundi'), (b'ru', 'Russian'), (b'ry', 'Rusyn'), (b'kin', 'Rwandi'), (b'sm', 'Samoan'), (b'sg', 'Sango'), (b'sa', 'Sanskrit'), (b'sc', 'Sardinian'), (b'sco', 'Scots'), (b'gd', 'Scottish Gaelic'), (b'trv', 'Seediq'), (b'skx', 'Seko Padang'), (b'sr', 'Serbian'), (b'sr-latn', 'Serbian, Latin'), (b'sh', 'Serbo-Croatian'), (b'crs', 'Seselwa Creole French'), (b'shp', 'Shipibo-Conibo'), (b'sna', 'Shona'), (b'sn', b'Shona'), (b'ii', 'Sichuan Yi'), (b'scn', 'Sicilian'), (b'sgn', 'Sign Languages'), (b'szl', 'Silesian'), (b'sd', 'Sindhi'), (b'si', 'Sinhala'), (b'sk', 'Slovak'), (b'sl', 'Slovenian'), (b'sby', 'Soli'), (b'so', b'Somali'), (b'som', 'Somali'), (b'sot', 'Sotho'), (b'nr', 'Southern Ndebele'), (b'st', 'Southern Sotho'), (b'es', 'Spanish'), (b'es-ec', 'Spanish (Ecuador)'), (b'es-419', 'Spanish (Latin America)'), (b'es-es', b'Spanish (Spain)'), (b'es-ar', 'Spanish, Argentinian'), (b'es-mx', 'Spanish, Mexican'), (b'es-ni', 'Spanish, Nicaraguan'), (b'su', 'Sundanese'), (b'sw', b'Swahili'), (b'swa', 'Swahili'), (b'ss', 'Swati'), (b'sv', 'Swedish'), (b'gsw', 'Swiss German'), (b'tl', 'Tagalog'), (b'ty', 'Tahitian'), (b'tg', 'Tajik'), (b'ta', 'Tamil'), (b'tar', 'Tarahumara, Central'), (b'cta', 'Tataltepec Chatino'), (b'tt', 'Tatar'), (b'te', 'Telugu'), (b'tet', 'Tetum'), (b'th', 'Thai'), (b'bo', 'Tibetan'), (b'ti', b'Tigrinya'), (b'tir', 'Tigrinya'), (b'toj', 'Tojolabal'), (b'to', 'Tonga'), (b'ts', 'Tsonga'), (b'tn', b'Tswana'), (b'tsn', 'Tswana'), (b'aeb', 'Tunisian Arabic'), (b'tr', 'Turkish'), (b'tk', 'Turkmen'), (b'tw', 'Twi'), (b'tzh', 'Tzeltal, Oxchuc'), (b'tzo', 'Tzotzil, Venustiano Carranza'), (b'uk', 'Ukrainian'), (b'umb', 'Umbundu'), (b'hsb', b'Upper Sorbian'), (b'ur', 'Urdu'), (b'ug', 'Uyghur'), (b'uz', 'Uzbek'), (b've', 'Venda'), (b'vi', 'Vietnamese'), (b'vo', 'Volapuk'), (b'wbl', 'Wakhi'), (b'wa', 'Walloon'), (b'wau', 'Wauja'), (b'cy', 'Welsh'), (b'fy', b'Western Frisian'), (b'pnb', 'Western Punjabi'), (b'wol', 'Wolof'), (b'wo', b'Wolof'), (b'xho', 'Xhosa'), (b'xh', b'Xhosa'), (b'tao', 'Yami (Tao)'), (b'yaq', 'Yaqui'), (b'yi', 'Yiddish'), (b'yo', b'Yoruba'), (b'yor', 'Yoruba'), (b'zam', 'Zapotec, Miahuatl\xe1n'), (b'zza', 'Zazaki'), (b'czn', 'Zenzontepec Chatino'), (b'za', 'Zhuang, Chuang'), (b'zu', b'Zulu'), (b'zul', 'Zulu')])),
                ('body', models.TextField()),
                ('created', models.DateTimeField(default=datetime.datetime.now)),
                ('team', models.ForeignKey(related_name='+', to='teams.Team')),
                ('user', models.ForeignKey(related_name='+', to='amara_auth.CustomUser', null=True)),
                ('video', models.ForeignKey(related_name='+', to='videos.Video')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TeamVideo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.TextField(help_text='Use this space to explain why you or your team need to caption or subtitle this video. Adding a note makes volunteers more likely to help out!', blank=True)),
                ('thumbnail', utils.amazon.fields.S3EnabledImageField(help_text='We automatically grab thumbnails for certain sites, e.g. Youtube', null=True, upload_to=b'teams/video_thumbnails/', blank=True)),
                ('all_languages', models.BooleanField(default=False, help_text='If you check this, other languages will not be displayed.', verbose_name='Need help with all languages')),
                ('created', models.DateTimeField(blank=True)),
                ('partner_id', models.CharField(default=b'', max_length=100, blank=True)),
                ('added_by', models.ForeignKey(to='amara_auth.CustomUser', null=True)),
                ('project', models.ForeignKey(to='teams.Project')),
                ('team', models.ForeignKey(to='teams.Team')),
                ('video', models.OneToOneField(to='videos.Video')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TeamVideoMigration',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('datetime', models.DateTimeField()),
                ('from_team', models.ForeignKey(related_name='+', to='teams.Team')),
                ('to_project', models.ForeignKey(related_name='+', to='teams.Project')),
                ('to_team', models.ForeignKey(related_name='+', to='teams.Team')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Workflow',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('autocreate_subtitle', models.BooleanField(default=False)),
                ('autocreate_translate', models.BooleanField(default=False)),
                ('review_allowed', models.PositiveIntegerField(default=0, verbose_name=b'reviewers', choices=[(0, b"Don't require review"), (10, b'Peer must review'), (20, b'Manager must review'), (30, b'Admin must review')])),
                ('approve_allowed', models.PositiveIntegerField(default=0, verbose_name=b'approvers', choices=[(0, b"Don't require approval"), (10, b'Manager must approve'), (20, b'Admin must approve')])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(blank=True, to='teams.Project', null=True)),
                ('team', models.ForeignKey(to='teams.Team')),
                ('team_video', models.ForeignKey(blank=True, to='teams.TeamVideo', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='workflow',
            unique_together=set([('team', 'project', 'team_video')]),
        ),
        migrations.AlterUniqueTogether(
            name='teamvideo',
            unique_together=set([('team', 'video')]),
        ),
        migrations.AlterUniqueTogether(
            name='teammember',
            unique_together=set([('team', 'user')]),
        ),
        migrations.AlterUniqueTogether(
            name='teamlanguagepreference',
            unique_together=set([('team', 'language_code')]),
        ),
        migrations.AddField(
            model_name='team',
            name='users',
            field=models.ManyToManyField(related_name='teams', verbose_name='users', through='teams.TeamMember', to='amara_auth.CustomUser'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='team',
            name='video',
            field=models.ForeignKey(related_name='intro_for_teams', verbose_name='Intro Video', blank=True, to='videos.Video', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='team',
            name='videos',
            field=models.ManyToManyField(to='videos.Video', verbose_name='videos', through='teams.TeamVideo'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='task',
            name='team',
            field=models.ForeignKey(to='teams.Team'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='task',
            name='team_video',
            field=models.ForeignKey(to='teams.TeamVideo'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='setting',
            name='team',
            field=models.ForeignKey(related_name='settings', to='teams.Team'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='setting',
            unique_together=set([('key', 'team', 'language_code')]),
        ),
        migrations.AddField(
            model_name='project',
            name='team',
            field=models.ForeignKey(to='teams.Team'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='project',
            unique_together=set([('team', 'slug'), ('team', 'name')]),
        ),
        migrations.AddField(
            model_name='membershipnarrowing',
            name='added_by',
            field=models.ForeignKey(related_name='narrowing_includer', blank=True, to='teams.TeamMember', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='membershipnarrowing',
            name='member',
            field=models.ForeignKey(related_name='narrowings', to='teams.TeamMember'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='membershipnarrowing',
            name='project',
            field=models.ForeignKey(blank=True, to='teams.Project', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='languagemanager',
            name='member',
            field=models.ForeignKey(related_name='languages_managed', to='teams.TeamMember'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invite',
            name='team',
            field=models.ForeignKey(related_name='invitations', to='teams.Team'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invite',
            name='user',
            field=models.ForeignKey(related_name='team_invitations', to='amara_auth.CustomUser'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='billingreport',
            name='teams',
            field=models.ManyToManyField(related_name='billing_reports', to='teams.Team'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='billingrecord',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='teams.Project', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='billingrecord',
            name='subtitle_language',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='videos.SubtitleLanguage', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='billingrecord',
            name='subtitle_version',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='videos.SubtitleVersion', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='billingrecord',
            name='team',
            field=models.ForeignKey(to='teams.Team'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='billingrecord',
            name='user',
            field=models.ForeignKey(to='amara_auth.CustomUser'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='billingrecord',
            name='video',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='videos.Video', null=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='billingrecord',
            unique_together=set([('video', 'new_subtitle_language')]),
        ),
        migrations.AddField(
            model_name='application',
            name='team',
            field=models.ForeignKey(related_name='applications', to='teams.Team'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='application',
            name='user',
            field=models.ForeignKey(related_name='team_applications', to='amara_auth.CustomUser'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='application',
            unique_together=set([('team', 'user', 'status')]),
        ),
    ]
