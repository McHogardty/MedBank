from django.db import models
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.conf import settings

import json
import datetime
import string


class classproperty(property):
    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()


class Stage(models.Model):
    stage_cache = {}

    number = models.IntegerField()

    def __unicode__(self):
        return u"Stage %s" % (self.number, )

    @classmethod
    def get_stage(self, n):
        if n in self.stage_cache:
            return self.stage_cache[n]
        else:
            s = self.objects.get(number=n)
            self.stage_cache[n] = s
            return s

    @classmethod
    def stage_one(self):
        return self.get_stage(1)
    STAGE_ONE = classproperty(stage_one)

    @classmethod
    def stage_two(self):
        return self.get_stage(2)
    STAGE_TWO = classproperty(stage_two)

    @classmethod
    def stage_three(self):
        return self.get_stage(3)
    STAGE_THREE = classproperty(stage_three)


class Student(models.Model):
    user = models.OneToOneField(User)
    stages = models.ManyToManyField(Stage, through='questions.Year')

    def __unicode__(self):
        return self.user.username

    def get_current_stage(self):
        return self.stages.get(year__year__exact=datetime.datetime.now().year)


class Year(models.Model):
    stage = models.ForeignKey(Stage)
    student = models.ForeignKey(Student)
    year = models.IntegerField()

    class Meta:
        unique_together = ('student', 'year')

    def __unicode__(self):
        return "%s: %s, %d" % (self.student, self.stage, self.year)


@receiver(models.signals.post_save, sender=User)
def user_created(sender, **kwargs):
    if kwargs['created']:
        s = Student()
        s.user = kwargs['instance']
        s.save()
        y = Year()
        y.student = s
        if kwargs['instance'].username == 'michael':
            y.stage = Stage.STAGE_ONE
        else:
            y.stage = kwargs['instance']._stage
        y.year = datetime.datetime.now().year
        y.save()


class TeachingBlock(models.Model):
    name = models.CharField(max_length=50)
    year = models.IntegerField()
    stage = models.ForeignKey(Stage)
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

    def has_ended(self):
        return self.end <= datetime.datetime.now().date()

    def can_write_questions(self):
        return self.start <= datetime.datetime.now().date() <= self.close
    can_write_questions = property(can_write_questions)

    def email_sent(self):
        return False
    email_sent = property(email_sent)

    def can_sign_up(self):
        return self.start <= datetime.datetime.now().date() <= self.end
    can_sign_up = property(can_sign_up)

    def questions_need_approval(self):
        return bool(self.activities.filter(questions__status=Question.PENDING_STATUS).count())

    def questions_approved_count(self):
        return Question.objects.filter(teaching_activity__block=self, status=Question.APPROVED_STATUS).count()

    def questions_pending_count(self):
        return Question.objects.filter(teaching_activity__block=self, status=Question.PENDING_STATUS).count()

    def questions_flagged_count(self):
        return Question.objects.filter(teaching_activity__block=self, status=Question.FLAGGED_STATUS).count()

    def question_count_for_student(self, s):
        return Question.objects.filter(teaching_activity__block=self, creator=s).count()


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
        c = self.questions.filter(creator=user.student).exclude(status=Question.DELETED_STATUS).count()
        # User is a question writer?
        u = self.question_writers.filter(id=user.student.id).count()
        r = 0

        if c < m and u:
            r += m - c

        return r

    def questions_for(self, user):
        r = self.questions.exclude(status=Question.DELETED_STATUS)
        if not user.has_perm('questions.can.approve'):
            r = r.filter(
                models.Q(creator=user.student) | models.Q(status=Question.APPROVED_STATUS)
            )
        return r

    def can_sign_up(self):
        return self.current_block().can_sign_up
    can_sign_up = property(can_sign_up)


class Question(models.Model):
    APPROVED_STATUS = 0
    PENDING_STATUS = 1
    DELETED_STATUS = 2
    FLAGGED_STATUS = 3
    STATUS_CHOICES = (
        (APPROVED_STATUS, 'Approved'),
        (PENDING_STATUS, 'Pending'),
        (DELETED_STATUS, 'Deleted'),
        (FLAGGED_STATUS, 'Flagged')
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

    def __init__(self, *args, **kwargs):
        super(Question, self).__init__(*args, **kwargs)
        # Adds properties to the model to check the status, e.g. self.approved, self.flagged
        for k in self.__class__.__dict__.keys():
            if not "_STATUS" in k or hasattr(self, k.split("_")[0].lower()):
                continue

            self.add_model_status_property_method(k)

    def add_model_status_property_method(self, k):
        def check_status_function(self):
            return self.status == getattr(self, k)

        setattr(self.__class__, k.split("_")[0].lower(), property(check_status_function))

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
