from __future__ import unicode_literals

from django.conf.urls import include, url

from .views import block, activity, question, admin, approval, general, quiz

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

# from queue import base

teaching_block_year_urls = [
    url(r'^edit/$', block.EditBlock.as_view(), name='block-edit'),
    url(r'^activity/all/$', block.BlockActivitiesView.as_view(), name='block-activities'),
    url(r'^release/$', block.ReleaseBlockView.as_view(), name='block-release'),
    url(r'^download/$', block.DownloadView.as_view(), name="block-download"),
    url(r'^admin/$', admin.BlockAdminView.as_view(), name='block-admin'),
    url(r'^admin/approval/statistics/$', admin.ApprovalStatisticsView.as_view(), name='block-approval-statistics'),
    url(r'^admin/upload/confirm/$', block.ConfirmUploadForTeachingBlock.as_view(), name='block-activity-upload-confirm'),
    url(r'^admin/upload/submit/$', block.UploadForTeachingBlock.as_view(), name='block-activity-upload-submit'),
    url(r'^admin/upload/start/$', block.StartUploadForTeachingBlock.as_view(), name='block-activity-upload'),
]

specific_block_urls = [
    # url(r'^download/$', block.DownloadView.as_view(), name="block-download"),
    url(r'^(?P<year>\d{4})/', include(teaching_block_year_urls)),
    url(r'^admin/select/$', block.ChangeAdminYear.as_view(), name="block-admin-select"),
]

block_urls = [
    url(r'^$', block.AllBlocksView.as_view(), name='block-list'),
    url(r'^open/$', block.OpenBlocksView.as_view(), name='block-open-list'),
    url(r'^released/$', block.ReleasedBlocksView.as_view(), name="block-released-list"),
    url(r'^new/$', block.NewBlock.as_view(), name='block-new'),
    url(r'^(?P<code>[a-z\d]{1,10})/', include(specific_block_urls)),
]

admin_urls = [
    url(r'^$', admin.AdminView.as_view(), name='admin'),
    url(r'^email/(?P<code>[a-z\d]{1,10})/(?P<year>\d{4})/$', general.EmailView.as_view(), name='email'),
    url(r'^dashboard/', general.DashboardAdminView.as_view(), name='dashboard-admin'),
    url(r'^approval/', approval.ApprovalDashboardAdmin.as_view(), name='approval-dashboard-admin'),
    url(r'^settings/create/$', admin.CreateMissingSettingsView.as_view(), name='admin-settings-create'),
    url(r'^settings/(?P<pk>\d+)/view/$', admin.SettingView.as_view(), name='admin-settings-view'),
    url(r'^settings/(?P<pk>\d+)/edit/$', admin.EditSettingView.as_view(), name='admin-settings-edit'),
]

comment_urls = [
    url(r'^new/$', question.AddComment.as_view(), name="comment-new"),
    url(r'^reply/(?P<comment_id>\d+)/$', question.AddComment.as_view(), name="comment-reply"),
]

specific_question_urls = [
    url(r'^$', question.ViewQuestion.as_view(), name='question-view'),
    url(r'^edit/$', question.UpdateQuestion.as_view(), name='question-edit'),
    url(r'^status/flag/$', approval.FlagQuestion.as_view(), name='question-flag'),
    url(r'^attributes/$', question.QuestionAttributes.as_view(), name='question-attributes'),
    url(r'^history/$', approval.ViewQuestionApprovalHistory.as_view(), name='question-approval-history'),
    url(r'^approval/$', approval.QuestionApproval.as_view(), name='question-approval'),
    url(r'^comment/', include(comment_urls)),
]

question_urls = [
    url(r'^new/$', question.NewQuestion.as_view(), name='question-new'),
    url(r'^(?P<pk>\d+)/', include(specific_question_urls)),
]

