# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def convert_block_year_to_writing_period(apps, schema_editor):
    TeachingBlockYear = apps.get_model("questions", "TeachingBlockYear")
    QuestionWritingPeriod = apps.get_model("questions", "QuestionWritingPeriod")

    for block_year in TeachingBlockYear.objects.all():
        writing_period = QuestionWritingPeriod()
        writing_period.block_year = block_year
        writing_period.stage = block_year.block.stage
        writing_period.activity_capacity = block_year.activity_capacity
        writing_period.start = block_year.start
        writing_period.end = block_year.end
        writing_period.close = block_year.close
        writing_period.release_date = block_year.release_date
        writing_period.save()


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0004_questionwritingperiod'),
    ]

    operations = [
        migrations.RunPython(convert_block_year_to_writing_period),
    ]
