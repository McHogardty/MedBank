from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required, permission_required
from django.views.generic import FormView, TemplateView, ListView
from django.contrib import messages
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.conf import settings
from django.core.mail import EmailMessage, send_mass_mail, get_connection, EmailMultiAlternatives

from .base import class_view_decorator, user_is_superuser

from questions import models, forms

import datetime

@class_view_decorator(login_required)
class DashboardView(TemplateView):
    template_name = "general/dashboard.html"

    def get_context_data(self, **kwargs):
        c = super(DashboardView, self).get_context_data(**kwargs)
        c.update({'example_quiz_slug': settings.EXAMPLE_QUIZ_SLUG})
        block_count = models.TeachingBlockYear.objects.get_open_blocks_for_year_and_date_and_student(datetime.datetime.now().year, datetime.datetime.now(), self.request.user.student).count()
        c.update({'block_count': block_count})

        released_blocks = models.TeachingBlockYear.objects.get_released_blocks_for_year_and_date_and_student(
                                datetime.datetime.now().year,
                                datetime.datetime.now(),
                                self.request.user.student
        )
        c.update({"released_block_count": released_blocks.count()})
        message_settings = list(models.StudentDashboardSetting.objects.filter(name__in=models.StudentDashboardSetting.ALL_SETTINGS))
        message_settings = dict((setting.name, setting) for setting in message_settings)

        c['current_assigned_activities'] = list(models.TeachingActivityYear.objects.get_unreleased_activities_assigned_to(self.request.user.student))
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
        c['released_block_view_url'] = models.TeachingBlockYear.get_released_block_display_url()
        c['open_block_view_url'] = models.TeachingBlockYear.get_open_block_display_url()

        return c


@class_view_decorator(user_is_superuser)
class DashboardAdminView(ListView):
    template_name = "general/dashboard_admin.html"
    model = models.StudentDashboardSetting

    def get_context_data(self, **kwargs):
        c = super(DashboardAdminView, self).get_context_data(**kwargs)
        c['dashboard_settings'] = self.object_list
        return c


@class_view_decorator(user_is_superuser)
class EmailView(FormView):
    template_name = "admin/email.html"
    form_class = forms.EmailForm

    def dispatch(self, request, *args, **kwargs):
        try:
            self.tb = models.TeachingBlockYear.objects.get_from_kwargs(**self.kwargs)
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
            i.update({'email' : '<p><a href="%s">Click here</a> to view the block on MedBank.</p>' % (
                self.request.build_absolute_uri(self.tb.get_activity_display_url()),
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

        subject = "[MedBank] %s" % c['subject']
        body = '<html><body style="font-family:%s,Helvetica,Arial,sans-serif;font-size:14px;">%s</body></html>' % ("'Helvetica Neue'", c['email'])
        from_email = "SUMS MedBank <medbank@sydneymedsoc.org.au>"
        c = get_connection(fail_silently=False)

        email_messages = tuple(EmailMessage(subject, body, from_email, [r, ]) for r in recipients)
        for m in email_messages:
            m.content_subtype = 'html'
        c.send_messages(email_messages)

        messages.success(self.request, "Your email has been successfully queued to be sent.")
        return redirect('admin')

