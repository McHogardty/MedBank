from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required, permission_required
from django.views.generic import DetailView, FormView, TemplateView
from django.views.generic.edit import CreateView, UpdateView
from django.http import Http404
from django.contrib import messages
from django.shortcuts import redirect
from django.db import transaction
from django.core.urlresolvers import reverse

from .base import class_view_decorator, user_is_superuser, track_changes

from questions import models, forms, emails
import reversion

import json
import htmlentitydefs

@class_view_decorator(login_required)
class QuestionGuide(TemplateView):
    template_name = "question/guide.html"


@class_view_decorator(login_required)
@class_view_decorator(track_changes)
class NewQuestion(CreateView):
    model = models.Question
    form_class = forms.NewQuestionForm
    template_name = "question/new.html"

    def dispatch(self, request, *args, **kwargs):
        try:
            self.activity = models.TeachingActivity.objects.get_from_kwargs(**kwargs)
        except models.TeachingActivity.DoesNotExist:
            raise Http404

        writing_period_id = request.GET.get("writing_period", None)
        writing_period = None
        if writing_period_id and request.user.is_superuser:
            try:
                writing_period = models.QuestionWritingPeriod.objects.get(id=writing_period_id)
            except models.QuestionWritingPeriod.DoesNotExist:
                pass
        self.activity_year = self.activity.get_latest_activity_year_for_student(request.user.student, writing_period=writing_period)
        self.writing_period = writing_period

        if not self.activity_year.questions_can_be_written_by(self.request.user.student):
            messages.warning(request, "You are not currently able to write questions for this activity.")
            return redirect(self.activity)

        return super(NewQuestion, self).dispatch(request, *args, **kwargs)

    def get_initial(self):
        i = super(NewQuestion, self).get_initial().copy()
        i['teaching_activity_year'] = self.activity_year
        i['creator'] = self.request.user.student
        return i

    def get_form_kwargs(self):
        kwargs = super(NewQuestion, self).get_form_kwargs()
        kwargs['change_student'] = self.request.user.is_superuser
        return kwargs

    def form_valid(self, form):
        reversion.set_comment("Question created.")
        question = form.save()
        messages.success(self.request, "Thanks, your question has been submitted!") # You'll get an email when it's approved.")
        emails.send_question_creation_email(self.request.user.student, question, self.request.build_absolute_uri(question.get_absolute_url()))
        return redirect("%s?%s" % (question.get_absolute_url(), "writing_period=%s" % self.writing_period.id if self.writing_period else ""))


@class_view_decorator(login_required)
@class_view_decorator(track_changes)
class UpdateQuestion(UpdateView):
    form_class = forms.NewQuestionForm
    template_name = "question/new.html"

    def dispatch(self, request, *args, **kwargs):
        r = super(UpdateQuestion, self).dispatch(request, *args, **kwargs)

        if not self.object.is_editable_by(self.request.user.student):
            messages.warning(self.request, "Unfortunately you are unable to edit that question.")
            return redirect(self.object)

        return r

    def get_object(self):
        try:
            return models.Question.objects.get_from_kwargs(allow_deleted=self.request.user.is_superuser, **self.kwargs)
        except models.Question.DoesNotExist:
            raise Http404

    def get_form_kwargs(self):
        k = super(UpdateView, self).get_form_kwargs()
        k['change_student'] = self.request.user.is_superuser
        k['edit_mode'] = True
        return k

    def form_valid(self, form):
        c = form.cleaned_data
        reversion.set_comment(c['reason'])
        question = form.save()
        emails.send_question_updated_email(self.request.user.student, question, self.request.build_absolute_uri(question.get_absolute_url()))
        return redirect(self.object.get_absolute_url())

    def get_context_data(self, **kwargs):
        c = super(UpdateQuestion, self).get_context_data(**kwargs)
        c['question'] = self.object
        c['can_cancel'] = True
        c['cancel_url'] = self.get_success_url()
        return c


