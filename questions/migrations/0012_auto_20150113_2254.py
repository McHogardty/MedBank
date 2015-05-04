# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def create_block_weeks_from_activities(apps, schema_editor):
	TeachingBlockYear = apps.get_model("questions", "TeachingBlockYear")
	BlockWeek = apps.get_model("questions", "BlockWeek")

	for block_year in TeachingBlockYear.objects.all():
		weeks = {}

		writing_period = block_year.writing_periods.get()		

		for activity in block_year.activities.all():
			week = weeks.setdefault(activity.week, [])
			week.append(activity)

		for week, activities in weeks.items():
			block_week = BlockWeek()
			block_week.writing_period = writing_period
			block_week.sort_index = week
			block_week.name = "Week %s" % week
			block_week.save()

			for activity in activities:
				activity.block_week = block_week
				activity.save()



class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0011_auto_20150117_2349'),
    ]

    operations = [
    	migrations.RunPython(create_block_weeks_from_activities),
    ]
