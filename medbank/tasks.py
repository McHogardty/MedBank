from django.core.mail import send_mail

from queue.task import Task


class ChangePasswordEmailTask(Task):
    def __init__(self, body, recipient):
        self.body = body
        self.recipient = recipient

    def run(self):
        send_mail('Account change request - SUMS MedBank', self.body, "SUMS MedBank <medbank@sydneymedsoc.org.au>", [self.recipient, ])
