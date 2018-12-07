# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0005_auto_20180418_0950'),
    ]

    operations = [
        migrations.RunSQL(
            sql=["alter table videos_videoindex engine=InnoDB;"],
            reverse_sql=["alter table videos_videoindex engine=MyISAM;"])
    ]
