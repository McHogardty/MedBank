from django.conf.urls import patterns, include, url

from .forms import TeachingActivityBulkUploadForm, TeachingActivityBulkUploadWizard, NewTeachingBlockForm

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('questions.views',
    url(r'^$', 'home'),
    url(r'^admin/$', 'admin'),
    url(r'^download/$', 'download'),
    url(r'^ta/new/$', 'new_ta'),
    url(r'^ta/(?P<ta_id>\d+)/$', 'view_ta'),
    url(r'^ta/(?P<ta_id>\d+)/question/new/$', 'new'),
    url(r'^ta/(?P<ta_id>\d+)/question/(?P<q_id>\d+)/edit/$', 'new'),
    url(r'^ta/(?P<ta_id>\d+)/question/(?P<q_id>\d+)/$', 'view'),
    url(r'^ta/(?P<ta_id>\d+)/question/(?P<q_id>\d+)/approve/$', 'approve'),
    url(r'^ta/(?P<ta_id>\d+)/question/(?P<q_id>\d+)/pending/$', 'make_pending'),
    url(r'^ta/upload/$', 'new_ta_upload'),
    url(r'^ta/(?P<ta_id>\d+)/signup/$', 'signup'),
)
