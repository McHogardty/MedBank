from medbank import bsforms
from .models import Question, TeachingActivity, TeachingBlock, Student
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


class NewQuestionForm(bsforms.BootstrapHorizontalModelForm):
    """A form for creation and editing of questions."""
    body = forms.CharField(label="Question body", widget=forms.Textarea(attrs={'class': 'span6'}))
    options = QuestionOptionsField()
    answer = forms.ChoiceField(choices=ANSWER_CHOICES, widget=forms.Select(attrs={'class': 'span1'}))
    explanation = forms.CharField(widget=forms.Textarea(attrs={'class': 'span6'}))
    creator = forms.ModelChoiceField(queryset=Student.objects.all(), widget=forms.HiddenInput())
    teaching_activity = forms.ModelChoiceField(queryset=TeachingActivity.objects.all(), widget=forms.HiddenInput())

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


class NewTeachingBlockForm(bsforms.BootstrapHorizontalModelForm):
    start = forms.DateField(widget=forms.TextInput(
        attrs={'class': 'datepicker', 'data-date-format': 'dd/mm/yyyy'}
    ), help_text="The first day that students can assign themselves to activities in this block.")
    end = forms.DateField(widget=forms.TextInput(
        attrs={'class': 'datepicker', 'data-date-format': 'dd/mm/yyyy'}
    ), help_text="The last day that students can assign themselves to activities in this block.")

    class Meta:
        model = TeachingBlock

    def clean(self):
        c = super(NewTeachingBlockForm, self).clean()
        s = c.get('start')
        e = c.get('end')

        if s and e:
            if s > e:
                self._errors["end"] = self.error_class(["The end date should not be less than the start date."])
                del c["end"]

        return c


class NewTeachingBlockDetailsForm(bsforms.BootstrapHorizontalModelForm):
    class Meta:
        model = TeachingBlock
        exclude = ('name', 'year')


class TeachingBlockValidationForm(bsforms.BootstrapHorizontalModelForm):
    class Meta:
        model = TeachingBlock
        exclude = ('stage', 'number', 'start', 'end')

class EmailForm(bsforms.BootstrapHorizontalForm):
    subject = forms.CharField(widget=forms.TextInput(attrs={'class': 'span6'}))
    email = forms.CharField(widget=forms.Textarea(attrs={'class': 'span6'}))
    block = forms.ModelChoiceField(queryset=TeachingBlock.objects.all(), widget=forms.HiddenInput())
