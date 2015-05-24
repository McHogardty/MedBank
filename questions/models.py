from __future__ import division

from django.db import models
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.conf import settings
from django.utils.html import format_html
from django.utils.datastructures import SortedDict
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.template.defaultfilters import linebreaksbr
from django.utils import timezone

from medbank.models import Setting

import reversion
import json
import datetime
import string
import random
import hashlib
import collections
from HTMLParser import HTMLParser
from htmlentitydefs import name2codepoint, codepoint2name
import bs4

def int_to_base(x, base, places=0):
    """ A method which converts any base 10 integer (x) into its representation in a base using the lowercase alphabet in a fixed number of characters (places)."""
    digs = string.lowercase

    digits = []
    while x:
        digits.append(digs[x % base])
        x //= base
    if places and len(digits) > places: raise ValueError("There must be enough places to represent the number.")

    while places and len(digits) < places:
        digits.append(digs[0])

    digits.reverse()
    return ''.join(digits)


def hex_to_base_26(hex):
    """A method which converts a hexadecimal string (hex) into its base 26 representation using the lowercase alphabet."""
    return int_to_base(int(hex, 16), 26, places=36)


class classproperty(property):
    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()


class ObjectCacheMixin(object):
    def set_cache_value(self, attribute, value):
        setattr(self, attribute, value)

    def get_cache_value(self, attribute):
        if hasattr(self, attribute):
            return getattr(self, attribute)


class Stage(models.Model):
    number = models.IntegerField()
    name = models.CharField(max_length=100)
    sort_index = models.IntegerField()

    class Meta:
        ordering = ('sort_index',)

    def __unicode__(self):
        return self.name


class Year(models.Model):
    stage = models.ForeignKey(Stage)
    student = models.ForeignKey('questions.Student')
    year = models.IntegerField()

    class Meta:
        unique_together = ('student', 'year')

    def __unicode__(self):
        return "%s: %s, %d" % (self.student, self.stage, self.year)


class StudentManager(models.Manager):
    def get_from_kwargs(self, **kwargs):
        return self.get_queryset().select_related('user').get(user__username=kwargs.get('username'))


class Student(models.Model, ObjectCacheMixin):
    user = models.OneToOneField(User)
    stages = models.ManyToManyField(Stage, through='questions.Year')

    objects = StudentManager()

    def __unicode__(self):
        return self.user.username

    def get_url_kwargs(self):
        return {'username': self.user.username, }

    def get_absolute_url(self):
        return reverse('student-view', kwargs=self.get_url_kwargs())

    def has_perm(self, *args, **kwargs):
        return self.user.has_perm(*args, **kwargs)

    def all_assigned_activities(self):
        ACTIVITIES_CACHE_ATTR = "_assigned_activities"
        if hasattr(self, ACTIVITIES_CACHE_ATTR):
            return getattr(self, ACTIVITIES_CACHE_ATTR)

        activities = self.assigned_activities.all()
        setattr(self, ACTIVITIES_CACHE_ATTR, activities)
        return activities

    def add_stage(self, stage, year=datetime.datetime.now().year):
        try:
            y = Year.objects.get(student=self, year__exact=datetime.datetime.now().year)
        except Year.DoesNotExist:
            y = Year()
            y.student = self
            y.year = year
        y.stage = stage

        y.save()
        if hasattr(self, "_cached_stage"):
            del self._cached_stage

    def get_current_stage(self):
        if not hasattr(self, "_cached_stage"):
            self._cached_stage = self.stages.get(year__year__exact=datetime.datetime.now().year)

        return self._cached_stage

    def get_all_stages(self):
        return self.stages.distinct()

    def get_previous_stages(self):
        return self.stages.filter(sort_index__lt=self.get_current_stage().sort_index)

    def questions_due_soon_count(self):
        writing_periods_for_student = QuestionWritingPeriod.objects.writing_periods_for_student(self)
        count = self.assigned_activities.filter(block_week__writing_period__in=writing_periods_for_student, block_week__writing_period__close__range=[datetime.datetime.now(), datetime.datetime.now()+datetime.timedelta(weeks=1)]).count() * settings.QUESTIONS_PER_USER
        return count

    def future_block_count(self):
        return TeachingBlockYear.objects.get_open_blocks_assigned_to_student(self).count()

    def latest_quiz_attempt(self):
        return self.quiz_attempts.latest('date_submitted')


@receiver(models.signals.post_save, sender=User)
def user_created(sender, **kwargs):
    if kwargs['created'] and not kwargs['raw']:
        s = Student()
        s.user = kwargs['instance']
        s.save()
        y = Year()
        y.student = s
        y.stage = kwargs['instance']._stage
        y.year = datetime.datetime.now().year
        y.save()


class TeachingBlockManager(models.Manager):
    def get_from_kwargs(self, **kwargs):
        return self.get_queryset().get(code=kwargs.get('code'))

    def get_visible_blocks_for_student(self, student):
        block_years = TeachingBlockYear.objects.get_visible_block_years_for_student(student)
        return self.get_queryset().filter(years__in=block_years).distinct()


class TeachingBlock(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=10)
    sort_index = models.IntegerField(db_index=True)
    code_includes_week = models.BooleanField(default=True)

    objects = TeachingBlockManager()

    class Meta:
        ordering = ('sort_index',)

    def __unicode__(self):
        return self.name

    def filename(self):
        spaceless = "".join(self.name.split())
        commaless = "".join(spaceless.split(","))
        return commaless

    def get_url_kwargs(self):
        return {'code': self.code, }

    def get_download_url(self):
        return reverse('block-download', kwargs=self.get_url_kwargs())

    def get_admin_year_selection_url(self):
        return reverse('block-admin-select', kwargs=self.get_url_kwargs())

    def get_new_year_creation_url(self):
        return reverse('block-year-new', kwargs=self.get_url_kwargs())

    def get_admin_url(self):
        return reverse('block-admin', kwargs=self.get_url_kwargs())

    @classmethod
    def get_block_creation_url(self):
        return reverse('block-new')

    def get_latest_year(self):
        return self.years.latest("year")

    def latest_writing_period_for_student(self, student):
        if student.user.is_superuser:
            writing_periods = QuestionWritingPeriod.objects.filter(block_year__block=self)
        else:
            writing_periods = QuestionWritingPeriod.objects.writing_periods_for_student(student).filter(block_year__block=self)
        return writing_periods.last()

    def is_viewable_by(self, student):
        if student.user.is_superuser: return True

        if self.approved_questions_are_viewable_by(student):
            return True

        # A student can view a block open for signup if it is in their stage in the current year.
        open_block_years = TeachingBlockYear.objects.get_open_block_years_for_student(student)
        if open_block_years.filter(block=self).exists():
            # There is an open block year for this block to which the student has access.
            return True

        return False

    def is_available_for_download_by(self, student):
        return self.approved_questions_are_viewable_by(student)

    def approved_questions_are_viewable_by(self, student):
        if student.user.is_superuser: return True

        # A student can view approved questions if they have written questions for the block at some point.
        block_years = self.years.filter(writing_periods__weeks__activities__questions__creator=student) \
                                .annotate(questions_written=models.Count('writing_periods__weeks__activities__questions')) \
                                .filter(questions_written__gte=settings.QUESTIONS_PER_USER)

        return block_years.exists()

    def name_for_form_fields(self):
        return self.name.replace(" ", "_").replace(",", "").lower()


