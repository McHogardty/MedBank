from django.contrib.auth.decorators import permission_required
from django.views.generic import DetailView, ListView, FormView, TemplateView
from django.views.generic.base import RedirectView
from django.views.generic.edit import UpdateView
from django.http import Http404
from django.contrib import messages
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django import db

from .base import class_view_decorator

from questions import models, forms

@class_view_decorator(permission_required('questions.can_approve'))
class ApprovalGuide(TemplateView):
    template_name = "approval/guide.html"


@class_view_decorator(permission_required('questions.can_approve'))
class ApprovalDashboardView(TemplateView):
    template_name = "approval/dashboard.html"

    def get_context_data(self, **kwargs):
        c = super(ApprovalDashboardView, self).get_context_data(**kwargs)
        c["questions_to_approve"] = models.Question.objects.filter(approver=self.request.user.student, date_completed__isnull=True).count()
        message_settings = list(models.ApprovalDashboardSetting.objects.filter(name__in=models.ApprovalDashboardSetting.ALL_SETTINGS))
        message_settings = dict((setting.name, setting) for setting in message_settings)

        block_count = models.TeachingBlockYear.objects.get_blocks_with_unassigned_pending_questions_for_stages(self.request.user.student.get_all_stages()).count()

        override = message_settings.get(models.ApprovalDashboardSetting.OVERRIDE_MESSAGE, None)
        setting_to_use = None
        main_feature_text = ""
        secondary_feature_text = ""

        try:
            if override and (override.main_text() or override.secondary_text()):
                setting_to_use = override
            elif c["questions_to_approve"]:
                setting_to_use = message_settings[models.ApprovalDashboardSetting.ASSIGNED_QUESTIONS_NEED_APPROVAL]
            else:
                if block_count:
                    setting_to_use = message_settings[models.ApprovalDashboardSetting.ASSIGNED_QUESTIONS_APPROVED_AND_QUESTIONS_LEFT]
                else:
                    setting_to_use = message_settings[models.ApprovalDashboardSetting.ASSIGNED_QUESTIONS_APPROVED_NO_QUESTIONS_LEFT]
        except KeyError:
            pass

        if setting_to_use:
            main_feature_text = setting_to_use.main_text() or ""
            secondary_feature_text = setting_to_use.secondary_text() or ""

        if not main_feature_text and not secondary_feature_text:
            try:
                main_feature_text = message_settings[models.ApprovalDashboardSetting.DEFAULT_MESSAGE].main_text()
                secondary_feature_text = message_settings[models.ApprovalDashboardSetting.DEFAULT_MESSAGE].secondary_text()
            except KeyError:
                main_feature_text = ""
                secondary_feature_text = ""

        guide_message = message_settings.get(models.StudentDashboardSetting.GUIDE_MESSAGE, None)
        main_guide_text = guide_message.main_text() if guide_message else ""
        secondary_guide_text = guide_message.secondary_text() if guide_message else ""

        c.update({'main_feature_text': main_feature_text, "secondary_feature_text": secondary_feature_text})
        c.update({'main_guide_text': main_guide_text or "", "secondary_guide_text": secondary_guide_text or ""})
        c.update({'block_count': block_count})

        c['block_list_for_assigning_activities_url'] = models.TeachingBlockYear.get_approval_assign_block_list_url()
        return c


@class_view_decorator(permission_required('questions.can_approve'))
class AssignActivitiesForApprovalView(DetailView):
    template_name = "approval/assign.html"

    def dispatch(self, request, *args, **kwargs):
        r = super(AssignActivitiesForApprovalView, self).dispatch(request, *args, **kwargs)

        # Approvers can only approve for blocks they have completed.
        if not self.request.user.student.can_view_block_year(self.object):
            messages.warning(self.request, "Unfortunately you are unable to view that block right now.")
            return redirect(models.TeachingBlockYear.get_approval_assign_block_list_url())

        return r

    def get_object(self, *args, **kwargs):
        return models.TeachingBlockYear.objects.get_from_kwargs(**self.kwargs)

    def get_context_data(self, **kwargs):
        c = super(AssignActivitiesForApprovalView, self).get_context_data(**kwargs)

        c["teaching_block"] = self.object.block
        c["teaching_block_year"] = self.object
        c["weeks"] = self.object.get_pending_unassigned_activities_as_weeks()
        return c


