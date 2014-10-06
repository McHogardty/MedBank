from __future__ import unicode_literals

from django.contrib import messages
from django.views.generic import TemplateView, DetailView, View, ListView, RedirectView, CreateView, FormView, UpdateView
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404

from questions import models, forms
from .base import class_view_decorator, user_is_superuser, GetObjectMixin, JsonResponseMixin
from django.contrib.auth.decorators import login_required

import datetime
import json
import random

@class_view_decorator(login_required)
class QuizDashboard(TemplateView):
    template_name = "quiz/dashboard.html"

    def get_context_data(self, **kwargs):
        c = super(QuizDashboard, self).get_context_data(**kwargs)
        try:
            c['latest_quiz_attempt'] = models.QuizAttempt.objects.get_latest_quiz_attempt_for_student(self.request.user.student)
        except models.QuizAttempt.DoesNotExist:
            pass
        question_attempts = models.QuestionAttempt.objects.get_question_attempts_for_student(self.request.user.student)
        scores = []
        question_attempts_by_quiz_attempt = {}
        for question_attempt in question_attempts:
            l = question_attempts_by_quiz_attempt.setdefault(question_attempt.quiz_attempt, [])
            l.append(question_attempt)

        for question_list in question_attempts_by_quiz_attempt.values():
            if len(question_list) == 0: continue
            scores.append(float(sum(question.score() for question in question_list))/len(question_list))
        c['average_score'] = 100*float(sum(scores))/len(scores) if len(scores) > 0 else None
        return c


@class_view_decorator(login_required)
class QuizHistory(ListView):
    template_name = "quiz/history.html"

    def get_queryset(self):
        try:
            return models.QuizAttempt.objects.filter(student=self.request.user.student).order_by("-date_submitted")
        except models.QuizAttempt.DoesNotExist:
            raise Http404

    def get_context_data(self, **kwargs):
        c = super(QuizHistory, self).get_context_data(**kwargs)
        c['student_quiz_attempts'] = self.object_list
        return c


@class_view_decorator(login_required)
class QuizAttemptReport(GetObjectMixin, DetailView):
    template_name = "quiz/specific_history.html"
    model = models.QuizAttempt

    def dispatch(self, request, *args, **kwargs):
        response = super(QuizAttemptReport, self).dispatch(request, *args, **kwargs)
        if not self.object.is_viewable_by(self.request.user.student):
            messages.warning(request, "Unfortunately you are unable to view the history for that particular quiz attempt.")
            return redirect('quiz-home')
        return response

    def get_context_data(self, **kwargs):
        c = super(QuizAttemptReport, self).get_context_data(**kwargs)
        c['quiz_attempt'] = self.object
        return c