class TeachingBlockYearManager(models.Manager):
    def get_from_kwargs(self, **kwargs):
        return self.get_queryset().select_related().get(block__code=kwargs.get("code"), year=kwargs.get("year"))

    def get_blocks_for_student(self, student):
        # Returns only the blocks which the student has access to write for.
        queryset = self.get_queryset()

        # If the user is a superuser, return all open blocks.
        if not student.user.is_superuser:
            # First, look for all TeachingBlockYears with a stage which the student was in at any point.
            # Then, get only those TeachingBlockYears where the student was in that stage during the same year.
            # We need to do them in the same filter command, otherwise the two restrictions won't apply to the same Year object.
            queryset = queryset.filter(writing_periods__stage__year__student=student, writing_periods__stage__year__year=models.F('year'))

        return queryset

    def get_open_block_years_for_student(self, student):
        queryset = self.get_blocks_for_student(student)

        # Return only the open ones.
        now = datetime.datetime.now()
        return queryset.filter(writing_periods__end__gte=now, writing_periods__start__lte=now).distinct()

    def get_visible_block_years_for_student(self, student):
        blocks = TeachingBlock.objects.all()

        block_years = self.get_queryset().annotate(latest_release_year=models.Max('block__years__year')).filter(year__lte=models.F('latest_release_year'))

        if not student.user.is_superuser:
            block_years = block_years.filter(writing_periods__weeks__activities__questions__creator=student) \
                                    .annotate(questions_written=models.Count("writing_periods__weeks__activities__questions")) \
                                    .filter(questions_written__gte=settings.QUESTIONS_PER_USER) \
                                    .distinct()

        return block_years

    def get_latest_visible_block_years_for_student(self, student):
        block_years = self.get_visible_block_years_for_student(student)

        block_years = block_years.filter(year=models.F('latest_release_year'))

        return block_years

    def get_open_blocks_assigned_to_student(self, student):
        current_date = datetime.datetime.now()
        open_blocks = self.get_open_block_years_for_student(student)

        return open_blocks.filter(writing_periods__weeks__activities__question_writers=student)


class TeachingBlockYear(models.Model, ObjectCacheMixin):
    year = models.IntegerField()
    block = models.ForeignKey(TeachingBlock, related_name="years")

    objects = TeachingBlockYearManager()

    class Meta:
        unique_together = ('year', 'block')
        ordering = ('year', 'block__sort_index')

    def __unicode__(self):
        return "%s, %d" % (self.block, self.year)

    def filename(self):
        spaceless = "".join(self.block.name.split())
        commaless = "".join(spaceless.split(","))
        return "%s%d" % (commaless, self.year)

    def get_url_kwargs(self):
        return {'code': self.block.code, 'year': self.year}

    def get_activity_display_url(self):
        return reverse('block-activities', kwargs=self.get_url_kwargs())

    def get_activity_upload_url(self):
        return reverse('block-activity-upload', kwargs=self.get_url_kwargs())

    def get_activity_upload_submit_url(self):
        return reverse('block-activity-upload-submit', kwargs=self.get_url_kwargs())

    def get_activity_upload_confirm_url(self):
        return reverse('block-activity-upload-confirm', kwargs=self.get_url_kwargs())

    def get_admin_url(self):
        return "%s?year=%s" % (self.block.get_admin_url(), self.year)

    def get_edit_url(self):
        return reverse('block-edit', kwargs=self.get_url_kwargs())

    def get_download_url(self):
        return reverse('block-download', kwargs=self.get_url_kwargs())

    @classmethod
    def get_visible_block_display_url(cls):
        return reverse('block-visible-list')

    @classmethod
    def get_open_block_display_url(cls):
        return reverse('block-open-list')

    def name_for_form_fields(self):
        return self.block.name_for_form_fields()

    def writing_period_for_student(self, student):
        WRITING_PERIOD_CACHE = "_writing_period_cached"

        value = self.get_cache_value(WRITING_PERIOD_CACHE)
        if value: return value

        try:
            writing_period_for_student = self.writing_periods.get(stage__year__student=student, stage__year__year=self.year)
        except QuestionWritingPeriod.DoesNotExist:
            writing_period_for_student = None


        self.set_cache_value(WRITING_PERIOD_CACHE, writing_period_for_student)
        return writing_period_for_student

    def student_is_eligible_for_sign_up(self, student):
        return bool(self.writing_period_for_student(student)) and self.writing_period_for_student(student).can_sign_up

    def student_can_write_questions(self, student):
        return bool(self.writing_period_for_student(student)) and self.writing_period_for_student(student).can_write_questions

    def questions_for_status(self, status):
        return Question.objects.filter(teaching_activity_year__block_week__writing_period__block_year=self, status=status)

    def approved_questions(self):
        return self.questions_for_status(status=Question.APPROVED_STATUS)

    def questions_approved_count(self):
        return self.approved_questions().count()

    def question_count_for_student(self, s):
        return Question.objects.filter(teaching_activity_year__block_week__writing_period__block_year=self, creator=s).count()

    def questions_written_for_student(self, s):
        return Question.objects.filter(teaching_activity_year__block_week__writing_period__block_year=self, creator=s).exists()


class QuestionWritingPeriodManager(models.Manager):
    def get_from_kwargs(self, **kwargs):
        queryset = super(QuestionWritingPeriodManager, self).get_queryset().select_related()

        if 'code' and 'year' in kwargs:
            queryset = self.get_queryset().filter(block_year__block__code=kwargs.get("code"), block_year__year=kwargs.get("year"))

        return queryset.get(id=kwargs.get('id'))

    def writing_periods_for_student(self, student):
        queryset = self.get_queryset()

        # The student must be assigned to the same stage as the writing period in the same year as the block year for which the writing period exists.
        queryset = queryset.filter(stage__year__student=student, stage__year__year=models.F('block_year__year'))

        return queryset


class QuestionWritingPeriod(models.Model):
    block_year = models.ForeignKey(TeachingBlockYear, related_name='writing_periods')
    stage = models.ForeignKey(Stage, related_name='writing_periods')
    activity_capacity = models.IntegerField(verbose_name='Maximum users per activity', default=2)
    start = models.DateField(verbose_name='Start date')
    end = models.DateField(verbose_name='End date')
    close = models.DateField(verbose_name='Close date')
    release_date = models.DateField(verbose_name='Release date', blank=True, null=True)

    objects = QuestionWritingPeriodManager()

    class Meta:
        unique_together = ('block_year', 'stage')
        ordering = ('block_year', 'stage')

    def __str__(self):
        return "%s, %s" % (self.block_year, self.stage)

    def get_url_kwargs(self):
        return {'code': self.block_year.block.code, 'year': self.block_year.year, 'id': self.id}

    def get_activity_upload_url(self):
        return reverse('block-admin-period-upload', kwargs=self.get_url_kwargs())

    def get_activity_upload_submit_url(self):
        return reverse('block-admin-period-upload-submit', kwargs=self.get_url_kwargs())

    def get_activity_upload_confirm_url(self):
        return reverse('block-admin-period-upload-confirm', kwargs=self.get_url_kwargs())

    def get_edit_url(self):
        return reverse('block-admin-period-edit', kwargs=self.get_url_kwargs())

    def has_started(self):
        return self.start <= datetime.datetime.now().date()

    def has_ended(self):
        return self.end < datetime.datetime.now().date()

    def has_closed(self):
        return self.close < datetime.datetime.now().date()

    def can_write_questions(self):
        return self.start <= datetime.datetime.now().date() <= self.close
    can_write_questions = property(can_write_questions)

    def can_sign_up(self):
        return self.has_started() and not self.has_ended()
    can_sign_up = property(can_sign_up)

    def assigned_activities_count(self):
        return TeachingActivityYear.objects.filter(block_week__writing_period=self).exclude(question_writers=None).count()

    def total_activities_count(self):
        return TeachingActivityYear.objects.filter(block_week__writing_period=self).count()

    def assigned_users_count(self):
        return Student.objects.filter(assigned_activities__block_week__writing_period=self).distinct().count()

    def total_questions_count(self):
        return Question.objects.filter(teaching_activity_year__block_week__writing_period=self).exclude(status=Question.DELETED_STATUS).count()



class TeachingActivityManager(models.Manager):
    def get_from_kwargs(self, **kwargs):
        return self.get_queryset().get(reference_id=kwargs.get("reference_id"))


