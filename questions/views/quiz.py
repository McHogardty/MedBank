from django.contrib.auth.decorators import login_required, permission_required
from django.views.generic import View, DetailView, ListView, FormView, TemplateView
from django.views.generic.base import RedirectView
from django.views.generic.edit import CreateView, UpdateView
from django.http import HttpResponseServerError, HttpResponse
from django.contrib import messages
from django.shortcuts import redirect
from django.core.urlresolvers import reverse, reverse_lazy
from django.conf import settings

from .base import class_view_decorator

from questions import models, forms

import datetime
import random
import json

def get_allowed_blocks(user):
    allowed_blocks = models.TeachingBlockYear.objects.filter(release_date__year=datetime.datetime.now().year) \
                                                    .order_by('block__stage__number', 'block__code')
    if user.is_superuser:
        return allowed_blocks

    if user.has_perm("questions.can_approve"):
        allowed_blocks = allowed_blocks.filter(block__stage__number__lt=user.student.get_current_stage().number)
    else:
        allowed_blocks = allowed_blocks.filter(activities__questions__in=user.student.questions_created.all())

    return allowed_blocks.distinct()


@class_view_decorator(login_required)
class QuizChooseView(ListView):
    template_name = "quiz/choose.html"
    model = models.QuizSpecification

    def get_queryset(self):
        return super(QuizChooseView, self).get_queryset().filter(active=True).exclude(stage__number__gt=self.request.user.student.get_current_stage().number).exclude(questions__isnull=True)

    def get_context_data(self, **kwargs):
        c = super(QuizChooseView, self).get_context_data(**kwargs)

        allowed_blocks = models.TeachingBlockYear.objects.get_released_blocks_for_year_and_date_and_student(
            datetime.datetime.now().year, datetime.datetime.now(), self.request.user.student)

        if allowed_blocks.exists():
            c['form'] = forms.CustomQuizSpecificationForm(blocks=allowed_blocks)

        c['type_form'] = forms.PresetQuizSpecificationForm()
        return c


@class_view_decorator(login_required)
class QuizStartView(ListView):
    template_name = "quiz/quiz_start.html"
    model = models.TeachingBlockYear

    def get_queryset(self):
        start_of_year = datetime.date(year=datetime.datetime.now().year, month=1, day=1)
        q = super(QuizStartView, self).get_queryset()
        s = [stage.number for stage in self.request.user.student.get_all_stages()]
        return q.filter(block__stage__number__in=s).exclude(release_date__isnull=True).exclude(release_date__lte=start_of_year).order_by("block__stage__number", "block__code")


@class_view_decorator(login_required)
class QuizView(ListView):
    template_name = "quiz/quiz.html"
    model = models.TeachingBlockYear

    def get_queryset(self):
        return super(QuizView, self).get_queryset().exclude(release_date__isnull=True)


@class_view_decorator(login_required)
class QuizGenerationView(RedirectView):
    permanent = False
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
            bk = models.TeachingBlockYear.objects.filter(block__code=b['block'], year__in=b['years'])
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
        if self.request.method == "POST":
            return self.deal_with_post()

        questions = None
        try:
            self.request.session['mode'] = mode = self.request.GET['mode']
        except KeyError:
            messages.error(self.request, "An unexpected error occurred. Please try again.")
            return reverse('quiz-choose')

        if slug:
            try:
                quiz_specification = models.QuizSpecification.objects.get(slug=slug)
            except models.QuizSpecification.DoesNotExist:
                return reverse('quiz-choose')
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
            return reverse('quiz-choose')

        self.request.session['questions'] = questions
        return reverse('quiz')

    def deal_with_post(self):
        preset_quiz = 'quiz_specification' in self.request.POST
        if preset_quiz:
            form = forms.PresetQuizSpecificationForm(self.request.POST)
        else:
            allowed_blocks = get_allowed_blocks(self.request.user)
            if not allowed_blocks.exists():
                messages.error(self.request, "Something wasn't right there... Please try again.")
                return reverse('quiz-choose')

            form = forms.CustomQuizSpecificationForm(self.request.POST, blocks=allowed_blocks)

        if not form.is_valid():
            messages.error(self.request, "An unexpected error has occurred. Please try again.")
            return reverse('quiz-choose')

        questions = []
        self.request.session['mode'] = form.cleaned_data['quiz_type']
        if preset_quiz:
            self.request.session['quizspecification'] = form.cleaned_data['quiz_specification']
        else:
            for block in allowed_blocks:
                q = []
                number_needed = form.cleaned_data[block.name_for_form_fields()]
                if not number_needed: continue
                q += list(set(models.Question.objects.filter(teaching_activity_year__block_year=block, status=models.Question.APPROVED_STATUS)))
                random.seed()
                if number_needed > len(q):
                    number_needed = len(q)
                q = random.sample(q, number_needed)
                questions += q

            random.seed()
            random.shuffle(questions)
            attempt = models.QuizAttempt.create_from_list_and_student(questions, self.request.user.student)

            self.request.session['attempt'] = attempt

        return reverse('quiz')


