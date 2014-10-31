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

import json
import datetime
import string
import random
import markdown2
import html2text
import hashlib
import collections

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
    stage_cache = {}

    number = models.IntegerField()

    class Meta:
        ordering = ('number',)

    def __unicode__(self):
        return "Stage %s" % (self.number, )

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
        return Stage.objects.filter(number__lte=self.get_current_stage().number)

    def get_previous_stages(self):
        return Stage.objects.filter(number__lt=self.get_current_stage().number)

    def current_assigned_activities(self):
        return self.assigned_activities.filter(models.Q(block_year__release_date__year=datetime.datetime.now().year) | models.Q(block_year__start__year=datetime.datetime.now().year))

    def questions_due_soon_count(self):
        count = self.assigned_activities.filter(block_year__close__range=[datetime.datetime.now(), datetime.datetime.now()+datetime.timedelta(weeks=1)]).count() * settings.QUESTIONS_PER_USER
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
        if kwargs['instance'].username == 'michael':
            y.stage = Stage.STAGE_ONE
        else:
            y.stage = kwargs['instance']._stage
        y.year = datetime.datetime.now().year
        y.save()


class TeachingBlockManager(models.Manager):
    def get_from_kwargs(self, **kwargs):
        return self.get_queryset().get(code=kwargs.get('code'))

    def get_block_for_activity(self, activity):
        return self.get_queryset().filter(years__activities__teaching_activity=activity).get()

    def get_released_blocks_for_student(self, student):
        # Get the latest block year for each block.
        block_years = TeachingBlockYear.objects.get_released_block_years_for_student(student)
        return self.get_queryset().filter(years__in=block_years).distinct()


class TeachingBlock(models.Model):
    name = models.CharField(max_length=50)
    stage = models.ForeignKey(Stage)
    code = models.CharField(max_length=10)
    sort_index = models.IntegerField(db_index=True)

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

    def get_released_years(self):
        return self.years.filter(release_date__lte=datetime.datetime.now())
    released_years = property(get_released_years)

    def is_viewable_by(self, student):
        if student.user.is_superuser: return True

        if student.has_perm("questions.can_approve") and student.get_previous_stages().filter(id=self.stage.id).exists():
            return True

        block_is_released_and_questions_written = models.Q(release_date__lte=datetime.datetime.now(), activities__questions__creator=student)
        if self.years.filter(block_is_released_and_questions_written).exists():
            return True

        # A student can view a block open for signup if it is in their stage.
        if student.get_current_stage() == self.stage:
            block_is_open = models.Q(start__lte=datetime.datetime.now(), close__gte=datetime.datetime.now())
            if self.years.filter(block_is_open).exists():
                return True

        return False

    def is_available_for_download_by(self, student):
        return self.approved_questions_are_viewable_by(student) and self.released_years.exists()

    def approved_questions_are_viewable_by(self, student):
        if student.user.is_superuser: return True

        if student.has_perm("questions.can_approve") and student.get_all_stages().filter(id=self.stage.id).exists():
            return True

        block_is_released_and_questions_written = models.Q(release_date__lte=datetime.datetime.now(), activities__questions__creator=student)
        if self.years.filter(block_is_released_and_questions_written).exists():
            return True

        return False

    def can_be_approved_by(self, student):
        if student.user.is_superuser: return True

        if student.has_perm('questions.can_approve'):
            return student.get_previous_stages().filter(id=self.stage.id).exists()

        return False

    def name_for_form_fields(self):
        return self.name.replace(" ", "_").replace(",", "").lower()