class TeachingActivity(models.Model, ObjectCacheMixin):
    LECTURE_TYPE = 1
    PBL_TYPE = 0
    PRACTICAL_TYPE = 3
    SEMINAR_TYPE = 4
    WEEK_TYPE = 5
    CRS_TYPE = 6

    TYPE_CHOICES = (
        (LECTURE_TYPE, 'Lecture'),
        (PBL_TYPE, 'PBL'),
        (PRACTICAL_TYPE, 'Practical'),
        (SEMINAR_TYPE, 'Seminar'),
        (WEEK_TYPE, 'Week'),
        (CRS_TYPE, 'CRS')
    )
    name = models.CharField(max_length=150)
    activity_type = models.IntegerField(choices=TYPE_CHOICES)
    reference_id = models.IntegerField(unique=True)
    previous_activity = models.OneToOneField('self', null=True, blank=True)

    objects = TeachingActivityManager()

    def __unicode__(self):
        return self.name

    def get_url_kwargs(self):
        return {'reference_id': self.reference_id, }

    def get_absolute_url(self, writing_period=None):
        return "%s%s" % (reverse('activity-view', kwargs=self.get_url_kwargs()), ("?writing_period=%s" % writing_period.id) if writing_period else "")

    def get_signup_url(self):
        return reverse('activity-signup', kwargs=self.get_url_kwargs())

    def get_signup_from_block_url(self):
        return "%s?from=block" % (self.get_signup_url())

    def get_unassign_url(self):
        return reverse('activity-unassign', kwargs=self.get_url_kwargs())

    def get_assign_student_url(self):
        return reverse('activity-assign', kwargs=self.get_url_kwargs())

    def get_new_question_url(self):
        return reverse('question-new', kwargs=self.get_url_kwargs())

    def get_previous_activity_assign_url(self):
        return reverse('activity-assign-previous', kwargs=self.get_url_kwargs())

    def get_reference_url(self):
        compass_url = "http://smp.sydney.edu.au/compass/teachingactivity/view/id/%s"

        return compass_url % self.reference_id

    @classmethod
    def accepted_types(cls):
        accepted_types = collections.defaultdict(None)
        for k, v in cls.TYPE_CHOICES:
            if k == cls.WEEK_TYPE: continue
            accepted_types[v] = k

        return accepted_types

    @classmethod
    def get_type_value_from_name(cls, name):
        try:
            return cls.accepted_types()[name]
        except KeyError:
            raise ValueError("That activity type does not exist.")

    def is_viewable_by(self, student):
        if student.user.is_superuser: return True

        if self.has_student(student): return True

        return self.get_latest_activity_year_for_student(student).block_week.writing_period.block_year.block.is_viewable_by(student)

    def student_can_view_sign_up_information(self, student, writing_period=None):
        current_block = self.get_latest_activity_year_for_student(student, writing_period=writing_period).block_week.writing_period.block_year

        return current_block and current_block.student_is_eligible_for_sign_up(student)

    def student_is_eligible_for_sign_up(self, student):
        return self.current_block_year().student_is_eligible_for_sign_up(student)

    def approved_questions_are_viewable_by(self, student):
        if student.user.is_superuser: return True

        activity_year = self.get_latest_activity_year_for_student(student)
        return activity_year.block_week.writing_period.block_year.block.approved_questions_are_viewable_by(student)

    def questions_for(self, student):
        questions = []

        for activity_year in self.years.all():
            questions += activity_year.questions_for(student)

        return questions

    def student_has_written_questions(self, student):
        return self.years.filter(questions__creator=student).exists()

    def questions_written_by(self, student):
        questions = Question.objects.none()

        for activity_year in self.years.all():
            questions |= activity_year.questions_written_by(student)

        return questions

    def questions_left_for(self, student):
        return self.get_latest_activity_year_for_student(student).questions_left_for(student)

    def current_activity_year(self):
        CURRENT_YEAR_CACHE = "_current_year_cached"

        value = self.get_cache_value(CURRENT_YEAR_CACHE)
        if value: return value

        years = self.years.select_related("block_week__writing_period__block_year").select_related("block_week__writing_period__block_year__block")

        try:
            current_activity_year = years.get(block_week__writing_period__block_year__year=datetime.datetime.now().year)
        except TeachingActivityYear.DoesNotExist:
            current_activity_year = years.order_by("-block_week__writing_period__block_year__year")[0]

        self.set_cache_value(CURRENT_YEAR_CACHE, current_activity_year)
        return current_activity_year

    def get_latest_activity_year_for_student(self, student, writing_period=None):
        activity_year = None

        if writing_period:
            try:
                return self.get_activity_year_for_writing_period(writing_period)
            except TeachingActivityYear.DoesNotExist:
                pass

        years = self.years.select_related("block_week__writing_period__block_year__block")
        years = years.filter(block_week__writing_period__stage__year__student=student, block_week__writing_period__stage__year__year=models.F("block_week__writing_period__block_year__year"))

        try:
            return years.latest("block_week__writing_period__block_year__year")
        except TeachingActivityYear.DoesNotExist:
            return None

    def get_activity_year_for_writing_period(self, writing_period):
        return self.years.select_related("block_week__writing_period__block_year__block").get(block_week__writing_period=writing_period)

    def current_block_year(self):
        return self.current_activity_year().block_week.writing_period.block_year

    def years_available(self):
        years = [activity_year.block_week.writing_period.block_year.year for activity_year in self.years.select_related("block_week__writing_period__block_year").order_by("block_week__writing_period__block_year__year")]
        return list(set(years))

    def has_student(self, student):
        HAS_STUDENT_CACHE = "_has_student_cache"

        value = self.get_cache_value(HAS_STUDENT_CACHE)
        if value is not None:
            return value

        has_student = self.years.filter(question_writers=student).exists()
        self.set_cache_value(HAS_STUDENT_CACHE, has_student)
        return has_student

    def current_question_writer_count(self):
        current_year = self.current_activity_year()

        return current_year.question_writer_count()

    def question_writer_count_for_student(self, student, writing_period=None):
        activity_year = self.get_latest_activity_year_for_student(student, writing_period=writing_period)
        return 0 if not activity_year else activity_year.question_writer_count()


class BlockWeek(models.Model):
    name = models.CharField(max_length=50)
    sort_index = models.IntegerField(db_index=True)
    writing_period = models.ForeignKey(QuestionWritingPeriod, related_name="weeks")

    class Meta:
        ordering = ('writing_period', 'sort_index', )

    def __str__(self):
        return "%s, %s" % (self.name, self.writing_period)


class TeachingActivityYearManager(models.Manager):
    def get_activities_assigned_to(self, student):
        return self.get_queryset().filter(question_writers=student)

    def get_open_activities_assigned_to(self, student):
        open_blocks = TeachingBlockYear.objects.get_open_block_years_for_student(student)
        return self.get_activities_assigned_to(student).filter(block_week__writing_period__block_year__in=open_blocks)


    def get_from_kwargs(self, **kwargs):
        activity = self.get_queryset().filter(teaching_activity__reference_id=kwargs.get('reference_id'))
        if 'year' in kwargs:
            activity = activity.filter(block_week__writing_period__block_year__year=kwargs.get('year'))
        return activity.get()


