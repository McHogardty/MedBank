from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext, loader
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import HttpResponse, Http404, HttpResponseServerError
from django.core.urlresolvers import reverse, reverse_lazy
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.views.generic import View, ListView, DetailView, FormView, TemplateView
from django.views.generic.base import RedirectView
from django.views.generic.edit import CreateView, UpdateView
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
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
        bb = models.TeachingBlockYear.objects.filter(block__stage__number__in=s).order_by('block__code').distinct()
        if 'pending' in self.request.GET or 'flagged' in self.request.GET:
            records=models.ApprovalRecord.objects \
                .annotate(max=db.models.Max('question__approval_records__date_completed')) \
                .filter(max=db.models.F('date_completed'))
        else:
            bb = bb.filter(db.models.Q(release_date__year=datetime.datetime.now().year) | db.models.Q(start__year=datetime.datetime.now().year))

        if 'pending' in self.request.GET:
            # We have all the blocks with questions that have approval records. Now we need
            # The block with questions that
            records = records.filter(db.models.Q(status=models.ApprovalRecord.PENDING_STATUS) | db.models.Q(date_completed__isnull=True))
            bb = bb.filter(activities__questions__approval_records__in=records)
            bb |= models.TeachingBlockYear.objects.filter(activities__questions__approval_records__isnull=True).distinct()
        elif 'flagged' in self.request.GET:
            records = records.filter(status=models.ApprovalRecord.FLAGGED_STATUS)
            bb = bb.filter(activities__questions__approval_records__in=records)

        return bb

    def get_context_data(self, **kwargs):
        c = super(AllBlocksView, self).get_context_data(**kwargs)
        c.update({'flagged': 'flagged' in self.request.GET})
        return c


