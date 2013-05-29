from django.db import models
from django.contrib.auth.models import User


class Question(models.Model):
    body = models.TextField()
    options = models.TextField()
    answer = models.CharField(max_length=1)
    creator = models.ForeignKey(User)