class TeachingActivityYear(models.Model):
    teaching_activity = models.ForeignKey(TeachingActivity, related_name="years")
    block_week = models.ForeignKey(BlockWeek, related_name="activities", blank=True, null=True)
    position = models.IntegerField()
    question_writers = models.ManyToManyField(Student, blank=True, related_name='assigned_activities')

    objects = TeachingActivityYearManager()

    class Meta:
        ordering = ('block_week__writing_period', 'teaching_activity__activity_type', 'block_week', 'position')

    def name(self):
        return self.teaching_activity.name
    name = property(name)

    def __unicode__(self):
        return "%s" % (self.name, )

    def get_old_url_kwargs(self):
        return {'id': self.id, }

    def get_url_kwargs(self):
        return {'reference_id': self.teaching_activity.reference_id, 'year': self.block_week.writing_period.block_year.year}

    def activity_type(self):
        return self.teaching_activity.activity_type
    activity_type = property(activity_type)

    def get_activity_type_display(self):
        return self.teaching_activity.get_activity_type_display()

    def reference_id(self):
        return self.teaching_activity.reference_id
    reference_id = property(reference_id)

    def current_block(self):
        return self.block_week.writing_period.block_year

    def set_cache_value(self, attribute, value):
        setattr(self, attribute, value)

    def get_cache_value(self, attribute):
        if hasattr(self, attribute):
            return getattr(self, attribute)

    def student_has_written_questions(self, student):
        return self.questions.filter(creator=student).exists()

    def student_can_sign_up(self, student):
        # The student can sign up if the following conditions are met:
        # 1. The current activity year does not have enough writers
        # 2. They are not already signed up for that activity
        # 3. They can sign up for activities within the particular block.
        return not self.enough_writers() and not self.has_student(student) and self.block_week.writing_period.can_sign_up

    def student_can_unassign_activity(self, student):
        return self.has_student(student) and self.block_week.writing_period.can_sign_up and not self.student_has_written_questions(student)

    def add_student(self, student):
        self.question_writers.add(student)

    def remove_student(self, student):
        self.question_writers.remove(student)

    def question_writer_count(self):
        COUNT_CACHE_ATTR = "_question_writer_count"
        if hasattr(self, COUNT_CACHE_ATTR):
            return getattr(self, COUNT_CACHE_ATTR)

        count = self.question_writers.filter().count()
        setattr(self, COUNT_CACHE_ATTR, count)

        return count

    def questions_can_be_written_by(self, student):
        if student.user.is_superuser: return True

        return self.has_student(student) and self.block_week.writing_period.can_write_questions

    def annotate_for_writing_period(self, writing_period):
        # Have to include this method because django does not allow passing of arguments to models in templates.
        self.has_writers = self.has_writers_for_writing_period(writing_period)

    def enough_writers(self):
        return self.question_writer_count() >= self.block_week.writing_period.activity_capacity

    def has_writers_for_writing_period(self, writing_period):
        return bool(self.question_writer_count())

    def has_questions(self):
        return self.questions.exists()

    def has_writers(self):
        return self.question_writers.exists()

    def has_student(self, student):
        return self.question_writers.filter(id=student.id).exists()

    def questions_pending_count(self):
        return self.questions.filter(status=Question.PENDING_STATUS).count()

    def unassigned_questions_count(self):
        UNASSIGNED_COUNT_CACHE_ATTR = "_unassigned_questions_count"

        cached_value = self.get_cache_value(UNASSIGNED_COUNT_CACHE_ATTR)
        if cached_value is not None:
            return cached_value

        questions = self.questions.filter(status=Question.PENDING_STATUS) \
            .filter(models.Q(date_assigned__isnull=True, date_completed__isnull=True) | models.Q(date_assigned__isnull=False, date_completed__isnull=False)) \
            .distinct()
        count = questions.count()

        self.set_cache_value(UNASSIGNED_COUNT_CACHE_ATTR, count)
        return count

    def questions_left_for(self, student):
        if not self.has_student(student):
            # The user is not a question writer so they have no questions remaining.
            return 0

        # Max number of questions to write.
        m = settings.QUESTIONS_PER_USER
        # Current question count.
        c = self.questions.filter(creator=student).exclude(status=Question.DELETED_STATUS).count()
        r = 0

        if c < m:
            r += m - c

        return r

    def questions_written_by(self, student):
        return self.questions.filter(creator=student)

    def questions_for(self, student):
        questions = []

        questions = self.questions.all()

        if not student.user.is_superuser:
            # Nobody can view questions which have been deleted.
            questions = questions.exclude(status=Question.DELETED_STATUS).filter(models.Q(creator=student) | models.Q(status=Question.APPROVED_STATUS))

        return questions

    def can_sign_up(self):
        return self.current_block().can_sign_up
    can_sign_up = property(can_sign_up)

    def assign_pending_questions_to_student(self, student):
        for question in self.questions.all():
            if not question.date_completed and question.date_assigned:
                # The question has already been assigned to someone. Skip it.
                continue
            if question.date_completed and not question.pending:
                # The question is not pending and shouldn't be assigned to anyone.
                continue
            
            # The question is now either
            # 1. Not complete and not assigned, i.e. pending.
            # 2. Complete and pending
            # So we should assign it to someone.
            question.assign_to_student(student)


class QuestionManager(models.Manager):
    def get_from_kwargs(self, **kwargs):
        allow_deleted = kwargs.get('allow_deleted', False)
        questions = self.get_queryset().filter(pk=kwargs.get('pk'))
        if 'reference_id' in kwargs:
            questions = questions.filter(teaching_activity_year__teaching_activity__reference_id=kwargs.get('reference_id'))
        if not allow_deleted:
            questions = questions.exclude(status=Question.DELETED_STATUS)

        return questions.get()

    def get_approved_questions_for_block_and_years(self, block, years):
        return self.get_queryset().filter(teaching_activity_year__teaching_activity__years__block_week__writing_period__block_year__block=block, teaching_activity_year__block_week__writing_period__block_year__year__in=years) \
                                   .filter(status=Question.APPROVED_STATUS).distinct()


class QuestionParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.parsed_string = ""

    def parse_string(self, s):
        self.parsed_string = ""
        self.feed(s)
        return self.parsed_string

    def handle_starttag(self, tag, attrs):
        if tag == "sup":
            self.parsed_string += "^"
        if tag == "sub":
            self.parsed_string += "_"

    def handle_data(self, data):
        self.parsed_string += data

    def handle_entityref(self, name):
        c = unichr(name2codepoint[name])
        self.parsed_string += c  


