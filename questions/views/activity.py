from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required
from django.views.generic import DetailView, ListView
from django.views.generic.base import RedirectView
from django.views.generic.edit import UpdateView, FormView
from django.contrib import messages
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.http import Http404

from .base import class_view_decorator, user_is_superuser, GetObjectMixin

from questions import models, forms


@class_view_decorator(login_required)
class MyActivitiesView(ListView):
    model = models.TeachingActivityYear
    template_name = "activity/assigned.html"

    def get_queryset(self):
        return models.TeachingActivityYear.objects.get_unreleased_activities_assigned_to(self.request.user.student)

    def get_context_data(self, **kwargs):
        c = super(MyActivitiesView, self).get_context_data(**kwargs)
        c['assigned_activities'] = self.object_list
        return c


@class_view_decorator(login_required)
class ViewActivity(GetObjectMixin, DetailView):
    template_name="activity/view.html"
    model = models.TeachingActivity

    def dispatch(self, request, *args, **kwargs):
        r = super(ViewActivity, self).dispatch(request, *args, **kwargs)

        if not self.object.is_viewable_by(self.request.user.student):
            messages.warning(self.request, "Unfortunately you are unable to view that activity at this time.")
            return redirect(self.object.current_block_year().get_activity_display_url())

        return r

    def get_context_data(self, **kwargs):
        c = super(ViewActivity, self).get_context_data(**kwargs)
        c['question_list'] = []

        c['activity'] = self.object
        c['current_question_writer_count'] = self.object.current_question_writer_count()
        # The user can see questions written for this activity if they have written questions for this block at some point.
        c['can_view_questions'] = self.object.approved_questions_are_viewable_by(self.request.user.student)
        c['can_view_block'] = self.object.current_block_year().block.is_viewable_by(self.request.user.student)
        if c['can_view_questions']:
            c['question_list'] += self.object.questions_for(self.request.user.student)

        c['can_write_questions'] = self.object.questions_can_be_written_by(self.request.user.student)
        c['student_has_written_questions'] = self.object.student_has_written_questions(self.request.user.student)

        c['view_signup_status'] = self.object.student_can_view_sign_up_information(self.request.user.student)
        c['student_is_writing_for_activity'] = self.object.has_student(self.request.user.student)
        if c['student_is_writing_for_activity']:
            c['questions_left_for_student'] = self.object.questions_left_for(self.request.user.student)
            c['student_can_unassign_from_activity'] = self.object.student_can_unassign_activity(self.request.user.student)
        else:
            # The user only needs to view the information about signup and due dates if they are able to sign up for it.
            # This means that the current block year should not be released yet, and they should be in the right stage.
            if c['view_signup_status']:
                c['student_can_sign_up'] = self.object.student_can_sign_up(self.request.user.student)

        return c


@class_view_decorator(user_is_superuser)
class AssignPreviousActivity(GetObjectMixin, UpdateView):
    form_class = forms.AssignPreviousActivityForm
    template_name = "activity/assign_previous_activity.html"
    model = models.TeachingActivity

    def get_context_data(self, **kwargs):
        c = super(AssignPreviousActivity, self).get_context_data(**kwargs)
        c['teaching_activity'] = self.object
        return c

    def get_form_kwargs(self, **kwargs):
        k = super(AssignPreviousActivity, self).get_form_kwargs(**kwargs)
        k['activity_queryset'] = models.TeachingActivity.objects.filter(years__block_year__block=self.object.current_activity_year().block_year.block).distinct()
        return k

    def get_success_url(self):
        return self.object.get_absolute_url()


@class_view_decorator(login_required)
class SignupView(RedirectView):
    permanent = False
    def get_redirect_url(self, reference_id):
        try:
            activity = models.TeachingActivity.objects.get_from_kwargs(**{'reference_id': reference_id})
        except models.TeachingActivity.DoesNotExist:
            messages.error(self.request, "That teaching activity was not found.")
            return reverse('dashboard')

        if activity.student_can_sign_up(self.request.user.student):
            activity.add_student(self.request.user.student)
            messages.success(self.request, "You are now signed up to write questions for '%s'." % activity.name)
        elif not activity.current_block_year().student_is_eligible_for_sign_up(self.request.user.student):
            messages.warning(self.request, "Unfortunately you are unable to sign up to this activity because it is not in your current stage.")
        elif not activity.current_block_year().can_sign_up:
            messages.warning(self.request, "Unfortunately you cannot sign up to this activity because the signup period has closed.")
        elif activity.current_activity_year().enough_writers():
            messages.warning(self.request, "Sorry, we already have anough people signed up for that activity.")

        if self.request.GET.get("from") == "block":
            return activity.current_block_year().get_activity_display_url()
        else:
            return activity.get_absolute_url()


@class_view_decorator(login_required)
class UnassignView(RedirectView):
    permanent = False

    def get_redirect_url(self, reference_id):
        try:
            activity = models.TeachingActivity.objects.get_from_kwargs(reference_id=reference_id)
        except models.TeachingActivity.DoesNotExist:
            messages.error(self.request, "That teaching activity does not exist.")
            return reverse('dashboard')
        student = self.request.user.student
        if activity.student_can_unassign_activity(student):
            activity.remove_student(student)
            messages.success(self.request, "You have been unassigned from that activity")
        else:
            if not activity.has_student(self.request.user.student):
                messages.warning(self.request, "You weren't signed up to that activity for %s" % activity.current_block_year().year)
            elif not activity.current_block_year().can_sign_up:
                messages.error(self.request, "You are unable to unassign yourself from this activity because the sign-up period has closed.")
            elif activity.student_has_written_questions(self.request.user.student):
                messages.error(self.request, "Once you have started writing questions for an activity, you are not able unassign yourself from it.")
            else:
                messages.error(self.request, "Unfortunately you cannot unassign yourself from that activity.")

        return activity.get_absolute_url()


@class_view_decorator(user_is_superuser)
class AssignStudent(GetObjectMixin, FormView):
    permanent = False
    form_class = forms.StudentSelectionForm
    template_name = "activity/assign_student.html"

    def dispatch(self, request, *args, **kwargs):
        self.activity = models.TeachingActivity.objects.get_from_kwargs(**kwargs)

        return super(AssignStudent, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self, **kwargs):
        k = super(AssignStudent, self).get_form_kwargs(**kwargs)
        k['user_url'] = reverse("user-list")
        return k

    def get_initial(self, *args, **kwargs):
        i = super(AssignStudent, self).get_initial(*args, **kwargs)
        i['activity'] = self.activity
        return i

    def form_valid(self, form):
        student = form.cleaned_data['user'].student
        self.activity.add_student(student)
        # Use the user to prevent extra queries.
        messages.success(self.request, "The student %s was successfully added to this activity." % form.cleaned_data['user'].username)
        return redirect(self.activity)
