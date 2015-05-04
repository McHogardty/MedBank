# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0009_auto_20150103_2332'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='questionwritingperiod',
            options={'ordering': ('block_year', 'stage')},
        ),
        migrations.AlterUniqueTogether(
            name='questionwritingperiod',
            unique_together=set([('block_year', 'stage')]),
        ),
    ]
