# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0012_auto_20150113_2254'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='teachingactivityyear',
            options={'ordering': ('block_week__writing_period', 'teaching_activity__activity_type', 'block_week', 'position')},
        ),
        migrations.RemoveField(
            model_name='teachingactivityyear',
            name='block_year',
        ),
        migrations.RemoveField(
            model_name='teachingactivityyear',
            name='week',
        ),
    ]
