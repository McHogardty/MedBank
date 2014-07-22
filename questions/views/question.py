from django.contrib.auth.decorators import login_required, permission_required
from django.views.generic import DetailView, FormView, TemplateView
from django.views.generic.base import RedirectView
from django.views.generic.edit import CreateView, UpdateView
from django.http import Http404
from django.contrib import messages
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.template import loader

from .base import class_view_decorator

from questions import models, forms, tasks


@class_view_decorator(login_required)
class QuestionGuide(TemplateView):
    template_name = "question/guide.html"


@class_view_decorator(login_required)
class NewQuestion(CreateView):
    model = models.Question
    form_class = forms.NewQuestionForm
    template_name = "question/new.html"

    def dispatch(self, request, *args, **kwargs):
        try:
            self.activity = models.TeachingActivity.objects.get_from_kwargs(**kwargs)
        except models.TeachingActivity.DoesNotExist:
            raise Http404

        if not self.request.user.student.can_write_for(self.activity):
            messages.warning(request, "You are not currently able to write questions for this activity.")
            return redirect(self.activity)

        return super(NewQuestion, self).dispatch(request, *args, **kwargs)

    def get_initial(self):
        i = super(NewQuestion, self).get_initial().copy()
        i.update({'teaching_activity_year': self.activity.latest_year(), 'creator': self.request.user.student})
        return i

    def form_valid(self, form):
        messages.success(self.request, "Thanks, your question has been submitted!") # You'll get an email when it's approved.")
        return super(NewQuestion, self).form_valid(form)

    def get_success_url(self):
        return self.object.get_absolute_url()


@class_view_decorator(login_required)
class UpdateQuestion(UpdateView):
    model = models.Question
    form_class = forms.NewQuestionForm
    template_name = "question/new.html"

    def dispatch(self, request, *args, **kwargs):
        r = super(UpdateQuestion, self).dispatch(request, *args, **kwargs)

        if not self.request.user.student.can_edit(self.object):
            messages.warning(self.request, "Unfortunately you are unable to edit that question.")
            return redirect(self.object)

        return r

    def get_queryset(self):
        return models.Question.objects.filter(teaching_activity_year__teaching_activity__reference_id=self.kwargs['reference_id'])

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
                r.related_object = o
                r.reason_type = models.Reason.TYPE_EDIT
                r.save()
        return super(UpdateQuestion, self).form_valid(form)


    def get_success_url(self):
        return self.object.get_absolute_url()


@class_view_decorator(login_required)
class AddComment(CreateView):
    model = models.Comment
    form_class = forms.CommentForm
    template_name = "question/comment.html"

    def dispatch(self, request, *args, **kwargs):
        try:
            self.q = models.Question.objects.get(pk=self.kwargs['pk'])
        except models.Question.DoesNotExist:
            messages.error(self.request, "That question does not exist")
            return redirect('dashboard')
        if 'comment_id' in self.kwargs:
            try:
                self.c = models.Comment.objects.get(pk=self.kwargs['comment_id'])
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

            body = loader.render_to_string('email/newcomment.html', c)
            t = tasks.HTMLEmailTask(
                "[MedBank] One of your questions has received a comment",
                body,
                ["%s" % self.q.creator.user.email, ],
            )

            # queue.add_task(t)

        return redirect(self.q)


@class_view_decorator(login_required)
class ViewQuestion(DetailView):
    model = models.Question
    template_name = "question/view.html"

    def dispatch(self, request, *args, **kwargs):
        r = super(ViewQuestion, self).dispatch(request, *args, **kwargs)

        if not self.request.user.student.can_view(self.object):
            if self.object.deleted and not self.request.user.is_superuser:
                raise Http404
            messages.warning(self.request, "Unfortunately you are unable to view that question at this time.")
            return redirect(self.object.teaching_activity_year.teaching_activity)

        return r

    def get_context_data(self, **kwargs):
        c = super(ViewQuestion, self).get_context_data(**kwargs)

        c['student_can_edit_question'] = self.request.user.student.can_edit(self.object)

        if self.request.user.has_perm('questions.can_approve'):
            c['associated_reasons'] = self.object.associated_reasons()

        return c




@class_view_decorator(permission_required('questions.can_approve'))
class QuestionAttributes(FormView):
    form_class = forms.QuestionAttributesForm
    template_name = "question/attributes.html"

    def dispatch(self, request, *args, **kwargs):
        try:
            self.question = models.Question.objects.get(id=self.kwargs['pk'])
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