@reversion.register(exclude=["approver", "date_assigned", "date_completed", "requires_special_formatting", "approver"])
class Question(models.Model):
    APPROVED_STATUS = 0
    PENDING_STATUS = 1
    DELETED_STATUS = 2
    FLAGGED_STATUS = 3
    EDITING_STATUS = 4
    STATUS_CHOICES = (
        (APPROVED_STATUS, 'Approved'),
        (PENDING_STATUS, 'Pending'),
        (DELETED_STATUS, 'Deleted'),
        (FLAGGED_STATUS, 'Flagged'),
        (EDITING_STATUS, 'Editing'),
    )

    STATUS_TO_ACTION = (
        (APPROVED_STATUS, "Approve"),
        (PENDING_STATUS, "Make pending"),
        (FLAGGED_STATUS, "Flag"),
        (DELETED_STATUS, "Delete"),
    )

    body = models.TextField()
    options = models.TextField(blank=True)
    answer = models.CharField(max_length=1)
    explanation = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(Student, related_name="questions_created")
    approver = models.ForeignKey(Student, null=True, blank=True, related_name="questions_approved")
    teaching_activity_year = models.ForeignKey(TeachingActivityYear, related_name="questions")
    exemplary_question = models.BooleanField(default=False)
    requires_special_formatting = models.BooleanField(default=False)
    status = models.IntegerField(choices=STATUS_CHOICES, default=APPROVED_STATUS)
    date_assigned = models.DateTimeField(blank=True, null=True)
    date_completed = models.DateTimeField(blank=True, null=True)
    approver = models.ForeignKey(Student, related_name="assigned_questions", blank=True, null=True)

    reasons = generic.GenericRelation('questions.Reason', content_type_field="related_object_content_type", object_id_field="related_object_id")

    objects = QuestionManager()
    parser = QuestionParser()

    class Meta:
        permissions = (
            ('can_approve', 'Can approve questions'),
        )

    def __init__(self, *args, **kwargs):
        super(Question, self).__init__(*args, **kwargs)
        # Adds properties to the model to check the status, e.g. self.approved, self.flagged
        attribute_list = self.__class__.__dict__.keys()
        for k in attribute_list:
            if not "_STATUS" in k or hasattr(self, k.split("_")[0].lower()):
                continue

            self.add_model_status_property_method(k)

        self.sorted_options = None

        if '"answer":' in self.options:
            self.sorted_options = SortedDict()
            self.answer_letter = ""
            decoded_options = json.loads(self.options)
            flattened_options = [decoded_options["answer"], ] + decoded_options["distractor"]
            random.shuffle(flattened_options)
            for letter, option in zip(string.uppercase[:5], flattened_options):
                self.sorted_options[letter] = option
                if option == decoded_options["answer"]:
                    self.answer_letter = letter

        if self.explanation and "{" not in self.explanation:
            explanation = self.options_dict()
            for option, label in explanation.items():
                if option == self.answer:
                    explanation[option] = self.explanation
                else:
                    explanation[option] = ""

            self.explanation = json.dumps(explanation)

    def __str__(self):
        return "%s" % (self.id,)

    def _get_text(self, element):
        element_text = ""
        formatting_tags = {'sup': '^', 'sub': '_'}
        symbols = {}

        if isinstance(element, bs4.NavigableString):
            element_text += element.string
        elif isinstance(element, bs4.Tag):
            if element.contents:
                if element.name in formatting_tags:
                    element_text += formatting_tags[element.name]

                for subelement in element.contents:
                    element_text += self._get_text(subelement)

        return element_text

    def _soup_to_text(self, soup):
        body_text = ""

        for element in soup.body.contents:
            body_text += self._get_text(element)

        body_text = body_text.replace(u'\xa0', u' ')
        new_body_text = ""
        for c in body_text:
            if ord(c) in codepoint2name:
                new_body_text += codepoint2name[ord(c)]
            else:
                new_body_text += c

        return new_body_text

    def get_body_text(self):
        soup = bs4.BeautifulSoup(self.body)
        return self._soup_to_text(soup)

    def was_assigned_before_being_completed(self):
        return self.date_assigned and (not self.date_completed or self.date_assigned < self.date_completed)

    def get_url_kwargs(self):
        return {'pk': self.pk, 'reference_id': self.teaching_activity_year.teaching_activity.reference_id, }

    def get_query_string(self):
        params = []

        if not params:
            return ""
        return "?%s" % ("&".join(params),)

    def get_absolute_url(self):
        return reverse('question-view', kwargs=self.get_url_kwargs())

    def get_edit_url(self):
        query_string = self.get_query_string()
        return "%s%s" % (reverse('question-edit', kwargs=self.get_url_kwargs()), query_string)

    def get_add_to_specification_url(self):
        return reverse('quiz-spec-add', kwargs=self.get_url_kwargs())

    def get_flag_url(self):
        query_string = self.get_query_string()
        return "%s%s" % (reverse('question-flag', kwargs=self.get_url_kwargs()), query_string)

    def get_previous_version_url(self):
        return reverse('question-versions', kwargs=self.get_url_kwargs())

    def is_viewable_by(self, student):
        # A student can view a question in the following situations:
        # 1. They wrote it and it is not deleted.
        # 2. They wrote questions for that particular block and it is approved.
        # 3. They are the superuser.

        if student.user.is_superuser:
            return True

        if not self.deleted:
            if self.approved and self.teaching_activity_year.teaching_activity.approved_questions_are_viewable_by(student):
                return True
            else:
                return student == self.creator

        return False

    def is_editable_by(self, student):
        # A student can edit a question in the following situations:
        # 1. They wrote it, and the block is open for writing.
        # 2. They are an approver (or the superuser).
        return (self.creator == student and self.teaching_activity_year.questions_can_be_written_by(student)) or (self.approved and self.teaching_activity_year.teaching_activity.approved_questions_are_viewable_by(student))

    def add_model_status_property_method(self, k):
        def check_status_function(self):
            return self.status == getattr(Question, k)

        setattr(self.__class__, k.split("_")[0].lower(), property(check_status_function))

    def json_repr(self, include_answer=False):
        options = self.options_dict()
        label = options.keys()
        label.sort()
        options['labels'] = label
        json_repr = {'id': self.id, 'body': self.body, 'options': options}
        if include_answer:
            json_repr['answer'] = self.answer
            explanation = self.explanation_dict()
            labels = explanation.keys()
            labels.sort()
            explanation['labels'] = labels
            json_repr['explanation'] = explanation
            json_repr['url'] = self.get_absolute_url()

        return json_repr

    def unicode_body(self):
        return self.parser.parse_string(self.body)

    def unicode_options_list(self):
        ol = self.options_list()

        return [self.parser.parse_string(o) for o in ol]

    def unicode_explanation_list(self):
        el = self.explanation_list()

        return [self.parser.parse_string(e) for e in el]

    def options_dict(self):
        if self.sorted_options:
            return dict((letter, option["text"]) for letter, option in self.sorted_options.items())
        else:
            d = SortedDict()
            e = json.loads(self.options)
            f = e.keys()
            f.sort()
            for k in f:
                d[k] = e[k]
        return d

    def options_dict_text(self):
        d = self.options_dict()

        for key in d:
            soup = bs4.BeautifulSoup(d[key])
            d[key] = self._soup_to_text(soup)

        return d

    def options_list(self):
        if self.sorted_options:
            return [option["text"] for option in self.sorted_options.values()]
        else:
            l = list(json.loads(self.options).iteritems())
            l.sort(key=lambda x: x[0])
            return [j for i, j in l]

    def options_tuple(self):
        j = json.loads(self.options)
        return [(c, j[c]) for c in string.ascii_uppercase[:len(j)]]

    def option_value(self, option):
        return self.options_dict()[option]

    def correct_answer(self):
        return self.answer or self.answer_letter

    def explanation_list(self):
        return self.explanation_dict().values()

    def decode_explanation(self, explanation=None):
        explanation = explanation or self.explanation
        explanation_dict = SortedDict()
        if self.sorted_options:
            for letter, option in self.sorted_options.items():
                explanation_dict[letter] = option["explanation"]
        else:
            if "{" in self.explanation:
                explanation = json.loads(self.explanation)
            else:
                explanation = self.options_dict()
                for option, label in explanation.items():
                    if option == self.answer:
                        explanation[option] = self.explanation
                    else:
                        explanation[option] = ""
            keys = explanation.keys()
            keys.sort()
            for key in keys:
                explanation_dict[key] = explanation[key]

        return explanation_dict

    def explanation_dict(self):
        return self.decode_explanation()

    def explanation_for_answer(self):
        explanation = self.explanation_dict()
        if explanation:
            return explanation[self.answer]
        else:
            return self.explanation

    def user_is_creator(self, user):
        return user.student == self.creator

    def principal_comments(self):
        return self.comments.filter(reply_to__isnull=True)

    def block(self):
        return self.teaching_activity_year.block_week.writing_period.block_year

    def number_correct_attempts(self):
        return self.attempts.filter(answer=models.F("question__answer")).count()

    def total_attempts(self):
        return self.attempts.count()

    def success_rate(self):
        return self.number_correct_attempts() / self.total_attempts()

    def percent_success_rate(self):
        return self.success_rate() * 100

    def get_average_confidence_rating(self):
        return self.attempts.aggregate(models.Avg('confidence_rating'))['confidence_rating__avg']

    def answer_ratios(self):
        ratio_dict = {}
        for option in self.options_dict():
            ratio_dict[option] = self.attempts.filter(answer=option).count()

        ratio_dict[QuestionAttempt.DEFAULT_ANSWER] = self.attempts.filter(answer="").count()

        total_answers = sum(ratio_dict.values())

        if total_answers == 0:
            ratio_dict = dict((k, 0) for k in ratio_dict)
        else:
            ratio_dict = dict((k, v / total_answers) for k,v in ratio_dict.iteritems())

        return ratio_dict

    def discrimination(self):
        test_quiz_attempts = list(self.attempts.filter(quiz_attempt__quiz_specification__id=4))
        test_quiz_attempts.sort(key=lambda a: a.quiz_attempt.score())

        if len(test_quiz_attempts) < 2: return 0

        group_size = int(round(len(test_quiz_attempts) * 0.3))
        upper_group = test_quiz_attempts[-group_size:]
        lower_group = test_quiz_attempts[:group_size]

        difference = sum(qa.score() for qa in upper_group) - sum(qa.score() for qa in lower_group)
        return difference/group_size


