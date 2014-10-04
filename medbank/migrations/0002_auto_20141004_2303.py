# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0001_initial'),
        ('medbank', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='setting',
            name='last_modified_by',
            field=models.ForeignKey(related_name='modified_settings', editable=False, to='questions.Student'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='setting',
            unique_together=set([('class_name', 'name')]),
        ),
    ]
