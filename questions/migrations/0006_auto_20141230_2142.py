# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0005_auto_20141224_2108'),
    ]

    operations = [
        migrations.AddField(
            model_name='stage',
            name='name',
            field=models.CharField(default='', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='stage',
            name='sort_index',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]