@class_view_decorator(permission_required('questions.can_approve'))
class ApprovalHome(TemplateView):
    template_name = "approval/old-home.html"

    def get_context_data(self, **kwargs):
        c = super(ApprovalHome, self).get_context_data(**kwargs)
        c['has_assigned_approvals'] = models.Question.objects.filter(approver=self.request.user.student, date_completed__isnull=True).count()
        return c


@class_view_decorator(permission_required('questions.can_approve'))
class CompleteAssignedApprovalView(RedirectView):
    permanent = False

    def get_redirect_url(self, previous_question_id=None):
        # Keep track of question progress and total questions needing to be approved.
        self.progress = 0
        self.total = 0

        previous_question = None

        if previous_question_id:
            try:
                previous_question = models.Question.objects.get(pk=previous_question_id)
            except models.Question.DoesNotExist:
                messages.error(self.request, "That question was not found.")
                return reverse('approve-home')

        # Get all questions which have not been completed and order them by those assigned first.
        # Unless they are super human, they can only sign up to one activity at a particular moment in time,
        # so sorting by date_assigned should nicely sort the questions by teaching activity.
        # We allow people to skip questions. These questions will still be present so we just get all the
        # ones which were assigned AFTER the question which was skipped.
        questions = self.request.user.student.assigned_questions.filter(date_completed__isnull=True)

        if previous_question:
            # Get all of the questions assigned after the previous question.
            # Since it is more than likely that we assigned multiple questions in a particular
            # second, we also have to filter by ID
            questions = questions.filter(
                db.models.Q(date_assigned__gt=previous_question.date_assigned) | db.models.Q(date_assigned=previous_question.date_assigned, id__gt=previous_question.id)
            )

        questions = questions.order_by('date_assigned', 'id')

        try:
            current_question = questions[:1].get()
        except models.Question.DoesNotExist:
            messages.success(self.request, "All of your assigned questions have been approved.")
            return reverse('approve-home')

        return current_question.get_approval_url(multiple_approval_mode=True)


@class_view_decorator(permission_required('questions.can_approve'))
class AssignApproval(RedirectView):
    permanent = False
    def get_redirect_url(self, reference_id, year):
        try:
            activity = models.TeachingActivityYear.objects.get(teaching_activity__reference_id=reference_id, block_year__year=year)
        except models.TeachingActivityYear.DoesNotExist:
            messages.error(self.request, 'That teaching activity does not exist.')
            return reverse('approve-home')

        if activity.has_assigned_approver():
            messages.error(self.request, 'The teaching activity %s already has an assigned approver.' % activity)
        else:
            activity.assign_pending_questions_to_student(self.request.user.student)

            messages.success(self.request, 'You have been assigned to approve the activity %s.' % (activity, ))
        return activity.block_year.get_approval_assign_url()


@class_view_decorator(permission_required("questions.can_approve"))
class ViewQuestionApprovalHistory(DetailView):
    model = models.Question
    template_name = "question/history.html"

    def dispatch(self, request, *args, **kwargs):
        r = super(ViewQuestionApprovalHistory, self).dispatch(request, *args, **kwargs)

        if self.object.deleted and not self.request.user.is_superuser:
            raise Http404

        return r


