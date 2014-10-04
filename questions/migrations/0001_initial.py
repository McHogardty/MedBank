# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import questions.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0001_initial'),
        ('medbank', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApprovalRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_assigned', models.DateTimeField(null=True, blank=True)),
                ('date_completed', models.DateTimeField(null=True, blank=True)),
                ('status', models.IntegerField(default=1, null=True, blank=True, choices=[(0, b'Approved'), (1, b'Pending'), (2, b'Deleted'), (3, b'Flagged'), (4, b'Editing')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('body', models.TextField(verbose_name=b'Comment')),
                ('date_created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('body', models.TextField()),
                ('options', models.TextField(blank=True)),
                ('answer', models.CharField(max_length=1)),
                ('explanation', models.TextField()),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('exemplary_question', models.BooleanField(default=False)),
                ('requires_special_formatting', models.BooleanField(default=False)),
                ('status', models.IntegerField(default=1, choices=[(0, b'Approved'), (1, b'Pending'), (2, b'Deleted'), (3, b'Flagged'), (4, b'Editing')])),
                ('date_assigned', models.DateTimeField(null=True, blank=True)),
                ('date_completed', models.DateTimeField(null=True, blank=True)),
            ],
            options={
                'permissions': (('can_approve', 'Can approve questions'),),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='QuestionAttempt',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('position', models.PositiveIntegerField()),
                ('answer', models.CharField(max_length=1, null=True, blank=True)),
                ('time_taken', models.PositiveIntegerField(null=True, blank=True)),
                ('confidence_rating', models.IntegerField(blank=True, null=True, choices=[(1, b"I'm guessing"), (2, b"I'm doubtful"), (3, b"I'm feeling neutral"), (4, b"I'm fairly sure"), (5, b"I'm certain")])),
                ('date_completed', models.DateTimeField(null=True, blank=True)),
                ('question', models.ForeignKey(related_name=b'attempts', to='questions.Question')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='QuestionRating',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('rating', models.IntegerField(choices=[(1, b'+'), (-1, b'-')])),
                ('date_rated', models.DateTimeField(auto_now_add=True)),
                ('question', models.ForeignKey(related_name=b'ratings', to='questions.Question')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='QuizAttempt',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_submitted', models.DateTimeField(auto_now_add=True)),
                ('slug', models.SlugField(max_length=36)),
                ('quiz_type', models.CharField(max_length=20, choices=[(b'individual', b'After each question'), (b'classic', b'At the end')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='QuizQuestionSpecification',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('specification_type', models.IntegerField(choices=[(0, b'A specific question'), (1, b'A random choice of questions from a block'), (2, b'A list of questions')])),
                ('parameters', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='QuizSpecification',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('slug', models.SlugField(max_length=36)),
                ('active', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ('stage',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Reason',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('body', models.TextField()),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('reason_type', models.IntegerField(choices=[(0, b'Edited'), (1, b'Flagged')])),
                ('related_object_id', models.PositiveIntegerField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Stage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.IntegerField()),
            ],
            options={
                'ordering': ('number',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
            },
            bases=(models.Model, questions.models.ObjectCacheMixin),
        ),
        migrations.CreateModel(
            name='TeachingActivity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('activity_type', models.IntegerField(choices=[(1, b'Lecture'), (0, b'PBL'), (3, b'Practical'), (4, b'Seminar'), (5, b'Week')])),
                ('reference_id', models.IntegerField(unique=True)),
                ('previous_activity', models.OneToOneField(null=True, blank=True, to='questions.TeachingActivity')),
            ],
            options={
            },
            bases=(models.Model, questions.models.ObjectCacheMixin),
        ),
        migrations.CreateModel(
            name='TeachingActivityYear',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('week', models.IntegerField()),
                ('position', models.IntegerField()),
            ],
            options={
                'ordering': ('block_year', 'week', 'position'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TeachingBlock',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('code', models.CharField(max_length=10)),
                ('stage', models.ForeignKey(to='questions.Stage')),
            ],
            options={
                'ordering': ('stage', 'code'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TeachingBlockYear',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('year', models.IntegerField()),
                ('start', models.DateField(verbose_name=b'Start date')),
                ('end', models.DateField(verbose_name=b'End date')),
                ('close', models.DateField(verbose_name=b'Close date')),
                ('release_date', models.DateField(null=True, verbose_name=b'Release date', blank=True)),
                ('activity_capacity', models.IntegerField(default=2, verbose_name=b'Maximum users per activity')),
                ('sign_up_mode', models.IntegerField(choices=[(0, b'By activity'), (1, b'By week')])),
                ('weeks', models.IntegerField(verbose_name=b'Number of weeks')),
                ('block', models.ForeignKey(related_name=b'years', to='questions.TeachingBlock')),
            ],
            options={
                'ordering': ('year', 'block__code'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Year',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('year', models.IntegerField()),
                ('stage', models.ForeignKey(to='questions.Stage')),
                ('student', models.ForeignKey(to='questions.Student')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='year',
            unique_together=set([('student', 'year')]),
        ),
        migrations.AlterUniqueTogether(
            name='teachingblockyear',
            unique_together=set([('year', 'block')]),
        ),
        migrations.AddField(
            model_name='teachingactivityyear',
            name='block_year',
            field=models.ForeignKey(related_name=b'activities', to='questions.TeachingBlockYear'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='teachingactivityyear',
            name='question_writers',
            field=models.ManyToManyField(related_name=b'assigned_activities', null=True, to='questions.Student', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='teachingactivityyear',
            name='teaching_activity',
            field=models.ForeignKey(related_name=b'years', to='questions.TeachingActivity'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='student',
            name='stages',
            field=models.ManyToManyField(to='questions.Stage', through='questions.Year'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='student',
            name='user',
            field=models.OneToOneField(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='reason',
            name='creator',
            field=models.ForeignKey(related_name=b'reasons', to='questions.Student'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='reason',
            name='related_object_content_type',
            field=models.ForeignKey(blank=True, to='contenttypes.ContentType', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quizspecification',
            name='block',
            field=models.ForeignKey(blank=True, to='questions.TeachingBlock', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quizspecification',
            name='stage',
            field=models.ForeignKey(to='questions.Stage'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quizquestionspecification',
            name='quiz_specification',
            field=models.ForeignKey(related_name=b'questions', to='questions.QuizSpecification'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quizattempt',
            name='quiz_specification',
            field=models.ForeignKey(related_name=b'attempts', blank=True, to='questions.QuizSpecification', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quizattempt',
            name='student',
            field=models.ForeignKey(related_name=b'quiz_attempts', to='questions.Student'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='questionrating',
            name='student',
            field=models.ForeignKey(related_name=b'question_ratings', to='questions.Student'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='questionattempt',
            name='quiz_attempt',
            field=models.ForeignKey(related_name=b'questions', to='questions.QuizAttempt'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='question',
            name='approver',
            field=models.ForeignKey(related_name=b'assigned_questions', blank=True, to='questions.Student', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='question',
            name='creator',
            field=models.ForeignKey(related_name=b'questions_created', to='questions.Student'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='question',
            name='teaching_activity_year',
            field=models.ForeignKey(related_name=b'questions', to='questions.TeachingActivityYear'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='comment',
            name='creator',
            field=models.ForeignKey(related_name=b'comments', to='questions.Student'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='comment',
            name='question',
            field=models.ForeignKey(related_name=b'comments', to='questions.Question'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='comment',
            name='reply_to',
            field=models.ForeignKey(blank=True, to='questions.Comment', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='approvalrecord',
            name='approver',
            field=models.ForeignKey(related_name=b'approval_records', to='questions.Student'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='approvalrecord',
            name='question',
            field=models.ForeignKey(related_name=b'approval_records', to='questions.Question'),
            preserve_default=True,
        ),
        migrations.CreateModel(
            name='ApprovalDashboardSetting',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('medbank.setting', questions.models.DashboardSettingMixin),
        ),
        migrations.CreateModel(
            name='StudentDashboardSetting',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('medbank.setting', questions.models.DashboardSettingMixin),
        ),
    ]
