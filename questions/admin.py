from django.contrib import admin

from .models import Question, TeachingActivity, TeachingBlock, Student, Year

admin.site.register(Question)
admin.site.register(TeachingActivity)
admin.site.register(TeachingBlock)
admin.site.register(Student)
admin.site.register(Year)