@class_view_decorator(login_required)
class QuizView(TemplateView):
    template_name = "quiz/selection.html"
    model = models.QuizSpecification

    classes_to_prefixes = {
        forms.CustomQuizSpecificationForm: 'custom',
        forms.PresetQuizSpecificationForm: 'preset',
        forms.QuizTypeSelectionForm: 'type',
    }

    def dispatch(self, request, *args, **kwargs):
        self.current_form = None
        self.current_type_form = None

        quiz_specifications = models.QuizSpecification.objects.get_allowed_specifications_for_student(self.request.user.student)
        self.quiz_specifications = list(quiz_specifications)

        self.allowed_blocks = list(self.get_allowed_blocks())

        return super(QuizView, self).dispatch(request, *args, **kwargs)

    def get_class_from_prefix(self, prefix):
        for c, p in self.classes_to_prefixes.items():
            if p == prefix: return c

    def get_prefix_from_class(self, cls):
        return self.classes_to_prefixes[cls]

    def get_preset_form_class(self):
        return forms.PresetQuizSpecificationForm

    def get_custom_form_class(self):
        return forms.CustomQuizSpecificationForm

    def get_type_form_class(self):
        return forms.QuizTypeSelectionForm

    def get_allowed_blocks(self):
        return models.TeachingBlock.objects.get_released_blocks_for_student(self.request.user.student)

    def get_kwargs_from_class(self, cls):
        kwargs = {'prefix': self.get_prefix_from_class(cls), }

        if cls == self.get_custom_form_class():
            kwargs.update({'blocks': self.allowed_blocks})
            kwargs.update({'initial': {'repeat_questions': True }})

        return kwargs

    def get_context_data(self, **kwargs):
        c = super(QuizView, self).get_context_data(**kwargs)

        if self.allowed_blocks:
            form_class = self.get_custom_form_class()

            if self.current_form and self.current_form.__class__ == form_class:
                c['form'] = self.current_form
            else:
                form_kwargs = self.get_kwargs_from_class(form_class)
                c['form'] = form_class(**form_kwargs)

        form_class = self.get_preset_form_class()
        for specification in self.quiz_specifications:
            if self.current_form and self.current_form.__class__ == form_class:
                selection_form = self.current_form
            else:
                form_kwargs = self.get_kwargs_from_class(form_class)
                form_kwargs.update({'initial': {'quiz_specification': specification}})
                selection_form = form_class(**form_kwargs)

            specification.selection_form = selection_form

        c['specifications'] = self.quiz_specifications

        type_class = self.get_type_form_class()
        type_kwargs = self.get_kwargs_from_class(type_class)
        empty_type_form = type_class(**type_kwargs)
        if self.current_type_form:
            c['type_form'] = self.current_type_form
            c['empty_type_form'] = empty_type_form
        else:
            c['type_form'] = empty_type_form

        return c

    def post(self, request, *args, **kwargs):
        type_class = self.get_type_form_class()
        type_kwargs = self.get_kwargs_from_class(type_class)

        form_class = None
        for key in request.POST:
            form_class = self.get_class_from_prefix(key)
            if form_class:
                form_kwargs = self.get_kwargs_from_class(form_class)
                break

        if not form_class:
            messages.error(request, "An unexpected error has occurred.")
            return self.render_to_response(self.get_context_data())

        self.current_form = form_class(request.POST, **form_kwargs)
        self.current_form.was_checked = True
        self.current_type_form = type_class(request.POST, **type_kwargs)

        form_is_valid = self.current_form.is_valid()
        type_form_is_valid = self.current_type_form.is_valid()

        if not form_is_valid or not type_form_is_valid:
            return self.render_to_response(self.get_context_data())

        quiz_type = self.current_type_form.cleaned_data["quiz_type"]

        question_list = []
        quiz_specification = None
        if isinstance(self.current_form, self.get_preset_form_class()):
            quiz_specification = self.current_form.cleaned_data["quiz_specification"]
            question_list = list(quiz_specification.get_questions())
        else:
            cleaned_data = self.current_form.cleaned_data
            unique_questions_only = not cleaned_data['repeat_questions']
            total_questions = sum(cleaned_data[x] or 0 for x in self.current_form.block_fields)
            if total_questions > 80:
                messages.warning(self.request, "Unfortunately you can only choose up to 80 questions at a time. Please try again.")
                return redirect("quiz-choose")

            random.seed()
            for block in self.get_allowed_blocks():
                number_of_questions = cleaned_data[block.name_for_form_fields()]
                if number_of_questions:
                    questions_for_block = models.Question.objects.filter(teaching_activity_year__block_year__block=block, status=models.Question.APPROVED_STATUS).distinct()
                    if unique_questions_only:
                        questions_for_block = questions_for_block.exclude(attempts__quiz_attempt__student=self.request.user.student)
                    questions_for_block = list(questions_for_block)
                    if len(questions_for_block) < number_of_questions:
                        number_of_questions = len(questions_for_block)
                    question_list += random.sample(questions_for_block, number_of_questions)

        random.seed()
        random.shuffle(question_list)
        if len(question_list) == 0:
            messages.warning(self.request, "Unfortunately there were no questions which matched those parameters.")
            return redirect("quiz-choose")

        attempt = models.QuizAttempt.create_from_list_and_student(question_list, self.request.user.student, quiz_type=quiz_type, quiz_specification=None)

        return redirect(attempt.get_start_url(quiz_type))


