# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0010_auto_20150104_1537'),
    ]

    operations = [
        migrations.CreateModel(
            name='BlockWeek',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('sort_index', models.IntegerField(db_index=True)),
                ('writing_period', models.ForeignKey(related_name='weeks', to='questions.QuestionWritingPeriod')),
            ],
            options={
                'ordering': ('writing_period', 'sort_index'),
            },
            bases=(models.Model,),
        ),
        migrations.AlterModelOptions(
            name='teachingactivityyear',
            options={'ordering': ('block_year', 'teaching_activity__activity_type', 'week', 'position')},
        ),
        migrations.AddField(
            model_name='teachingactivityyear',
            name='block_week',
            field=models.ForeignKey(related_name='activities', blank=True, to='questions.BlockWeek', null=True),
            preserve_default=True,
        ),
    ]