@class_view_decorator(permission_required("questions.can_approve"))
class QuestionApproval(UpdateView):
    template_name = "question/approve.html"
    form_class = forms.QuestionApprovalForm
    model = models.Question

    def dispatch(self, request, *args, **kwargs):
        self.multiple_question_approval_mode = models.Question.request_is_in_multiple_approval_mode(request)
        r = super(QuestionApproval, self).dispatch(request, *args, **kwargs)

        # If the question is deleted, then nobody should be able to see it except the superusers.
        if self.object.deleted and not self.request.user.is_superuser:
            raise Http404

        return r

    def get_context_data(self, **kwargs):
        c = super(QuestionApproval, self).get_context_data(**kwargs)
        c['question'] = self.object
        c['multiple_question_approval_mode'] = self.multiple_question_approval_mode

        if self.multiple_question_approval_mode:
            # Add a progress bar to the top of the page. We will consider the progress bar 'reset' if they had no questions left to approve
            # when they last assigned some questions to themselves.
            # We will only consider questions which were assigned from the approval dashboard. This means any questions which were
            # 'manually' created (have identical assign and completion dates) should be excluded.
            all_questions = self.request.user.student.assigned_questions.exclude(date_completed=db.models.F('date_assigned'))
            completed_questions = []
            incomplete_questions = []
            for question in all_questions:
                if question.date_completed:
                    completed_questions.append(question)
                else:
                    incomplete_questions.append(question)

            incomplete_questions.sort(key=lambda q: q.date_assigned)
            completed_questions.sort(key=lambda q: q.date_completed)

            # If the incomplete question was assigned before the last completion date, it counts as part of that group.
            total = 0
            for index, question in enumerate(completed_questions):
                # Is the earliest assigned incomplete question before this complete question?

                if incomplete_questions[0].date_assigned <= question.date_completed:
                    # Then the complete question counts as part of this group of assigned questions.
                    # All the questions after this particular question will also count because they
                    # were completed after this particular question.
                    total = len(incomplete_questions) + len(completed_questions[index:])
                    break

            if not total:
                # If we don't break out of the loop, or if there are no complete questions then the earliest
                # incomplete question was assigned after all of the complete questions were completed. We
                # start counting again from the beginning.
                total = len(incomplete_questions)

            c['assigned_approvals_total'] = total
            c['assigned_approvals_remaining'] = len(incomplete_questions)
            c['assigned_approvals_completed'] = total - len(incomplete_questions)

        return c

    def form_valid(self, form):
        new_status = form.cleaned_data["new_status"]
        if new_status == models.Question.FLAGGED_STATUS:
            return redirect(self.object.get_flag_url(multiple_approval_mode=self.multiple_question_approval_mode))

        # Don't change the exemplary_question marker unless we're sure that the
        # change of status worked.
        # We don't need to check if the question is already a particular status because
        # the form already does that for us and removes that choice from the user's options.
        question = form.save(commit=False)
        question.change_status(new_status, self.request.user.student)
        question.save()

        if self.multiple_question_approval_mode:
            return redirect(question.get_next_approval_url())

        messages.success(self.request, "The status for this question has successfully been changed.")
        if new_status == models.Question.DELETED_STATUS:
            return redirect(self.object.teaching_activity_year.teaching_activity)
        return redirect(self.object)


@class_view_decorator(permission_required('questions.can_approve'))
class FlagQuestion(FormView):
    form_class = forms.ReasonForFlaggingForm
    template_name = "approval/flag.html"

    def dispatch(self, request, *args, **kwargs):
        self.multiple_question_approval_mode = models.Question.request_is_in_multiple_approval_mode(request)

        try:
            self.question = models.Question.objects.get(pk=self.kwargs['pk'])
        except models.Question.DoesNotExist:
            messages.error(request, "That question does not exist.")
            return redirect('home')

        return super(FlagQuestion, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(FlagQuestion, self).get_form_kwargs()
        kwargs.update({'initial': {'question': self.question, 'creator': self.request.user.student, 'reason_type': models.Reason.TYPE_FLAG}})
        return kwargs

    def form_valid(self, form):
        q = self.question
        
        q.change_status(models.Question.FLAGGED_STATUS, self.request.user.student)

        reason = form.save(commit=False)
        reason.related_object = q
        reason.save()

        if self.multiple_question_approval_mode:
            return redirect(q.get_next_approval_url())

        return redirect(q)