class ApprovalRecordManager(models.Manager):
    def get_latest_assigned_records_with_status(self, status):
        # THIS METHOD WILL NOT WORK CORRECTLY FOR PENDING RECORDS
        # We get approval records which satisfy the following:
        # 1. They are the latest assigned approval record for their question.
        # 2. They are complete.
        # 3. They have the correct status.
        return self.get_queryset().annotate(max=models.Max('question__approval_records__date_assigned')) \
                                .filter(max=models.F('date_assigned')) \
                                .filter(date_completed__isnull=False) \
                                .filter(status=status)


class ApprovalRecord(models.Model):
    """
        A class designed to track question approval history.
        * question: the question that the approval record is tracking
        * approver: the person who changed the status of a question
        * date_assigned: the date that the approver was assigned to change the status
        * date_completed: the date on which the status was changed
        * status: the status of the question after the change

        If date_completed and date_assigned are the same, then the change of status was done manually, i.e. outside of the
        approval system directly through the question display page.
    """
    APPROVED_STATUS = 0
    PENDING_STATUS = 1
    DELETED_STATUS = 2
    FLAGGED_STATUS = 3
    EDITING_STATUS = 4
    STATUS_CHOICES = (
        (APPROVED_STATUS, 'Approved'),
        (PENDING_STATUS, 'Pending'),
        (DELETED_STATUS, 'Deleted'),
        (FLAGGED_STATUS, 'Flagged'),
        (EDITING_STATUS, 'Editing'),
    )

    approver = models.ForeignKey(Student, related_name="approval_records")
    question = models.ForeignKey(Question, related_name="approval_records")
    date_assigned = models.DateTimeField(blank=True, null=True)
    date_completed = models.DateTimeField(blank=True, null=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=PENDING_STATUS, blank=True, null=True)

    reasons = generic.GenericRelation('questions.Reason', content_type_field="related_object_content_type", object_id_field="related_object_id")

    objects = ApprovalRecordManager()


    def __init__(self, *args, **kwargs):
        super(ApprovalRecord, self).__init__(*args, **kwargs)
        # Adds properties to the model to check the status, e.g. self.approved, self.flagged
        for k in self.__class__.__dict__.keys():
            if not "_STATUS" in k or hasattr(self, k.split("_")[0].lower()):
                continue

            self.add_model_status_property_method(k)

    def add_model_status_property_method(self, k):
        def check_status_function(self):
            if self.status is not None:
                return self.status == getattr(self, k)
            else:
                return self.PENDING_STATUS == getattr(self, k)

        setattr(self.__class__, k.split("_")[0].lower(), property(check_status_function))

    def was_assigned_before_being_completed(self):
        return self.date_assigned and (not self.date_completed or self.date_assigned < self.date_completed)


class QuizSpecificationManager(models.Manager):
    def get_from_kwargs(self, **kwargs):
        return self.get_queryset().get(slug=kwargs.get('slug'))

    def get_allowed_specifications_for_student(self, student):
        stages = student.get_all_stages()
        allowed_blocks = TeachingBlock.objects.get_visible_blocks_for_student(student)
        block_permission_needed = models.Q(block__in=allowed_blocks)
        no_permission_needed = models.Q(block__isnull=True)
        return self.get_queryset().filter(stage__in=stages, active=True).filter(block_permission_needed | no_permission_needed)


class QuizSpecification(models.Model):
    name = models.CharField(max_length=100)
    stage = models.ForeignKey(Stage)
    description = models.TextField(blank=True)
    # A 160-bit SHA1 hash converted to base 26 requires 36 characters to be represented.
    slug = models.SlugField(max_length=36)
    active = models.BooleanField(default=False)
    block = models.ForeignKey(TeachingBlock, blank=True, null=True)

    objects = QuizSpecificationManager()

    class Meta:
        ordering = ('stage',)

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.stage)

    def get_url_kwargs(self):
        return {'slug': self.slug, }

    def get_absolute_url(self):
        return reverse('quiz-specification-view', kwargs=self.get_url_kwargs())

    def get_edit_url(self):
        return reverse("quiz-specification-edit", kwargs=self.get_url_kwargs())

    def get_add_questions_url(self):
        return reverse('quiz-specification-questions-add', kwargs=self.get_url_kwargs())

    def get_add_questions_confirmation_url(self):
        return reverse('quiz-specification-questions-add-confirm', kwargs=self.get_url_kwargs())

    def generate_slug(self):
        return hex_to_base_26(hashlib.sha1("%s%s" % (self.name, self.description)).hexdigest())

    def get_questions(self):
        questions_to_return = Question.objects.none()

        for q in self.questions.all():
            questions_to_return |= q.get_questions()

        return questions_to_return

    def get_questions_in_order(self):
        return self.get_questions().order_by('teaching_activity_year__block_week__writing_period__block_year')

    def number_of_questions(self):
        return self.get_questions().count()

    def get_correct_question_attempts(self):
        # Get all of the QuestionAttempts for this specification which are correct.

        if hasattr(self, "_question_attempts"):
            return getattr(self, "_question_attempts")

        question_attempts = QuestionAttempt.objects.filter(quiz_attempt__quiz_specification=self) \
                            .filter(question__answer=models.F("answer")) \
                            .select_related('quiz_attempt')

        setattr(self, "_question_attempts", question_attempts)
        return question_attempts


    def average_score(self):
        # attempts = self.attempts.all()

        # Get all of the QuestionAttempts for this specification which are correct.
        question_attempts = self.get_correct_question_attempts()

        total_score = 0
        attempts = []
        for question_attempt in question_attempts:
            total_score += 1
            if question_attempt.quiz_attempt not in attempts:
                attempts.append(question_attempt.quiz_attempt)

        if not attempts: return 0
        return float(total_score)/len(attempts)

    def highest_score(self):
        question_attempts = self.get_correct_question_attempts()

        # Group them by QuizAttempt
        quiz_attempts = {}
        for question_attempt in question_attempts:
            l = quiz_attempts.setdefault(question_attempt.quiz_attempt, [])
            l.append(question_attempt)

        highest = 0
        if quiz_attempts:
            highest = max(len(question_attempts) for quiz_attempt, question_attempts in quiz_attempts.items())

        return highest

    def lowest_score(self):
        # Check whether people have gotten every question wrong. These will be mist in self.get_correct_question_attempts()
        complete_fails = self.attempts.exclude(questions__question__answer=models.F("questions__answer")).distinct()
        if complete_fails.exists(): return 0

        question_attempts = self.get_correct_question_attempts()

        # Group them by QuizAttempt
        quiz_attempts = {}
        for question_attempt in question_attempts:
            l = quiz_attempts.setdefault(question_attempt.quiz_attempt, [])
            l.append(question_attempt)

        lowest = 0
        if quiz_attempts:
            lowest = min(len(question_attempts) for quiz_attempt, question_attempts in quiz_attempts.items())

        return lowest


