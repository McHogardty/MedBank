from django.conf.urls import patterns, include, url

from .views import block, activity, question, admin, approval, general, quiz

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

# from queue import base

specific_block_urls = patterns("",
    url(r'^edit/$', block.EditBlock.as_view(), name='block-edit'),
    url(r'^activity/all/$', block.BlockActivitiesView.as_view(), name='block-activities'),
    url(r'^release/$', block.ReleaseBlockView.as_view(), name='block-release'),
    url(r'^download/(?P<mode>(question|answer))/$', block.DownloadView.as_view(), name="block-download"),
    url(r'^admin/$', admin.BlockAdminView.as_view(), name='block-admin'),
    url(r'^admin/approval/statistics/$', admin.ApprovalStatisticsView.as_view(), name='block-approval-statistics'),
    url(r'^admin/upload/confirm/$', block.ConfirmUploadForTeachingBlock.as_view(), name='block-activity-upload-confirm'),
    url(r'^admin/upload/submit/$', block.UploadForTeachingBlock.as_view(), name='block-activity-upload-submit'),
    url(r'^admin/upload/start/$', block.StartUploadForTeachingBlock.as_view(), name='block-activity-upload'),
)

block_urls = patterns("",
    url(r'^$', block.AllBlocksView.as_view(), name='block-list'),
    url(r'^open/$', block.OpenBlocksView.as_view(), name='block-open-list'),
    url(r'^released/$', block.ReleasedBlocksView.as_view(), name="block-released-list"),
    url(r'^new/$', block.NewBlock.as_view(), name='block-new'),
    url(r'^(?P<code>[a-z\d]{1,10})/(?P<year>\d{4})/', include(specific_block_urls)),
)

admin_urls = patterns("",
    url(r'^$', admin.AdminView.as_view(), name='admin'),
    url(r'^email/(?P<code>[a-z\d]{1,10})/(?P<year>\d{4})/$', general.EmailView.as_view(), name='email'),
    url(r'^settings/create/$', admin.CreateMissingSettingsView.as_view(), name='admin-settings-create'),
    url(r'^settings/(?P<pk>\d+)/view/$', admin.SettingView.as_view(), name='admin-settings-view'),
    url(r'^settings/(?P<pk>\d+)/edit/$', admin.EditSettingView.as_view(), name='admin-settings-edit'),
)

comment_urls = patterns("",
    url(r'^new/$', question.AddComment.as_view(), name="comment-new"),
    url(r'^reply/(?P<comment_id>\d+)/$', question.AddComment.as_view(), name="comment-reply"),
)

specific_question_urls = patterns("",
    url(r'^$', question.ViewQuestion.as_view(), name='question-view'),
    url(r'^edit/$', question.UpdateQuestion.as_view(), name='question-edit'),
    url(r'^specification/add/$', quiz.QuizSpecificationAdd.as_view(), name='quiz-spec-add'),
    url(r'^status/flag/$', approval.FlagQuestion.as_view(), name='question-flag'),
    url(r'^attributes/$', question.QuestionAttributes.as_view(), name='question-attributes'),
    url(r'^history/$', approval.ViewQuestionApprovalHistory.as_view(), name='question-approval-history'),
    url(r'^approval/$', approval.QuestionApproval.as_view(), name='question-approval'),
    url(r'^comment/', include(comment_urls)),
)

question_urls = patterns("",
    url(r'^new/$', question.NewQuestion.as_view(), name='question-new'),
    url(r'^(?P<pk>\d+)/', include(specific_question_urls)),
)

specific_activity_urls = patterns("",
    url(r'^$', activity.ViewActivity.as_view(), name="activity-view"),
    url(r'^signup/$', activity.SignupView.as_view(), name="activity-signup"),
    url(r'^year/(?P<year>\d+)/assign/$', approval.AssignApproval.as_view(), name='activity-approval-assign'),
    url(r'^unassign/$', activity.UnassignView.as_view(), name='activity-unassign'),
    url(r'^previous/$', activity.AssignPreviousActivity.as_view(), name='activity-assign-previous'),
    url(r'^question/', include(question_urls))
)

