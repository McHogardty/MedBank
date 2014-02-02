from django.contrib import admin

from .models import (Question, TeachingActivity, TeachingBlock,
	TeachingBlockYear, Student, Year, Stage, Comment,
	QuizAttempt, QuestionAttempt)

admin.site.register(Question)
admin.site.register(TeachingActivity)
admin.site.register(TeachingBlock)
admin.site.register(TeachingBlockYear)
admin.site.register(Student)
admin.site.register(Year)
admin.site.register(Stage)
admin.site.register(Comment)
admin.site.register(QuizAttempt)
admin.site.register(QuestionAttempt)