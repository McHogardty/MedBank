from django.contrib import admin

from .models import Question, TeachingActivity, TeachingBlock, Student, Year, Stage, Comment

admin.site.register(Question)
admin.site.register(TeachingActivity)
admin.site.register(TeachingBlock)
admin.site.register(Student)
admin.site.register(Year)
admin.site.register(Stage)
admin.site.register(Comment)