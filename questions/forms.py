from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import format_html, format_html_join
from django.utils.encoding import force_text
from django.db import models

from medbank import bsforms
from .models import Question, TeachingActivity, TeachingBlock, TeachingBlockYear, Student, Comment, TeachingActivityYear, QuizSpecification, Reason

import string
import json
import datetime


class QuestionOptionsWidget(forms.MultiWidget):
    def __init__(self, attrs=None):
        widgets = [
            forms.TextInput(),
            forms.TextInput(),
            forms.TextInput(),
            forms.TextInput(),
            forms.TextInput(),
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


class QuestionOptionWidget(forms.MultiWidget):
    def __init__(self, attrs=None):
        widgets = [
            forms.TextInput(),
            forms.TextInput(),
        ]
        super(QuestionOptionWidget, self).__init__(widgets, attrs)

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
        alphabet = ['Text', 'Explanation']
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
            forms.CharField(),
        ]
        super(QuestionOptionsField, self).__init__(fields, *args, **kwargs)

        self.is_question_options_field = True

    def compress(self, values):
        if not values:
            values = [u''] * 5
        return json.dumps(dict(zip(string.ascii_uppercase[:len(values)], values)))

ANSWER_CHOICES = ((x, x) for x in string.ascii_uppercase[:5])


class QuestionOptionField(forms.MultiValueField):
    widget = QuestionOptionWidget

    def __init__(self, *args, **kwargs):
        fields = [
            forms.CharField(),
            forms.CharField(),
        ]
        super(QuestionOptionField, self).__init__(fields, *args, **kwargs)

        self.is_question_options_field = True

    def compress(self, values):
        return {'text': values[0], 'explanation': values[1]}

ANSWER_CHOICES = ((x, x) for x in string.ascii_uppercase[:5])


class NewQuestionForm(bsforms.NewBootstrapModelForm):
    """A form for creation and editing of questions."""
    body = forms.CharField(label="Question body", widget=forms.Textarea())
    #body = forms.CharField(label="Question body", widget=bsforms.RichTextarea())
    options = QuestionOptionsField()
    answer = forms.ChoiceField(choices=ANSWER_CHOICES, widget=forms.Select())
    #explanation = forms.CharField(widget=forms.Textarea())
    #explanation = forms.CharField(widget=bsforms.RichTextarea())
    explanation = QuestionOptionsField(required=False, help_text="Please explain why the answer is correct. You can also explain why the other answers are incorrect.")
    creator = forms.ModelChoiceField(queryset=Student.objects.all(), widget=forms.HiddenInput())
    teaching_activity_year = forms.ModelChoiceField(queryset=TeachingActivityYear.objects.all(), widget=forms.HiddenInput())

    def __init__(self, admin=False, *args, **kwargs):
        super(NewQuestionForm, self).__init__(*args, **kwargs)
        if admin:
            self.fields['reason'] = forms.CharField(label='Reason for editing', widget=forms.Textarea(), help_text="This reason will be sent in an email to the question writer. Be nice! (and please use proper grammar)")

    def clean(self):
        answer = self.cleaned_data['answer']
        if answer:
            explanations = json.loads(self.cleaned_data['explanation'])
            if not explanations[answer]:
                extra = "also " if any(v for k, v in explanations.iteritems() if k != answer) else ""
                self._errors['explanation'] = self.error_class(["You must %swrite an explanation for the answer, %s." % (extra, answer)])
        return super(NewQuestionForm, self).clean()

    class Meta:
        model = Question
        exclude = ('status', 'approver', 'suitable_for_faculty', 'suitable_for_quiz', 'requires_special_formatting')


class TeachingActivityValidationForm(bsforms.BootstrapHorizontalModelForm):
    class Meta:
        model = TeachingActivity


class TeachingActivityYearValidationForm(bsforms.BootstrapHorizontalModelForm):
    class Meta:
        model = TeachingActivityYear
        exclude = ('teaching_activity', 'block_year')


class NewTeachingActivityForm(bsforms.BootstrapHorizontalModelForm):
    class Meta:
        model = TeachingActivity


class NewTeachingActivityYearForm(bsforms.BootstrapHorizontalModelForm):
    class Meta:
        model = TeachingActivityYear
        exclude = ('teaching_activity',)