@class_view_decorator(login_required)
class QuizQuestionView(View):
    http_method_names = ['get', ]

    def get(self, request, *args, **kwargs):
        GET = request.GET
        attempt = None
        specification = None

        if 'quiz_attempt' in GET:
            try:
                attempt = models.QuizAttempt.objects.get(slug=GET.get('quiz_attempt'))
            except models.QuizAttempt.DoesNotExist:
                return HttpResponseServerError(json.dumps({'error': 'Quiz attempt does not exist.'}), mimetype="application/json")
        if 'specification' in GET:
            try:
                specification = models.QuizSpecification.objects.get(slug=GET.get('specification'))
            except models.QuizSpecification.DoesNotExist:
                return HttpResponseServerError(json.dumps({'error': 'Quiz specification does not exist.'}), mimetype="application/json")

        done = GET.getlist('done')
        possible_questions = models.Question.objects.none()
        preset_quiz = attempt and attempt.quiz_specification is not None

        if preset_quiz:
            possible_questions = attempt.quiz_specification.get_questions().exclude(id__in=done)
        elif specification:
            possible_questions = specification.get_questions().exclude(id__in=done)
        else:
            possible_questions = attempt.questions.order_by("position").exclude(question__id__in=done)

        if preset_quiz:
            to_exclude = attempt.questions.all()
            possible_questions = possible_questions.exclude(id__in=to_exclude).order_by("?")

        try:
            question = possible_questions[0]
        except IndexError:
            return HttpResponse(json.dumps({'status': 'done'}), mimetype="application/json")

        if not preset_quiz and not specification:
            question = question.question

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

        return HttpResponse(json.dumps({'status': 'attempt', 'attempt': attempt.slug, 'report_url': reverse('quiz-attempt-report', kwargs={'slug': attempt.slug}) }), mimetype='application/json')


@class_view_decorator(login_required)
class QuizQuestionSubmit(View):
    def post(self, request, *args, **kwargs):
        POST = request.POST

        attempt = models.QuizAttempt.objects.get(slug=POST["quiz_attempt"])
        question = models.Question.objects.get(id=POST["id"])
        try:
            question_attempt = attempt.questions.get(question=question)
        except models.QuestionAttempt.DoesNotExist:
            question_attempt = models.QuestionAttempt()
        question_attempt.quiz_attempt = attempt
        question_attempt.question = question
        question_attempt.position = POST["position"]
        question_attempt.answer = POST.get("choice")
        question_attempt.time_taken = POST.get("time_taken", 0)
        question_attempt.confidence_rating = POST.get("confidence") or models.QuestionAttempt.DEFAULT_CONFIDENCE;
        question_attempt.save()

        return HttpResponse(json.dumps(question.json_repr(include_answer=True)), mimetype="application/json")


