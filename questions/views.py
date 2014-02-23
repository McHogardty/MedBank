from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext, loader
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import HttpResponse, Http404, HttpResponseServerError
from django.core.urlresolvers import reverse
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.views.generic import View, ListView, DetailView, FormView, TemplateView
from django.views.generic.base import RedirectView
from django.views.generic.edit import CreateView, UpdateView
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django import db

import forms
import models
import document
import queue
import tasks

import csv
import json
import datetime
import collections
import os
import pwd
import random
import smtplib
import html2text
import time


def class_view_decorator(function_decorator):
    """Convert a function based decorator into a class based decorator usable
    on class based Views.

    Can't subclass the `View` as it breaks inheritance (super in particular),
    so we monkey-patch instead.
    """

    def simple_decorator(View):
        View.dispatch = method_decorator(function_decorator)(View.dispatch)
        return View

    return simple_decorator


@class_view_decorator(login_required)
class AllBlocksView(ListView):
    model = models.TeachingBlockYear
    template_name = "choose.html"

    def get_queryset(self):
        s = [stage.number for stage in self.request.user.student.get_all_stages()]
        bb = models.TeachingBlockYear.objects.filter(db.models.Q(release_date__year=datetime.datetime.now().year) | db.models.Q(start__year=datetime.datetime.now().year)).filter(block__stage__number__in=s).order_by('block__number')
        print bb.query
        if 'pending' in self.request.GET:
            bb = bb.filter(activities__questions__status=models.Question.PENDING_STATUS).distinct()
        elif 'flagged' in self.request.GET:
            bb = bb.filter(activities__questions__status=models.Question.FLAGGED_STATUS).distinct()
        return bb

    def get_context_data(self, **kwargs):
        c = super(AllBlocksView, self).get_context_data(**kwargs)
        c.update({'flagged': 'flagged' in self.request.GET})
        return c


@class_view_decorator(login_required)
class DashboardView(TemplateView):
    template_name = "dashboard.html"


@class_view_decorator(login_required)
class MyActivitiesView(ListView):
    model = models.TeachingActivityYear
    template_name = "mine.html"

    def get_queryset(self):
        ret = {}
        ta = models.TeachingActivityYear.objects.filter(question_writers=self.request.user).order_by('week', 'position')
        for t in ta:
            l = ret.setdefault(t.block_year, [])
            l.append(t)
        ret = ret.items()
        ret.sort(key=lambda a: a[0].number)
        return ret


@class_view_decorator(login_required)
class AllActivitiesView(ListView):
    model = models.TeachingActivityYear
    template_name = "all2.html"

    def dispatch(self, request, *args, **kwargs):
        r = super(AllActivitiesView, self).dispatch(request, *args, **kwargs)
        b = self.teaching_block
        s = self.request.user.student
        if not b.stage in s.get_all_stages() and not b.question_count_for_student(s):
            raise Http404
        if not b.can_access() and not request.user.has_perm("questions.can_approve"):
            messages.error(request, "That block cannot be accessed right now.")
            return redirect('block-list')
        return r

    def get_teaching_block(self):
        tb = models.TeachingBlockYear.objects.get(block__number=self.kwargs['number'], year=self.kwargs['year'])
        self.teaching_block = tb
        return tb

    def get_queryset(self):
        ta = models.TeachingActivityYear.objects.filter(block_year__block__number=self.kwargs['number'], block_year__year=self.kwargs['year'])
        by_week = {}
        for t in ta:
            l = by_week.setdefault(t.week, [])
            l.append(t)
        for v in by_week.values():
            v.sort(key=lambda t: (t.activity_type, t.position))
        return [(k, not all(t.enough_writers() for t in by_week[k]), by_week[k]) for k in by_week]

    def get_context_data(self, **kwargs):
        c = super(AllActivitiesView, self).get_context_data(**kwargs)
        c['teaching_block'] = self.get_teaching_block()
        if self.teaching_block.released:
            c['override_base'] = "newbase_with_actions.html"
        return c


@class_view_decorator(permission_required('questions.can_approve'))
class AdminView(TemplateView):
    template_name = 'admin.html'

    def get_context_data(self, **kwargs):
        c = super(AdminView, self).get_context_data(**kwargs)
        tb = models.TeachingBlockYear.objects.order_by('block__stage', 'block__number')
        questions_pending = any(b.questions_need_approval() for b in tb)
        questions_flagged = any(b.questions_flagged_count() for b in tb)
        c.update({'blocks': tb, 'questions_pending': questions_pending, 'questions_flagged': questions_flagged,})
        c.update({'debug_mode': settings.DEBUG, 'maintenance_mode': settings.MAINTENANCE_MODE, })
        c.update({'u': pwd.getpwuid(os.getuid()).pw_name, 'd': os.environ})
        return c


class BlockAdminView(DetailView):
    model = models.TeachingBlockYear
    template_name = "admin/block_admin.html"

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()

        return queryset.get(year=self.kwargs["year"], block__number=self.kwargs["number"])


