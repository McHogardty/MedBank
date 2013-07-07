from django.core.mail import EmailMessage

from queue.task import Task
import document
import models

import datetime


class SimpleTask(Task):
    def run(self):
        print "It works!"


class DocumentEmailTask(Task):
    def run(self):
        tb = models.TeachingBlock.objects.filter(
            start__lte=datetime.datetime.now().date
        ).latest("start")

        e = EmailMessage(
            'Questions for %s' % unicode(tb),
            "Hello.",
            "michaelhagarty@gmail.com",
            ["michaelhagarty@gmail.com"],
        )
        e.attach('questions.docx', document.generate_document(tb, False).getvalue())
        e.attach('answers.docx', document.generate_document(tb, True).getvalue())

        e.send()
