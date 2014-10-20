# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0002_teachingblock_sort_index'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='teachingblock',
            options={'ordering': ('sort_index',)},
        ),
        migrations.AlterModelOptions(
            name='teachingblockyear',
            options={'ordering': ('year', 'block__sort_index')},
        ),
        migrations.AlterField(
            model_name='teachingactivity',
            name='name',
            field=models.CharField(max_length=150),
        ),
    ]
