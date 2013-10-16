from django.core.mail import EmailMessage, send_mass_mail, get_connection, EmailMultiAlternatives

from queue.task import Task
import document
import models

import datetime
import time


class DocumentEmailTask(Task):
    def __init__(self, pk, *args, **kwargs):
        self.pk = pk
        return super(DocumentEmailTask, self).__init__(*args, **kwargs)

    def run(self):
        tb = models.TeachingBlock.objects.filter(
            start__lte=datetime.datetime.now().date
        ).latest("start")

        e = EmailMessage(
            '[MedBank] Questions for %s' % unicode(tb),
            "Hello.",
            "medbank@sydneymedsoc.org.au",
            ["michaelhagarty@gmail.com"],
        )
        e.attach('questions.docx', document.generate_document(tb, False).getvalue())
        e.attach('answers.docx', document.generate_document(tb, True).getvalue())
        try:
            e.send()
        except Exception as e:
            f = open('email.%s' % time.time(), 'w')
            f.write(sys.exc_info())
            f.close()

class EmailTask(Task):
    def __init__(self, subject, body, recipients):
        self.subject = subject
        self.body = body
        self.recipients = recipients

    def run(self):
        messages = (
            (self.subject,
            self.body,
            "SUMS MedBank <medbank@sydneymedsoc.org.au>",
            [r, ]) 
        for r in self.recipients)

        send_mass_mail(messages)

class HTMLEmailTask(Task):
    def __init__(self, subject, body, recipients):
        self.subject = subject
        self.body = body
        self.recipients = recipients

    def run(self):
        c = get_connection(fail_silently=False)

        messages = tuple(EmailMessage(self.subject, self.body, "SUMS MedBank <medbank@sydneymedsoc.org.au>", [r, ]) for r in self.recipients)
        for m in messages:
            m.content_subtype = 'html'
        return c.send_messages(messages)
