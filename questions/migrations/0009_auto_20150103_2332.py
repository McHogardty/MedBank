# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0008_auto_20150103_1445'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='teachingblockyear',
            name='activity_capacity',
        ),
        migrations.RemoveField(
            model_name='teachingblockyear',
            name='close',
        ),
        migrations.RemoveField(
            model_name='teachingblockyear',
            name='end',
        ),
        migrations.RemoveField(
            model_name='teachingblockyear',
            name='release_date',
        ),
        migrations.RemoveField(
            model_name='teachingblockyear',
            name='sign_up_mode',
        ),
        migrations.RemoveField(
            model_name='teachingblockyear',
            name='start',
        ),
        migrations.RemoveField(
            model_name='teachingblockyear',
            name='weeks',
        ),
    ]
