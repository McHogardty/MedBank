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
        return models.TeachingActivityYear.objects.get_open_activities_assigned_to(self.request.user.student)

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

        writing_period_id = self.request.GET.get("writing_period", None)
        writing_period = None
        if writing_period_id and self.request.user.is_superuser:
            try:
                writing_period = models.QuestionWritingPeriod.objects.get(id=writing_period_id)
            except models.QuestionWritingPeriod.DoesNotExist:
                pass
        activity_year = self.object.get_latest_activity_year_for_student(self.request.user.student, writing_period=writing_period)

        current_block_year = activity_year.block_week.writing_period.block_year
        # current_writing_period = current_block_year.writing_period_for_student(self.request.user.student)
        c['question_list'] = []
        # c['current_writing_period'] = current_writing_period
        # c['latest_activity_year'] = self.object.current_activity_year()
        c['activity_year'] = activity_year

        c['activity'] = self.object

        c['can_view_questions'] = self.object.approved_questions_are_viewable_by(self.request.user.student)
        c['can_view_block'] = activity_year.block_week.writing_period.block_year.block.is_viewable_by(self.request.user.student)
        c['view_signup_status'] = self.object.student_can_view_sign_up_information(self.request.user.student, writing_period=writing_period)
        c['student_has_written_questions'] = self.object.student_has_written_questions(self.request.user.student)
        c['can_write_questions'] = activity_year.questions_can_be_written_by(self.request.user.student)

        if c['can_view_questions']:
            c['question_list'] += self.object.questions_for(self.request.user.student)
        elif c['student_has_written_questions']:
            c['question_list'] += self.object.questions_written_by(self.request.user.student)

        c['student_is_writing_for_activity'] = self.object.has_student(self.request.user.student)
        if c['view_signup_status']:
            c['current_question_writer_count'] = self.object.question_writer_count_for_student(self.request.user.student, writing_period=writing_period)
        if c['student_is_writing_for_activity']:
            c['student_can_unassign_from_activity'] = activity_year.student_can_unassign_activity(self.request.user.student)
        else:
            if c['view_signup_status']:
                c['student_can_sign_up'] = activity_year.student_can_sign_up(self.request.user.student)

        return c


@class_view_decorator(user_is_superuser)
class AssignPreviousActivity(GetObjectMixin, UpdateView):
    form_class = forms.AssignPreviousActivityForm
    template_name = "activity/assign_previous_activity.html"
    model = models.TeachingActivity

    def get_context_data(self, **kwargs):
        c = super(AssignPreviousActivity, self).get_context_data(**kwargs)
        c['teaching_activity'] = self.object
        c['activity_blocks'] = models.TeachingBlock.objects.filter(years__writing_periods__weeks__activities__teaching_activity=self.object).distinct()
        return c

    def get_form_kwargs(self, **kwargs):
        k = super(AssignPreviousActivity, self).get_form_kwargs(**kwargs)
        k['activity_queryset'] = models.TeachingActivity.objects.all()
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

        writing_period_id = self.request.GET.get('writing_period', None)
        writing_period = None
        if writing_period_id and self.request.user.is_superuser:
            try:
                writing_period = models.QuestionWritingPeriod.objects.get(id=writing_period_id)
            except models.QuestionWritingPeriod.DoesNotExist:
                pass
        activity_year = activity.get_latest_activity_year_for_student(self.request.user.student, writing_period=writing_period)

        if activity_year.student_can_sign_up(self.request.user.student):
            activity_year.add_student(self.request.user.student)
            messages.success(self.request, "You are now signed up to write questions for '%s'." % activity.name)
        else:
            messages.warning(self.request, "Unfortunately you are unable to sign up for this activity.")

        if writing_period:
            return activity.get_absolute_url(writing_period=writing_period)
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

        writing_period_id = self.request.GET.get('writing_period', None)
        writing_period = None
        if writing_period_id and self.request.user.is_superuser:
            try:
                writing_period = models.QuestionWritingPeriod.objects.get(id=writing_period_id)
            except models.QuestionWritingPeriod.DoesNotExist:
                pass
        activity_year = activity.get_latest_activity_year_for_student(self.request.user.student, writing_period=writing_period)

        if activity_year.student_can_unassign_activity(self.request.user.student):
            activity_year.remove_student(self.request.user.student)
            messages.success(self.request, "You have been unassigned from that activity")
        else:
            if not activity_year.has_student(self.request.user.student):
                messages.warning(self.request, "You weren't signed up to that activity for %s" % activity_year.block_week.writing_period.block_year.year)
            elif not activity_year.block_week_writing_period.block_year.student_can_sign_up():
                messages.error(self.request, "You are unable to unassign yourself from this activity because the sign-up period has closed.")
            elif activity_year.student_has_written_questions(self.request.user.student):
                messages.error(self.request, "Once you have started writing questions for an activity, you are not able unassign yourself from it.")
            else:
                messages.error(self.request, "Unfortunately you cannot unassign yourself from that activity.")

        if writing_period:
            return activity.get_absolute_url(writing_period=writing_period)
        else:
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

        writing_period_id = self.request.GET.get('writing_period', None)
        writing_period = None
        if writing_period_id and self.request.user.is_superuser:
            try:
                writing_period = models.QuestionWritingPeriod.objects.get(id=writing_period_id)
            except models.QuestionWritingPeriod.DoesNotExist:
                pass
        activity_year = self.activity.get_latest_activity_year_for_student(self.request.user.student, writing_period=writing_period)

        activity_year.add_student(student)

        # Use the user to prevent extra queries.
        messages.success(self.request, "The student %s was successfully added to this activity." % form.cleaned_data['user'].username)
        return redirect(self.activity.get_absolute_url(writing_period=writing_period))
