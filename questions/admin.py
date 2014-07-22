from django.contrib import admin

from .models import (Question, TeachingActivity, TeachingActivityYear, TeachingBlock,
	TeachingBlockYear, Student, Year, Stage, Comment,
	QuizAttempt, QuestionAttempt, QuizSpecification, QuizQuestionSpecification,
	StudentDashboardSetting, ApprovalRecord)

class TeachingActivityYearAdmin(admin.ModelAdmin):
	filter_horizontal = ['question_writers',]

admin.site.register(Question)
admin.site.register(ApprovalRecord)
admin.site.register(TeachingActivity)
admin.site.register(TeachingActivityYear, TeachingActivityYearAdmin)
admin.site.register(TeachingBlock)
admin.site.register(TeachingBlockYear)
admin.site.register(Student)
admin.site.register(Year)
admin.site.register(Stage)
admin.site.register(Comment)
admin.site.register(QuizAttempt)
admin.site.register(QuestionAttempt)
admin.site.register(QuizSpecification)
admin.site.register(QuizQuestionSpecification)
admin.site.register(StudentDashboardSetting)