from django.template.loader import render_to_string
from django.contrib.staticfiles import finders

import post_office

import premailer

css_files = [finders.find('medbank/css/bootstrap-email.css'), finders.find('medbank/css/bootstrap-custom.css')]

def _send_email(template_name, template_context, recipient, sender="SUMS MedBank <medbank@sydneymedsoc.org.au>", subject=""):
	html = render_to_string("%s.html" % template_name, template_context)
	css_inliner = premailer.Premailer(html, external_styles=css_files, disable_validation=True)
	html = css_inliner.transform()
	# txt = render_to_string("%s.txt" % template_name, template_context.copy())

	post_office.mail.send(
		recipient,
		sender,
		subject="[MedBank] %s" % subject,
		# message=txt,
		html_message=html,
	)



def send_question_creation_email(student, question, question_url, template_name="email/question_created"):
	# Sends an email to the creator of the question confirming that their question has been submitted.
	template_context = {"question": question, "question_url": question_url}

	_send_email(template_name, template_context, student.user.email, subject="Question submitted")


def send_question_updated_email(student, question, question_url, template_name="question_updated"):
	# Sends two emails, one to the updater, and one to the creator.
	# If the updater and the creator are the same person, it does not send two emails.

	template_context = {"question": question, "question_url": question_url}

	_send_email("email/update_submitted", template_context, student.user.email, subject="Update submitted")
	_send_email("email/question_updated", template_context, question.creator.user.email, subject="Question updated")

