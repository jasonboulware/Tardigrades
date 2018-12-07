# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import warnings

from django.db import models, migrations

def add_fulltext_index(apps, schema_editor):
    # Need to wrap this SQL code in catchwarnings since MySQL gives a warning
    # about creating the fulltext index
    cursor = schema_editor.connection.cursor()
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        cursor.execute('ALTER TABLE videos_videoindex '
                       'ADD FULLTEXT INDEX ft_text (text)')

class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0006_auto_20180614_0726'),
    ]

    operations = [
        migrations.RunSQL([
            'ALTER TABLE videos_videourl ADD INDEX url_prefix (url(255))'
        ]),
        migrations.RunPython(add_fulltext_index),
        migrations.RunSQL([
            'ALTER TABLE videos_videoindex MODIFY text LONGTEXT '
            'CHARACTER SET utf8 COLLATE utf8_unicode_ci',
        ]),
    ]
