# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def update_stage_information(apps, schema_editor):
	Stage = apps.get_model("questions", "Stage")

	for stage in Stage.objects.all():
		stage.name = "Stage %s" % stage.number
		stage.sort_index = stage.number
		stage.save()

class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0006_auto_20141230_2142'),
    ]

    operations = [
	    migrations.RunPython(update_stage_information),
    ]
