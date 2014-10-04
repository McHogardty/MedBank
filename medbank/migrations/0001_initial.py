# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Setting',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('class_name', models.CharField(max_length=100, editable=False)),
                ('name', models.CharField(max_length=100, editable=False)),
                ('verbose_name', models.CharField(max_length=100)),
                ('description', models.TextField(null=True, blank=True)),
                ('value', models.TextField(null=True, blank=True)),
                ('last_modified_date', models.DateTimeField(auto_now=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