@class_view_decorator(login_required)
class Quiz(TemplateView):
    def dispatch(self, request, *args, **kwargs):
        if 'quizspecification' in request.session:
            self.quiz_specification = request.session.pop('quizspecification')
        if 'attempt' in request.session:
            self.attempt = request.session.pop('attempt')

        if hasattr(self, 'attempt'):
            self.number_of_questions = self.attempt.questions.count()
        elif hasattr(self, "quiz_specification"):
            self.number_of_questions = self.quiz_specification.number_of_questions()
        else:
            return redirect('quiz-choose')

        try:
            self.mode = request.session.pop('mode')                
        except KeyError:
            return redirect('quiz-choose')

        # elif self.mode == 'classic':
        #     if hasattr(self, 'attempt'):
        #         self.questions = [question_attempt.question for question_attempt in self.attempt.questions.all()]
        #     elif hasattr(self, "quiz_specification"):
                # self.questions = self.quiz_specification.get_questions().order_by("?")


        return super(Quiz, self).dispatch(request, *args, **kwargs)

    def get_template_names(self):
        modes_to_templates = {'individual': 'quiz/quiz_individual.html', 'block': 'quiz/quiz.html', 'classic': 'quiz/quiz_individual.html'}

        return modes_to_templates.get(self.mode, 'quiz/quiz.html')

    def get_context_data(self, **kwargs):
        context = super(Quiz, self).get_context_data(**kwargs)
        context['confidence_range'] = models.QuestionAttempt.CONFIDENCE_CHOICES
        context['questions'] = range(self.number_of_questions)
        context['classic_mode'] = self.mode == "classic"
        if hasattr(self, "attempt"):
               context['attempt'] = self.attempt
        if hasattr(self, "quiz_specification"):
            context['specification'] = self.quiz_specification
        return context


@class_view_decorator(login_required)
class QuizSubmit(RedirectView):
    permanent = False

    def get_redirect_url(self):
        if not self.request.method == 'POST':
            return reverse('quiz-choose')
        p = self.request.POST
        specification = p.get('specification')
        attempt = None
        if specification:
            try:
                specification = models.QuizSpecification.objects.get(slug=specification)
            except models.QuizSpecification.DoesNotExist:
                specification = None
        if 'attempt' in p:
            try:
                attempt = models.QuizAttempt.objects.get(slug=p.get('attempt'))
            except models.QuizAttempt.DoesNotExist:
                pass

        if not attempt and not specification:
            messages.error(self.request, "An unexpected error has occurred. We're sorry for the inconvenience, please try again.")
            return reverse('quiz-choose')

        questions = []
        qq = models.Question.objects.filter(id__in=p.getlist('question', []))
        if not qq.count():
            return reverse('quiz-choose')
        for q in qq:
            parameter_prefix = "question-%d-" % q.id
            try:
                q.position = p.get("%sposition" % parameter_prefix, "")
            except ValueError:
                if settings.DEBUG: print "Got a value error"
                q.position = ""
            q.choice = p.get("%sanswer" % parameter_prefix) or None
            q.time_taken = p.get("%stime-taken" % parameter_prefix)
            q.confidence_rating = p.get("%sconfidence-rating" % parameter_prefix) or None
            if not q.position:
                return reverse("quiz-choose")
            questions.append(q)
        questions.sort(key=lambda x: x.position)
        self.request.session['questions'] = questions
        
        new_attempt = not attempt
        if new_attempt:
            attempt = models.QuizAttempt()

        attempt.student = self.request.user.student
        if specification:
            attempt.quiz_specification = specification
        attempt.save()

        if new_attempt:
            for q in questions:
                question_attempt = models.QuestionAttempt()
                question_attempt.quiz_attempt = attempt
                question_attempt.question = q
                question_attempt.position = q.position
                question_attempt.answer = q.choice
                question_attempt.time_taken = q.time_taken
                question_attempt.confidence_rating = q.confidence_rating
                question_attempt.save()
        else:
            question_by_ID = {}
            for q in questions:
                question_by_ID[q.id] = q

            for question_attempt in attempt.questions.all():
                question = question_by_ID[question_attempt.question.id]

                question_attempt.answer = question.choice
                question_attempt.time_taken = q.time_taken
                question_attempt.confidence_rating = q.confidence_rating
                question_attempt.position = q.position
                question_attempt.save()

        return reverse('quiz-attempt-report', kwargs={'slug': attempt.slug})


@class_view_decorator(login_required)
class QuizReport(ListView):
    template_name = "quiz/quiz.html"

    def dispatch(self, request, *args, **kwargs):
        if 'slug' in kwargs:
            try:
                attempt = models.QuizAttempt.objects.get(slug=kwargs['slug'])
            except models.QuizAttempt.DoesNotExist:
                return redirect('quiz-choose')
            self.questions = attempt.get_questions()
        elif 'questions' in request.session:
            self.questions = request.session.pop('questions')
        else:
            return redirect('quiz-choose')
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
        list_by_block.sort(key=lambda x: (x[0].stage, x[0].code))
        c['confidence_range'] = models.QuestionAttempt.CONFIDENCE_CHOICES
        c.update({'by_block': list_by_block})
        return c


