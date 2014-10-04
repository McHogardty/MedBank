from __future__ import unicode_literals

# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ApprovalRecord'
        db.create_table(u'questions_approvalrecord', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('approver', self.gf('django.db.models.fields.related.ForeignKey')(related_name='approval_records', to=orm['questions.Student'])),
            ('question', self.gf('django.db.models.fields.related.ForeignKey')(related_name='approval_records', to=orm['questions.Question'])),
            ('date_assigned', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('date_completed', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.IntegerField')(default=1)),
        ))
        db.send_create_signal(u'questions', ['ApprovalRecord'])


    def backwards(self, orm):
        # Deleting model 'ApprovalRecord'
        db.delete_table(u'questions_approvalrecord')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'questions.approvalrecord': {
            'Meta': {'object_name': 'ApprovalRecord'},
            'approver': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'approval_records'", 'to': u"orm['questions.Student']"}),
            'date_assigned': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_completed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'approval_records'", 'to': u"orm['questions.Question']"}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '1'})
        },
        u'questions.comment': {
            'Meta': {'object_name': 'Comment'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'comments'", 'to': u"orm['questions.Student']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'comments'", 'to': u"orm['questions.Question']"}),
            'reply_to': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['questions.Comment']", 'null': 'True', 'blank': 'True'})
        },
        u'questions.question': {
            'Meta': {'object_name': 'Question'},
            'answer': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'approver': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'questions_approved'", 'null': 'True', 'to': u"orm['questions.Student']"}),
            'body': ('django.db.models.fields.TextField', [], {}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'questions_created'", 'to': u"orm['questions.Student']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'explanation': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'options': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'requires_special_formatting': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'suitable_for_faculty': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'suitable_for_quiz': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'teaching_activity_year': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'questions'", 'to': u"orm['questions.TeachingActivityYear']"})
        },
        u'questions.questionattempt': {
            'Meta': {'object_name': 'QuestionAttempt'},
            'answer': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'confidence_rating': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'position': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attempts'", 'to': u"orm['questions.Question']"}),
            'quiz_attempt': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'questions'", 'to': u"orm['questions.QuizAttempt']"}),
            'time_taken': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'questions.questionrating': {
            'Meta': {'object_name': 'QuestionRating'},
            'date_rated': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ratings'", 'to': u"orm['questions.Question']"}),
            'rating': ('django.db.models.fields.IntegerField', [], {}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'question_ratings'", 'to': u"orm['questions.Student']"})
        },
        u'questions.quizattempt': {
            'Meta': {'object_name': 'QuizAttempt'},
            'date_submitted': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quiz_specification': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'attempts'", 'null': 'True', 'to': u"orm['questions.QuizSpecification']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '36'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'quiz_attempts'", 'to': u"orm['questions.Student']"})
        },
        u'questions.quizquestionspecification': {
            'Meta': {'object_name': 'QuizQuestionSpecification'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parameters': ('django.db.models.fields.TextField', [], {}),
            'quiz_specification': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'questions'", 'to': u"orm['questions.QuizSpecification']"}),
            'specification_type': ('django.db.models.fields.IntegerField', [], {})
        },
        u'questions.quizspecification': {
            'Meta': {'object_name': 'QuizSpecification'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '36'}),
            'stage': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['questions.Stage']"})
        },
        u'questions.reason': {
            'Meta': {'object_name': 'Reason'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reasons'", 'to': u"orm['questions.Student']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reasons_edited'", 'to': u"orm['questions.Question']"}),
            'reason_type': ('django.db.models.fields.IntegerField', [], {})
        },
        u'questions.stage': {
            'Meta': {'object_name': 'Stage'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'number': ('django.db.models.fields.IntegerField', [], {})
        },
        u'questions.student': {
            'Meta': {'object_name': 'Student'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stages': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['questions.Stage']", 'through': u"orm['questions.Year']", 'symmetrical': 'False'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True'})
        },
        u'questions.teachingactivity': {
            'Meta': {'object_name': 'TeachingActivity'},
            'activity_type': ('django.db.models.fields.IntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'reference_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'questions.teachingactivityyear': {
            'Meta': {'object_name': 'TeachingActivityYear'},
            'block_year': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'activities'", 'to': u"orm['questions.TeachingBlockYear']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'position': ('django.db.models.fields.IntegerField', [], {}),
            'question_writers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'assigned_activities'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['questions.Student']"}),
            'teaching_activity': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'years'", 'to': u"orm['questions.TeachingActivity']"}),
            'week': ('django.db.models.fields.IntegerField', [], {})
        },
        u'questions.teachingblock': {
            'Meta': {'object_name': 'TeachingBlock'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'stage': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['questions.Stage']"})
        },
        u'questions.teachingblockyear': {
            'Meta': {'unique_together': "(('year', 'block'),)", 'object_name': 'TeachingBlockYear'},
            'activity_capacity': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'block': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'years'", 'to': u"orm['questions.TeachingBlock']"}),
            'close': ('django.db.models.fields.DateField', [], {}),
            'end': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'release_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'sign_up_mode': ('django.db.models.fields.IntegerField', [], {}),
            'start': ('django.db.models.fields.DateField', [], {}),
            'weeks': ('django.db.models.fields.IntegerField', [], {}),
            'year': ('django.db.models.fields.IntegerField', [], {})
        },
        u'questions.year': {
            'Meta': {'unique_together': "(('student', 'year'),)", 'object_name': 'Year'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stage': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['questions.Stage']"}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['questions.Student']"}),
            'year': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['questions']