activity_urls = patterns("",
    url(r'^$', activity.MyActivitiesView.as_view(), name='activity-mine'),
    url(r'^(?P<reference_id>\d+)/', include(specific_activity_urls)),
)

quiz_urls = patterns("",
    url(r'^$', quiz.Quiz.as_view(), name='quiz'),
    url(r'^choose/$', quiz.QuizChooseView.as_view(), name="quiz-choose"),
    url(r'^question/next/$', quiz.QuizQuestionView.as_view(), name='quiz-question'),
    url(r'^question/submit/$', quiz.QuizQuestionSubmit.as_view(), name='quiz-question-submit'),
    url(r'^attempt/generate/$', quiz.NewQuizAttempt.as_view(), name='quiz-generate-attempt'),
    url(r'^start/$', quiz.QuizStartView.as_view(), name='quiz-start'),
    url(r'^(?P<slug>[a-z]+)/start/$', quiz.QuizGenerationView.as_view(), name='quiz-spec'),
    url(r'^(?P<slug>[a-z]+)/view/$', quiz.QuizSpecificationView.as_view(), name='quiz-spec-view'),
    url(r'^prepare/$', quiz.QuizGenerationView.as_view(), name='quiz-prepare'),
    url(r'^submit/$', quiz.QuizSubmit.as_view(), name='quiz-submit'),
    url(r'^report/$', quiz.QuizReport.as_view(), name='quiz-report'),
    url(r'^(?P<slug>[a-z]+)/report/$', quiz.QuizIndividualSummary.as_view(), name='quiz-attempt-report'),
    url(r'^add/$', quiz.NewQuizSpecificationView.as_view(), name='quiz-spec-new'),
    url(r'^(?P<slug>[a-z]+)/edit/$', quiz.UpdateQuizSpecificationView.as_view(), name='quiz-spec-edit'),
    url(r'^(?P<slug>[a-z]+)/question/add/$', quiz.AddQuizSpecificationQuestions.as_view(), name='quiz-spec-question-add'),
    url(r'^(?P<slug>[a-z]+)/question/confirm/$', quiz.ConfirmQuizSpecificationQuestion.as_view(), name='quiz-spec-question-confirm'),
)

approval_urls = patterns("",
    url(r'^$', approval.ApprovalDashboardView.as_view(), name="approve-home"),
    url(r'^guide/$', approval.ApprovalGuide.as_view(), name="approve-guide"),
    url(r'^approve/$', block.PendingBlocksForApprovalView.as_view(), name="approve-choose-block"),
    url(r'^approve/(?P<code>[a-z\d]{1,10})/(?P<year>\d{4})/$', approval.AssignActivitiesForApprovalView.as_view(), name="approve-choose-activity"),
    url(r'^assigned/$', approval.CompleteAssignedApprovalView.as_view(), name="approve-assigned"),
    url(r'^assigned/(?P<previous_question_id>\d+)/next/$', approval.CompleteAssignedApprovalView.as_view(), name="approve-assigned-next"),
)


    # url(r'^approve/$', All BlocksView.as_view(template_name="approve.html"), name='admin-approve-choose'),
    # url(r'^approve/(?P<code>[a-z\d]{1,10})/(?P<year>\d{4})/$', StartApprovalView.as_view(), name='admin-approve-start'),
    # url(r'^approve/assigned/$', StartApprovalView.as_view(), name='admin-approve-assigned-start'),
    # url(r'^approve/(?P<code>[a-z\d]{1,10})/(?P<year>\d{4})/(?P<q_id>\d+)/$', StartApprovalView.as_view(), name='admin-approve'),

urlpatterns = patterns(
    'questions.views',
    url(r'^$', general.DashboardView.as_view(), name='dashboard'),
    url(r'^block/', include(block_urls)),
    url(r'^admin/', include(admin_urls)),
    url(r'^activity/', include(activity_urls)),
    url(r'^quiz/', include(quiz_urls)),
    url(r'^approval/', include(approval_urls)),
    url(r'^guide/$', question.QuestionGuide.as_view(), name='question-guide'),
)