class QueryStringMixin(object):
    def query_string(self):
        allowed = ['show', 'approve', 'flagged']
        g = self.request.GET.keys()
        if not g:
            return ""
        params = [k for k in g if k in allowed]
        return "?%s" % ("&".join(params))


@class_view_decorator(permission_required('questions.can_approve'))
class StartApprovalView(QueryStringMixin, RedirectView):
    permanent = False

    def query_string(self, initial):
        if initial:
            qs =  "?show&approve"
            if 'flagged' in self.request.GET:
                qs += "&flagged"
            return qs
        else:
            return super(StartApprovalView, self).query_string()

    def get_redirect_url(self, number, year, q_id=None):
        try:
            b = models.TeachingBlockYear.objects.get(block__number=number, year=year)
        except models.TeachingBlockYear.DoesNotExist:
            messages.error(self.request, "That teaching block does not exist.")
            return reverse('admin')
        tb = models.TeachingBlockYear.objects.filter(start__lte=datetime.datetime.now().date).latest("start")

        previous_q = None
        try:
            previous_q = models.Question.objects.get(pk=q_id)
        except models.Question.DoesNotExist:
            pass
        if 'flagged' in self.request.GET:
            s = models.Question.FLAGGED_STATUS
        else:
            s = models.Question.PENDING_STATUS
        q = models.Question.objects.filter(teaching_activity_year__block_year=b).filter(
                db.models.Q(status=s) | db.models.Q(pk=q_id)
            )
        try:
            if previous_q:
                q = q.filter(date_created__gte=previous_q.date_created).order_by('date_created')[1:2].get()
            else:
                q = q.order_by('date_created')[:1].get()
        except models.Question.DoesNotExist:
            m = 'All questions for that block have been approved'
            if 'flagged' in self.request.GET:
                m = 'There are no more flagged questions in that block.'
            messages.success(self.request, m)
            return reverse('admin')
        return "%s%s" % (reverse('view', kwargs={'pk': q.id, 'ta_id': q.teaching_activity_year.id}), self.query_string(previous_q == None))


