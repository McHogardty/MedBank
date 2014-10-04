from __future__ import unicode_literals

# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Stage'
        db.create_table(u'questions_stage', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('number', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'questions', ['Stage'])

        # Adding model 'Year'
        db.create_table(u'questions_year', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('stage', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['questions.Stage'])),
            ('student', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['questions.Student'])),
            ('year', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'questions', ['Year'])

        # Adding unique constraint on 'Year', fields ['student', 'year']
        db.create_unique(u'questions_year', ['student_id', 'year'])

        # Adding model 'Student'
        db.create_table(u'questions_student', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True)),
        ))
        db.send_create_signal(u'questions', ['Student'])

        # Adding model 'TeachingBlock'
        db.create_table(u'questions_teachingblock', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('year', self.gf('django.db.models.fields.IntegerField')()),
            ('stage', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['questions.Stage'])),
            ('number', self.gf('django.db.models.fields.IntegerField')()),
            ('start', self.gf('django.db.models.fields.DateField')()),
            ('end', self.gf('django.db.models.fields.DateField')()),
            ('close', self.gf('django.db.models.fields.DateField')()),
            ('release_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('activity_capacity', self.gf('django.db.models.fields.IntegerField')(default=2)),
            ('sign_up_mode', self.gf('django.db.models.fields.IntegerField')()),
            ('weeks', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'questions', ['TeachingBlock'])

        # Adding unique constraint on 'TeachingBlock', fields ['year', 'number']
        db.create_unique(u'questions_teachingblock', ['year', 'number'])

        # Adding model 'TeachingActivity'
        db.create_table(u'questions_teachingactivity', (
            ('id', self.gf('django.db.models.fields.IntegerField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('week', self.gf('django.db.models.fields.IntegerField')()),
            ('position', self.gf('django.db.models.fields.IntegerField')()),
            ('activity_type', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'questions', ['TeachingActivity'])

        # Adding unique constraint on 'TeachingActivity', fields ['id', 'week', 'position']
        db.create_unique(u'questions_teachingactivity', ['id', 'week', 'position'])

        # Adding M2M table for field block on 'TeachingActivity'
        m2m_table_name = db.shorten_name(u'questions_teachingactivity_block')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('teachingactivity', models.ForeignKey(orm[u'questions.teachingactivity'], null=False)),
            ('teachingblock', models.ForeignKey(orm[u'questions.teachingblock'], null=False))
        ))
        db.create_unique(m2m_table_name, ['teachingactivity_id', 'teachingblock_id'])

        # Adding M2M table for field question_writers on 'TeachingActivity'
        m2m_table_name = db.shorten_name(u'questions_teachingactivity_question_writers')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('teachingactivity', models.ForeignKey(orm[u'questions.teachingactivity'], null=False)),
            ('student', models.ForeignKey(orm[u'questions.student'], null=False))
        ))
        db.create_unique(m2m_table_name, ['teachingactivity_id', 'student_id'])

        # Adding model 'Question'
        db.create_table(u'questions_question', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('body', self.gf('django.db.models.fields.TextField')()),
            ('options', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('answer', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('explanation', self.gf('django.db.models.fields.TextField')()),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(related_name='questions_created', to=orm['questions.Student'])),
            ('approver', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='questions_approved', null=True, to=orm['questions.Student'])),
            ('teaching_activity', self.gf('django.db.models.fields.related.ForeignKey')(related_name='questions', to=orm['questions.TeachingActivity'])),
            ('status', self.gf('django.db.models.fields.IntegerField')(default=1)),
        ))
        db.send_create_signal(u'questions', ['Question'])

        # Adding model 'Reason'
        db.create_table(u'questions_reason', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('body', self.gf('django.db.models.fields.TextField')()),
            ('question', self.gf('django.db.models.fields.related.ForeignKey')(related_name='reasons_edited', to=orm['questions.Question'])),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(related_name='reasons', to=orm['questions.Student'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'questions', ['Reason'])

        # Adding model 'Comment'
        db.create_table(u'questions_comment', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('body', self.gf('django.db.models.fields.TextField')()),
            ('question', self.gf('django.db.models.fields.related.ForeignKey')(related_name='comments', to=orm['questions.Question'])),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(related_name='comments', to=orm['questions.Student'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('reply_to', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['questions.Comment'], null=True, blank=True)),
        ))
        db.send_create_signal(u'questions', ['Comment'])


    def backwards(self, orm):
        # Removing unique constraint on 'TeachingActivity', fields ['id', 'week', 'position']
        db.delete_unique(u'questions_teachingactivity', ['id', 'week', 'position'])

        # Removing unique constraint on 'TeachingBlock', fields ['year', 'number']
        db.delete_unique(u'questions_teachingblock', ['year', 'number'])

        # Removing unique constraint on 'Year', fields ['student', 'year']
        db.delete_unique(u'questions_year', ['student_id', 'year'])

        # Deleting model 'Stage'
        db.delete_table(u'questions_stage')

        # Deleting model 'Year'
        db.delete_table(u'questions_year')

        # Deleting model 'Student'
        db.delete_table(u'questions_student')

        # Deleting model 'TeachingBlock'
        db.delete_table(u'questions_teachingblock')

        # Deleting model 'TeachingActivity'
        db.delete_table(u'questions_teachingactivity')

        # Removing M2M table for field block on 'TeachingActivity'
        db.delete_table(db.shorten_name(u'questions_teachingactivity_block'))

        # Removing M2M table for field question_writers on 'TeachingActivity'
        db.delete_table(db.shorten_name(u'questions_teachingactivity_question_writers'))

        # Deleting model 'Question'
        db.delete_table(u'questions_question')

        # Deleting model 'Reason'
        db.delete_table(u'questions_reason')

        # Deleting model 'Comment'
        db.delete_table(u'questions_comment')


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
            'status': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'teaching_activity': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'questions'", 'to': u"orm['questions.TeachingActivity']"})
        },
        u'questions.reason': {
            'Meta': {'object_name': 'Reason'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reasons'", 'to': u"orm['questions.Student']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reasons_edited'", 'to': u"orm['questions.Question']"})
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
            'Meta': {'unique_together': "(('id', 'week', 'position'),)", 'object_name': 'TeachingActivity'},
            'activity_type': ('django.db.models.fields.IntegerField', [], {}),
            'block': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'activities'", 'symmetrical': 'False', 'to': u"orm['questions.TeachingBlock']"}),
            'id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'position': ('django.db.models.fields.IntegerField', [], {}),
            'question_writers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['questions.Student']", 'null': 'True', 'blank': 'True'}),
            'week': ('django.db.models.fields.IntegerField', [], {})
        },
        u'questions.teachingblock': {
            'Meta': {'unique_together': "(('year', 'number'),)", 'object_name': 'TeachingBlock'},
            'activity_capacity': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'close': ('django.db.models.fields.DateField', [], {}),
            'end': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'number': ('django.db.models.fields.IntegerField', [], {}),
            'release_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'sign_up_mode': ('django.db.models.fields.IntegerField', [], {}),
            'stage': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['questions.Stage']"}),
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