class QuizQuestionSpecification(models.Model):
    SPECIFIC_QUESTION = 0
    RANDOM_FROM_BLOCK = 1
    QUESTION_LIST = 2

    SPECIFICATION_TYPE_CHOICES = (
        (SPECIFIC_QUESTION, "A specific question"),
        (RANDOM_FROM_BLOCK, "A random choice of questions from a block"),
        (QUESTION_LIST, "A list of questions"),
    )

    specification_type = models.IntegerField(choices=SPECIFICATION_TYPE_CHOICES)
    quiz_specification = models.ForeignKey(QuizSpecification, related_name="questions")
    parameters = models.TextField()

    def __unicode__(self):
        return "%s, %s" % (self.get_display(), self.quiz_specification)

    def get_display(self):
        if self.specification_type == self.SPECIFIC_QUESTION:
            return "%s (%s)" % (self.get_specification_type_display(), self.get_parameters_dict()["question"])
        elif self.specification_type == self.QUESTION_LIST:
            return "%s (%s)" % (self.get_specification_type_display(), ", ".join(str(x) for x in self.get_parameters_dict()["question_list"]))

    @classmethod
    def from_parameters(cls, **kwargs):
        allowed_kwargs = ['question', 'question_list']
        parameters = {}
        instance = cls()

        for key in kwargs:
            if key in allowed_kwargs:
                parameters[key] = kwargs[key]

        instance.parameters = json.dumps(parameters)

        return instance

    @classmethod
    def from_specific_question(cls, question):
        instance = cls.from_parameters(question=question.id)
        instance.specification_type = cls.SPECIFIC_QUESTION
        return instance

    @classmethod
    def from_list_of_questions(cls, question_list):
        instance = cls.from_parameters(question_list=[question.id for question in question_list])
        instance.specification_type = cls.QUESTION_LIST
        return instance

    def get_parameters_dict(self):
        return json.loads(self.parameters)

    def get_questions(self):
        parameters = self.get_parameters_dict()
        questions_to_return = Question.objects.none()

        if 'question' in parameters:
            condition = models.Q(id__in=[parameters["question"],])
        elif 'question_list' in parameters:
            condition = models.Q(id__in=parameters["question_list"])

        questions_to_return |= Question.objects.filter(condition)

        return questions_to_return.select_related("teaching_activity_year")


class QuizAttemptManager(models.Manager):
    def get_from_kwargs(self, **kwargs):
        return self.get_queryset().get(slug=kwargs.get('slug'))

    def get_latest_quiz_attempt_for_student(self, student):
        return self.get_quiz_attempts_for_student(student).latest("date_submitted")

    def get_quiz_attempts_for_student(self, student):
        return self.get_queryset().filter(student=student).prefetch_related("questions")


class QuizAttempt(models.Model):
    INDIVIDUAL_QUIZ_TYPE = "individual"
    CLASSIC_QUIZ_TYPE = "classic"
    QUIZ_TYPE_CHOICES = (
        (INDIVIDUAL_QUIZ_TYPE, "After each question"),
        (CLASSIC_QUIZ_TYPE, "At the end"),
    )
    student = models.ForeignKey(Student, related_name="quiz_attempts")
    date_submitted = models.DateTimeField(auto_now_add=True)
    quiz_specification = models.ForeignKey(QuizSpecification, related_name="attempts", blank=True, null=True)
    slug = models.SlugField(max_length=36)
    quiz_type = models.CharField(choices=QUIZ_TYPE_CHOICES, max_length=20)

    objects = QuizAttemptManager()

    def __unicode__(self):
        return "Quiz attempt for %s" % self.student

    def get_url_kwargs(self):
        return {'slug': self.slug}

    def get_questions_url(self):
        return reverse("quiz-attempt-questions", kwargs=self.get_url_kwargs())

    def get_answer_submission_url(self):
        return reverse("quiz-attempt-submit", kwargs=self.get_url_kwargs())

    def get_submission_url(self):
        return reverse("quiz-attempt-submit-all", kwargs=self.get_url_kwargs())

    def get_report_url(self):
        return reverse("quiz-attempt-report", kwargs=self.get_url_kwargs())

    def get_start_url(self, quiz_type):
        return reverse("quiz-attempt-start", kwargs=self.get_url_kwargs())

    def get_resume_url(self):
        return reverse("quiz-attempt-resume", kwargs=self.get_url_kwargs())

    def is_viewable_by(self, student):
        return student.user.is_superuser or student == self.student

    @classmethod
    def create_from_list_and_student(cls, question_list, student, quiz_type="", quiz_specification=None):
        instance = cls()
        instance.student = student
        instance.quiz_type = quiz_type
        if quiz_specification: instance.quiz_specification = quiz_specification
        instance.save()

        if len(question_list) != len(set(question_list)):
            raise ValueError("The list of questions provided has duplicate entries.")

        for n, question in enumerate(question_list):
            attempt = QuestionAttempt()
            attempt.quiz_attempt = instance
            attempt.question = question
            attempt.position = n+1
            attempt.save()

        return instance

    def get_questions(self):
        q = []

        for question in self.questions.all():
            qq = question.question
            qq.choice = question.answer
            qq.position = question.position
            qq.time_taken = question.time_taken
            qq.confidence_rating = question.confidence_rating
            q.append(qq)

        return q

    def get_question_attempt_by_question(self, questionID):
        return self.questions.get(question__id=questionID)

    def generate_slug(self):
        spec = self.quiz_specification.id if self.quiz_specification else ""
        date_string = datetime.datetime.now().strftime("%Y%m%d %H%M")
        rand_string = "".join(random.choice(string.lowercase) for i in range(6))
        to_hash = "%s%s%s%s" % (self.student.user.username, date_string, spec, rand_string)
        return hex_to_base_26(hashlib.sha1(to_hash).hexdigest())

    def date_completed(self):
        if self.incomplete_questions().exists(): return None
        return self.questions.aggregate(models.Max('date_completed'))['date_completed__max']
    date_completed = property(date_completed)

    def incomplete_questions(self):
        return self.questions.filter(date_completed__isnull=True)

    def questions_in_order(self):
        return self.questions.order_by('position')

    def incomplete_questions_in_order(self):
        return self.incomplete_questions().order_by("position")

    def score(self):
        return self.questions.filter(answer=models.F("question__answer")).count()

    def number_of_questions_completed(self):
        return self.questions.filter(date_completed__isnull=False).count()

    def number_of_questions_incomplete(self):
        return self.incomplete_questions().count()

    def complete(self):
        return not self.incomplete_questions().exists()
    complete = property(complete)

    def complete_questions_in_order(self):
        if self.quiz_specification:
            attempts = list(self.questions.all())
            all_questions = list(self.quiz_specification.get_questions())
            attempt_questions = list(a.question.id for a in self.questions.all())
            for question in all_questions:
                if question.id not in attempt_questions:
                    question_attempt = QuestionAttempt()
                    question_attempt.quiz_attempt = self
                    question_attempt.question = question
                    attempts.append(question_attempt)
        else:
            attempts = self.questions.order_by("position")
        return attempts

    def percent_score(self):
        number_of_questions = self.quiz_specification.number_of_questions() if self.quiz_specification else self.questions.count()
        if number_of_questions == 0:
            return 0.0
        return self.score() / number_of_questions * 100


@receiver(models.signals.pre_save, sender=QuizSpecification)
@receiver(models.signals.pre_save, sender=QuizAttempt)
def generate_quiz_slug(sender, instance, **args):
    if not args["raw"]:
        instance.slug = instance.generate_slug()


class QuestionAttemptManager(models.Manager):
    def get_question_attempts_for_student(self, student):
        return self.get_queryset().filter(quiz_attempt__student=student).select_related('quiz_attempt', 'question')


