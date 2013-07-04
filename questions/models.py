from django.db import models
from django.dispatch import receiver
from django.contrib.auth.models import User

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
        return self.activities.filter(question_writer__isnull=False).count()

    def total_activities_count(self):
        return self.activities.count()


class TeachingActivity(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name=u'ID')
    name = models.CharField(max_length=100)
    week = models.IntegerField()
    position = models.IntegerField()
    block = models.ManyToManyField(TeachingBlock, related_name='activities')
    question_writer = models.ForeignKey(Student, blank=True, null=True)

    class Meta:
        unique_together = ('id', 'week', 'position')

    def __unicode__(self):
        return self.name

    def current_block(self):
        try:
            return self.block.get(year=datetime.datetime.now().year)
        except TeachingBlock.DoesNotExist:
            return None


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
    creator = models.ForeignKey(Student)
    teaching_activity = models.ForeignKey(TeachingActivity, related_name="questions")
    status = models.IntegerField(choices=STATUS_CHOICES, default=PENDING_STATUS)

    def approved(self):
        return self.status == self.APPROVED_STATUS

    def pending(self):
        return self.status == self.PENDING_STATUS

    def deleted(self):
        return self.status == self.DELETED_STATUS

    def options_list(self):
        l = list(json.loads(self.options).iteritems())
        l.sort(key=lambda x: x[0])
        return [j for i, j in l]

    def options_tuple(self):
        j = json.loads(self.options)
        return [(c, j[c]) for c in string.ascii_uppercase[:len(j)]]

    class Meta:
        permissions = (
            ('can_approve', 'Can approve questions'),
        )
