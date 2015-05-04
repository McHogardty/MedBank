# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0013_auto_20150123_2340'),
    ]

    operations = [
        migrations.AlterField(
            model_name='question',
            name='status',
            field=models.IntegerField(default=0, choices=[(0, b'Approved'), (1, b'Pending'), (2, b'Deleted'), (3, b'Flagged'), (4, b'Editing')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='teachingactivity',
            name='activity_type',
            field=models.IntegerField(choices=[(1, b'Lecture'), (0, b'PBL'), (3, b'Practical'), (4, b'Seminar'), (5, b'Week'), (6, b'CRS')]),
            preserve_default=True,
        ),
    ]