class TeachingBlockYearManager(models.Manager):
    def get_all_blocks_for_stages(self, stages):
        if not isinstance(stages, (list, tuple, models.query.QuerySet)):
            stages = [stages, ]

        return self.get_queryset().filter(block__stage__in=stages)

    def get_blocks_with_pending_questions_for_stages(self, stages):
        all_blocks_for_stages = self.get_all_blocks_for_stages(stages)

        blocks = all_blocks_for_stages.filter(activities__questions__status=Question.PENDING_STATUS)

        return blocks.distinct().order_by("year", "block")

    def get_blocks_with_unassigned_pending_questions_for_stages(self, stages):
        all_blocks_for_stages = self.get_all_blocks_for_stages(stages)

        blocks = all_blocks_for_stages.filter(activities__questions__in=Question.objects.get_unassigned_pending_questions())

        return blocks.distinct().order_by("year", "block")

    def get_blocks_with_flagged_questions_for_stages(self, stages):
        all_blocks_for_stages = self.get_all_blocks_for_stages(stages)

        return all_blocks_for_stages.filter(activities__questions__status=Question.FLAGGED_STATUS).distinct().order_by("year", "block")

    def get_all_blocks_for_year_and_stages(self, year, stages):
        # Returns all of the blocks for the supplied year which were
        # 1. In one of the supplied stages
        # 2. a. Released in that particular year, OR
        #    b. Starting in that particular year
        all_blocks_for_stages = self.get_all_blocks_for_stages(stages)

        return all_blocks_for_stages.filter(models.Q(release_date__year=year) | models.Q(start__year=year)).distinct()

    def get_released_blocks_for_year_and_date_and_stages(self, year, date, stages):
        # Returns all the blocks for the year which were released before the date provide. 
        all_blocks_for_stages = self.get_all_blocks_for_stages(stages)

        return all_blocks_for_stages.filter(year=year, release_date__lte=date)

    def get_released_blocks_for_year_and_date_and_student(self, year, date, student):
        if student.user.is_superuser:
            stages = Stage.objects.all()
        elif student.has_perm("questions.can_approve"):
            stages = student.get_all_stages()
        else:
            stages = student.get_current_stage()

        blocks = self.get_released_blocks_for_year_and_date_and_stages(year, date, stages)

        if student.user.is_superuser or student.has_perm("questions.can_approve"):
            return blocks

        return blocks.filter(activities__questions__creator=student).distinct()

    def get_released_block_years_for_student(self, student):
        # The following conditions apply:
        # 1. A student must have written questions for a block to be able to see all of its questions.
        # 2. A student may not see the previous questions for a block until the questions are released
        #    for the year to which they have contributed.
        # 3. If the block year to which a student has contributed is released, they may see up to the
        #    latest block year released for that block.

        # First we get all of block_years containing questions written by the student.
        block_years = self.get_queryset().filter(activities__questions__creator=student).distinct()

        # Next we calculate the latest year of release for each block year the student has written questions for.
        # A stupid workaround we need to do because django's annotate doesn't let you annotate over subsets of a queryset.
        block_years = block_years.extra(select=collections.OrderedDict([
                ('latest_release_year', 'SELECT MAX(tby1.year) FROM questions_teachingblockyear tby1 WHERE tby1.block_id = questions_teachingblockyear.block_id AND tby1.release_date IS NOT NULL AND tby1.release_date <= %s'),
            ]), select_params=(timezone.now(),))

        released_block_year_conditions = models.Q()

        # If the year they have written questions for is already released, they may see up to the latest year of release.
        for block_year in block_years:
            if block_year.year <= block_year.latest_release_year:
                released_block_year_conditions |= models.Q(block=block_year.block, year=block_year.latest_release_year)

        # released_block_years_conditions restricts the block years only to those which satisfy the conditions above.
        return self.get_queryset().filter(released_block_year_conditions)

    def get_unreleased_blocks_for_student(self, student):
        current_date = datetime.datetime.now()
        if student.has_perm("questions.can_approve"):
            stages = student.get_all_stages()
        else:
            stages = student.get_current_stage()

        all_blocks_for_stages = self.get_all_blocks_for_stages(stages)

        release_date_null = models.Q(release_date__isnull=True)
        release_date_too_early = models.Q(release_date__gt=current_date)
        return all_blocks_for_stages.filter(release_date_null | release_date_too_early)

    def all_open_blocks(self):
        return self.get_queryset().filter(start__lte=datetime.datetime.now(), close__gte=datetime.datetime.now())

    def get_open_blocks_for_year_and_date_and_stages(self, year, date, stages):
        all_blocks_for_stages = self.get_all_blocks_for_stages(stages)

        # We want all blocks which were open in the specified year. This means that 
        return all_blocks_for_stages.filter(year=year, end__gte=date, start__lte=date)

    def get_open_blocks_for_year_and_date_and_student(self, year, date, student):
        if student.user.is_superuser:
            stages = student.get_all_stages()
        # elif student.has_perm("questions.can_approve"):
        #     stages = student.get_previous_stages()
        else:
            stages = student.get_current_stage()

        blocks = self.get_open_blocks_for_year_and_date_and_stages(year, date, stages)

        return blocks.distinct()

    def get_from_kwargs(self, **kwargs):
        return self.get_queryset().select_related().get(block__code=kwargs.get("code"), year=kwargs.get("year"))

    def get_open_blocks_assigned_to_student(self, student):
        current_date = datetime.datetime.now()
        open_blocks = self.get_open_blocks_for_year_and_date_and_student(current_date.year, current_date, student)

        return open_blocks.filter(activities__question_writers=student)

    def get_blocks_requiring_approval_for_student(self, student):
        if not student.has_perm('questions.can_approve'): return self.none()

        blocks = self.get_queryset()
        if not student.user.is_superuser:
            blocks = self.get_all_blocks_for_stages(student.get_previous_stages())

        return blocks.filter(activities__questions__in=Question.objects.get_unassigned_pending_questions()).distinct()



