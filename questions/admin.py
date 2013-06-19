from django.contrib import admin

from .models import Question, TeachingActivity, TeachingBlock

admin.site.register(Question)
admin.site.register(TeachingActivity)
admin.site.register(TeachingBlock)
