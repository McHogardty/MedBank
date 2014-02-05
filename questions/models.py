from django.db import models
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.conf import settings
from django.utils.html import format_html
from django.utils.datastructures import SortedDict

import json
import datetime
import string
import markdown2
import html2text


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


class Year(models.Model):
    stage = models.ForeignKey(Stage)
    student = models.ForeignKey('questions.Student')
    year = models.IntegerField()

    class Meta:
        unique_together = ('student', 'year')

    def __unicode__(self):
        return "%s: %s, %d" % (self.student, self.stage, self.year)


class Student(models.Model):
    user = models.OneToOneField(User)
    stages = models.ManyToManyField(Stage, through='questions.Year')

    def __unicode__(self):
        return self.user.username


    def add_stage(self, stage):
        try:
            y = Year.objects.get(student=self, year__exact=datetime.datetime.now().year)
            print "Stage retrieved"
        except Year.DoesNotExist:
            y = Year()
            y.student = self
            y.year = datetime.datetime.now().year
            print "Stage created"
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

    def current_assigned_activities(self):
        return self.assigned_activities.filter(models.Q(block_year__release_date__year=datetime.datetime.now().year) | models.Q(block_year__start__year=datetime.datetime.now().year))

    def questions_due_soon_count(self):
        count = self.assigned_activities.filter(block_year__close__range=[datetime.datetime.now(), datetime.datetime.now()+datetime.timedelta(weeks=1)]).count() * settings.QUESTIONS_PER_USER
        return count

    def future_block_count(self):
        return TeachingBlockYear.objects.filter(close__gte=datetime.datetime.now(), activities__question_writers=self).count()


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
    stage = models.ForeignKey(Stage)
    number = models.IntegerField(verbose_name=u'Block number')

    def __unicode__(self):
        return self.name


class TeachingBlockYear(models.Model):
    ACTIVITY_MODE = 0
    WEEK_MODE = 1

    MODE_CHOICES = (
        (ACTIVITY_MODE, 'By activity'),
        (WEEK_MODE, 'By week')
    )
    year = models.IntegerField(null=True)
    start = models.DateField(verbose_name=u'Start date')
    end = models.DateField(verbose_name=u'End date')
    close = models.DateField(verbose_name=u'Close date')
    release_date = models.DateField(verbose_name=u'Release date', blank=True, null=True)
    activity_capacity = models.IntegerField(verbose_name=u'Maximum users per activity', default=2)
    sign_up_mode = models.IntegerField(choices=MODE_CHOICES)
    weeks = models.IntegerField(verbose_name=u'Number of weeks')
    block = models.ForeignKey(TeachingBlock, related_name="years")

    class Meta:
        unique_together = ('year', 'block')

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

    def name(self):
        return self.block.name
    name = property(name)

    def stage(self):
        return self.block.stage
    stage = property(stage)

    def number(self):
        return self.block.number
    number = property(number)

    def assigned_activities_count(self):
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
        print "Can access is %s" % (self.can_write_questions or self.released,)
        return self.can_write_questions or self.released

    def can_sign_up(self):
        return self.start <= datetime.datetime.now().date() <= self.end
    can_sign_up = property(can_sign_up)

    def questions_need_approval(self):
        return bool(self.activities.filter(questions__status=Question.PENDING_STATUS).count())

    def questions_approved_count(self):
        return Question.objects.filter(teaching_activity__block_year=self, status=Question.APPROVED_STATUS).count()

    def questions_pending_count(self):
        return Question.objects.filter(teaching_activity__block_year=self, status=Question.PENDING_STATUS).count()

    def questions_flagged_count(self):
        return Question.objects.filter(teaching_activity__block_year=self, status=Question.FLAGGED_STATUS).count()

    def question_count_for_student(self, s):
        return Question.objects.filter(teaching_activity__block_year=self, creator=s).count()



class TeachingActivity(models.Model):
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
        (WEEK_TYPE, ''),
    )
    id = models.IntegerField(primary_key=True, verbose_name=u'ID')
    name = models.CharField(max_length=100)
    week = models.IntegerField()
    position = models.IntegerField()
    block_year = models.ManyToManyField(TeachingBlockYear, related_name='activities')
    question_writers = models.ManyToManyField(Student, blank=True, null=True, related_name='assigned_activities')
    activity_type = models.IntegerField(choices=TYPE_CHOICES)

    class Meta:
        unique_together = ('id', 'week', 'position')

    def __unicode__(self):
        return self.name

    def current_block(self):
        try:
            return self.block_year.get(year=datetime.datetime.now().year)
        except TeachingBlockYear.DoesNotExist:
            return None

    def enough_writers(self):
        return self.question_writers.count() >= self.current_block().activity_capacity

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

    class Meta:
        permissions = (
            ('can_approve', 'Can approve questions'),
        )

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

    def options_dict(self):
        d = SortedDict()
        e = json.loads(self.options)
        f = e.keys()
        f.sort()
        for k in f:
            d[k] = e[k]
        return d

    def options_list(self):
        l = list(json.loads(self.options).iteritems())
        l.sort(key=lambda x: x[0])
        return [j for i, j in l]

    def options_tuple(self):
        j = json.loads(self.options)
        return [(c, j[c]) for c in string.ascii_uppercase[:len(j)]]

    def user_is_creator(self, user):
        return user.has_perm('questions.can_approve') or user.student == self.creator

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


class QuizAttempt(models.Model):
    student = models.ForeignKey(Student, related_name="quiz_attempts")
    date_submitted = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return u"Quiz attempt for %s" % self.student


class QuestionAttempt(models.Model):
    GUESS = 1
    UNSURE = 2
    NEUTRAL = 3
    SURE = 4
    CERTAIN = 5

    CONFIDENCE_CHOICES = (
        (GUESS, "I guessed"),
        (UNSURE, "I'm doubtful"),
        (NEUTRAL, "Feeling neutral"),
        (SURE, "Fairly sure"),
        (CERTAIN, "I'm certain"),
    )

    quiz_attempt = models.ForeignKey(QuizAttempt, related_name="questions")
    question = models.ForeignKey(Question, related_name="attempts")
    position = models.PositiveIntegerField()
    answer = models.CharField(max_length=1, blank=True, null=True)
    time_taken = models.PositiveIntegerField()
    confidence_rating = models.IntegerField(choices=CONFIDENCE_CHOICES, blank=True, null=True)


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


class Reason(models.Model):
    body = models.TextField()
    question = models.ForeignKey(Question, related_name="reasons_edited")
    creator = models.ForeignKey(Student, related_name="reasons")
    date_created = models.DateTimeField(auto_now_add=True)


class Comment(models.Model):
    body = models.TextField(verbose_name="Comment")
    question = models.ForeignKey(Question, related_name="comments")
    creator = models.ForeignKey(Student, related_name="comments")
    date_created = models.DateTimeField(auto_now_add=True)
    reply_to = models.ForeignKey('self', blank=True, null=True)

    def replies(self):
        return Comment.objects.filter(reply_to=self)

