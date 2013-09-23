from django.conf.urls import patterns, include, url

from .views import (AllBlocksView, AllActivitiesView, ViewActivity,
    NewActivity, ViewQuestion, NewQuestion, UpdateQuestion, NewBlock,
    MyActivitiesView, UnassignView, ApproveQuestionsView, StartApprovalView,
    EmailView, ChangeStatus)

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

from queue import base

urlpatterns = patterns(
    'questions.views',
    url(r'^block/$', AllBlocksView.as_view(), name='block-list'),
    url(r'^test/$', 'test'),
    url(r'^block/(?P<number>\d{1,2})/(?P<year>\d{4})/$', AllActivitiesView.as_view(), name='activity-list'),
    url(r'^admin/$', 'admin', name='admin'),
    url(r'^admin/email/(?P<pk>\d{1,2})/(?P<year>\d{4})/$', EmailView.as_view(), name='email'),
    url(r'^admin/approve/$', AllBlocksView.as_view(template_name="approve.html"), name='admin-approve-choose'),
    url(r'^admin/approve/(?P<pk>\d{1,2})/$', StartApprovalView.as_view(), name='admin-approve-start'),
    url(r'^admin/approve/(?P<pk>\d{1,2})/(?P<q_id>\d+)/$', StartApprovalView.as_view(), name='admin-approve'),
    url(r'^download/(?P<pk>\d{1,2})/(?P<mode>[a-z]+)/$', 'download'),
    url(r'^send/(?P<pk>\d{1,2})/$', 'send'),
    url(r'^ta/$', MyActivitiesView.as_view(), name='activity-mine'),
    url(r'^ta/new/$', NewActivity.as_view(), name='activity-new'),
    url(r'^block/new/$', NewBlock.as_view(), name='block-new'),
    url(r'^ta/(?P<pk>\d+)/$', ViewActivity.as_view(template_name="view_ta.html"), name='ta'),
    url(r'^ta/(?P<ta_id>\d+)/question/new/$', NewQuestion.as_view(), name='new'),
    url(r'^ta/(?P<ta_id>\d+)/question/(?P<pk>\d+)/edit/$', UpdateQuestion.as_view(), name='edit'),
    url(r'^ta/(?P<ta_id>\d+)/question/(?P<pk>\d+)/$', ViewQuestion.as_view(template_name="view.html"), name='view'),
    url(r'^ta/(?P<ta_id>\d+)/question/(?P<q_id>\d+)/(?P<action>[a-z]+)/$', ChangeStatus.as_view(), name="question-status"),
    url(r'^ta/upload/$', 'new_ta_upload', name='activity-upload'),
    url(r'^ta/(?P<ta_id>\d+)/signup/$', 'signup'),
    url(r'^ta/(?P<pk>\d+)/unassign/$', UnassignView.as_view(), name='activity-unassign'),
    url(r'^testemail/$', 'email_test'),
)