class TeachingActivityBulkUploadForm(bsforms.NewBootstrapForm):
    ta_file = forms.FileField(label="Activity Information File")
    year = forms.IntegerField()


class NewTeachingBlockForm(bsforms.NewBootstrapModelForm):
    class Meta:
        model = TeachingBlock


class BootstrapRadioFieldRenderer(forms.widgets.RadioFieldRenderer):
    def render(self):
        return format_html(format_html_join('\n', '<div class="radio">{0}</div>', [(force_text(w),) for w in self]))


class NewTeachingBlockYearForm(bsforms.NewBootstrapModelForm):
#    start = forms.DateField(widget=forms.TextInput(
#        attrs={'class': 'datepicker', 'data-date-format': 'dd/mm/yyyy'}
#    ), help_text="The first day that students can assign themselves to activities in this block.")
#    end = forms.DateField(widget=forms.TextInput(
#        attrs={'class': 'datepicker', 'data-date-format': 'dd/mm/yyyy'}
#    ), help_text="The last day that students can assign themselves to activities in this block.")
    block = forms.ModelChoiceField(queryset=TeachingBlock.objects.exclude(years__year__exact=datetime.datetime.now().year).order_by('stage__number', 'code'))
    year = forms.IntegerField(initial=datetime.datetime.now().year, widget=bsforms.StaticControl())
    start = forms.DateField(widget=forms.DateInput(attrs={"class": "date"}), help_text="The first day that students can assign themselves to activities in this block.", label="Start date")
    end = forms.DateField(widget=forms.DateInput(attrs={"class": "date"}), help_text="The last day that students can assign themselves to activities in this block.", label="End date")
    close = forms.DateField(widget=forms.DateInput(attrs={"class": "date"}), help_text="The last day that students can write questions for activities in this block.", label="Close date")
    release_date = forms.CharField(required=False, max_length=10, widget=bsforms.StaticControl(), help_text="The release date will be set once an administrator releases the block to students.")
    sign_up_mode = forms.TypedChoiceField(widget=forms.RadioSelect(renderer=BootstrapRadioFieldRenderer), choices=TeachingBlockYear.MODE_CHOICES, coerce=int)

    class Meta:
        model = TeachingBlockYear
        fields = ('block', 'year', 'start', 'end', 'close', 'release_date', 'activity_capacity', 'sign_up_mode', 'weeks')

    def __init__(self, *args, **kwargs):
        super(NewTeachingBlockYearForm, self).__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields['block'].queryset = TeachingBlock.objects.exclude(years__year__exact=self.instance.year) | TeachingBlock.objects.filter(id=self.instance.block.id)

    def clean(self):
        c = super(NewTeachingBlockYearForm, self).clean()
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
        exclude = ('stage', 'code', 'start', 'end')


class NewQuizSpecificationForm(bsforms.NewBootstrapModelForm):
    class Meta:
        model = QuizSpecification
        exclude = ('slug', )


class QuestionQuizSpecificationForm(bsforms.NewBootstrapForm):
    specification = forms.ModelChoiceField(queryset=QuizSpecification.objects.all())


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


# class ReasonForFlaggingForm(bsforms.NewBootstrapModelForm):
#     body = forms.CharField(widget=forms.Textarea(), label="Reason")
#     question = forms.ModelChoiceField(queryset=Question.objects.all(), widget=forms.HiddenInput())
#     reason_type = forms.ChoiceField(choices=Reason.REASON_TYPES, widget=forms.HiddenInput())
#     creator = forms.ModelChoiceField(queryset=Student.objects.all(), widget=forms.HiddenInput())

#     class Meta:
#         model = Reason

class ReasonForFlaggingForm(bsforms.NewBootstrapForm):
    reason = forms.CharField(widget=forms.Textarea())

class QuestionAttributesForm(bsforms.NewBootstrapModelForm):
    suitable_for_quiz = forms.BooleanField(widget=bsforms.CheckboxInput(), label="This is suitable for inclusion in the model quiz for this block, and for submission to the Faculty for consideration as official exam material.", required=False)
    requires_special_formatting = forms.BooleanField(widget=bsforms.CheckboxInput(), label="This question requires special formatting.", required=False)

    class Meta:
        model = Question
        exclude = ('body', 'options', 'answer', 'explanation', 'date_created', 'creator', 'approver', 'teaching_activity_year', 'status', 'suitable_for_faculty')

