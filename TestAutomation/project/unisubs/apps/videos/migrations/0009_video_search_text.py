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
        cursor.execute('ALTER TABLE videos_video '
                       'ADD FULLTEXT INDEX ft_text (search_text)')

class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0008_auto_20180820_1023'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='search_text',
            field=models.TextField(default=b''),
            preserve_default=True,
        ),
        migrations.RunPython(add_fulltext_index),
    ]
