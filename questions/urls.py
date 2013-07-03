from django.conf.urls import patterns, include, url

from .forms import TeachingActivityBulkUploadWizard, NewTeachingBlockForm
from .views import AllActivitiesView, ViewActivity, NewActivity, ViewQuestion, NewQuestion, UpdateQuestion, NewBlock

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('questions.views',
    url(r'^$', AllActivitiesView.as_view(), name='home'),
    url(r'^admin/$', 'admin', name='admin'),
    url(r'^download/(?P<mode>[a-z]+)/$', 'download'),
    url(r'^send/$', 'send'),
    url(r'^ta/new/$', NewActivity.as_view(), name='activity-new'),
    url(r'^block/new/$', NewBlock.as_view(), name='block-new'),
    url(r'^ta/(?P<pk>\d+)/$', ViewActivity.as_view(template_name="view_ta.html"), name='ta'),
    url(r'^ta/(?P<ta_id>\d+)/question/new/$', NewQuestion.as_view(), name='new'),
    url(r'^ta/(?P<ta_id>\d+)/question/(?P<pk>\d+)/edit/$', UpdateQuestion.as_view(), name='edit'),
    url(r'^ta/(?P<ta_id>\d+)/question/(?P<pk>\d+)/$', ViewQuestion.as_view(template_name="view.html"), name='view'),
    url(r'^ta/(?P<ta_id>\d+)/question/(?P<q_id>\d+)/approve/$', 'approve'),
    url(r'^ta/(?P<ta_id>\d+)/question/(?P<q_id>\d+)/pending/$', 'make_pending'),
    url(r'^ta/upload/$', 'new_ta_upload', name='activity-upload'),
    url(r'^ta/(?P<ta_id>\d+)/signup/$', 'signup'),
)
