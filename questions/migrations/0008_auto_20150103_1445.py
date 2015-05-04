# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0007_auto_20141230_2144'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='stage',
            options={'ordering': ('sort_index',)},
        ),
        migrations.RemoveField(
            model_name='teachingblock',
            name='stage',
        ),
    ]
