from django.conf.urls import patterns, include, url

from .views import (AllBlocksView, AllActivitiesView, ViewActivity,
    NewActivity, ViewQuestion, NewQuestion, UpdateQuestion, NewBlock,
    MyActivitiesView, UnassignView, ApproveQuestionsView, StartApprovalView,
    EmailView, ChangeStatus, AdminView, ReleaseBlockView, EditBlock, AddComment,
    QuizView, Quiz, QuizStartView, QuizQuestionsView, QuizSubmit, QuizReport,
    DashboardView, BlockAdminView)

from django.views.generic import TemplateView

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

from queue import base

urlpatterns = patterns(
    'questions.views',
    url(r'^$', DashboardView.as_view(), name='dashboard'),
    url(r'^block/$', AllBlocksView.as_view(), name='block-list'),
    url(r'^block/(?P<number>\d{1,2})/(?P<year>\d{4})/$', AllActivitiesView.as_view(), name='activity-list'),
    url(r'^block/(?P<number>\d{1,2})/(?P<year>\d{4})/release/$', ReleaseBlockView.as_view(), name='release'),
    url(r'^block/(?P<number>\d{1,2})/(?P<year>\d{4})/admin/$', BlockAdminView.as_view(), name='block-admin'),
    url(r'^admin/$', AdminView.as_view(), name='admin'),
    url(r'^admin/email/(?P<number>\d{1,2})/(?P<year>\d{4})/$', EmailView.as_view(), name='email'),
    url(r'^admin/approve/$', AllBlocksView.as_view(template_name="approve.html"), name='admin-approve-choose'),
    url(r'^admin/approve/(?P<number>\d{1,2})/(?P<year>\d{4})/$', StartApprovalView.as_view(), name='admin-approve-start'),
    url(r'^admin/approve/(?P<number>\d{1,2})/(?P<year>\d{4})/(?P<q_id>\d+)/$', StartApprovalView.as_view(), name='admin-approve'),
    url(r'^download/(?P<number>\d{1,2})/(?P<year>\d{4})/(?P<mode>[a-z]+)/$', 'download'),
    #url(r'^send/(?P<pk>\d{1,2})/$', 'send'),
    url(r'^quiz/$', Quiz.as_view(), name='quiz'),
    url(r'^quiz/start/$', QuizStartView.as_view(), name='quiz-start'),
    url(r'^quiz/(?P<slug>[a-z]+)/start/$', QuizQuestionsView.as_view(), name='quiz-spec'),
    url(r'^quiz/prepare/$', QuizQuestionsView.as_view(), name='quiz-prepare'),
    url(r'^quiz/submit/$', QuizSubmit.as_view(), name='quiz-submit'),
    url(r'^quiz/report/$', QuizReport.as_view(), name='quiz-report'),
    url(r'^quiz/report/(?P<slug>[a-z]+)/$', QuizReport.as_view(), name='quiz-report'),
    url(r'^ta/$', MyActivitiesView.as_view(), name='activity-mine'),
    url(r'^ta/new/$', NewActivity.as_view(), name='activity-new'),
    url(r'^block/new/$', NewBlock.as_view(), name='block-new'),
    url(r'^block/(?P<number>\d{1,2})/(?P<year>\d{4})/edit/$', EditBlock.as_view(), name='block-edit'),
    url(r'^ta/(?P<pk>\d+)/$', ViewActivity.as_view(template_name="view_ta.html"), name='ta'),
    url(r'^ta/(?P<ta_id>\d+)/question/new/$', NewQuestion.as_view(), name='new'),
    url(r'^ta/(?P<ta_id>\d+)/question/(?P<pk>\d+)/edit/$', UpdateQuestion.as_view(), name='edit'),
    url(r'^ta/(?P<ta_id>\d+)/question/(?P<pk>\d+)/$', ViewQuestion.as_view(template_name="view.html"), name='view'),
    url(r'^ta/(?P<ta_id>\d+)/question/(?P<pk>\d+)/comment/new/$', AddComment.as_view(), name="comment-new"),
    url(r'^ta/(?P<ta_id>\d+)/question/(?P<pk>\d+)/comment/reply/(?P<comment_id>\d+)/$', AddComment.as_view(), name="comment-reply"),
    url(r'^ta/(?P<ta_id>\d+)/question/(?P<q_id>\d+)/(?P<action>[a-z]+)/$', ChangeStatus.as_view(), name="question-status"),
    url(r'^ta/upload/$', 'new_ta_upload', name='activity-upload'),
    url(r'^ta/(?P<ta_id>\d+)/signup/$', 'signup'),
    url(r'^ta/(?P<pk>\d+)/unassign/$', UnassignView.as_view(), name='activity-unassign'),
)