@class_view_decorator(login_required)
class AddComment(CreateView):
    model = models.Comment
    form_class = forms.CommentForm
    template_name = "question/comment.html"

    def dispatch(self, request, *args, **kwargs):
        try:
            self.q = models.Question.objects.get_from_kwargs(allow_deleted=self.request.user.is_superuser, **self.kwargs)
        except models.Question.DoesNotExist:
            messages.error(self.request, "That question does not exist")
            return redirect('dashboard')
        if 'comment_id' in self.kwargs:
            try:
                self.c = models.Comment.objects.get_from_kwargs(**self.kwargs)
            except models.Comment.DoesNotExist:
                messages.error(self.request, "That comment does not exist")
                return redirect('dashboard')

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
                'link': self.request.build_absolute_uri(self.q.get_absolute_url())
            }

            # body = loader.render_to_string('email/newcomment.html', c)
            # t = tasks.HTMLEmailTask(
            #     "[MedBank] One of your questions has received a comment",
            #     body,
            #     ["%s" % self.q.creator.user.email, ],
            # )

            # queue.add_task(t)

        return redirect(self.q)


@class_view_decorator(login_required)
class ViewQuestion(DetailView):
    template_name = "question/view.html"

    def dispatch(self, request, *args, **kwargs):
        r = super(ViewQuestion, self).dispatch(request, *args, **kwargs)

        if not self.object.is_viewable_by(self.request.user.student):
            if self.object.deleted and not self.request.user.is_superuser:
                raise Http404
            messages.warning(self.request, "Unfortunately you are unable to view that question at this time.")
            return redirect(self.object.teaching_activity_year.teaching_activity)

        return r

    def get_object(self):
        try:
            question = models.Question.objects.get_from_kwargs(allow_deleted=self.request.user.is_superuser, **self.kwargs)
        except models.Question.DoesNotExist:
            raise Http404

        if 'version' in self.request.GET:
            try:
                version = reversion.get_for_object(question).get(id=self.request.GET['version'])
            except reversion.models.Version.DoesNotExist:
                messages.error(self.request, "That version could not be found.")
            else:
                fd = version.field_dict
                # raise
                for field_name, value in version.field_dict.items():
                    if field_name in ['teaching_activity_year', 'id', 'creator']:
                        continue
                    setattr(question, field_name, value)

        return question

    def get_context_data(self, **kwargs):
        c = super(ViewQuestion, self).get_context_data(**kwargs)

        c['student_can_edit_question'] = self.object.is_editable_by(self.request.user.student)
        c['has_revisions'] = len(reversion.get_for_object(self.object)) > 1
        c['writing_period_id'] = self.request.GET.get("writing_period", None)

        # print self.object.unicode_body()
        return c


@class_view_decorator(login_required)
class ViewPreviousVersions(DetailView):
    template_name = "question/revisions.html"

    def dispatch(self, request, *args, **kwargs):
        r = super(ViewPreviousVersions, self).dispatch(request, *args, **kwargs)

        if not self.object.is_viewable_by(self.request.user.student):
            if self.object.deleted and not self.request.user.is_superuser:
                raise Http404
            messages.warning(self.request, "Unfortunately you are unable to view previous versions of that question at this time.")
            return redirect(self.object.teaching_activity_year.teaching_activity)

        return r

    def get_object(self):
        try:
            return models.Question.objects.get_from_kwargs(allow_deleted=self.request.user.is_superuser, **self.kwargs)
        except models.Question.DoesNotExist:
            raise Http404

    def get_context_data(self, **kwargs):
        c = super(ViewPreviousVersions, self).get_context_data(**kwargs)

        c['previous_versions'] = reversion.get_for_object(self.object)[1:]
        for version in c['previous_versions']:
            version.field_dict["explanation_dict"] = json.loads(version.field_dict["explanation"])

        return c



@class_view_decorator(user_is_superuser)
class QuestionAttributes(FormView):
    form_class = forms.QuestionAttributesForm
    template_name = "question/attributes.html"

    def dispatch(self, request, *args, **kwargs):
        try:
            self.question = models.Question.objects.get_from_kwargs(allow_deleted=self.request.user.is_superuser, **kwargs)
        except models.Question.DoesNotExist:
            messages.error(request, "That question does not exist.")
            return redirect('home')

        return super(QuestionAttributes, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(QuestionAttributes, self).get_form_kwargs()
        kwargs.update({'instance': self.question})
        return kwargs

    def form_valid(self, form):
        form.save()
        return super(QuestionAttributes, self).form_valid(form)

    def get_success_url(self):
        return self.question.get_absolute_url()
