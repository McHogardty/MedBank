from medbank import bsforms
from .models import Question, TeachingActivity, TeachingBlock, Student, Comment
from django import forms
from django.utils.safestring import mark_safe
from django.contrib.formtools.wizard.views import CookieWizardView
from django.shortcuts import redirect
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.contrib import auth


import string
import json
import os
import csv


class QuestionOptionsWidget(forms.MultiWidget):
    def __init__(self, attrs=None):
        widgets = [
            forms.TextInput(attrs={'class': ''}),
            forms.TextInput(attrs={'class': ''}),
            forms.TextInput(attrs={'class': ''}),
            forms.TextInput(attrs={'class': ''}),
            forms.TextInput(attrs={'class': ''}),
        ]
        super(QuestionOptionsWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if not value:
            return []
        j = json.loads(value)
        return [j[x] for x in string.ascii_uppercase[:len(j)]]

    def render(self, name, value, attrs=None):
        if self.is_localized:
            for widget in self.widgets:
                widget.is_localized = self.is_localized

        if not isinstance(value, list):
            value = self.decompress(value)

        output = ['<div class="options_table span6"><table style="width:100%;">']
        final_attrs = self.build_attrs(attrs)
        c = final_attrs.get('class', '')
        if c:
            c += " input-block-level"
        else:
            c = "input-block-level"
        final_attrs['class'] = c
        id_ = final_attrs.get('id', None)
        alphabet = string.ascii_uppercase
        for i, widget in enumerate(self.widgets):
            try:
                widget_value = value[i]
            except IndexError:
                widget_value = None
            if id_:
                final_attrs = dict(final_attrs, id='%s_%s' % (id_, alphabet[i]))
            output.append('<tr><td class="option-label">%s</td><td class="">' % (alphabet[i], ))
            output.append(widget.render(name + '_%s' % i, widget_value, final_attrs))
            output.append('</td></tr>')
        output.append('</table></div>')
        return mark_safe(self.format_output(output))


class QuestionOptionsField(forms.MultiValueField):
    widget = QuestionOptionsWidget

    def __init__(self, *args, **kwargs):
        fields = [
            forms.CharField(),
            forms.CharField(),
            forms.CharField(),
            forms.CharField(),
            forms.CharField()
        ]
        super(QuestionOptionsField, self).__init__(fields, *args, **kwargs)

        self.is_question_options_field = True

    def compress(self, values):
        return json.dumps(dict(zip(string.ascii_uppercase[:len(values)], values)))

ANSWER_CHOICES = ((x, x) for x in string.ascii_uppercase[:5])


class NewQuestionForm(bsforms.NewBootstrapModelForm):
    """A form for creation and editing of questions."""
    body = forms.CharField(label="Question body", widget=forms.Textarea())
    options = QuestionOptionsField()
    answer = forms.ChoiceField(choices=ANSWER_CHOICES, widget=forms.Select())
    explanation = forms.CharField(widget=forms.Textarea())
    creator = forms.ModelChoiceField(queryset=Student.objects.all(), widget=forms.HiddenInput())
    teaching_activity = forms.ModelChoiceField(queryset=TeachingActivity.objects.all(), widget=forms.HiddenInput())

    def __init__(self, admin=False, *args, **kwargs):
        super(NewQuestionForm, self).__init__(*args, **kwargs)
        if admin:
            self.fields['reason'] = forms.CharField(label='Reason for editing', widget=forms.Textarea(), help_text="This reason will be sent in an email to the question writer. Be nice! (and please use proper grammar)")

    class Meta:
        model = Question
        exclude = ('status', 'approver')


class TeachingActivityValidationForm(bsforms.BootstrapHorizontalModelForm):
    class Meta:
        model = TeachingActivity
        exclude = ('block')


class NewTeachingActivityForm(bsforms.BootstrapHorizontalModelForm):
    class Meta:
        model = TeachingActivity


class TeachingActivityBulkUploadForm(bsforms.BootstrapHorizontalForm):
    ta_file = forms.FileField()
    year = forms.IntegerField()


class NewTeachingBlockForm(bsforms.NewBootstrapModelForm):
#    start = forms.DateField(widget=forms.TextInput(
#        attrs={'class': 'datepicker', 'data-date-format': 'dd/mm/yyyy'}
#    ), help_text="The first day that students can assign themselves to activities in this block.")
#    end = forms.DateField(widget=forms.TextInput(
#        attrs={'class': 'datepicker', 'data-date-format': 'dd/mm/yyyy'}
#    ), help_text="The last day that students can assign themselves to activities in this block.")
    start = forms.DateField(widget=forms.TextInput(), help_text="The first day that students can assign themselves to activities in this block.")
    end = forms.DateField(widget=forms.TextInput(), help_text="The last day that students can assign themselves to activities in this block.")
    close = forms.DateField(widget=forms.TextInput(), help_text="The last day that students can write questions for activities in this block.")
    release_date = forms.CharField(required=False, max_length=10, widget=bsforms.StaticControl(), help_text="The release date will be set once an administrator releases the block to students.")

    class Meta:
        model = TeachingBlock

    def clean(self):
        c = super(NewTeachingBlockForm, self).clean()
        del c['release_date']
        start = c.get('start')
        end = c.get('end')
        close = c.get('close')

        if start and end and close:
            if start > end:
                self._errors["end"] = self.error_class(["The end date should not be earlier than the start date."])
                del c["end"]
            if start > close:
                self._errors["close"] = self.error_class(["The close date should not be earlier than the start date."])
            elif end > close:
                self._errors["close"] = self.error_class(["The close date should not be earlier than the end date."])

        if self.instance and self.instance.release_date:
            if end >= self.instance.release_date:
                self._errors["end"] = self.error_class(["The release date should not occur on or after the release date."])
            if start >= self.instance.release_date:
                self._errors["start"] = self.error_class(["The start date should not occur on or after the release date."])

        return c

    def clean_release_date(self):
        return


class NewTeachingBlockDetailsForm(bsforms.BootstrapHorizontalModelForm):
    class Meta:
        model = TeachingBlock
        exclude = ('name', 'year')


class TeachingBlockValidationForm(bsforms.BootstrapHorizontalModelForm):
    class Meta:
        model = TeachingBlock
        exclude = ('stage', 'number', 'start', 'end')

class EmailForm(bsforms.NewBootstrapForm):
    from_address = forms.CharField(widget=bsforms.StaticControl())
    subject = forms.CharField(widget=bsforms.TextInputWithAddon(add_on="[MedBank]", attrs={'class': 'span6'}))
    email = forms.CharField(widget=forms.Textarea(attrs={'class': 'span6'}))
    block = forms.ModelChoiceField(queryset=TeachingBlock.objects.all(), widget=forms.HiddenInput())


class CommentForm(bsforms.NewBootstrapModelForm):
    creator = forms.ModelChoiceField(queryset=Student.objects.all(), widget=forms.HiddenInput())
    question = forms.ModelChoiceField(queryset=Question.objects.all(), widget=forms.HiddenInput())
    reply_to = forms.ModelChoiceField(required=False, queryset=Comment.objects.all(), widget=forms.HiddenInput())

    class Meta:
        model = Comment
