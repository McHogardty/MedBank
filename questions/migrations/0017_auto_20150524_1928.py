# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0016_auto_20150328_2141'),
    ]

    operations = [
        migrations.AlterField(
            model_name='teachingactivityyear',
            name='question_writers',
            field=models.ManyToManyField(related_name='assigned_activities', to='questions.Student', blank=True),
        ),
    ]
