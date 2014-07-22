from django.contrib.auth.decorators import login_required, permission_required
from django.views.generic import DetailView, ListView
from django.views.generic.base import RedirectView
from django.views.generic.edit import UpdateView
from django.contrib import messages
from django.shortcuts import redirect
from django.core.urlresolvers import reverse

from .base import class_view_decorator, user_is_superuser

from questions import models, forms

@class_view_decorator(login_required)
class MyActivitiesView(ListView):
    model = models.TeachingActivityYear
    template_name = "activity/mine.html"

    def get_queryset(self):
        ret = {}
        ta = models.TeachingActivityYear.objects.filter(question_writers=self.request.user).order_by('week', 'position')
        for t in ta:
            l = ret.setdefault(t.block_year, [])
            l.append(t)
        ret = ret.items()
        ret.sort(key=lambda a: a[0].code)
        return ret



@class_view_decorator(login_required)
class ViewActivity(DetailView):
    model = models.TeachingActivityYear
    template_name="activity/view.html"

    def dispatch(self, request, *args, **kwargs):
        r = super(ViewActivity, self).dispatch(request, *args, **kwargs)

        if not self.request.user.student.can_view_activity(self.object):
            messages.warning(self.request, "Unfortunately you are unable to view that activity at this time.")
            return redirect(self.object.latest_block().get_activity_display_url())

        return r

    def get_object(self):
        return models.TeachingActivity.objects.get(reference_id=self.kwargs['reference_id'])

    def get_context_data(self, **kwargs):
        c = super(ViewActivity, self).get_context_data(**kwargs)
        question_list = []

        latest_activity_year = self.object.latest_year()
        latest_block_year = latest_activity_year.block_year

        c['activity'] = self.object
        # The user can see questions written for this activity if they have written questions for this block at some point.
        has_written_questions_for_block = any(activity_year.block_year.question_count_for_student(self.request.user.student) for activity_year in self.object.years.all())
        c['can_view_questions'] = has_written_questions_for_block or self.request.user.has_perm("questions.can_approve")
        if c['can_view_questions']:
            question_list += self.object.questions_for(self.request.user.student)
        c['can_write_questions'] = self.request.user.student.can_write_for(self.object)
        c['question_list'] = question_list
        # The user has written questions for the activity.
        c['student_has_written_questions'] = bool(self.object.years.filter(questions__creator=self.request.user.student).count())

        # The user only needs to view the information about signup and due dates if they are able to sign up for it.
        # This means that the latest block year should not be released yet, and they should be in the right stage.
        c['view_signup_status'] = latest_block_year.block.stage == self.request.user.student.get_current_stage() and not latest_block_year.released

        c['student_can_sign_up'] = self.request.user.student.can_sign_up_for(self.object)
        c['student_is_writing_for_activity'] = self.request.user.student.is_writing_for(self.object)
        c['questions_left_for_student'] = latest_activity_year.questions_left_for(self.request.user.student)

        # The student can unassign themselves from an activity if three conditions are met:
        # 1. They are writing for the latest activity year
        # 2. The activity_year that they are signed up for still has its signup period open
        # 3. They have not written any questions for the activity.
        c['student_can_unassign_from_activity'] = self.request.user.student.can_unassign_from(self.object)
        return c


@class_view_decorator(user_is_superuser)
class AssignPreviousActivity(UpdateView):
    form_class = forms.AssignPreviousActivityForm
    template_name = "activity/assign_previous_activity.html"

    def get_object(self, *args, **kwargs):
        return models.TeachingActivity.objects.get_from_kwargs(**self.kwargs)

    def get_context_data(self, **kwargs):
        c = super(AssignPreviousActivity, self).get_context_data(**kwargs)
        c['teaching_activity'] = self.object
        return c


    def get_success_url(self):
        return self.object.get_absolute_url()


@class_view_decorator(login_required)
class SignupView(RedirectView):
    permanent = False
    def get_redirect_url(self, reference_id):
        print "Getting to view."
        try:
            activity = models.TeachingActivity.objects.get(reference_id=reference_id)
        except models.TeachingActivity.DoesNotExist:
            messages.error(self.request, "That teaching activity was not found.")
            return reverse('dashboard')

        if self.request.user.student.can_sign_up_for(activity):
            activity.add_student(self.request.user.student)
            messages.success(self.request, "You are now signed up to write questions for '%s'." % activity.name)
        elif not self.request.user.student.get_current_stage() == activity.latest_block().block.stage:
            messages.warning(self.request, "Unfortunately you are unable to sign up to this activity because it is not in your current stage.")
        elif not activity.latest_block().can_sign_up:
            messages.warning(self.request, "Unfortunately you cannot sign up to this activity because the signup period has closed.")
        elif activity.latest_year().enough_writers():
            messages.warning(self.request, "Sorry, we already have anough people signed up for that activity.")

        if self.request.GET.get("from") == "block":
            return activity.latest_block().get_activity_display_url()
        else:
            return activity.get_absolute_url()


@class_view_decorator(login_required)
class UnassignView(RedirectView):
    permanent = False

    def get_redirect_url(self, reference_id):
        try:
            activity = models.TeachingActivity.objects.get(reference_id=reference_id)
        except models.TeachingActivity.DoesNotExist:
            messages.error(self.request, "That teaching activity does not exist.")
            return reverse('dashboard')
        student = self.request.user.student
        if student.can_unassign_from(activity):
            activity.remove_student(student)
            messages.success(self.request, "You have been unassigned from that activity")
        else:
            if not student.is_writing_for_year(activity.latest_year()):
                messages.warning(self.request, "You weren't signed up to that activity for %s" % activity.latest_year().block_year.year)
            elif not activity.latest_year().block_year.can_sign_up:
                messages.error(self.request, "You are unable to unassign yourself from this activity because the sign-up period has closed.")
            elif activity.latest_year().questions_written_by(student).exists():
                messages.error(self.request, "Once you have started writing questions for an activity, you are not able unassign yourself from it.")
            else:
                messages.error(self.request, "Unfortunately you cannot unassign yourself from that activity.")

        return activity.get_absolute_url()


