# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0014_auto_20150213_1948'),
    ]

    operations = [
        migrations.AddField(
            model_name='teachingblock',
            name='code_includes_week',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
    ]