specific_activity_urls = [
    url(r'^$', activity.ViewActivity.as_view(), name="activity-view"),
    url(r'^signup/$', activity.SignupView.as_view(), name="activity-signup"),
    url(r'^year/(?P<year>\d+)/assign/$', approval.AssignApproval.as_view(), name='activity-approval-assign'),
    url(r'^unassign/$', activity.UnassignView.as_view(), name='activity-unassign'),
    url(r'^previous/$', activity.AssignPreviousActivity.as_view(), name='activity-assign-previous'),
    url(r'^question/', include(question_urls))
]

activity_urls = [
    url(r'^$', activity.MyActivitiesView.as_view(), name='activity-mine'),
    url(r'^(?P<reference_id>\d+)/', include(specific_activity_urls)),
]

quiz_attempt_urls = [
    url(r"^questions/$", quiz.QuizAttemptQuestionsView.as_view(), name="quiz-attempt-questions"),
    url(r"^submit/$", quiz.SubmitAnswerView.as_view(), name="quiz-attempt-submit"),
    url(r"^submit/all/$", quiz.SubmitAllAnswersView.as_view(), name="quiz-attempt-submit-all"),
    url(r"^report/$", quiz.QuizAttemptReport.as_view(), name="quiz-attempt-report"),
    url(r'^start/$', quiz.ResumeAttemptView.as_view(), name="quiz-attempt-start"),
    url(r"^resume/$", quiz.ResumeAttemptView.as_view(), name="quiz-attempt-resume"),
]

specific_quiz_specification_urls = [
    url(r"^$", quiz.QuizSpecificationView.as_view(), name="quiz-specification-view"),
    url(r"^edit/$", quiz.UpdateQuizSpecificationView.as_view(), name="quiz-specification-edit"),
    url(r"^questions/add/$", quiz.AddQuizSpecificationQuestions.as_view(), name="quiz-specification-questions-add"),
    url(r"^questions/add/confirm/$", quiz.ConfirmQuizSpecificationQuestions.as_view(), name="quiz-specification-questions-add-confirm"),
]

quiz_specification_urls = [
    url(r"^new/$", quiz.NewQuizSpecificationView.as_view(), name="quiz-specification-new"),
    url(r'^(?P<slug>[a-z]+)/', include(specific_quiz_specification_urls)),
]

quiz_urls = [
    url(r'^$', quiz.QuizDashboard.as_view(), name='quiz-home'),
    url(r'^history/$', quiz.QuizHistory.as_view(), name='quiz-history'),
    url(r'^choose/$', quiz.QuizView.as_view(), name='quiz-choose'),
    url(r'^attempt/(?P<slug>[a-z]+)/', include(quiz_attempt_urls)),
    url(r'^specification/', include(quiz_specification_urls)),
    url(r'^admin/$', quiz.QuizAdminView.as_view(), name="quiz-admin"),
]

approval_urls = [
    url(r'^$', approval.ApprovalDashboardView.as_view(), name="approve-home"),
    url(r'^guide/$', approval.ApprovalGuide.as_view(), name="approve-guide"),
    url(r'^approve/$', block.PendingBlocksForApprovalView.as_view(), name="approve-choose-block"),
    url(r'^approve/(?P<code>[a-z\d]{1,10})/(?P<year>\d{4})/$', approval.AssignActivitiesForApprovalView.as_view(), name="approve-choose-activity"),
    url(r'^assigned/$', approval.CompleteAssignedApprovalView.as_view(), name="approve-assigned"),
    url(r'^assigned/(?P<previous_question_id>\d+)/next/$', approval.CompleteAssignedApprovalView.as_view(), name="approve-assigned-next"),
]

urlpatterns = [
    url(r'^$', general.DashboardView.as_view(), name='dashboard'),
    url(r'^block/', include(block_urls)),
    url(r'^admin/', include(admin_urls)),
    url(r'^activity/', include(activity_urls)),
    url(r'^quiz/', include(quiz_urls)),
    url(r'^approval/', include(approval_urls)),
    url(r'^guide/$', question.QuestionGuide.as_view(), name='question-guide'),
]