@class_view_decorator(login_required)
class DashboardView(TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        c = super(DashboardView, self).get_context_data(**kwargs)
        c.update({'example_quiz_slug': settings.EXAMPLE_QUIZ_SLUG})
        allowed_blocks = models.TeachingBlockYear.objects.filter(block__stage=self.request.user.student.get_current_stage())
        block_count = allowed_blocks.filter(start__lte=datetime.datetime.now(), end__gte=datetime.datetime.now()).count()
        c.update({'block_count': block_count})

        message_settings = list(models.StudentDashboardSetting.objects.filter(name__in=models.StudentDashboardSetting.ALL_SETTINGS))
        message_settings = dict((setting.name, setting) for setting in message_settings)

        override = message_settings.get(models.StudentDashboardSetting.OVERRIDE_MESSAGE, None)
        setting_to_use = None
        main_feature_text = ""
        secondary_feature_text = ""

        try:
            if override and (override.main_text() or override.secondary_text()):
                setting_to_use = override
            elif self.request.user.student.current_assigned_activities().exists():
                if self.request.user.student.questions_due_soon_count():
                    setting_to_use = message_settings[models.StudentDashboardSetting.HAS_QUESTIONS_DUE_SOON]
                elif self.request.user.student.future_block_count():
                    setting_to_use = message_settings[models.StudentDashboardSetting.HAS_QUESTIONS_DUE_LATER]
                else:
                    setting_to_use = message_settings[models.StudentDashboardSetting.ALL_QUESTIONS_SUBMITTED]
            else:
                if block_count:
                    setting_to_use = message_settings[models.StudentDashboardSetting.NO_CURRENT_ACTIVITIES_AND_BLOCKS_OPEN]
                else:
                    setting_to_use = message_settings[models.StudentDashboardSetting.NO_CURRENT_ACTIVITIES_OR_BLOCKS_OPEN]
        except KeyError:
            pass

        if setting_to_use:
            main_feature_text = setting_to_use.main_text() or ""
            secondary_feature_text = setting_to_use.secondary_text() or ""

        if not main_feature_text and not secondary_feature_text:
            try:
                main_feature_text = message_settings[models.StudentDashboardSetting.DEFAULT_MESSAGE].main_text()
                secondary_feature_text = message_settings[models.StudentDashboardSetting.DEFAULT_MESSAGE].secondary_text()
            except KeyError:
                main_feature_text = ""
                secondary_feature_text = ""

        guide_message = message_settings.get(models.StudentDashboardSetting.GUIDE_MESSAGE, None)
        main_guide_text = guide_message.main_text() if guide_message else ""
        secondary_guide_text = guide_message.secondary_text() if guide_message else ""

        c.update({'main_feature_text': main_feature_text, "secondary_feature_text": secondary_feature_text})
        c.update({'main_guide_text': main_guide_text or "", "secondary_guide_text": secondary_guide_text or ""})

        return c


@class_view_decorator(permission_required('questions.can_approve'))
class ApprovalDashboardView(TemplateView):
    template_name = "approval/dashboard.html"

    def get_context_data(self, **kwargs):
        c = super(ApprovalDashboardView, self).get_context_data(**kwargs)
        c["questions_to_approve"] = models.ApprovalRecord.objects.filter(approver=self.request.user.student, date_completed__isnull=True).count()
        message_settings = list(models.ApprovalDashboardSetting.objects.filter(name__in=models.ApprovalDashboardSetting.ALL_SETTINGS))
        message_settings = dict((setting.name, setting) for setting in message_settings)

        s = [stage.number for stage in self.request.user.student.get_all_stages()]
        block_years = models.TeachingBlockYear.objects.filter(block__stage__number__in=s) \
            .filter(db.models.Q(release_date__year=datetime.datetime.now().year) | db.models.Q(start__year=datetime.datetime.now().year)) \
            .order_by('block__code').distinct()

        records=models.ApprovalRecord.objects \
            .annotate(max=db.models.Max('question__approval_records__date_completed')) \
            .filter(max=db.models.F('date_completed')) \
            .filter(status=models.ApprovalRecord.PENDING_STATUS)
        block_years = block_years.filter(db.models.Q(activities__questions__approval_records__in=records) | db.models.Q(activities__questions__approval_records__isnull=True))
        block_count = block_years.count()

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
        return c


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
        ret.sort(key=lambda a: a[0].code)
        return ret


@class_view_decorator(login_required)
class AllActivitiesView(ListView):
    model = models.TeachingActivityYear

    def dispatch(self, request, *args, **kwargs):
        self.teaching_block = None
        self.get_teaching_block()
        if not self.teaching_block:
            raise Http404
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
        if self.teaching_block:
            return self.teaching_block
        try:
            tb = models.TeachingBlockYear.objects.select_related().get(block__code=self.kwargs['code'], year=self.kwargs['year'])
        except models.TeachingBlockYear.DoesNotExist:
            return
        self.teaching_block = tb
        return tb

    def get_queryset(self):
        ta = models.TeachingActivityYear.objects.filter(block_year__block__code=self.kwargs['code'], block_year__year=self.kwargs['year']).select_related().prefetch_related('question_writers')
        if 'approve' in self.request.GET:
            ta = ta.exclude(questions__isnull=True)

            # We want all of those teaching activities who have questions without records,
            # or pending questions whose latest record is complete. These are the only ones
            # who we can assign an approver to.
            records = models.ApprovalRecord.objects.annotate(max=db.models.Max('question__approval_records__date_completed')) \
                .filter(max=db.models.F('date_completed')) \
                .filter(status=models.ApprovalRecord.PENDING_STATUS) \
                .select_related('question', 'question__teaching_activity_year')
            activities = list(set([record.question.teaching_activity_year.id for record in records]))
            ta = ta.filter(db.models.Q(id__in=activities) | db.models.Q(questions__approval_records__isnull=True))

        ta = ta.distinct()

        by_week = {}
        for t in ta:
            l = by_week.setdefault(t.week, [])
            l.append(t)
        for v in by_week.values():
            v.sort(key=lambda t: (t.activity_type, t.position))
        return [(k, not all(t.enough_writers() for t in by_week[k]), by_week[k]) for k in by_week]

    def get_context_data(self, **kwargs):
        c = super(AllActivitiesView, self).get_context_data(**kwargs)
        c['teaching_block'] = self.teaching_block
        if self.teaching_block.released:
            c['override_base'] = "newbase_with_actions.html"
        return c

    def get_template_names(self):
        return "approval/assign.html" if 'approve' in self.request.GET else "all2.html"


@class_view_decorator(permission_required('questions.can_approve'))
class AdminView(TemplateView):
    template_name = 'admin.html'

    def get_context_data(self, **kwargs):
        c = super(AdminView, self).get_context_data(**kwargs)
        tb = models.TeachingBlockYear.objects.order_by('block__stage', 'block__code')
        questions_pending = models.Question.questions_pending()
        questions_flagged = models.Question.questions_flagged()
        c.update({'blocks': tb, 'questions_pending': questions_pending, 'questions_flagged': questions_flagged,})
        c.update({'debug_mode': settings.DEBUG, 'maintenance_mode': settings.MAINTENANCE_MODE, })
        c.update({'quiz_specifications': models.QuizSpecification.objects.order_by('stage')})
        c.update({'student_dashboard_settings': models.StudentDashboardSetting.objects.all()})
        c.update({'approval_dashboard_settings': models.ApprovalDashboardSetting.objects.all()})
        return c

from medbank.models import Setting
@class_view_decorator(permission_required('questions.can_approve'))
class SettingView(DetailView):
    template_name = "admin/setting.html"
    queryset = Setting.objects.filter(class_name__in=[models.StudentDashboardSetting.__name__, models.ApprovalDashboardSetting.__name__])

    def get_object(self, *args, **kwargs):
        object = super(SettingView, self).get_object(*args, **kwargs)
        object.__class__ = getattr(models, object.class_name)
        return object



@class_view_decorator(permission_required('questions.can_approve'))
class EditSettingView(UpdateView):
    template_name = "generic/form.html"
    queryset = Setting.objects.filter(class_name__in=[models.StudentDashboardSetting.__name__, models.ApprovalDashboardSetting.__name__])
    form_class = forms.SettingEditForm

    def get_object(self, *args, **kwargs):
        object = super(EditSettingView, self).get_object(*args, **kwargs)
        object.__class__ = getattr(models, object.class_name)
        return object

    def get_context_data(self, **kwargs):
        c = super(EditSettingView, self).get_context_data(**kwargs)
        c['object_name'] = "Student Dashboard Setting"
        return c

    def form_valid(self, form):
        c = form.cleaned_data
        value_dict = {}
        value_dict["main_text"] = c["main_text"]
        value_dict["secondary_text"] = c["secondary_text"]

        self.object.value = json.dumps(value_dict)
        self.object.save()
        return super(EditSettingView, self).form_valid(form)

    def get_success_url(self):
        return reverse('admin-settings-view', kwargs={'pk': self.object.pk})


@class_view_decorator(permission_required('questions.can_approve'))
class CreateMissingSettingsView(RedirectView):
    permanent = False

    def get_redirect_url(self):
        settings_classes = [models.StudentDashboardSetting, models.ApprovalDashboardSetting]
        
        for cls in settings_classes:
            message_settings = cls.objects.filter(name__in=cls.ALL_SETTINGS).values_list('name', flat=True)
            message_settings = list(message_settings)
            if len(message_settings) != len(cls.ALL_SETTINGS):
                for setting in cls.ALL_SETTINGS:
                    if setting not in message_settings:
                        new_setting = cls()
                        new_setting.name = setting
                        new_setting.last_modified_by = self.request.user.student
                        new_setting.save()

                        message_settings.append(new_setting)

        return reverse('admin')


@class_view_decorator(permission_required('questions.can_approve'))
class BlockAdminView(DetailView):
    model = models.TeachingBlockYear
    template_name = "admin/block_admin.html"

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()

        return queryset.select_related("block").get(year=self.kwargs["year"], block__code=self.kwargs["code"])


@class_view_decorator(permission_required('questions.can_approve'))
class ApprovalStatisticsView(DetailView):
    model = models.TeachingBlockYear
    template_name = "admin/approval_statistics.html"

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()

        return queryset.select_related("block").get(year=self.kwargs["year"], block__code=self.kwargs["code"])

class QueryStringMixin(object):
    def query_string(self):
        allowed = ['show', 'approve', 'flagged', 'assigned']
        allowed_with_parameters = ['total', 'progress']
        g = self.request.GET.keys()
        if not g:
            return ""
        params = [k for k in g if k in allowed]
        if hasattr(self, "total") and hasattr(self, "progress") and self.total:
            params.append("total=%s" % self.total)
            params.append("progress=%s" % self.progress)
        else:
            params += ["%s=%s" % (k, self.request.GET[k]) for k in g if k in allowed_with_parameters]
        return "?%s" % ("&".join(params))


@class_view_decorator(permission_required('questions.can_approve'))
class ApprovalHome(TemplateView):
    template_name = "approval/old-home.html"

    def get_context_data(self, **kwargs):
        c = super(ApprovalHome, self).get_context_data(**kwargs)
        c['has_assigned_approvals'] = models.ApprovalRecord.objects.filter(approver=self.request.user.student, date_completed__isnull=True).count()
        return c


@class_view_decorator(permission_required('questions.can_approve'))
class StartApprovalView(QueryStringMixin, RedirectView):
    permanent = False

    def query_string(self, initial):
        if initial:
            parameters = ['show', 'approve']
            qs =  "?show&approve"
            if 'flagged' in self.request.GET:
                parameters.append('flagged')
            if 'assigned' in self.request.GET:
                parameters.append('assigned')
            if self.total:
                parameters.append('total=%s' % self.total)
                parameters.append('progress=%s' % self.progress)
            qs = "?%s" % ("&".join(parameters))
            return qs
        else:
            return super(StartApprovalView, self).query_string()

    def get_redirect_url(self, code=None, year=None, q_id=None):
        # Measure the progress and total records for an assigned approver.
        self.progress = 0
        self.total = 0

        # q_id contains the ID of the question which was just approved in approval mode.
        previous_q = None
        try:
            previous_q = models.Question.objects.get(pk=q_id)
        except models.Question.DoesNotExist:
            pass

        if 'assigned' in self.request.GET:
            # Get all approval records which have not been completed. Order them by those assigned first.
            # Unless they are super human, they can only sign up to one activity at a particular moment in time,
            # so sorting by date_assigned should nicely sort the approval records by teaching activity.
            # We allow people to skip questions. These approval records will still be present so we just get all the
            # ones which were assigned AFTER the question with the record which was skipped.
            previous_latest_record = None
            if previous_q:
                previous_latest_record = previous_q.latest_approval_record()

            approval_records = self.request.user.student.approval_records.all()
            if previous_latest_record:
                approval_records = approval_records.filter(db.models.Q(date_completed__isnull=True) | db.models.Q(id=previous_latest_record.id))
                approval_records = approval_records.filter(date_assigned__gte=previous_q.latest_approval_record().date_assigned)
            else:
                approval_records = approval_records.filter(date_completed__isnull=True)

            approval_records = approval_records.order_by('date_assigned', 'id')

            try:
                if previous_q:
                    # It is possible that we can assign them to two questions at the same date and time because we do three at once. Use the ID as a fallback since it is autoincrement.
                    q = approval_records.filter(id__gte=previous_latest_record.id)[1:2].get().question
                else:
                    q = approval_records[:1].get().question
            except models.ApprovalRecord.DoesNotExist:
                messages.success(self.request, "All of your assigned questions have been approved.")
                return reverse('approve-home')

            # Add a progress bar to the top of the page. We will consider the progress bar 'reset' if they had no questions left to approve
            # when they last assigned some questions to themselves.
            all_approval_records = list(self.request.user.student.approval_records.all())
            completed_approval_records = []
            incomplete_approval_records = []
            for record in all_approval_records:
                if record.date_completed:
                    completed_approval_records.append(record)
                else:
                    incomplete_approval_records.append(record)

            incomplete_approval_records.sort(key=lambda r: r.date_assigned)
            completed_approval_records.sort(key=lambda r: r.date_completed)

            # If the incomplete record was assigned before the last completion date, it counts as part of that group.
            if completed_approval_records:
                for index, record in enumerate(completed_approval_records):
                    # Is the earliest assigned incomplete record before this complete record?

                    if incomplete_approval_records[0].date_assigned <= record.date_completed:
                        # It counts as part of this group of approvals
                        self.request.session['total_records'] = len(incomplete_approval_records) + len(completed_approval_records[index:])
                        self.total = len(incomplete_approval_records) + len(completed_approval_records[index:])
                        break

                    # The earliest incomplete record was assigned after all the others were completed. Start the count from the beginning.
                    self.request.session['total_records'] = len(incomplete_approval_records)
                    self.total = len(incomplete_approval_records)
            else:
                self.request.session['total_records'] = len(incomplete_approval_records)
                self.total = len(incomplete_approval_records)

            self.request.session['records_remaining'] = len(incomplete_approval_records)
            self.progress = self.total - len(incomplete_approval_records)

        else:
            try:
                b = models.TeachingBlockYear.objects.get(block__code=code, year=year)
            except models.TeachingBlockYear.DoesNotExist:
                messages.error(self.request, "That teaching block does not exist.")
                return reverse('admin')
            tb = models.TeachingBlockYear.objects.filter(start__lte=datetime.datetime.now().date).latest("start")

            records = models.ApprovalRecord.objects.filter(question__teaching_activity_year__block_year=b) \
                        .annotate(max=db.models.Max('question__approval_records__date_completed')) \
                        .filter(max=db.models.F('date_completed'))
            q = models.Question.objects.filter(teaching_activity_year__block_year=b)
            if 'flagged' in self.request.GET:
                records = records.filter(status=models.ApprovalRecord.FLAGGED_STATUS)
            else:
                records = records.filter(status=models.ApprovalRecord.PENDING_STATUS)

            q = q.filter(db.models.Q(approval_records__in=records) | db.models.Q(pk=q_id))

            if 'flagged' not in self.request.GET:
                q |= models.Question.objects.filter(db.models.Q(approval_records__isnull=True) | db.models.Q(approval_records__date_completed__isnull=True)) \
                                            .filter(teaching_activity_year__block_year=b)

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
class QuestionGuide(TemplateView):
    template_name = "question/guide.html"


@class_view_decorator(login_required)
class NewQuestion(CreateView):
    model = models.Question
    form_class = forms.NewQuestionForm
    template_name = "new.html"

    def dispatch(self, request, *args, **kwargs):
        self.ta = check_ta_perm_for_question(self.kwargs['ta_id'], self.request.user)
        if not self.ta.current_block().can_write_questions and not self.request.user.is_superuser:
            messages.warning(request, "You are not currently able to write questions for this teaching activity.")
            return redirect('ta', pk=self.ta.id)
        return super(NewQuestion, self).dispatch(request, *args, **kwargs)

    def get_initial(self):
        i = super(NewQuestion, self).get_initial().copy()
        i.update({'teaching_activity_year': self.ta, 'creator': self.request.user.student})
        return i

    def form_valid(self, form):
        messages.success(self.request, "Thanks, your question has been submitted! You'll get an email when it's approved.")
        return super(NewQuestion, self).form_valid(form)

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
                r.reason_type = models.Reason.TYPE_EDIT
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

        if ta.questions.filter(creator=self.request.user.student).count():
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


@class_view_decorator(permission_required('questions.can_approve'))
class AssignApproval(RedirectView):
    permanent = False
    def get_redirect_url(self, ta_id):
        try:
            activity = models.TeachingActivityYear.objects.get(id=ta_id)
        except:
            messages.error(self.request, 'That teaching activity does not exist.')
            return reverse('approve-home')

        if activity.has_assigned_approver():
            messages.error(self.request, 'The teaching activity %s already has an assigned approver.' % activity)
        else:
            for question in activity.questions.all():
                try:
                    # Make them the approver on the latest record if it is incomplete.
                    latest_record = question.latest_approval_record()
                except models.ApprovalRecord.DoesNotExist:
                    # No records at all, make one.
                    latest_record = models.ApprovalRecord()

                if latest_record.date_completed:
                    if latest_record.status == models.ApprovalRecord.PENDING_STATUS:
                        # Latest record was to make the question pending. So we need a new record.
                        latest_record = models.ApprovalRecord()
                    else:
                        # Question is not pending, so it doesn't need a new record.
                        continue

                record = models.ApprovalRecord()
                record.question = question
                record.approver = self.request.user.student
                record.save()

            messages.success(self.request, 'You have been assigned to approve the activity %s with record %s' % (activity, record.id))
        return "%s?approve" % reverse('activity-list', kwargs={'code':activity.block_year.block.code, 'year': activity.block_year.year,})


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
        return models.TeachingBlockYear.objects.get(year=self.kwargs["year"], block__code=self.kwargs["code"])

    def get_success_url(self):
        return reverse('admin')


@class_view_decorator(login_required)
class ViewActivity(DetailView):
    model = models.TeachingActivityYear

    def get_context_data(self, **kwargs):
        c = super(ViewActivity, self).get_context_data(**kwargs)
        c['can_view_questions'] = bool(self.object.block_year.question_count_for_student(self.request.user.student)) or self.request.user.has_perm("questions.can_approve")
        c['has_written_questions'] = bool(self.object.questions.filter(creator=self.request.user.student))
        return c


@class_view_decorator(login_required)
class ViewQuestion(DetailView):
    model = models.Question

    def dispatch(self, request, *args, **kwargs):
        r = super(ViewQuestion, self).dispatch(request, *args, **kwargs)

        if self.object.pending and not self.object.user_is_creator(self.request.user):
            raise Http404
        if self.object.deleted and not self.request.user.is_superuser:
            raise Http404

        return r

    def get_context_data(self, **kwargs):
        c = super(ViewQuestion, self).get_context_data(**kwargs)
        c['show'] = 'show' in self.request.GET
        c['approval_mode'] = 'approve' in self.request.GET
        c['flagged_mode'] = 'flagged' in self.request.GET
        c['assigned'] = 'assigned' in self.request.GET
        if 'total' in self.request.GET:
            c['total_assigned_approvals'] = int(self.request.GET.get('total', 0))
            c['records_completed'] = int(self.request.GET.get('progress', 0))
            c['records_remaining'] = c['total_assigned_approvals'] - c['records_completed']
        return c


@class_view_decorator(login_required)
class ViewQuestionApprovalHistory(DetailView):
    model = models.Question
    template_name = "question/history.html"

    def dispatch(self, request, *args, **kwargs):
        r = super(ViewQuestionApprovalHistory, self).dispatch(request, *args, **kwargs)

        if self.object.deleted and not self.request.user.is_superuser:
            raise Http404

        return r


def get_allowed_blocks(user):
    allowed_blocks = models.TeachingBlockYear.objects.filter(release_date__year=datetime.datetime.now().year) \
                                                    .order_by('block__stage__number', 'block__code')
    if user.is_superuser:
        return allowed_blocks

    if user.has_perm("questions.can_approve"):
        allowed_blocks = allowed_blocks.filter(block__stage__number__lt=user.student.get_current_stage().number)
    else:
        allowed_blocks = allowed_blocks.filter(activities__questions__in=user.student.questions_created.all())

    return allowed_blocks

@class_view_decorator(login_required)
# @class_view_decorator(ensure_csrf_cookie)
class QuizChooseView(ListView):
    template_name = "quiz/choose.html"
    model = models.QuizSpecification

    def get_queryset(self):
        return super(QuizChooseView, self).get_queryset().exclude(stage__number__gt=self.request.user.student.get_current_stage().number).exclude(questions__isnull=True)

    def get_context_data(self, **kwargs):
        c = super(QuizChooseView, self).get_context_data(**kwargs)

        allowed_blocks = get_allowed_blocks(self.request.user)
        if allowed_blocks.exists():
            c['form'] = forms.CustomQuizSpecificationForm(blocks=allowed_blocks)

        c['type_form'] = forms.PresetQuizSpecificationForm()
        return c


@class_view_decorator(login_required)
class QuizStartView(ListView):
    template_name = "quiz_start.html"
    model = models.TeachingBlockYear

    def get_queryset(self):
        start_of_year = datetime.date(year=datetime.datetime.now().year, month=1, day=1)
        q = super(QuizStartView, self).get_queryset()
        s = [stage.number for stage in self.request.user.student.get_all_stages()]
        return q.filter(block__stage__number__in=s).exclude(release_date__isnull=True).exclude(release_date__lte=start_of_year).order_by("block__stage__number", "block__code")


@class_view_decorator(login_required)
class QuizView(ListView):
    template_name = "quiz.html"
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
                records = models.ApprovalRecord.objects.filter(question__teaching_activity_year__block_year=bk) \
                            .annotate(max=db.models.Max('question__approval_records__date_completed')) \
                            .filter(max=db.models.F('date_completed')) \
                            .select_related('question') \
                            .filter(status=models.ApprovalRecord.APPROVED_STATUS)
                # q += models.Question.objects.filter(teaching_activity_year__block_year=bk, status=models.ApprovalRecord.APPROVED_STATUS)
                q += [record.question for record in records]
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
        print "Getting redirect url"
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
        self.request.session['mode'] = mode = form.cleaned_data['quiz_type']
        if preset_quiz:
            self.request.session['quizspecification'] = quiz_specification = form.cleaned_data['quiz_specification']
        else:
            for block in allowed_blocks:
                q = []
                number_needed = form.cleaned_data[block.name_for_form_fields()]
                if not number_needed: continue
                records = models.ApprovalRecord.objects.filter(question__teaching_activity_year__block_year=block) \
                                .annotate(max=db.models.Max('question__approval_records__date_completed')) \
                                .filter(max=db.models.F('date_completed')) \
                                .select_related('question') \
                                .filter(status=models.ApprovalRecord.APPROVED_STATUS)
                q += [record.question for record in records]
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
        print "Returning %s" % json.dumps(question)
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
        open("saved.attempt", "w").close()

        return HttpResponse(json.dumps({'status': 'attempt', 'attempt': attempt.slug, 'report_url': reverse('quiz-attempt-report', kwargs={'slug': attempt.slug}) }), mimetype='application/json')


@class_view_decorator(login_required)
class QuizQuestionSubmit(View):
    def post(self, request, *args, **kwargs):
        POST = request.POST
        # if settings.DEBUG: print "Got post %s" % POST
        attempt = models.QuizAttempt.objects.get(slug=POST["quiz_attempt"])
        question = models.Question.objects.get(id=POST["id"])
        try:
            question_attempt = models.QuizAttempt.objects.get(question=question)
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
        modes_to_templates = {'individual': 'quiz_individual.html', 'block': 'quiz.html', 'classic': 'quiz_individual.html'}

        return modes_to_templates.get(self.mode, 'quiz.html')

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
        if specification:
            try:
                specification = models.QuizSpecification.objects.get(id=specification)
            except models.QuizSpecification.DoesNotExist:
                specification = None
        if 'attempt' in p:
            try:
                attempt = models.QuizAttempt.objects.get(slug=p.get('attempt'))
            except models.QuizAttempt.DoesNotExist:
                attempt = None

        if not attempt and not specification:
            messages.error(self.request, "An unexpected error has occurred. Please try again.")
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
    template_name = "quiz.html"

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
    template_name = "quiz_individual.html"

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


class UpdateQuizSpecificationView(UpdateView):
    model = models.QuizSpecification
    form_class = forms.NewQuizSpecificationForm
    template_name = "admin/new.html"
    success_url = reverse_lazy('admin')

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
        return redirect('view', pk=question.pk, ta_id=question.teaching_activity_year.id)

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
class ChangeStatus(QueryStringMixin, RedirectView):
    permanent = False

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

        if action == "flag":
            return "%s%s" % (reverse('question-flag', kwargs={'ta_id': q.teaching_activity_year.id, 'q_id': q_id}), self.query_string())

        is_new = False
        if not getattr(q, actions_to_props[action]):
            try:
                # Look for existing approval record as someone may have been assigned.
                record = q.latest_approval_record()
            except models.ApprovalRecord.DoesNotExist:
                # No approval records, so question was not assigned to anyone.
                record = models.ApprovalRecord()
                is_new = True

            if record.date_completed:
                # Question was assigned and completed, so we don't want to overwrite the old record.
                record = models.ApprovalRecord()
                is_new = True

            update_date_assigned = not is_new and record.approver != self.request.user.student
            record.status = getattr(models.ApprovalRecord, '%s_STATUS' % actions_to_props[action].upper())
            record.approver = self.request.user.student
            record.question = q
            record.save()

            # Makes sure that date_completed is not earlier than date_assigned which is automatically saved with a new record.
            if update_date_assigned:
                record.date_assigned = datetime.datetime.now()
            record.date_completed = record.date_assigned if is_new or update_date_assigned else datetime.datetime.now()
            record.save()

        r = "%s%%s"
        if 'approve' in self.request.GET:
            r = r % reverse('admin-approve', kwargs={'code': q.teaching_activity_year.block_year.code, 'year': q.teaching_activity_year.block_year.year, 'q_id': q.id})
        else:
            r = r % reverse('view', kwargs={'pk': q_id, 'ta_id': q.teaching_activity_year.id})
        r = r % self.query_string()

        return r


@class_view_decorator(permission_required('questions.can_approve'))
class FlagQuestion(FormView, QueryStringMixin):
    form_class = forms.ReasonForFlaggingForm
    template_name = "approval/flag.html"

    def dispatch(self, request, *args, **kwargs):
        try:
            self.question = models.Question.objects.get(id=self.kwargs['q_id'])
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
        try:
            # If there is an incomplete record, it should be edited with the current info.
            record = q.latest_approval_record()
        except models.ApprovalRecord.DoesNotExist:
            # There are no records at all.
            record = models.ApprovalRecord()

        if record.date_completed:
            # The last record is complete. So we need a new one.
            record = models.ApprovalRecord()

        record.status = models.ApprovalRecord.FLAGGED_STATUS
        record.question = q
        record.approver = self.request.user.student
        record.reason = form.cleaned_data['reason']
        record.save()

        # Ensures that date_completed is later than date_assigned, which is automatically added when saved the first time.
        record.date_completed = datetime.datetime.now()
        record.save()

        r = "%s%%s"
        if 'approve' in self.request.GET:
            r = r % reverse('admin-approve', kwargs={'code': q.teaching_activity_year.block_year.code, 'year': q.teaching_activity_year.block_year.year, 'q_id': q.id})
        else:
            r = r % reverse('view', kwargs={'pk': q.id, 'ta_id': q.teaching_activity_year.id})
        r = r % self.query_string()

        return redirect(r)


@class_view_decorator(permission_required('questions.can_approve'))
class QuestionAttributes(QueryStringMixin, FormView):
    form_class = forms.QuestionAttributesForm
    template_name = "question/attributes.html"

    def dispatch(self, request, *args, **kwargs):
        try:
            self.question = models.Question.objects.get(id=self.kwargs['q_id'])
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
        return "%s%s" % (reverse('view', kwargs={'pk': self.question.id, 'ta_id': self.question.teaching_activity_year.id}), self.query_string())



@class_view_decorator(permission_required('questions.can_approve'))
class ReleaseBlockView(RedirectView):
    permanent = False
    def get_redirect_url(self, code, year):
        try:
            block =  models.TeachingBlockYear.objects.get(year=year, block__code=code)
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
def download(request, code, year, mode):
    try:
        tb = models.TeachingBlockYear.objects.get(year=year, block__code=code)
    except models.TeachingBlockYear.DoesNotExist:
        messages.error(request, 'That block does not exist.')
        return redirect('admin')

    if not tb.released and not request.user.has_perm("questions.can_approve"):
        raise PermissionDenied

    if not tb.question_count_for_student(request.user.student) and not request.user.has_perm("questions.can_approve") and not (tb.stage != request.user.student.get_current_stage() and tb.stage in request.user.student.get_all_stages()):
        messages.error(request, "Unfortunately you haven't written any questions for this block, so you are unable to download the other questions.")
        return redirect('dashboard')

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
            self.tb = models.TeachingBlockYear.objects.get(block__code=self.kwargs['code'], year=self.kwargs['year'])
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
                self.request.build_absolute_uri(reverse('questions.views.download', kwargs={'year': self.tb.year, 'code': self.tb.code, 'mode': 'question'})),
                self.request.build_absolute_uri(reverse('questions.views.download', kwargs={'year': self.tb.year, 'code': self.tb.code, 'mode': 'answer'})),
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
    b.code = block.code
    b.start = block.start
    b.end = block.end

    return b


class UploadView(FormView):
    form_class = forms.TeachingActivityBulkUploadForm

    def dispatch(self, request, *args, **kwargs):
        if not models.TeachingBlock.objects.count():
            messages.error(request, "You can't upload teaching activities without first having created a teaching block.")
            return redirect('admin')

        return super(UploadView, self).dispatch(request, *args, **kwargs)

    def process_form(self, form):
        y = form.cleaned_data['year']
        r = list(csv.reader(form.cleaned_data['ta_file'].read().splitlines()))
        h = [hh.lower().replace(" ", "_") for hh in r[0]]
        by_position = {}
        by_name = {}
        by_block = {}
        already_exist = []
        blocks = list(set(dict(zip(h, row))['block'] for row in r[1:]))
        errors = []
        existing_blocks = models.TeachingBlock.objects.filter(code__in=blocks)
        existing_block_years_by_block = {} # Years by block.
        for b in existing_blocks:
            by_year = existing_block_years_by_block.setdefault(b.code, {})
            for by in b.years.all():
                by_year[by.year] = by

        for block_number in blocks:
            if not block_number: continue
            block_number = block_number
            if block_number in existing_block_years_by_block:
                if y in existing_block_years_by_block[block_number]:
                    block_year = existing_block_years_by_block[block_number][y]
                else:
                    errors.append("Block %s does not yet exist in %s" % (block_number, y))
                    continue
                by_block[existing_block_years_by_block[block_number][y]] = []
            else:
                errors.append("Block %s was not found" % block_number)
        if errors:
            self.request.session['block_errors'] = errors
            return
        
        for row in r[1:]:
            hr = dict(zip(h, row))
            try:
                hr['activity_type'] = self.get_accepted_types()[hr['teaching_activity_type']]
                # hr['block'] = existing_block_years_by_block[int(hr["block"])][y]
            except KeyError:
                errors.append(hr)
                continue

            activity_form = forms.TeachingActivityValidationForm(hr)
            if activity_form.is_valid():
                activity = activity_form.save(commit=False)
                activity_year_form = forms.TeachingActivityYearValidationForm(hr)
                if activity_year_form.is_valid():
                    activity_year = activity_year_form.save(commit=False)
                    activity_year.teaching_activity = activity
                    l = by_position.setdefault((activity_year.week, activity_year.position, activity.activity_type), [])
                    l.append(activity_year)
                    l = by_name.setdefault(activity.name.lower(), [])
                    l.append(activity_year)
                    by_block[existing_block_years_by_block[hr['block']][y]].append(activity_year)
                else:
                    errors.append(hr)
            else:
                if str(f.errors).find("exists"):
                    already_exist.append(hr)
                else:
                    errors.append(hr)
        if errors or already_exist:
            self.request.session['errors'] = errors
            self.request.session['already_exist'] = already_exist
            return
        else:
            dup_by_position = [v for k, v in by_position.iteritems() if len(v) > 1]
            dup_by_name = [v for k, v in by_name.iteritems() if len(v) > 1]
            if dup_by_position or dup_by_name:
                self.request.session["dup_by_position"] = [v for k, v in by_position.iteritems() if len(v) > 1]
                self.request.session["dup_by_name"] = [v for k, v in by_name.iteritems() if len(v) > 1]
                return
            else:
                for bb in by_block:
                    by_block[bb].sort(key=lambda ta: (ta.week, ta.position))
                self.request.session["by_block"] = by_block
                self.request.session["blocks"] = existing_block_years_by_block.keys()
                self.request.session["year"] = y
                self.request.session["accepted_types"] = self.get_accepted_types().keys()
                return

    def form_valid(self, form):
        self.process_form(form)
        return super(UploadView, self).form_valid(form)

    def get_success_url(self):
        error_attributes = ['block_errors', 'errors', 'already_exist', 'dup_by_position', 'dup_by_name']
        if any(att in self.request.session for att in error_attributes):
            return reverse('activity-upload-error')
        return reverse('activity-upload-confirm')

    def get_template_names(self):
        return "admin/upload.html"

    def get_accepted_types(self):
        if not hasattr(self, "accepted_types"):
            self.accepted_types = collections.defaultdict(None)
            for k, v in models.TeachingActivity.TYPE_CHOICES:
                self.accepted_types[v] = k

        return self.accepted_types
            

    def get_context_data(self, **kwargs):
        c = super(UploadView, self).get_context_data(**kwargs)
        c['accepted_types'] = self.get_accepted_types().keys()
        return c


class UploadConfirmationView(TemplateView):
    template_name = "admin/confirm_upload.html"

    def set_extra_context(self, session):
        self.extra_context = {}
        self.extra_context['tab'] = session.pop("by_block")
        self.extra_context['blocks'] = session.pop("blocks")
        self.extra_context['year'] = session.pop("year")
        self.extra_context['accepted_types'] = session.pop("accepted_types")

    def dispatch(self, request, *args, **kwargs):
        try:
            self.set_extra_context(request.session)
        except:
            return redirect('activity-upload')
        return super(UploadConfirmationView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        c = super(UploadConfirmationView, self).get_context_data(**kwargs)
        c.update(self.extra_context)
        return c


class UploadSubmissionView(View):
    def post(self, request, *args, **kwargs):
        y = request.POST.get('year')
        i = request.POST.getlist('reference_id')
        r = request.POST.copy()
        # blocks = dict((b.number, b) for b in models.TeachingBlock.objects.filter(year=y))
        block_years = dict((b.code, b) for b in models.TeachingBlockYear.objects.filter(year=y))
        for ii in i:
            data = {
                'reference_id': ii,
                'name': request.POST.get('name_%s' % ii),
                'block_year': block_years[request.POST.get('block_%s' % ii)].id,
                'week': request.POST.get('week_%s' % ii),
                'position': request.POST.get('position_%s' % ii),
                'activity_type': request.POST.get('activity_type_%s' % ii),
            }
            activity_form = forms.NewTeachingActivityForm(data)
            if activity_form.is_valid():
                activity = activity_form.save(commit=False)
                activity_year_form = forms.NewTeachingActivityYearForm(data)
                if activity_year_form.is_valid():
                    activity_year = activity_year_form.save(commit=False)
                    activity.save()
                    activity_year.teaching_activity = activity
                    activity_year.save()
            else:
                return redirect('activity-upload')
        return redirect('admin')


class UploadErrorView(TemplateView):
    template_name = "admin/upload_error.html"

    def get_context_data(self, **kwargs):
        c = super(UploadErrorView, self).get_context_data(**kwargs)
        c["block_errors"] = self.request.session.pop("block_errors", None)
        c["errors"] = self.request.session.pop("errors", None)
        c["already_exist"] = self.request.session.pop("already_exist", None)
        c["dup_by_position"] = self.request.session.pop("dup_by_position", None)
        c["dup_by_name"] = self.request.session.pop("dup_by_name", None)
        c["duplicates"] = bool(c["dup_by_position"] or c["dup_by_name"])

        return c


@login_required
def new_ta_upload(request):
    accepted_types = collections.defaultdict(None)
    if not models.TeachingBlock.objects.count():
        messages.error(request, "You can't upload teaching activities without first having created a teaching block.")
        return redirect('admin')
    for k, v in models.TeachingActivity.TYPE_CHOICES:
        print "%s\t%s" % (k,v)
        accepted_types[v] = k
    if request.method == "POST":
        if 'id' in request.POST:
            y = request.POST.get('year')
            i = request.POST.getlist('id')
            r = request.POST.copy()
            blocks = dict((b.code, b) for b in models.TeachingBlock.objects.filter(year=y))
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
                    blocks[bb.code] = bb
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
                existing_blocks = models.TeachingBlock.objects.filter(code_in=blocks)
                b = {}
                for bb in existing_blocks:
                    d = b.setdefault(bb.code, {})
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
                            b[bb.code][y] = bb
                            new_blocks.append(bb)
                        by_block[bb] = []
                    else:
                        errors.append("Block %s was not found" % bb)
                if errors:
                    return render_to_response("admin/upload.html", {
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
                        "admin/upload.html",
                        {'errors': errors, 'already_exist': already_exist},
                        context_instance=RequestContext(request)
                    )
                else:
                    dup_by_position = [v for k, v in by_position.iteritems() if len(v) > 1]
                    dup_by_name = [v for k, v in by_name.iteritems() if len(v) > 1]
                    if dup_by_position or dup_by_name:
                        return render_to_response(
                            "admin/upload.html",
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
                            "admin/upload.html",
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
        "admin/upload.html",
        {
            'form': form,
            'accepted_types': accepted_types.keys(),
        },
        context_instance=RequestContext(request)
    )
