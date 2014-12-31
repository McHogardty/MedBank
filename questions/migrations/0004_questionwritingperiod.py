# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0003_auto_20141020_1752'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuestionWritingPeriod',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('activity_capacity', models.IntegerField(default=2, verbose_name=b'Maximum users per activity')),
                ('start', models.DateField(verbose_name=b'Start date')),
                ('end', models.DateField(verbose_name=b'End date')),
                ('close', models.DateField(verbose_name=b'Close date')),
                ('release_date', models.DateField(null=True, verbose_name=b'Release date', blank=True)),
                ('block_year', models.ForeignKey(related_name=b'writing_periods', to='questions.TeachingBlockYear')),
                ('stage', models.ForeignKey(related_name=b'writing_periods', to='questions.Stage')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
