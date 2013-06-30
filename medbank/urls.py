from django.conf.urls import patterns, include, url

from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^$', 'medbank.views.home'),
    url(r'^%s$' % settings.LOGIN_URL.lstrip("/"), 'django.contrib.auth.views.login', name="login"),
    url(r'^logout/$', 'medbank.views.logout_view', name="logout"),
    url(r'^newuser/$', 'medbank.views.create_user', name="create_user"),
    url(r'^questions/', include('questions.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

handler500 = 'medbank.views.server_error'
