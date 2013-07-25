from django.db import models
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.conf import settings

import json
import datetime
import string

STAGE_ONE = 0
STAGE_TWO = 1
STAGE_THREE = 2
STAGE_CHOICES = (
    (STAGE_ONE, "Stage 1"),
    (STAGE_TWO, "Stage 2"),
    (STAGE_THREE, "Stage 3"),
)


class Stage(models.Model):
    number = models.IntegerField(choices=STAGE_CHOICES)


class Student(models.Model):
    user = models.OneToOneField(User)
    stage = models.IntegerField(choices=STAGE_CHOICES)

    def __unicode__(self):
        return self.user.username


@receiver(models.signals.post_save, sender=User)
def user_created(sender, **kwargs):
    if kwargs['created']:
        s = Student()
        s.user = kwargs['instance']
        s.stage = STAGE_ONE
        s.save()


class TeachingBlock(models.Model):
    name = models.CharField(max_length=50)
    year = models.IntegerField()
    stage = models.IntegerField(choices=STAGE_CHOICES)
    number = models.IntegerField(verbose_name=u'Block number')
    start = models.DateField(verbose_name=u'Start date')
    end = models.DateField(verbose_name=u'End date')
    close = models.DateField(verbose_name=u'Close date', blank=True)

    class Meta:
        unique_together = ('year', 'number')

    def __unicode__(self):
        return "%s, %d" % (self.name, self.year)

    def assigned_activities_count(self):
        return self.activities.exclude(question_writers=None).count()

    def total_activities_count(self):
        return self.activities.count()

    def has_started(self):
        return self.start <= datetime.datetime.now().date()

    def can_write_questions(self):
        return self.start <= datetime.datetime.now().date() <= self.end
    can_write_questions = property(can_write_questions)

    def questions_need_approval(self):
        return bool(self.activities.filter(questions__status=Question.PENDING_STATUS).count())

    def questions_approved_count(self):
        return Question.objects.filter(teaching_activity__block=self, status=Question.APPROVED_STATUS).count()

    def questions_pending_count(self):
        return Question.objects.filter(teaching_activity__block=self, status=Question.PENDING_STATUS).count()


class TeachingActivity(models.Model):
    LECTURE_TYPE = 1
    PBL_TYPE = 0
    PRACTICAL_TYPE = 3
    SEMINAR_TYPE = 4
    TYPE_CHOICES = (
        (LECTURE_TYPE, 'Lecture'),
        (PBL_TYPE, 'PBL'),
        (PRACTICAL_TYPE, 'Practical'),
        (SEMINAR_TYPE, 'Seminar'),
    )
    id = models.IntegerField(primary_key=True, verbose_name=u'ID')
    name = models.CharField(max_length=100)
    week = models.IntegerField()
    position = models.IntegerField()
    block = models.ManyToManyField(TeachingBlock, related_name='activities')
    question_writers = models.ManyToManyField(Student, blank=True, null=True)
    activity_type = models.IntegerField(choices=TYPE_CHOICES)

    class Meta:
        unique_together = ('id', 'week', 'position')

    def __unicode__(self):
        return self.name

    def current_block(self):
        try:
            return self.block.get(year=datetime.datetime.now().year)
        except TeachingBlock.DoesNotExist:
            return None

    def enough_writers(self):
        return self.question_writers.count() >= settings.USERS_PER_ACTIVITY

    def has_writers(self):
        return bool(self.question_writers.count())

    def has_questions(self):
        return bool(self.questions.count())

    def questions_left_for(self, user):
        # Max number of questions to write.
        m = settings.QUESTIONS_PER_USER
        # Current question count.
        c = self.questions.filter(creator=user.student).count()
        # User is a question writer?
        u = self.question_writers.filter(id=user.student.id).count()
        r = 0

        if c < m and u:
            r += m - c

        return r

    def questions_for(self, user):
        r = self.questions.all()
        if not user.has_perm('questions.can.approve'):
            r = r.filter(
                models.Q(creator=user.student) | models.Q(status=Question.APPROVED_STATUS)
            )
        return r


class Question(models.Model):
    APPROVED_STATUS = 0
    PENDING_STATUS = 1
    DELETED_STATUS = 2
    STATUS_CHOICES = (
        (APPROVED_STATUS, 'Approved'),
        (PENDING_STATUS, 'Pending'),
        (DELETED_STATUS, 'Deleted')
    )
    body = models.TextField()
    options = models.TextField(blank=True)
    answer = models.CharField(max_length=1)
    explanation = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(Student, related_name="questions_created")
    approver = models.ForeignKey(Student, null=True, blank=True, related_name="questions_approved")
    teaching_activity = models.ForeignKey(TeachingActivity, related_name="questions")
    status = models.IntegerField(choices=STATUS_CHOICES, default=PENDING_STATUS)

    def approved(self):
        return self.status == self.APPROVED_STATUS
    approved = property(approved)

    def pending(self):
        return self.status == self.PENDING_STATUS
    pending = property(pending)

    def deleted(self):
        return self.status == self.DELETED_STATUS
    deleted = property(deleted)

    def options_list(self):
        l = list(json.loads(self.options).iteritems())
        l.sort(key=lambda x: x[0])
        return [j for i, j in l]

    def options_tuple(self):
        j = json.loads(self.options)
        return [(c, j[c]) for c in string.ascii_uppercase[:len(j)]]

    def user_is_creator(self, user):
        return user.has_perm('questions.can_approve') or user.student == self.creator

    class Meta:
        permissions = (
            ('can_approve', 'Can approve questions'),
        )
