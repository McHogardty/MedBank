from __future__ import unicode_literals

from django.views.generic import DetailView, TemplateView
from django.views.generic.base import RedirectView
from django.views.generic.edit import UpdateView, FormView
from django.core.urlresolvers import reverse
from django.conf import settings
from django.shortcuts import redirect

from .base import class_view_decorator, user_is_superuser, GetObjectMixin

from questions import models, forms

import json
import datetime

@class_view_decorator(user_is_superuser)
class AdminView(TemplateView):
    template_name = 'admin/admin.html'

    def get_context_data(self, **kwargs):
        c = super(AdminView, self).get_context_data(**kwargs)
        c.update({'blocks': models.TeachingBlock.objects.all(),})
        c.update({'debug_mode': settings.DEBUG, 'maintenance_mode': settings.MAINTENANCE_MODE, })
        c.update({'quiz_specifications': models.QuizSpecification.objects.order_by('stage')})
        c.update({'student_dashboard_settings': models.StudentDashboardSetting.objects.all()})
        c.update({'approval_dashboard_settings': models.ApprovalDashboardSetting.objects.all()})
        c['block_creation_url'] = models.TeachingBlock.get_block_creation_url()
        return c


from medbank.models import Setting
@class_view_decorator(user_is_superuser)
class SettingView(DetailView):
    template_name = "admin/setting.html"
    queryset = Setting.objects.filter(class_name__in=[models.StudentDashboardSetting.__name__, models.ApprovalDashboardSetting.__name__])

    def get_object(self, *args, **kwargs):
        object = super(SettingView, self).get_object(*args, **kwargs)
        object.__class__ = getattr(models, object.class_name)
        return object


@class_view_decorator(user_is_superuser)
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


@class_view_decorator(user_is_superuser)
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


@class_view_decorator(user_is_superuser)
class BlockAdminView(GetObjectMixin, DetailView):
    model = models.TeachingBlock
    template_name = "block/admin.html"

    def get_context_data(self, **kwargs):
        c = super(BlockAdminView, self).get_context_data(**kwargs)
        c['teaching_block'] = self.object
        c['new_year_required'] = not self.object.years.filter(year=datetime.datetime.now().year).exists()

        year = self.request.GET.get("year", None)
        current_year = None

        if year:
            try:
                current_year = self.object.years.get(year=year)
            except models.TeachingBlockYear.DoesNotExist:
                current_year = None

        if current_year is None:
            try:
                current_year = self.object.get_latest_year()
            except models.TeachingBlockYear.DoesNotExist:
                current_year = None

        c['current_year'] = current_year
        # c['number_questions_pending'] = self.object.questions_pending_count()
        # c['number_questions_approved'] = self.object.questions_approved_count()
        # c['number_questions_flagged'] = self.object.questions_flagged_count()
        return c


@class_view_decorator(user_is_superuser)
class ApprovalStatisticsView(GetObjectMixin, DetailView):
    model = models.TeachingBlockYear
    template_name = "admin/approval_statistics.html"

    def query_string(self):
        allowed = ['approve', 'flagged', 'assigned',]
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

@class_view_decorator(user_is_superuser)
class StudentLookup(FormView):
    form_class = forms.StudentLookupForm
    template_name = "admin/student_lookup.html"

    def get_form_kwargs(self, **kwargs):
        k = super(StudentLookup, self).get_form_kwargs(**kwargs)
        k['user_url'] = reverse("user-list")
        return k

    def form_valid(self, form):
        return redirect(form.cleaned_data['user'].student)


@class_view_decorator(user_is_superuser)
class ViewStudent(GetObjectMixin, DetailView):
    model = models.Student
    template_name = "admin/student_info.html"

    def get_context_data(self, **kwargs):
        c = super(ViewStudent, self).get_context_data(**kwargs)
        c['student'] = self.object

        questions_written = list(self.object.questions_created.all())
        c['number_questions_written'] = len(questions_written)

        blocks_with_questions = {}
        for question in questions_written:
            questions_for_block =  blocks_with_questions.setdefault(question.teaching_activity_year.block_week.writing_period.block_year, [])
            questions_for_block.append(question)
        c['blocks_with_questions'] = blocks_with_questions
        return c