@class_view_decorator(login_required)
class QuizIndividualSummary(DetailView):
    model = models.QuizAttempt
    template_name = "quiz/quiz_individual.html"

    def get_queryset(self):
        queryset = super(QuizIndividualSummary, self).get_queryset()

        queryset = queryset.select_related("quiz_specification").prefetch_related("quiz_specification__questions", "quiz_specification__attempts")

        return queryset

    def get_context_data(self, **kwargs):
        c = super(QuizIndividualSummary, self).get_context_data(**kwargs)
        c['summary_mode'] = True
        c['questions'] = c['object'].complete_questions_in_order()
        return c


@class_view_decorator(permission_required('questions.can_approve'))
class NewQuizSpecificationView(CreateView):
    model = models.QuizSpecification
    form_class = forms.NewQuizSpecificationForm
    template_name = "admin/new.html"
    success_url = reverse_lazy('admin')


@class_view_decorator(permission_required('questions.can_approve'))
class UpdateQuizSpecificationView(UpdateView):
    model = models.QuizSpecification
    form_class = forms.NewQuizSpecificationForm
    template_name = "admin/new.html"
    success_url = reverse_lazy('admin')


@class_view_decorator(permission_required('questions.can_approve'))
class AddQuizSpecificationQuestions(FormView):
    template_name = "admin/add_specification_questions.html"
    form_class = forms.QuestionForm

    def dispatch(self, request, *args, **kwargs):
        try:
            self.specification = models.QuizSpecification.objects.get(slug=kwargs['slug'])
        except models.QuizSpecification.DoesNotExist:
            messages.error("That quiz specification does not exist.")
            return redirect("admin")

        self.questions = []

        return super(AddQuizSpecificationQuestions, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AddQuizSpecificationQuestions, self).get_context_data(**kwargs)
        context['specification'] = self.specification
        context['questions'] = self.questions
        return context

    def get_initial(self):
        if self.questions:
            return {'questions_selected': self.questions}

    def form_valid(self, form):
        self.questions += form.cleaned_data['questions_selected']
        if form.cleaned_data['question_id'] not in self.questions:
            self.questions.append(form.cleaned_data['question_id'])

        # Way to get around self.get_form adding in the data from the post request.
        self.request.method = "GET"
        return self.render_to_response(self.get_context_data(form=self.get_form(self.get_form_class())))


@class_view_decorator(permission_required('questions.can_approve'))
class ConfirmQuizSpecificationQuestion(RedirectView):
    permanent = False
    
    def get_redirect_url(self, slug):
        try:
            specification = models.QuizSpecification.objects.get(slug=slug)
        except models.QuizSpecification.DoesNotExist:
            messages.error(self.request, "That quiz specification does not exist.")

        if self.request.method != "POST":
            messages.error(self.request, "Sorry, an unexpected error occurred. Please try again.")
        else:
            form = forms.ConfirmQuestionSelectionForm(self.request.POST)

            if form.is_valid():
                questions = form.cleaned_data["question_id"]
                question_specification = models.QuizQuestionSpecification.form_list_of_questions(questions)
                question_specification.quiz_specification = specification
                question_specification.save()
                messages.success(self.request, "Questions added successfully!")
            else:
                messages.error(self.request, "Sorry, an unexpected error occured. Please try again.")

        return reverse('quiz-spec-view', kwargs={'slug': specification.slug})


@class_view_decorator(permission_required('questions.can_approve'))
class QuizSpecificationView(DetailView):
    model = models.QuizSpecification
    template_name = "admin/specification.html"


@class_view_decorator(permission_required('questions.can_approve'))
class QuizSpecificationAdd(FormView):
    form_class = forms.QuestionQuizSpecificationForm
    template_name = "admin/add_specification.html"

    def form_valid(self, form):
        try:
            question = models.Question.objects.get(pk=self.kwargs["pk"])
        except models.Question.DoesNotExist:
            messages.error(self.request, "That question does not exist.")
            return redirect('admin')

        spec = form.cleaned_data['specification']

        qa = models.QuizQuestionSpecification.from_specific_question(question)
        qa.quiz_specification = spec
        qa.save()

        messages.success(self.request, "This question was successfully added to the specification %s." % spec.name)
        return redirect(question)
