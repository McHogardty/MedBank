from __future__ import unicode_literals

# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'TeachingBlock', fields ['year', 'number']
        db.delete_unique(u'questions_teachingblock', ['year', 'number'])

        # Deleting field 'TeachingBlock.year'
        db.delete_column(u'questions_teachingblock', 'year')

        # Deleting field 'TeachingBlock.close'
        db.delete_column(u'questions_teachingblock', 'close')

        # Deleting field 'TeachingBlock.end'
        db.delete_column(u'questions_teachingblock', 'end')

        # Deleting field 'TeachingBlock.release_date'
        db.delete_column(u'questions_teachingblock', 'release_date')

        # Deleting field 'TeachingBlock.start'
        db.delete_column(u'questions_teachingblock', 'start')

        # Deleting field 'TeachingBlock.sign_up_mode'
        db.delete_column(u'questions_teachingblock', 'sign_up_mode')

        # Deleting field 'TeachingBlock.weeks'
        db.delete_column(u'questions_teachingblock', 'weeks')

        # Deleting field 'TeachingBlock.activity_capacity'
        db.delete_column(u'questions_teachingblock', 'activity_capacity')

        # Removing M2M table for field block on 'TeachingActivity'
        m2m_table_name = db.shorten_name(u'questions_teachingactivity_block')
        db.delete_unique(m2m_table_name, ['teachingactivity_id', 'teachingblock_id'])
        db.delete_table(m2m_table_name)

        # Renaming M2M table for field block_new on 'TeachingActivity'
        m2m_first_table_name = db.shorten_name(u'questions_teachingactivity_block_new')
        m2m_second_table_name = db.shorten_name(u'questions_teachingactivity_block')
        db.rename_table(m2m_first_table_name, m2m_second_table_name)


    def backwards(self, orm):
        # Renaming M2M table for field block on 'TeachingActivity'
        m2m_first_table_name = db.shorten_name(u'questions_teachingactivity_block')
        m2m_second_table_name = db.shorten_name(u'questions_teachingactivity_block_new')
        db.rename_table(m2m_first_table_name, m2m_second_table_name)

        # Adding M2M table for field block on 'TeachingActivity'
        m2m_table_name = db.shorten_name(u'questions_teachingactivity_block')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('teachingactivity', models.ForeignKey(orm[u'questions.teachingactivity'], null=False)),
            ('teachingblock', models.ForeignKey(orm[u'questions.teachingblockyear'], null=False))
        ))
        db.create_unique(m2m_table_name, ['teachingactivity_id', 'teachingblock_id'])


        # Adding field 'TeachingBlock.year'
        db.add_column(u'questions_teachingblock', 'year',
                      self.gf('django.db.models.fields.IntegerField')(default=2013),
                      keep_default=False)

        # Adding field 'TeachingBlock.close'
        db.add_column(u'questions_teachingblock', 'close',
                      self.gf('django.db.models.fields.DateField')(default=datetime.datetime(2014, 1, 5, 0, 0)),
                      keep_default=False)

        # Adding field 'TeachingBlock.end'
        db.add_column(u'questions_teachingblock', 'end',
                      self.gf('django.db.models.fields.DateField')(default=datetime.datetime(2014, 1, 5, 0, 0)),
                      keep_default=False)

        # Adding field 'TeachingBlock.release_date'
        db.add_column(u'questions_teachingblock', 'release_date',
                      self.gf('django.db.models.fields.DateField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'TeachingBlock.start'
        db.add_column(u'questions_teachingblock', 'start',
                      self.gf('django.db.models.fields.DateField')(default=datetime.datetime(2014, 1, 5, 0, 0)),
                      keep_default=False)

        # Adding field 'TeachingBlock.sign_up_mode'
        db.add_column(u'questions_teachingblock', 'sign_up_mode',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)

        # Adding field 'TeachingBlock.weeks'
        db.add_column(u'questions_teachingblock', 'weeks',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)

        # Adding field 'TeachingBlock.activity_capacity'
        db.add_column(u'questions_teachingblock', 'activity_capacity',
                      self.gf('django.db.models.fields.IntegerField')(default=2),
                      keep_default=False)

        # Adding unique constraint on 'TeachingBlock', fields ['year', 'number']
        db.create_unique(u'questions_teachingblock', ['year', 'number'])


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
            'block': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'activities'", 'symmetrical': 'False', 'to': u"orm['questions.TeachingBlockYear']"}),
            'id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'position': ('django.db.models.fields.IntegerField', [], {}),
            'question_writers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['questions.Student']", 'null': 'True', 'blank': 'True'}),
            'week': ('django.db.models.fields.IntegerField', [], {})
        },
        u'questions.teachingblock': {
            'Meta': {'object_name': 'TeachingBlock'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'number': ('django.db.models.fields.IntegerField', [], {}),
            'stage': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['questions.Stage']"})
        },
        u'questions.teachingblockyear': {
            'Meta': {'unique_together': "(('year', 'block'),)", 'object_name': 'TeachingBlockYear'},
            'activity_capacity': ('django.db.models.fields.IntegerField', [], {'default': '2', 'null': 'True'}),
            'block': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['questions.TeachingBlock']", 'null': 'True'}),
            'close': ('django.db.models.fields.DateField', [], {}),
            'end': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'release_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'sign_up_mode': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'start': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            'weeks': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'year': ('django.db.models.fields.IntegerField', [], {'null': 'True'})
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