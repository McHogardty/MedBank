# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='teachingblock',
            name='sort_index',
            field=models.IntegerField(default=0, db_index=True),
            preserve_default=False,
        ),
    ]