class QuestionAttempt(models.Model):
    DEFAULT_ANSWER = ""
    DEFAULT_CONFIDENCE = 0
    GUESS = 1
    UNSURE = 2
    NEUTRAL = 3
    SURE = 4
    CERTAIN = 5
    GUESS_WORD = "guessing"
    UNSURE_WORD = "doubtful"
    NEUTRAL_WORD = "feeling neutral"
    SURE_WORD = "fairly sure"
    CERTAIN_WORD = "certain"

    CONFIDENCE_CHOICES = (
        (GUESS, "I'm %s" % (GUESS_WORD, )),
        (UNSURE, "I'm %s" % (UNSURE_WORD, )),
        (NEUTRAL, "I'm %s" % (NEUTRAL_WORD, )),
        (SURE, "I'm %s" % (SURE_WORD, )),
        (CERTAIN, "I'm %s" % (CERTAIN_WORD, )),
    )

    SECOND_PERSON_CONFIDENCE_CHOICES = (
        (GUESS, "You were %s" % (GUESS_WORD, )),
        (UNSURE, "You were %s" % (UNSURE_WORD, )),
        (NEUTRAL, "You were %s" % (NEUTRAL_WORD, )),
        (SURE, "You were %s" % (SURE_WORD, )),
        (CERTAIN, "You were %s" % (CERTAIN_WORD, )),
    )

    THIRD_PERSON_CONFIDENCE_CHOICES = (
        (GUESS, "They were %s" % (GUESS_WORD, )),
        (UNSURE, "They were %s" % (UNSURE_WORD, )),
        (NEUTRAL, "They were %s" % (NEUTRAL_WORD, )),
        (SURE, "They were %s" % (SURE_WORD, )),
        (CERTAIN, "They were %s" % (CERTAIN_WORD, )),
    )

    quiz_attempt = models.ForeignKey(QuizAttempt, related_name="questions")
    question = models.ForeignKey(Question, related_name="attempts")
    position = models.PositiveIntegerField()
    answer = models.CharField(max_length=1, blank=True, null=True)
    time_taken = models.PositiveIntegerField(blank=True, null=True)
    confidence_rating = models.IntegerField(choices=CONFIDENCE_CHOICES, blank=True, null=True)
    date_completed = models.DateTimeField(blank=True, null=True)

    objects = QuestionAttemptManager()

    def incorrect_answer(self):
        if self.answer and not self.answer == self.question.answer:
            return {'option': self.answer, 'value': self.question.option_value(self.answer)}

        return {}

    def student_choice(self):
        if self.answer:
            return {'option': self.answer, 'value': self.question.option_value(self.answer), 'explanation': self.question.explanation_dict()[self.answer]}

        return {}

    def correct_answer(self):
        return {'option': self.question.answer, 'value': self.question.option_value(self.question.answer), 'explanation': self.question.explanation_dict()[self.question.answer]}

    def score(self):
        return int(self.answer == self.question.answer)

    def get_average_confidence_rating_display(self):
        average = int(round(self.question.get_average_confidence_rating()))
        try:
            return dict(self.THIRD_PERSON_CONFIDENCE_CHOICES)[average]
        except:
            return ""

    def get_confidence_rating_display_second_person(self):
        if not self.confidence_rating:
            return ""
        return dict(self.SECOND_PERSON_CONFIDENCE_CHOICES)[self.confidence_rating]

    def get_confidence_rating_display_third_person(self):
        if not self.confidence_rating:
            return ""
        return dict(self.THIRD_PERSON_CONFIDENCE_CHOICES)[self.confidence_rating]


class QuestionRating(models.Model):
    UPVOTE = 1
    DOWNVOTE = -1

    RATING_CHOICES = (
        (UPVOTE, "+"),
        (DOWNVOTE, "-"),
    )

    student = models.ForeignKey(Student, related_name="question_ratings")
    question = models.ForeignKey(Question, related_name="ratings")
    rating = models.IntegerField(choices = RATING_CHOICES)
    date_rated = models.DateTimeField(auto_now_add=True)


class ReasonManager(models.Manager):
    def get_reasons_associated_with_object(self, related_object):
        object_content_type = ContentType.objects.get_for_model(model=related_object)

        return self.get_queryset().filter(related_object_content_type=object_content_type, related_object_id=related_object.id)

    def get_reasons_associated_with_multiple_objects(self, related_objects):
        related_objects_list = list(related_objects)
        if not related_objects_list:
            return self.none()
        object_content_type = ContentType.objects.get_for_model(model=related_objects[0])

        return self.get_queryset().filter(related_object_content_type=object_content_type, related_object_id__in=related_objects)


class Reason(models.Model):
    TYPE_EDIT = 0
    TYPE_FLAG = 1
    
    REASON_TYPES = (
        (TYPE_EDIT, "Edited"),
        (TYPE_FLAG, "Flagged"),
    )
    
    body = models.TextField()
    creator = models.ForeignKey(Student, related_name="reasons")
    date_created = models.DateTimeField(auto_now_add=True)
    reason_type = models.IntegerField(choices=REASON_TYPES)
    related_object_id = models.PositiveIntegerField(blank=True, null=True)
    related_object_content_type = models.ForeignKey(ContentType, blank=True, null=True)
    related_object = generic.GenericForeignKey('related_object_content_type', 'related_object_id')

    objects = ReasonManager()

    def for_flagging(self):
        return self.reason_type == self.TYPE_FLAG

    def for_editing(self):
        return self.reason_type == self.TYPE_EDIT


class Comment(models.Model):
    body = models.TextField(verbose_name="Comment")
    question = models.ForeignKey(Question, related_name="comments")
    creator = models.ForeignKey(Student, related_name="comments")
    date_created = models.DateTimeField(auto_now_add=True)
    reply_to = models.ForeignKey('self', blank=True, null=True)

    def replies(self):
        return Comment.objects.filter(reply_to=self)


class DashboardSettingMixin(object):
    def get_value_dict(self):
        if self.value and "{" in self.value:
            return json.loads(self.value)
        else:
            return None

    def build_value_attr(self, key):
        key = "_".join(key.split())
        return "_%s" % key

    def get_value_from_dict(self, key):
        if hasattr(self, self.build_value_attr(key)):
            return getattr(self, self.build_value_attr(key))

        value = self.get_value_dict()
        if isinstance(value, dict):
            setattr(self, self.build_value_attr(key), value[key])
            return value[key]

        return None

    def main_text(self):
        return self.get_value_from_dict("main_text")

    def secondary_text(self):
        return self.get_value_from_dict("secondary_text")


class StudentDashboardSetting(Setting, DashboardSettingMixin):
    HAS_QUESTIONS_DUE_SOON = "has_questions_due_soon"
    HAS_QUESTIONS_DUE_LATER = "has_questions_due_later"
    ALL_QUESTIONS_SUBMITTED = "all_questions_submitted"
    NO_CURRENT_ACTIVITIES_OR_BLOCKS_OPEN = "no_current_activities_or_blocks_open"
    NO_CURRENT_ACTIVITIES_AND_BLOCKS_OPEN = "no_current_activities_and_blocks_open"
    DEFAULT_MESSAGE = "default_message"
    OVERRIDE_MESSAGE = "override_message"

    GUIDE_MESSAGE = "guide_message"

    ALL_SETTINGS = [
        HAS_QUESTIONS_DUE_SOON, HAS_QUESTIONS_DUE_LATER, ALL_QUESTIONS_SUBMITTED,
        NO_CURRENT_ACTIVITIES_OR_BLOCKS_OPEN, NO_CURRENT_ACTIVITIES_AND_BLOCKS_OPEN,
        DEFAULT_MESSAGE, OVERRIDE_MESSAGE, GUIDE_MESSAGE
    ]

    class Meta:
        proxy = True


class ApprovalDashboardSetting(Setting, DashboardSettingMixin):
    DEFAULT_MESSAGE = "default_message"
    OVERRIDE_MESSAGE = "override_message"
    ASSIGNED_QUESTIONS_APPROVED_NO_QUESTIONS_LEFT = "assigned_questions_approved_no_questions_left"
    ASSIGNED_QUESTIONS_APPROVED_AND_QUESTIONS_LEFT = "assigned_questions_approved_and_questions_left"
    ASSIGNED_QUESTIONS_NEED_APPROVAL = "assigned_questions_need_approval"

    GUIDE_MESSAGE = "guide_message"

    ALL_SETTINGS = [
        DEFAULT_MESSAGE, OVERRIDE_MESSAGE,
        ASSIGNED_QUESTIONS_APPROVED_AND_QUESTIONS_LEFT, ASSIGNED_QUESTIONS_APPROVED_NO_QUESTIONS_LEFT,
        ASSIGNED_QUESTIONS_NEED_APPROVAL, GUIDE_MESSAGE
    ]

    class Meta:
        proxy = True

