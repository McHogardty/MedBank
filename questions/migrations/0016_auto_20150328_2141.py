# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.utils.text import normalize_newlines

def convert_questions_to_html(apps, schema_editor):
    Question = apps.get_model("questions", "Question")

    for question in Question.objects.all():
        body = normalize_newlines(question.body).strip()
        question.body = "<p>%s</p>" % body.replace("\n", "<br />")
        question.save()


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0015_teachingblock_code_includes_week'),
    ]

    operations = [
        migrations.RunPython(convert_questions_to_html),
    ]