@class_view_decorator(login_required)
class ResumeAttemptView(GetObjectMixin, DetailView):
    model = models.QuizAttempt

    def get_template_names(self):
        modes_to_templates = {
            models.QuizAttempt.CLASSIC_QUIZ_TYPE: "quiz/preset_classic.html",
            models.QuizAttempt.INDIVIDUAL_QUIZ_TYPE: "quiz/preset_individual.html"
        }

        return modes_to_templates[self.object.quiz_type]

    def dispatch(self, request, *args, **kwargs):
        r = super(ResumeAttemptView, self).dispatch(request, *args, **kwargs)
        if not self.object.is_viewable_by(self.request.user.student):
            messages.warning(request, "Unfortunately you are unable to view that particular quiz attempt.")
            return redirect('quiz-home')
        return r

    def get_context_data(self, **kwargs):
        c = super(ResumeAttemptView, self).get_context_data(**kwargs)

        questions = list(self.object.questions_in_order())
        c['number_of_questions'] = len(questions)
        c['questions'] = [question.position for question in questions]
        c['confidence_choices'] = models.QuestionAttempt.CONFIDENCE_CHOICES
        c['quiz_attempt_questions_url'] = self.object.get_questions_url()
        c['quiz_attempt_report_url'] = self.object.get_report_url()
        if self.object.quiz_type == models.QuizAttempt.INDIVIDUAL_QUIZ_TYPE:
            c['quiz_attempt_question_submission_url'] = self.object.get_answer_submission_url()
        elif self.object.quiz_type == models.QuizAttempt.CLASSIC_QUIZ_TYPE:
            c['quiz_attempt_submission_url'] = self.object.get_submission_url()
        return c


@class_view_decorator(login_required)
class QuizAttemptQuestionsView(JsonResponseMixin, View):
    def get(self, request, *args, **kwargs):
        from django.conf import settings
        if settings.DEBUG:
            import time
            time.sleep(3);
        data = {}

        try:
            attempt = models.QuizAttempt.objects.get_from_kwargs(**kwargs)
        except models.QuizAttempt.DoesNotExist:
            data = {'status': 'error', 'message': 'Not found.'}
            return self.render_to_json_response(data)

        if not attempt.is_viewable_by(request.user.student):
            data = {'status': 'error', 'message': 'Permission denied.'}
            return self.render_to_json_response(data)

        data["status"] = "success"
        questions = []
        question_attempts = attempt.questions_in_order()
        for question_attempt in question_attempts:
            completed = question_attempt.date_completed is not None
            question = question_attempt.question.json_repr(include_answer=completed)
            question["position"] = question_attempt.position
            question["completed"] = completed
            if completed:
                question["choice"] = question_attempt.answer
                question["confidence_rating"] = question_attempt.confidence_rating
            questions.append(question)

        data["questions"] = questions
        return self.render_to_json_response(data)