class TeachingBlockYear(models.Model):
    ACTIVITY_MODE = 0
    WEEK_MODE = 1

    MODE_CHOICES = (
        (ACTIVITY_MODE, 'By activity'),
        (WEEK_MODE, 'By week')
    )
    year = models.IntegerField()
    start = models.DateField(verbose_name='Start date')
    end = models.DateField(verbose_name='End date')
    close = models.DateField(verbose_name='Close date')
    release_date = models.DateField(verbose_name='Release date', blank=True, null=True)
    activity_capacity = models.IntegerField(verbose_name='Maximum users per activity', default=2)
    sign_up_mode = models.IntegerField(choices=MODE_CHOICES)
    weeks = models.IntegerField(verbose_name='Number of weeks')
    block = models.ForeignKey(TeachingBlock, related_name="years")

    objects = TeachingBlockYearManager()

    class Meta:
        unique_together = ('year', 'block')
        ordering = ('year', 'block__sort_index')

    def __unicode__(self):
        return "%s, %d" % (self.block, self.year)

    def filename(self):
        spaceless = "".join(self.name.split())
        commaless = "".join(spaceless.split(","))
        return "%s%d" % (commaless, self.year)

    def __init__(self, *args, **kwargs):
        super(TeachingBlockYear, self).__init__(*args, **kwargs)
        # Adds properties to the model to check the mode, e.g. self.by_activity
        for k in self.__class__.__dict__.keys():
            if not "_MODE" in k or hasattr(self, "by_%s" % k.split("_")[0].lower()):
                continue

            self.add_model_mode_property_method(k)

    def add_model_mode_property_method(self, k):
        def check_mode_function(self):
            return self.sign_up_mode == getattr(self, k)

        setattr(self.__class__, "by_%s" % k.split("_")[0].lower(), property(check_mode_function))

    def get_url_kwargs(self):
        return {'code': self.block.code, 'year': self.year}

    def get_activity_display_url(self):
        return reverse('block-activities', kwargs=self.get_url_kwargs())

    def get_approval_assign_url(self):
        return reverse('approve-choose-activity', kwargs=self.get_url_kwargs())

    def get_activity_upload_url(self):
        return reverse('block-activity-upload', kwargs=self.get_url_kwargs())

    def get_activity_upload_submit_url(self):
        return reverse('block-activity-upload-submit', kwargs=self.get_url_kwargs())

    def get_activity_upload_confirm_url(self):
        return reverse('block-activity-upload-confirm', kwargs=self.get_url_kwargs())

    def get_admin_url(self):
        return reverse('block-admin', kwargs=self.get_url_kwargs())

    def get_approval_statistics_url(self):
        return reverse('block-approval-statistics', kwargs=self.get_url_kwargs())

    def get_edit_url(self):
        return reverse('block-edit', kwargs=self.get_url_kwargs())

    def get_download_url(self):
        return reverse('block-download', kwargs=self.get_url_kwargs())

    def get_release_url(self):
        return reverse("block-release", kwargs=self.get_url_kwargs())

    @classmethod
    def get_block_display_url(cls):
        return reverse("block-list")

    @classmethod
    def get_released_block_display_url(cls):
        return reverse('block-released-list')

    @classmethod
    def get_open_block_display_url(cls):
        return reverse('block-open-list')

    @classmethod
    def get_approval_assign_block_list_url(cls):
        return reverse("approve-choose-block")

    def name(self):
        return self.block.name
    name = property(name)

    def stage(self):
        return self.block.stage
    stage = property(stage)

    def code(self):
        return self.block.code
    code = property(code)

    def name_for_form_fields(self):
        return self.block.name_for_form_fields()

    def convert_activities_to_weeks(self, activities):
        weeks = {}
        weeks_list = []

        for activity in activities:
            week = weeks.setdefault(activity.week, [])
            week.append(activity)
        
        for week in weeks:
            individual_week = {'number': week}
            individual_week['activities'] = weeks[week]
            weeks_list.append(individual_week)
        return weeks_list

    def get_activities_as_weeks(self):
        activities = self.activities.select_related().order_by("week", "teaching_activity__activity_type", "position")

        return self.convert_activities_to_weeks(activities)

    def get_pending_unassigned_activities_as_weeks(self):
        # There are two ways a pending question is unassigned:
        # 1. It has no approver.
        # 2. It was completed.
        activities = self.activities.filter(questions__in=Question.objects.get_unassigned_pending_questions()).distinct()

        return self.convert_activities_to_weeks(activities)

    def assigned_activities_count(self):#
        return self.activities.exclude(question_writers=None).count()

    def total_activities_count(self):
        return self.activities.count()

    def assigned_users_count(self):
        return Student.objects.filter(assigned_activities__block_year=self).distinct().count()

    def is_active(self):
        current_year = datetime.datetime.now().year
        if self.release_date:
            return self.release_date.year == current_year

        return self.close.year == current_year

    def student_is_eligible_for_sign_up(self, student):
        return self.block.stage == student.get_current_stage()

    def student_can_sign_up(self, student):
        return self.student_is_eligible_for_sign_up(student) and self.can_sign_up

    def has_started(self):
        return self.start <= datetime.datetime.now().date()

    def has_ended(self):
        return self.end <= datetime.datetime.now().date()

    def has_closed(self):
        return self.close < datetime.datetime.now().date()

    def can_write_questions(self):
        return self.start <= datetime.datetime.now().date() <= self.close
    can_write_questions = property(can_write_questions)

    def released(self):
        return self.release_date and self.release_date <= datetime.datetime.now().date()
    released = property(released)

    def can_access(self):
        return self.can_write_questions or self.released

    def can_sign_up(self):
        return self.start <= datetime.datetime.now().date() <= self.end
    can_sign_up = property(can_sign_up)

    def questions_need_approval(self):
        return bool(self.questions_pending_count())

    def questions_for_status(self, status):
        return Question.objects.filter(teaching_activity_year__block_year=self, status=status)

    def approved_questions(self):
        return self.questions_for_status(status=Question.APPROVED_STATUS)

    def flagged_questions(self):
        return self.questions_for_status(status=Question.FLAGGED_STATUS)

    def questions_approved_count(self):
        return self.approved_questions().count()

    def questions_pending_count(self):
        return Question.objects.filter(teaching_activity_year__block_year=self, status=Question.PENDING_STATUS).count()

    def questions_flagged_count(self):
        return self.flagged_questions().count()

    def total_questions_count(self):
        return Question.objects.filter(teaching_activity_year__block_year=self).exclude(status=Question.DELETED_STATUS).count()

    def question_count_for_student(self, s):
        return Question.objects.filter(teaching_activity_year__block_year=self, creator=s).count()

    def questions_written_for_student(self, s):
        return Question.objects.filter(teaching_activity_year__block_year=self, creator=s).exists()

    def get_latest_approved_records(self):
        approval_records = ApprovalRecord.objects.filter(question__teaching_activity_year__block_year=self) \
            .annotate(max=models.Max('question__approval_records__date_completed')) \
            .filter(max=models.F('date_completed')) \
            .select_related('question') \
            .filter(status=ApprovalRecord.APPROVED_STATUS)

        return approval_records.order_by("approver__user__username").select_related("approver", "approver__user")


