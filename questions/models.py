from django.db import models
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.conf import settings
from django.utils.html import format_html
from django.utils.datastructures import SortedDict

import json
import datetime
import string
import random
import markdown2
import html2text
import hashlib

def int_to_base(x, base, places=0):
    """ A method which converts any base 10 integer (x) into its representation in a base using the lowercase alphabet in a fixed number of characters (places)."""
    digs = string.lowercase

    digits = []
    while x:
        digits.append(digs[x % base])
        x /= base
    if places and len(digits) > places: raise ValueError("There must be enough places to represent the number.")

    while places and len(digits) < places:
        digits.append(digs[0])

    digits.reverse()
    return u''.join(digits)


def hex_to_base_26(hex):
    """A method which converts a hexadecimal string (hex) into its base 26 representation using the lowercase alphabet."""
    return int_to_base(int(hex, 16), 26, places=36)


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
    year = models.IntegerField()
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
        return Question.objects.filter(teaching_activity_year__block_year=self, status=Question.APPROVED_STATUS).count()

    def questions_pending_count(self):
        return Question.objects.filter(teaching_activity_year__block_year=self, status=Question.PENDING_STATUS).count()

    def questions_flagged_count(self):
        return Question.objects.filter(teaching_activity_year__block_year=self, status=Question.FLAGGED_STATUS).count()

    def question_count_for_student(self, s):
        return Question.objects.filter(teaching_activity_year__block_year=self, creator=s).count()


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
    name = models.CharField(max_length=100)
    activity_type = models.IntegerField(choices=TYPE_CHOICES)
    reference_id = models.IntegerField(blank=True, null=True)

    def __unicode__(self):
        return self.name


class TeachingActivityYear(models.Model):
    teaching_activity = models.ForeignKey(TeachingActivity, related_name="years")
    week = models.IntegerField()
    position = models.IntegerField()
    block_year = models.ForeignKey(TeachingBlockYear, related_name='activities')
    question_writers = models.ManyToManyField(Student, blank=True, null=True, related_name='assigned_activities')

    def __unicode__(self):
        return self.name

    def name(self):
        return self.teaching_activity.name
    name = property(name)

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
    teaching_activity_year = models.ForeignKey(TeachingActivityYear, related_name="questions")
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

    def block(self):
        return self.teaching_activity_year.block_year


class QuizSpecification(models.Model):
    name = models.CharField(max_length=100)
    stage = models.ForeignKey(Stage, blank=True, null=True)
    # A 160-bit SHA1 hash converted to base 26 requires 36 characters to be represented.
    slug = models.SlugField(max_length=36)

    def __unicode__(self):
        return self.name

    def generate_slug(self):
        return hex_to_base_26(hashlib.sha1(self.name).hexdigest())

    def get_questions(self):
        questions_to_return = []

        for q in self.questions.all():
            questions_to_return += q.get_questions()

        return questions_to_return


class QuizQuestionSpecification(models.Model):
    SPECIFIC_QUESTION = 0
    RANDOM_FROM_BLOCK = 1

    SPECIFICATION_TYPE_CHOICES = (
        (SPECIFIC_QUESTION, "A specific question"),
        (RANDOM_FROM_BLOCK, "A random choice of questions from a block")
    )

    specification_type = models.IntegerField(choices=SPECIFICATION_TYPE_CHOICES)
    quiz_specification = models.ForeignKey(QuizSpecification, related_name="questions")
    parameters = models.TextField()

    def __unicode__(self):
        return "%s, %s" % (self.get_display(), self.quiz_specification)

    def get_display(self):
        if self.specification_type == self.SPECIFIC_QUESTION:
            return "%s (%s)" % (self.get_specification_type_display(), self.get_parameters_dict()["question"])

    @classmethod
    def from_parameters(cls, **kwargs):
        allowed_kwargs = ['question',]
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

    def get_parameters_dict(self):
        return json.loads(self.parameters)

    def get_questions(self):
        parameters = self.get_parameters_dict()
        questions_to_return = []

        if 'question' in parameters:
            condition = models.Q(id__in=[parameters["question"],])

        questions_to_return += Question.objects.filter(condition)

        return questions_to_return


class QuizAttempt(models.Model):
    student = models.ForeignKey(Student, related_name="quiz_attempts")
    date_submitted = models.DateTimeField(auto_now_add=True)
    quiz_specification = models.ForeignKey(QuizSpecification, related_name="attempts", blank=True, null=True)
    slug = models.SlugField(max_length=36)

    def __unicode__(self):
        return u"Quiz attempt for %s" % self.student

    def get_questions(self):
        q = []

        for question in self.questions.all():
            qq = question.question
            qq.choice = qq.answer = question.answer
            qq.position = question.position
            qq.time_taken = question.time_taken
            qq.confidence_rating = question.confidence_rating
            q.append(qq)

        return q

    def generate_slug(self):
        spec = self.quiz_specification.id if self.quiz_specification else ""
        date_string = datetime.datetime.now().strftime("%Y%m%d %H%M")
        rand_string = "".join(random.choice(string.lowercase) for i in range(6))
        to_hash = "%s%s%s%s" % (self.student.user.username, date_string, spec, rand_string)
        return hex_to_base_26(hashlib.sha1(to_hash).hexdigest())


@receiver(models.signals.pre_save, sender=QuizSpecification)
@receiver(models.signals.pre_save, sender=QuizAttempt)
def generate_quiz_slug(sender, instance, **args):
    instance.slug = instance.generate_slug()


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