@class_view_decorator(login_required)
class SubmitAllAnswersView(RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        try:
            attempt = models.QuizAttempt.objects.get_from_kwargs(**kwargs)
        except models.QuizAttempt.DoesNotExist:
            messages.warning(self.request, "Unfortunately an error has occurred and those answers could not be submitted.")
            return reverse('quiz-home')

        if not attempt.is_viewable_by(self.request.user.student):
            messages.error(self.request, "Unfortunately you do not have permission to be able to submit answers for that particular quiz attempt.")
            return reverse('quiz-home')

        date_completed = datetime.datetime.now()
        for question_attempt in attempt.incomplete_questions():
            question_id = question_attempt.question.id
            question_attempt.answer = self.request.POST.get("question-%s-choice" % question_id) or models.QuestionAttempt.DEFAULT_ANSWER
            question_attempt.confidence_rating = self.request.POST.get("question-%s-confidence_rating" % question_id) or models.QuestionAttempt.DEFAULT_CONFIDENCE
            question_attempt.time_taken = self.request.POST.get("question-%s-time_taken" % question_id) or 0
            question_attempt.date_completed = date_completed
            question_attempt.save()

        return attempt.get_report_url()


@class_view_decorator(login_required)
class SubmitAnswerView(JsonResponseMixin, View):
    def post(self, request, *args, **kwargs):
        from django.conf import settings
        if settings.DEBUG:
            import time
            time.sleep(1);

        data = {}

        try:
            attempt = models.QuizAttempt.objects.get_from_kwargs(**kwargs)
        except models.QuizAttempt.DoesNotExist:
            data = {'status': 'error', 'message': 'Not found.'}
            return self.render_to_json_response(data)

        if not attempt.is_viewable_by(self.request.user.student):
            data = {'status': 'error', 'message': 'Permission denied.'}

        if 'question_id' not in request.POST:
            data = {"status": "error", "message": "Question ID not provided."}
            return self.render_to_json_response(data)

        question_attempt = attempt.get_question_attempt_by_question(request.POST['question_id'])
        if question_attempt.date_completed:
            data = {"status": "error", "message": "Question already answered for this quiz."}
            return self.render_to_json_response(data)

        question_attempt.answer = request.POST.get("choice", question_attempt.DEFAULT_ANSWER)
        question_attempt.confidence_rating = request.POST.get("confidence_rating", question_attempt.DEFAULT_CONFIDENCE)
        question_attempt.time_taken = request.POST.get("time_taken", 0)
        # question_attempt.save()
        question_attempt.date_completed = datetime.datetime.now()
        question_attempt.save()

        question = question_attempt.question

        data = question.json_repr(include_answer=True)
        data["status"] = "success"
        data["completed"] = True
        data["status"] = "success"
        data["confidence_rating"] = question_attempt.confidence_rating
        data["choice"] = question_attempt.answer

        return self.render_to_json_response(data)


@class_view_decorator(user_is_superuser)
class QuizAdminView(TemplateView):
    template_name = "quiz/admin.html"

    def get_context_data(self, **kwargs):
        c = super(QuizAdminView, self).get_context_data(**kwargs)
        c['quiz_specifications'] = models.QuizSpecification.objects.order_by('stage')
        return c


@class_view_decorator(user_is_superuser)
class NewQuizSpecificationView(CreateView):
    model = models.QuizSpecification
    form_class = forms.NewQuizSpecificationForm
    template_name = "quiz/specification/new.html"

    def get_success_url(self):
        return self.object.get_absolute_url()


@class_view_decorator(user_is_superuser)
class UpdateQuizSpecificationView(UpdateView):
    model = models.QuizSpecification
    form_class = forms.NewQuizSpecificationForm
    template_name = "quiz/specification/new.html"

    def get_success_url(self):
        return self.object.get_absolute_url()

@class_view_decorator(user_is_superuser)
class QuizSpecificationView(DetailView):
    model = models.QuizSpecification
    template_name = "quiz/specification/view.html"

    def get_context_data(self, **kwargs):
        c = super(QuizSpecificationView, self).get_context_data(**kwargs)
        c['specification'] = self.object
        return c


@class_view_decorator(user_is_superuser)
class AddQuizSpecificationQuestions(FormView):
    template_name = "quiz/specification/add_questions.html"
    form_class = forms.QuestionForm

    def dispatch(self, request, *args, **kwargs):
        try:
            self.specification = models.QuizSpecification.objects.get_from_kwargs(**kwargs)
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


@class_view_decorator(user_is_superuser)
class ConfirmQuizSpecificationQuestions(RedirectView):
    permanent = False
    
    def get_redirect_url(self, slug):
        try:
            specification = models.QuizSpecification.objects.get_from_kwargs(**{'slug': slug})
        except models.QuizSpecification.DoesNotExist:
            messages.error(self.request, "That quiz specification does not exist.")
            return reverse('quiz-admin')

        if self.request.method != "POST":
            messages.error(self.request, "Sorry, an unexpected error occurred. Please try again.")
            return specification.get_add_questions_url()
        else:
            form = forms.ConfirmQuestionSelectionForm(self.request.POST)

            if form.is_valid():
                questions = form.cleaned_data["question_id"]
                question_specification = models.QuizQuestionSpecification.from_list_of_questions(questions)
                question_specification.quiz_specification = specification
                question_specification.save()
                messages.success(self.request, "Questions added successfully!")
            else:
                messages.error(self.request, "Sorry, an unexpected error occured. Please try again.")

        return specification.get_absolute_url()