class TeachingActivityManager(models.Manager):
    def get_from_kwargs(self, **kwargs):
        return self.get_queryset().get(reference_id=kwargs.get("reference_id"))


class TeachingActivity(models.Model, ObjectCacheMixin):
    LECTURE_TYPE = 1
    PBL_TYPE = 0
    PRACTICAL_TYPE = 3
    SEMINAR_TYPE = 4
    WEEK_TYPE = 5
    TYPE_CHOICES = (
        (LECTURE_TYPE, 'Lecture'),
        (PBL_TYPE, 'PBL'),
        (PRACTICAL_TYPE, 'Practical'),
        (SEMINAR_TYPE, 'Seminar'),
        (WEEK_TYPE, 'Week'),
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

    def get_absolute_url(self):
        return reverse('activity-view', kwargs=self.get_url_kwargs())

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
            if k == cls.PRACTICAL_TYPE: continue
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

        return self.current_block_year().block.is_viewable_by(student)

    def student_can_view_sign_up_information(self, student):
        current_block = self.current_block_year()

        return not current_block.released and current_block.student_is_eligible_for_sign_up(student)

    def student_is_eligible_for_sign_up(self, student):
        return self.current_block_year().student_is_eligible_for_sign_up(student)

    def student_can_sign_up(self, student):
        # The student can sign up if the following conditions are met:
        # 1. The current activity year does not have enough writers
        # 2. They are not already signed up for that activity
        # 3. They can sign up for activities within the particular block.
        current_year = self.current_activity_year()

        return not current_year.enough_writers() and not self.has_student(student) and current_year.block_year.student_can_sign_up(student)

    def student_can_unassign_activity(self, student):
        return self.has_student(student) and self.current_block_year().can_sign_up and not self.student_has_written_questions(student)

    def approved_questions_are_viewable_by(self, student):
        if student.user.is_superuser: return True

        if self.student_has_written_questions(student): return True
        return self.current_block_year().block.approved_questions_are_viewable_by(student)

    def questions_can_be_written_by(self, student):
        if student.user.is_superuser: return True

        current_year = self.current_activity_year()
        return self.has_student(student) and current_year.block_year.can_write_questions

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
        return self.current_activity_year().questions_left_for(student)

    def current_activity_year(self):
        CURRENT_YEAR_CACHE = "_current_year_cached"

        value = self.get_cache_value(CURRENT_YEAR_CACHE)
        if value: return value

        years = self.years.select_related("block_year").select_related("block_year__block")

        try:
            current_activity_year = years.get(block_year__year=datetime.datetime.now().year)
        except TeachingActivityYear.DoesNotExist:
            current_activity_year = years.order_by("-block_year__year")[0]

        self.set_cache_value(CURRENT_YEAR_CACHE, current_activity_year)
        return current_activity_year
        
    def current_block_year(self):
        return self.current_activity_year().block_year

    def years_available(self):
        return [activity_year.block_year.year for activity_year in self.years.select_related("block_year").order_by("block_year__year")]

    def add_student(self, student):
        current_year = self.current_activity_year()
        current_year.question_writers.add(student)
        current_year.save()

    def remove_student(self, student):
        current_year = self.current_activity_year()
        current_year.question_writers.remove(student)

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


class TeachingActivityYearManager(models.Manager):
    def get_activities_assigned_to(self, student):
        return self.get_queryset().filter(question_writers=student)

    def get_unreleased_activities_assigned_to(self, student):
        unreleased_blocks = TeachingBlockYear.objects.get_unreleased_blocks_for_student(student)
        return self.get_activities_assigned_to(student).filter(block_year__in=unreleased_blocks)

    def get_from_kwargs(self, **kwargs):
        activity = self.get_queryset().filter(teaching_activity__reference_id=kwargs.get('reference_id'))
        if 'year' in kwargs:
            activity = activity.filter(block_year__year=kwargs.get('year'))
        return activity.get()


class TeachingActivityYear(models.Model):
    teaching_activity = models.ForeignKey(TeachingActivity, related_name="years")
    week = models.IntegerField()
    position = models.IntegerField()
    block_year = models.ForeignKey(TeachingBlockYear, related_name='activities')
    question_writers = models.ManyToManyField(Student, blank=True, null=True, related_name='assigned_activities')

    objects = TeachingActivityYearManager()

    class Meta:
        ordering = ('block_year', 'week', 'position')

    def name(self):
        return self.teaching_activity.name
    name = property(name)

    def __unicode__(self):
        return "%s" % (self.name, )

    def get_old_url_kwargs(self):
        return {'id': self.id, }

    def get_url_kwargs(self):
        return {'reference_id': self.teaching_activity.reference_id, 'year': self.block_year.year}

    def get_approval_assign_url(self):
        return reverse('activity-approval-assign', kwargs=self.get_url_kwargs())

    def activity_type(self):
        return self.teaching_activity.activity_type
    activity_type = property(activity_type)

    def get_activity_type_display(self):
        return self.teaching_activity.get_activity_type_display()

    def reference_id(self):
        return self.teaching_activity.reference_id
    reference_id = property(reference_id)

    def current_block(self):
        return self.block_year

    def set_cache_value(self, attribute, value):
        setattr(self, attribute, value)

    def get_cache_value(self, attribute):
        if hasattr(self, attribute):
            return getattr(self, attribute)

    def question_writer_count(self):
        COUNT_CACHE_ATTR = "_question_writer_count"
        if hasattr(self, COUNT_CACHE_ATTR):
            return getattr(self, COUNT_CACHE_ATTR)

        count = self.question_writers.count()
        setattr(self, COUNT_CACHE_ATTR, count)

        return count

    def enough_writers(self):
        return self.question_writer_count() >= self.current_block().activity_capacity

    def has_writers(self):
        return bool(self.question_writer_count())

    def has_questions(self):
        return self.questions.exists()

    def has_student(self, student):
        return self.teaching_activity.has_student(student)

    def has_assigned_approver(self):
        # If an activity has an assigned approver then of all the pending questions
        # 1. None should lack an approver (approver__isnull=True)
        # 2. None should be complete (date_completed__isnull=False)
        questions = self.questions.filter(status=Question.PENDING_STATUS) \
                .filter(models.Q(approver__isnull=True) | models.Q(date_completed__isnull=False))

        return not questions.exists()

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
            questions = questions.exclude(status=Question.DELETED_STATUS)

        if not student.has_perm('questions.can_approve'):
            # The user is not an approver so they are only allowed to view questions they wrote, or
            # questions which have been approved.
            questions = questions.filter(
                models.Q(creator=student) | models.Q(status=Question.APPROVED_STATUS)
            )

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

    def get_unassigned_pending_questions(self):
        # Pending questions are unassigned if one of the two are satisfied:
        # 1. It was completed.
        # 2. It has no approver.
        return self.get_queryset().filter(status=Question.PENDING_STATUS) \
            .filter(models.Q(date_completed__isnull=False) | models.Q(approver__isnull=True)) \
            .distinct()

    def get_approved_questions_for_block_and_years(self, block, years):
        return self.get_queryset().filter(teaching_activity_year__block_year__block=block) \
                                   .filter(teaching_activity_year__block_year__year__in=years) \
                                   .filter(status=Question.APPROVED_STATUS)


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
    status = models.IntegerField(choices=STATUS_CHOICES, default=PENDING_STATUS)
    date_assigned = models.DateTimeField(blank=True, null=True)
    date_completed = models.DateTimeField(blank=True, null=True)
    approver = models.ForeignKey(Student, related_name="assigned_questions", blank=True, null=True)

    reasons = generic.GenericRelation('questions.Reason', content_type_field="related_object_content_type", object_id_field="related_object_id")

    objects = QuestionManager()

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

        if "{" not in self.explanation:
            explanation = self.options_dict()
            for option, label in explanation.items():
                if option == self.answer:
                    explanation[option] = self.explanation
                else:
                    explanation[option] = ""

            self.explanation = json.dumps(explanation)

    def __str__(self):
        return "%s" % (self.id,)

    def was_assigned_before_being_completed(self):
        return self.date_assigned and (not self.date_completed or self.date_assigned < self.date_completed)

    def get_approval_records_recent_first(self):
        return self.approval_records.order_by("-date_assigned")

    def get_url_kwargs(self):
        return {'pk': self.pk, 'reference_id': self.teaching_activity_year.teaching_activity.reference_id, }

    @classmethod
    def request_is_in_multiple_approval_mode(self, request):
        return request.GET.get("mode") == "multiple"

    def get_query_string(self, multiple_approval_mode=False):
        params = []
        if multiple_approval_mode:
            params.append("mode=multiple")

        if not params:
            return ""
        return "?%s" % ("&".join(params),)

    def get_absolute_url(self):
        return reverse('question-view', kwargs=self.get_url_kwargs())

    def get_edit_url(self, multiple_approval_mode=False):
        query_string = self.get_query_string(multiple_approval_mode=multiple_approval_mode)
        return "%s%s" % (reverse('question-edit', kwargs=self.get_url_kwargs()), query_string)

    def get_add_to_specification_url(self):
        return reverse('quiz-spec-add', kwargs=self.get_url_kwargs())

    def get_approval_url(self, multiple_approval_mode=False):
        query_string = self.get_query_string(multiple_approval_mode=multiple_approval_mode)
        return "%s%s" % (reverse('question-approval', kwargs=self.get_url_kwargs()), query_string)

    def get_next_approval_url(self):
        return reverse('approve-assigned-next', kwargs={'previous_question_id': self.id, })

    def get_approval_history_url(self):
        return reverse('question-approval-history', kwargs=self.get_url_kwargs())

    def get_flag_url(self, multiple_approval_mode=False):
        query_string = self.get_query_string(multiple_approval_mode=multiple_approval_mode)
        return "%s%s" % (reverse('question-flag', kwargs=self.get_url_kwargs()), query_string)

    def is_viewable_by(self, student):
        # A student can view a question in the following situations:
        # 1. They wrote it and it is not deleted.
        # 2. They wrote questions for that particular block and it is approved.
        # 3. They are the superuser.

        if student.user.is_superuser:
            return True

        if not self.deleted:
            if student.has_perm('questions.can_approve'):
                return True

            if self.approved and self.teaching_activity_year.block_year.block.approved_questions_are_viewable_by(student):
                return True
            else:
                return student == self.creator

        return False

    def is_editable_by(self, student):
        # A student can edit a question in the following situations:
        # 1. They wrote it, and the block is open for writing.
        # 2. They are an approver (or the superuser).
        return student.has_perm("questions.can_approve") or (self.creator == student and self.teaching_activity_year.block_year.can_write_questions)

    def change_status(self, new_status, student):
        # A manual change is once which occurs outside the regular approval process.
        # This is when:
        # 1. The question is currently complete.
        # 2. The question is currently assigned but the person changing the status is different.
        #
        # If the question is brand new and has not been assigned, approver is None and the below
        # code also treats it as a manual change.
        is_manual_change = False

        if self.date_completed:
            # We only need to create an approval record for the current status
            # if it has already been completed.
            self.create_new_record()
            is_manual_change = True
        else:
            is_manual_change = student != self.approver

        self.status = new_status
        self.approver = student
        if is_manual_change:
            self.date_assigned = datetime.datetime.now()

        # We want the date_completed to be identical to the date_assigned when the status
        # is manually changed instead of through the approval process.
        self.date_completed = self.date_assigned if is_manual_change else datetime.datetime.now()
        self.save()

    def create_new_record(self):
        approval_record = ApprovalRecord()
        approval_record.question = self
        approval_record.status = self.status
        approval_record.approver = self.approver
        approval_record.date_assigned = self.date_assigned
        approval_record.date_completed = self.date_completed
        approval_record.save()

        if self.flagged:
            for reason in self.reasons.filter(reason_type=Reason.TYPE_FLAG):
                reason.related_object = approval_record
                reason.save()

        return approval_record


    def assign_to_student(self, student):
        if self.date_completed:
            # The question already has a status. If it was made pending, then
            # we can assign an approver, but we have to create the history first.
            if self.status == self.PENDING_STATUS:
                self.create_new_record()
                self.date_completed = None
            else:
                # The question is not pending and thus does not accept a new approver.
                return

        self.approver = student
        self.date_assigned = datetime.datetime.now()
        self.save()

    def add_model_status_property_method(self, k):
        def check_status_function(self):
            return self.status == getattr(Question, k)

        setattr(self.__class__, k.split("_")[0].lower(), property(check_status_function))

    def json_repr(self, include_answer=False):
        options = self.options_dict()
        label = options.keys()
        label.sort()
        options['labels'] = label
        json_repr = {'id': self.id, 'body': linebreaksbr(self.body), 'options': options}
        if include_answer:
            json_repr['answer'] = self.answer
            explanation = self.explanation_dict()
            labels = explanation.keys()
            labels.sort()
            explanation['labels'] = labels
            json_repr['explanation'] = explanation
            json_repr['url'] = self.get_absolute_url()

        return json_repr

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

    def explanation_dict(self):
        if self.sorted_options:
            explanation_dict = SortedDict()
            for letter, option in self.sorted_options.items():
                explanation_dict[letter] = option["explanation"]
            return explanation_dict
        else:
            explanation_dict = SortedDict()
            # print "Generating explanation"
            if "{" in self.explanation:
                explanation = json.loads(self.explanation)
            else:
                explanation = self.options_dict()
                for option, label in explanation.items():
                    if option == self.answer:
                        explanation[option] = self.explanation
                    else:
                        explanation[option] = ""
                # print explanation
            keys = explanation.keys()
            keys.sort()
            for key in keys:
                explanation_dict[key] = explanation[key]
            return explanation_dict

    def explanation_for_answer(self):
        explanation = self.explanation_dict()
        if explanation:
            return explanation[self.answer]
        else:
            return self.explanation

    def user_is_creator(self, user):
        return user.has_perm('questions.can_approve') or user.student == self.creator

    def latest_approver(self):
        return self.approver

    def principal_comments(self):
        return self.comments.filter(reply_to__isnull=True)

    def body_html(self):
        return format_html(markdown2.markdown(self.body))

    def explanation_html(self):
        return format_html(markdown2.markdown(self.explanation))

    def set_body_html(self, body):
        self.body = html2text.html2text(body)

    def set_explanation_html(self, body):
        self.body = html2text.html2text(body)

    def block(self):
        return self.teaching_activity_year.block_year

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

    def associated_reasons(self):
        reasons_associated_with_question = Reason.objects.get_reasons_associated_with_object(self)
        reasons_associated_with_records = Reason.objects.get_reasons_associated_with_multiple_objects(self.approval_records.all())
        reasons = list(reasons_associated_with_question) + list(reasons_associated_with_records)
        reasons.sort(key=lambda r: r.date_created, reverse=True)
        return reasons


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
        allowed_blocks = TeachingBlock.objects.get_released_blocks_for_student(student)
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
        return self.get_questions().order_by('teaching_activity_year__block_year')

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

