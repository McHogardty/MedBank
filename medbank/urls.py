from django.conf.urls import patterns, include, url

from django.conf import settings
import forms

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

from medbank.views import ResetPasswordRequest, ResetPassword, FeedbackView
from django.views.generic import TemplateView

urlpatterns = patterns(
    '',
    url(r'^$', 'medbank.views.home'),
    url(r'^(?P<name>[0-9]+)/$', 'medbank.views.test'),
    url(r'^%s$' % settings.LOCAL_LOGIN_URL.lstrip("/"), 'django.contrib.auth.views.login', {'authentication_form': forms.BootstrapAuthenticationForm}, name="login"),
    url(r'^logout/$', 'medbank.views.logout_view', name="logout"),
    url(r'^user/new/$', 'medbank.views.create_user', name="create_user"),
    url(r'^password/reset/sent/$', TemplateView.as_view(template_name="password/reset_email_success.html"), name="reset_password_sent"),
    url(r'^password/reset/success/$', TemplateView.as_view(template_name="password/reset_success.html"), name="reset_password_success"),
    url(r'^password/reset/(?P<token>[\w:-]+)/$', ResetPassword.as_view(), name="reset_password"),
    url(r'^password/reset/$', ResetPasswordRequest.as_view(), name="reset_password_request"),
    url(r'^stage/change/$', settings.STAGE_SELECTION_VIEW, name="pick_stage"),
    url(r'^feedback/$', FeedbackView.as_view(), name="feedback"),
    url(r'^questions/', include('questions.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

handler500 = 'medbank.views.server_error'