@class_view_decorator(permission_required('questions.can_approve'))
class ApproveQuestionsView(ListView):
    model = models.Question
    template_name = "approve.html"

    def get_query_set(self):
        return models.Question.objects.filter(teaching_activity_year__block=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        c = super(ApproveQuestionsView, self).get_context_data(**kwargs)
        c['questions'] = self.get_queryset()
        return c


def check_ta_perm_for_question(ta_id, u):
    ta = get_object_or_404(models.TeachingActivityYear, pk=ta_id)

    if not u.student in ta.question_writers.all() and not u.has_perm("questions.can_approve"):
        raise PermissionDenied

    return ta


@class_view_decorator(login_required)
class NewQuestion(CreateView):
    model = models.Question
    form_class = forms.NewQuestionForm
    template_name = "new.html"

    def dispatch(self, request, *args, **kwargs):
        self.ta = check_ta_perm_for_question(self.kwargs['ta_id'], self.request.user)
        if not self.ta.current_block().can_write_questions:
            messages.warning(request, "You are not currently able to write questions for this teaching activity.")
            return redirect('ta', pk=self.ta.id)
        return super(NewQuestion, self).dispatch(request, *args, **kwargs)

    def get_initial(self):
        i = super(NewQuestion, self).get_initial().copy()
        i.update({'teaching_activity_year': self.ta, 'creator': self.request.user.student})
        return i

    def get_success_url(self):
        return reverse('view', kwargs={'pk': self.object.id, 'ta_id': self.ta.id})


@class_view_decorator(login_required)
class UpdateQuestion(QueryStringMixin, UpdateView):
    model = models.Question
    form_class = forms.NewQuestionForm
    template_name = "new.html"

    def dispatch(self, request, *args, **kwargs):
        self.ta = check_ta_perm_for_question(self.kwargs['ta_id'], self.request.user)
        return super(UpdateQuestion, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return models.Question.objects.filter(teaching_activity_year__id=self.kwargs['ta_id'])

    def get_object(self):
        o = super(UpdateQuestion, self).get_object()

        if o.creator != self.request.user.student and not self.request.user.has_perm('questions.can_approve'):
            raise PermissionDenied

        return o

    def get_form_kwargs(self):
        k = super(UpdateView, self).get_form_kwargs()
        if self.request.user.has_perm("questions.can_approve") and self.get_object().creator != self.request.user:
            k.update({'admin': True})
        return k

    def form_valid(self, form):
        o = self.get_object()
        if self.request.user.has_perm("questions.can_approve") and o.creator != self.request.user:
            c = form.cleaned_data
            if c['reason']:
                r = models.Reason()
                r.body = c['reason']
                r.creator = self.request.user.student
                r.question = o
                r.save()
        return super(UpdateQuestion, self).form_valid(form)


    def get_success_url(self):
        return "%s%s" % (reverse('view', kwargs={'pk': self.object.id, 'ta_id': self.ta.id}), self.query_string())


@class_view_decorator(login_required)
class AddComment(CreateView):
    model = models.Comment
    form_class = forms.CommentForm
    template_name = "comment.html"

    def dispatch(self, request, *args, **kwargs):
        try:
            self.q = models.Question.objects.get(pk=self.kwargs['pk'])
        except models.Question.DoesNotExist:
            messages.error(self.request, "That question does not exist")
            return redirect('activity-mine')
        if 'comment_id' in self.kwargs:
            try:
                self.c = models.Comment.objects.get(pk=self.kwargs['comment_id'])
            except models.Comment.DoesNotExist:
                messages.error(self.request, "That comment does not exist")
                return redirect('activity-mine')

        return super(AddComment, self).dispatch(request, *args, **kwargs)

    def get_initial(self):
        i = super(AddComment, self).get_initial()
        i.update({'creator': self.request.user, 'question': self.q})
        if 'comment_id' in self.kwargs:
            i.update({'reply_to': self.c})
        return i


    def form_valid(self, form):
        c = form.cleaned_data
        form.save()
        if not c['reply_to']:
            c = {
                'user': self.q.creator.user,
                'link': self.request.build_absolute_uri(reverse('view', kwargs={'pk': self.q.id, 'ta_id': self.q.teaching_activity_year.id}))
            }

            body = loader.render_to_string('email/newcomment.html', c)
            t = tasks.HTMLEmailTask(
                "[MedBank] One of your questions has received a comment",
                body,
                ["%s" % self.q.creator.user.email, ],
            )

            queue.add_task(t)

        return redirect('view', pk=self.q.id, ta_id=self.q.teaching_activity_year.id)


@class_view_decorator(login_required)
class UnassignView(RedirectView):
    permanent = False

    def get_redirect_url(self, pk):
        try:
            ta = models.TeachingActivityYear.objects.get(pk=pk)
        except models.TeachingActivityYear.DoesNotExist:
            return reverse('medbank.views.home')
        if not ta.question_writers.filter(user=self.request.user).count():
            messages.warning(self.request, "You weren't signed up to that activity")
            return reverse('ta', kwargs={'pk': pk})

        if ta.questions_for(self.request.user).count():
            messages.error(self.request, "Once you have started writing questions for an activity, you can't unassign yourself from it.")
            return reverse('ta', kwargs={'pk': pk})

        ta.question_writers.remove(self.request.user.student)
        messages.success(self.request, "You have been unassigned from that activity")
        return reverse('ta', kwargs={'pk': pk})


@login_required
def signup(request, ta_id):
    try:
        ta = models.TeachingActivityYear.objects.get(id=ta_id)
    except models.TeachingActivityYear.DoesNotExist:
        if request.is_ajax():
            return HttpResponse(
                json.dumps({
                    'result': 'error',
                    'summary': 'Hmm... this activity could not be found.',
                    'info': 'Please try again.'
                }),
                mimetype="application/json"
            )
        else:
            messages.error(request, "Hmm... that teaching activity could not be found.")
            return redirect("home")

    already_assigned = request.user.student in ta.question_writers.all()

    if not already_assigned:
        if ta.enough_writers():
            if request.is_ajax():
                return HttpResponse(
                    json.dumps({
                        'result': 'error',
                        'summary': 'We have enough people signed up to this activity.',
                        'info': 'Unfortunately %s people have already signed up for this teaching activity. Please choose another activity for submitting questions.'
                    }),
                    mimetype="application/json"
                )
            else:
                messages.error(request, "Sorry, that activity is already assigned to somebody else.")
                return redirect("questions.views.home")
        if not request.user.student.get_current_stage() == ta.current_block().stage:
            if request.is_ajax():
                return HttpResponse(
                    json.dumps({
                        'result': 'error',
                        'summary': 'This activity is in a different stage to yours.',
                        'info': 'You are unable to sign up to this activity because it is not in your current stage. Please choose another activity for submitting questions.'
                    }),
                    mimetype="application/json"
                )
            else:
                messages.error(request, "You are unable to sign up to this activity because it is not in your current stage. Please choose another activity for submitting questions.")
                return redirect("questions.views.home")        
        ta.question_writers.add(request.user.student)
        ta.save()

    if request.is_ajax():
        return HttpResponse(
            json.dumps({
                'result': 'success',
                'view_url': reverse('ta', kwargs={'pk': int(ta_id)})
            }),
            mimetype="application/json"
        )
    else:
        return redirect("ta", pk=ta_id)


@class_view_decorator(login_required)
class NewActivity(CreateView):
    model = models.TeachingActivityYear
    template_name = "new_ta.html"
    form_class = forms.NewTeachingActivityForm

    def get_context_data(self, **kwargs):
        c = super(NewActivity, self).get_context_data(**kwargs)
        c['heading'] = "activity"
        return c


@class_view_decorator(permission_required('questions.can_approve'))
class NewBlock(CreateView):
    model = models.TeachingBlockYear
    template_name = "new_ta.html"
    form_class = forms.NewTeachingBlockYearForm

    def get_context_data(self, **kwargs):
        c = super(NewBlock, self).get_context_data(**kwargs)
        c['heading'] = "block"
        return c

    def form_valid(self, form):
        c = form.cleaned_data
        b = form.save()
        if c['sign_up_mode'] == models.TeachingBlockYear.WEEK_MODE:
            for w in range(1, c['weeks'] + 1):
                a = models.TeachingActivity()
                a.name = "Week %d" % w
                a.activity_type = models.TeachingActivity.WEEK_TYPE
                a.save()
                tay = models.TeachingActivityYear()
                tay.week = w
                tay.position = 1
                tay.block_year = b
                tay.teaching_activity = a
                tay.save()

        return redirect('admin')

    def get_success_url(self):
        return reverse('admin')


@class_view_decorator(permission_required('questions.can_approve'))
class EditBlock(UpdateView):
    model = models.TeachingBlockYear
    template_name = "new_ta.html"
    form_class = forms.NewTeachingBlockYearForm

    def get_context_data(self, **kwargs):
        c = super(EditBlock, self).get_context_data(**kwargs)
        c['heading'] = "block"
        return c

    def get_object(self):
        return models.TeachingBlockYear.objects.get(year=self.kwargs["year"], block__number=self.kwargs["number"])

    def get_success_url(self):
        return reverse('admin')


@class_view_decorator(login_required)
class ViewActivity(DetailView):
    model = models.TeachingActivityYear


@class_view_decorator(login_required)
class ViewQuestion(DetailView):
    model = models.Question

    def dispatch(self, request, *args, **kwargs):
        r = super(ViewQuestion, self).dispatch(request, *args, **kwargs)

        if self.object.pending and not self.object.user_is_creator(self.request.user):
            raise Http404
        if self.object.deleted and not self.request.user.has_perm("can_approve"):
            raise Http404

        return r

    def get_context_data(self, **kwargs):
        c = super(ViewQuestion, self).get_context_data(**kwargs)
        c['show'] = 'show' in self.request.GET
        c['approval_mode'] = 'approve' in self.request.GET
        c['flagged_mode'] = 'flagged' in self.request.GET
        return c


@class_view_decorator(login_required)
class QuizStartView(ListView):
    template_name = "quiz_start.html"
    model = models.TeachingBlockYear

    def get_queryset(self):
        start_of_year = datetime.date(year=datetime.datetime.now().year, month=1, day=1)
        q = super(QuizStartView, self).get_queryset()
        s = [stage.number for stage in self.request.user.student.get_all_stages()]
        return q.filter(block__stage__number__in=s).exclude(release_date__isnull=True).exclude(release_date__lte=start_of_year).order_by("block__stage__number", "block__number")


@class_view_decorator(login_required)
class QuizView(ListView):
    template_name = "quiz.html"
    model = models.TeachingBlockYear

    def get_queryset(self):
        return super(QuizView, self).get_queryset().exclude(release_date__isnull=True)

@class_view_decorator(login_required)
class QuizGenerationView(RedirectView):
    def generate_questions(self):
        g = self.request.GET
        blocks = []
        questions = []
        for b in g.getlist('block'):
            d = {}
            d["block"] = int(b)
            d["question_number"] = int(g['block_%s_question_number' % b])
            d["years"] = [int(y) for y in g.getlist('block_%s_year' % b)]
            blocks.append(d)
        if not blocks:
            return []

        for b in blocks:
            bk = models.TeachingBlockYear.objects.filter(block__number=b['block'], year__in=b['years'])
            q = []
            if not bk.count():
                return []
            for bb in bk:
                q += models.Question.objects.filter(teaching_activity_year__block_year=bk, status=models.Question.APPROVED_STATUS)
            random.seed()
            if b["question_number"] > len(q):
                b["question_number"] = len(q)
            q = random.sample(q, b["question_number"])
            questions += q

        return questions

    def number_of_questions(self):
        number = 0
        for b in self.request.GET.getlist('block'):
            number += int(self.request.GET.get('block_%s_question_number', 0))

        return number

    def get_redirect_url(self, slug=None):
        questions = None
        self.request.session['mode'] = mode = self.request.GET.get('mode', 'block')

        if slug:
            try:
                quiz_specification = models.QuizSpecification.objects.get(slug=slug)
            except models.QuizSpecification.DoesNotExist:
                return reverse('quiz-start')
            self.request.session['quizspecification'] = quiz_specification

        if mode == 'individual':
            number = 0
            if quiz_specification:
                number += quiz_specification.number_of_questions()
            else:
                number += self.number_of_questions()
            self.request.session['number_of_questions'] = number
            return reverse('quiz')

        if quiz_specification:
            questions = quiz_specification.get_questions()
        else:
            questions = self.generate_questions()
        if not questions:
            return reverse('quiz-start')

        self.request.session['questions'] = questions
        return reverse('quiz')


@class_view_decorator(login_required)
class QuizQuestionView(View):
    http_method_names = ['get', ]

    def get(self, request, *args, **kwargs):
        # if settings.DEBUG: time.sleep(1)
        GET = request.GET
        spec = None
        attempt = None
        if 'specification' in GET:
            try:
                spec = models.QuizSpecification.objects.get(slug=GET.get('specification'))
            except models.QuizSpecification.DoesNotExist:
                return HttpResponseServerError(json.dumps({'error': 'Quiz specification does not exist.'}), mimetype="application/json")
        if 'quiz_attempt' in GET:
            try:
                attempt = models.QuizAttempt.objects.get(slug=GET.get('quiz_attempt'))
            except models.QuizAttempt.DoesNotExist:
                return HttpResponseServerError(json.dumps({'error': 'Quiz specification does not exist.'}), mimetype="application/json")

        done = GET.getlist('done')
        possible_questions = models.Question.objects.all()
        if spec:
            possible_questions = spec.get_questions()

        for question in done:
            possible_questions = possible_questions.exclude(id=question)

        if attempt:
            to_exclude = attempt.questions.all()
            possible_questions = possible_questions.exclude(id__in=to_exclude)

        try:
            question = possible_questions.order_by("?")[0]
        except IndexError:
            return HttpResponse(json.dumps({'status': 'done'}), mimetype="application/json")
        question = question.json_repr()
        question['status'] = "question"
        return HttpResponse(json.dumps(question), mimetype="application/json")


@class_view_decorator(login_required)
class NewQuizAttempt(View):
    def post(self, request, *args, **kwargs):
        POST = request.POST

        spec = None
        if 'specification' in POST:
            try:
                spec = models.QuizSpecification.objects.get(slug=POST.get('specification'))
            except models.QuizSpecification.DoesNotExist:
                # TODO: make this a status 500
                return HttpResponse(json.dumps({'error': 'That specification does not exist.', }), mimetype='application/json')

        attempt = models.QuizAttempt()
        attempt.student = request.user.student
        if spec: attempt.quiz_specification = spec
        attempt.save()

        return HttpResponse(json.dumps({'status': 'attempt', 'attempt': attempt.slug, }), mimetype='application/json')


@class_view_decorator(login_required)
class QuizQuestionSubmit(View):
    def post(self, request, *args, **kwargs):
        POST = request.POST
        print "Got post %s" % POST
        attempt = models.QuizAttempt.objects.get(slug=POST["quiz_attempt"])
        question = models.Question.objects.get(id=POST["id"])
        question_attempt = models.QuestionAttempt()
        question_attempt.quiz_attempt = attempt
        question_attempt.question = question
        question_attempt.position = POST["position"]
        question_attempt.answer = POST.get("choice")
        question_attempt.time_taken = POST.get("time_taken", 0)
        question_attempt.confidence_rating = POST.get("confidence") or models.QuestionAttempt.DEFAULT_CONFIDENCE;
        question_attempt.save()

        return HttpResponse(json.dumps(question.json_repr()), mimetype="application/json")


@class_view_decorator(login_required)
class Quiz(ListView):
    model = models.Question
    template_name = "quiz.html"

    def dispatch(self, request, *args, **kwargs):
        try:
            self.questions = request.session.pop('questions', models.Question.objects.none())
            self.mode = request.session.pop('mode')
            if self.mode == 'individual':
                self.number_of_questions = request.session.pop('number_of_questions')
        except KeyError:
            return redirect('quiz-start')

        if 'quizspecification' in request.session:
            self.quiz_specification = request.session.pop('quizspecification')
        return super(Quiz, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.questions

    def get_template_names(self):
        modes_to_templates = {'individual': 'quiz_individual.html', 'block': 'quiz.html'}

        return modes_to_templates.get(self.mode, 'quiz.html')

    def get_context_data(self, **kwargs):
        context = super(Quiz, self).get_context_data(**kwargs)
        context['confidence_range'] = models.QuestionAttempt.CONFIDENCE_CHOICES
        if hasattr(self, "quiz_specification"):
            context['specification'] = self.quiz_specification
        if hasattr(self, "number_of_questions"):
            context['number_of_questions'] = self.number_of_questions
        return context


@class_view_decorator(login_required)
class QuizSubmit(RedirectView):
    def get_redirect_url(self):
        if not self.request.method == 'POST':
            return reverse('quiz-start')
        p = self.request.POST
        specification = p.get('specification')
        if specification:
            try:
                specification = models.QuizSpecification.objects.get(id=specification)
            except models.QuizSpecification.DoesNotExist:
                specification = None

        questions = []
        qq = models.Question.objects.filter(id__in=p.getlist('question', []))
        if not qq.count():
            return reverse('quiz-start')
        for q in qq:
            parameter_prefix = "question-%d-" % q.id
            try:
                q.position = p.get("%sposition" % parameter_prefix, "")
            except ValueError:
                print "Got a value error"
                q.position = ""
            q.choice = p.get("%sanswer" % parameter_prefix) or None
            q.time_taken = p.get("%stime-taken" % parameter_prefix)
            q.confidence_rating = p.get("%sconfidence-rating" % parameter_prefix) or None
            if not q.position:
                return reverse("quiz-start")
            questions.append(q)
        questions.sort(key=lambda x: x.position)
        self.request.session['questions'] = questions
        
        quiz_attempt = models.QuizAttempt()
        quiz_attempt.student = self.request.user.student
        quiz_attempt.quiz_specification = specification
        quiz_attempt.save()

        for q in questions:
            question_attempt = models.QuestionAttempt()
            question_attempt.quiz_attempt = quiz_attempt
            question_attempt.question = q
            question_attempt.position = q.position
            question_attempt.answer = q.choice
            question_attempt.time_taken = q.time_taken
            question_attempt.confidence_rating = q.confidence_rating
            question_attempt.save() 
        return reverse('quiz-report')


@class_view_decorator(login_required)
class QuizReport(ListView):
    template_name = "quiz.html"

    def dispatch(self, request, *args, **kwargs):
        if 'slug' in kwargs:
            try:
                attempt = models.QuizAttempt.objects.get(slug=kwargs['slug'])
            except models.QuizAttempt.DoesNotExist:
                return redirect('quiz-start')
            self.questions = attempt.get_questions()
        elif 'questions' in request.session:
            self.questions = request.session.pop('questions')
        else:
            return redirect('quiz-start')
        return super(QuizReport, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.questions

    def get_context_data(self, **kwargs):
        c = super(QuizReport, self).get_context_data(**kwargs)
        c.update({'report': True, 'number_correct': sum(1 for q in self.questions if q.choice == q.answer)})
        by_block = {}
        for q in self.questions:
            d = by_block.setdefault(q.teaching_activity_year.block_year, {})
            l = d.setdefault('questions', [])
            l.append(q)
        for d in by_block.values():
            d['number_correct'] = sum(1 for q in d['questions'] if q.choice == q.answer)
        list_by_block = [[k,v] for k,v in by_block.iteritems()]
        list_by_block.sort(key=lambda x: (x[0].stage, x[0].number))
        c['confidence_range'] = models.QuestionAttempt.CONFIDENCE_CHOICES
        c.update({'by_block': list_by_block})
        return c

@class_view_decorator(login_required)
class QuizIndividualSummary(DetailView):
    model = models.QuizAttempt
    template_name = "quiz_summary.html"

@login_required
def view(request, ta_id, q_id):
    try:
        q = models.Question.objects.get(id=q_id)
    except models.Question.DoesNotExist:
        messages.error(request, "Hmm... that question could not be found")

    if q.teaching_activity_year.id != int(ta_id):
        messages.error(request, "Sorry, an unknown error occurred. Please try again.")
        return redirect('questions.views.home')

    return render_to_response("view.html", {'q': q, 'show': 'show' in request.GET}, context_instance=RequestContext(request))   


@class_view_decorator(permission_required("questions.can_approve"))
class ChangeStatus(RedirectView):
    permanent = False

    def query_string(self):
        g = self.request.GET
        if not g:
            return ""
        qs = "?"
        if 'show' in g:
            qs += 'show'
            if 'approve' in g:
                qs += "&"
        if 'approve' in g:
            qs += "approve"

        return qs

    def get_redirect_url(self, ta_id, q_id, action):
        actions_to_props = {
            'approve': 'approved',
            'pending': 'pending',
            'delete': 'deleted',
            'flag': 'flagged'
        }
        try:
            q = models.Question.objects.get(id=q_id)
        except models.Question.DoesNotExist:
            messages.error(self.request, "Hmm... that question could not be found.")
            return redirect('questions.views.home')

        if q.teaching_activity_year.id != int(ta_id):
            messages.error(self.request, "Sorry, an unknown error occurred. Please try again.")
            return redirect('questions.views.home')

        if not getattr(q, actions_to_props[action]):
            q.status = getattr(models.Question, '%s_STATUS' % actions_to_props[action].upper())
            q.approver = self.request.user.student
            q.save()

        r = "%s%%s"
        if 'approve' in self.request.GET:
            r = r % reverse('admin-approve', kwargs={'number': q.teaching_activity_year.block_year.number, 'year': q.teaching_activity_year.block_year.year, 'q_id': q.id})
        else:
            r = r % reverse('view', kwargs={'pk': q_id, 'ta_id': q.teaching_activity_year.id})
        r = r % self.query_string()
        return r


@class_view_decorator(permission_required('questions.can_approve'))
class ReleaseBlockView(RedirectView):
    def get_redirect_url(self, number, year):
        try:
            block =  models.TeachingBlockYear.objects.get(year=year, block__number=number)
        except models.TeachingBlockYear.DoesNotExist:
            messages.error(self.request, "That block does not exist.")
        else:
            if not block.questions_pending_count():
                if datetime.datetime.now().date() >= block.close:                
                    block.release_date = datetime.datetime.now().date()
                    block.save()
                    messages.success(self.request, "The block %s has been released to students." % (block.name, ))
                else:
                    messages.error(self.request, "Students are still able to write questions for %s. This block needs to be closed before you can release questions to students." % (block.name, ))
            else:
                messages.error(self.request, "The block %s still has questions pending, so it cannot be released to students." % (block.name, ))
        return reverse('admin')


@login_required
def download(request, number, year, mode):
    try:
        tb = models.TeachingBlockYear.objects.get(year=year, block__number=number)
    except models.TeachingBlockYear.DoesNotExist:
        messages.error(request, 'That block does not exist.')
        return redirect('admin')

    if not tb.released and not request.user.has_perm("questions.can_approve"):
        raise PermissionDenied

    if not tb.question_count_for_student(request.user.student) and not request.user.has_perm("questions.can_approve") and not (tb.stage != request.user.student.get_current_stage() and tb.stage in request.user.student.get_all_stages()):
        messages.error(request, "Unfortunately you haven't written any questions for this block, so you are unable to download the other questions.")
        return redirect('activity-mine')

    f = document.generate_document(tb, mode == "answer", request)
    r = HttpResponse(f.getvalue(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    r['Content-Disposition'] = 'attachment; filename=%sQuestions%s%s.docx' % (tb.filename(), "Answers" if mode == "answer" else "", datetime.datetime.now().strftime("%Y%M%d"))
    f.close()
    return r


# @permission_required('questions.can_approve')
# def send(request, pk):
#     t = tasks.DocumentEmailTask(pk=pk)
#     queue.add_task(t)
#     messages.success(request, "The email was successfully queued to be sent!")
#     return redirect('questions.views.admin')


@class_view_decorator(permission_required('questions.can_approve'))
class EmailView(FormView):
    template_name = "email.html"
    form_class = forms.EmailForm

    def dispatch(self, request, *args, **kwargs):
        try:
            self.tb = models.TeachingBlockYear.objects.get(block__number=self.kwargs['number'], year=self.kwargs['year'])
        except models.TeachingBlockYear.DoesNotExist:
            messages.error(request, "That teaching block does not exist.")
            return redirect("admin")

        r = super(EmailView, self).dispatch(request, *args, **kwargs)
        return r


    def get_recipients(self):
        recipients = models.Student.objects.filter(assigned_activities__block_year=self.tb).distinct()
        if 'document' in self.request.GET:
            recipients = recipients.filter(questions_created__teaching_activity_year__block_year=self.tb).distinct()
        return recipients


    def get_context_data(self, **kwargs):
        c = super(EmailView, self).get_context_data(**kwargs)
        c.update({'tb': self.tb, 'recipients': self.get_recipients()})
        return c

    def get_initial(self):
        i = super(EmailView,self).get_initial()
        i.update({ 'block': self.tb, 'from_address': settings.EMAIL_FROM_ADDRESS, })
        if 'document' in self.request.GET:
            i.update({'email' : '<p><a href="%s">Click here</a> to access the questions document.</p>\n<p><a href="%s">Click here</a> to access the document with answers.</p>' % (
                self.request.build_absolute_uri(reverse('questions.views.download', kwargs={'year': self.tb.year, 'number': self.tb.number, 'mode': 'question'})),
                self.request.build_absolute_uri(reverse('questions.views.download', kwargs={'year': self.tb.year, 'number': self.tb.number, 'mode': 'answer'})),
            )})
        return i

    def form_valid(self, form):
        c = form.cleaned_data
        recipients = [s.user.email for s in self.get_recipients()]
        if self.request.user.email not in recipients:
            recipients.append(self.request.user.email)
        tags = {
            '<strong>': '<strong style="font-weight:bold">',
            '<p>': '<p style="font-family:%s,Helvetica,Arial,sans-serif;font-size:14px;margin: 0 0 10px;">' % ("'Helvetica Neue'",),
            '<a href="': '<a style="color:#428bca;text-decoration:none;" href="',
            '\r': '',
            '\r\n': '',
            '\n': ''
        }

        for tag in tags:
            c['email'] = c['email'].replace(tag, tags[tag])

        t = tasks.HTMLEmailTask(
            "[MedBank] %s" % c['subject'],
            '<html><body style="font-family:%s,Helvetica,Arial,sans-serif;font-size:14px;">%s</body></html>' % ("'Helvetica Neue'", c['email']),
            recipients
        )

        #queue.add_task(t)
        t.run()
        messages.success(self.request, "Your email has been successfully queued to be sent.")

        return redirect('admin')


def copy_block(block):
    b = models.TeachingBlock()

    b.name = block.name
    b.year = block.year
    b.stage = block.stage
    b.number = block.number
    b.start = block.start
    b.end = block.end

    return b


@login_required
def new_ta_upload(request):
    accepted_types = collections.defaultdict(None)
    if not models.TeachingBlock.objects.count():
        messages.error(request, "You can't upload teaching activities without first having created a teaching block.")
        return redirect('admin')
    for k, v in models.TeachingActivity.TYPE_CHOICES:
        accepted_types[v] = k
    if request.method == "POST":
        if 'id' in request.POST:
            y = request.POST.get('year')
            i = request.POST.getlist('id')
            r = request.POST.copy()
            blocks = dict((b.number, b) for b in models.TeachingBlock.objects.filter(year=y))
            new_blocks = request.POST.getlist('new_block')
            for bb in new_blocks:
                data = {
                    'number': bb,
                    'name': request.POST.get('new_block_%d_name' % bb),
                    'year': request.POST.get('new_block_%d_year' % bb),
                    'stage': request.POST.get('new_block_%d_stage' % bb),
                    'start': request.POST.get('new_block_%d_start' % bb),
                    'end': request.POST.get('new_block_%d_end' % bb),
                }
                f = forms.NewTeachingBlockForm(data)
                if f.is_valid():
                    bb = f.save()
                    blocks[bb.number] = bb
                else:
                    raise
            for ii in i:
                data = {
                    'id': ii,
                    'name': request.POST.get('name_%s' % ii),
                    'block': [blocks[int(request.POST.get('block_%s' % ii))].id],
                    'week': request.POST.get('week_%s' % ii),
                    'position': request.POST.get('position_%s' % ii),
                    'activity_type': request.POST.get('activity_type_%s' % ii),
                }
                f = forms.NewTeachingActivityForm(data)
                if f.is_valid():
                    f.save()
                else:
                    return redirect('activity-upload')
            return redirect('admin')
        else:
            form = forms.TeachingActivityBulkUploadForm(request.POST, request.FILES)
            if form.is_valid():
                y = form.cleaned_data['year']
                r = list(csv.reader(form.cleaned_data['ta_file'].read().splitlines()))
                h = [hh.lower().replace(" ", "_") for hh in r[0]]
                by_position = {}
                by_name = {}
                by_block = {}
                already_exist = []
                blocks = list(set(dict(zip(h, row))['block'] for row in r[1:]))
                errors = []
                new_blocks = []
                existing_blocks = models.TeachingBlock.objects.filter(number__in=blocks)
                b = {}
                for bb in existing_blocks:
                    d = b.setdefault(bb.number, {})
                    d[bb.year] = bb
                for bb in blocks:
                    try:
                        bb = int(bb)
                    except:
                        errors.append("%s is not a number" % bb)
                    if bb in b:
                        if y in b[bb]:
                            bb = b[bb][y]
                        else:
                            bb = copy_block(b[bb][max(b[bb].keys())])
                            bb.year = y
                            bb.start.year = y
                            bb.end.year = y
                            b[bb.number][y] = bb
                            new_blocks.append(bb)
                        by_block[bb] = []
                    else:
                        errors.append("Block %s was not found" % bb)
                if errors:
                    return render_to_response("upload.html", {
                        'block_errors': errors
                    }, context_instance=RequestContext(request))
                for row in r[1:]:
                    hr = dict(zip(h, row))
                    hr['activity_type'] = accepted_types[hr['teaching_activity_type']]
                    f = forms.TeachingActivityValidationForm(hr)
                    if f.is_valid():
                        ta = f.save(commit=False)
                        l = by_position.setdefault((ta.week, ta.position, ta.activity_type), [])
                        l.append(ta)
                        l = by_name.setdefault(ta.name.lower(), [])
                        l.append(ta)
                        by_block[b[int(hr['block'])][y]].append(ta)
                    else:
                        if str(f.errors).find("exists"):
                            already_exist.append(hr)
                        else:
                            errors.append(hr)
                if errors or already_exist:
                    return render_to_response(
                        "upload.html",
                        {'errors': errors, 'already_exist': already_exist},
                        context_instance=RequestContext(request)
                    )
                else:
                    dup_by_position = [v for k, v in by_position.iteritems() if len(v) > 1]
                    dup_by_name = [v for k, v in by_name.iteritems() if len(v) > 1]
                    if dup_by_position or dup_by_name:
                        return render_to_response(
                            "upload.html",
                            {
                                'duplicates': True,
                                'dup_by_position': dup_by_position,
                                'dup_by_name': dup_by_name
                            },
                            context_instance=RequestContext(request)
                        )
                    else:
                        for bb in by_block:
                            by_block[bb].sort(key=lambda ta: (ta.week, ta.position))
                        return render_to_response(
                            "upload.html",
                            {
                                'tab': by_block,
                                'blocks': b.keys(),
                                'year': y,
                                'new_blocks': new_blocks,
                                'accepted_types': accepted_types.keys(),
                            },
                            context_instance=RequestContext(request)
                        )
    else:
        form = forms.TeachingActivityBulkUploadForm()
    return render_to_response(
        "upload.html",
        {
            'form': form,
            'accepted_types': accepted_types.keys(),
        },
        context_instance=RequestContext(request)
    )
