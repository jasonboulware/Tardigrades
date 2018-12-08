# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('amara_auth', '0001_initial'),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_pk', models.TextField(verbose_name=b'object ID')),
                ('content', models.TextField(max_length=3000, verbose_name=b'comment')),
                ('submit_date', models.DateTimeField(auto_now_add=True)),
                ('content_type', models.ForeignKey(related_name='content_type_set_for_comment', to='contenttypes.ContentType')),
                ('reply_to', models.ForeignKey(blank=True, to='comments.Comment', null=True)),
                ('user', models.ForeignKey(to='amara_auth.CustomUser')),
            ],
            options={
                'ordering': ('-submit_date',),
            },
            bases=(models.Model,),
        ),
    ]
