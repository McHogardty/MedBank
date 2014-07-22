from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import format_html, format_html_join
from django.utils.encoding import force_text
from django.db import models

from medbank import bsforms
from medbank.forms import SettingEditForm
from .models import Question, TeachingActivity, TeachingBlock, TeachingBlockYear, Student, Comment, TeachingActivityYear, QuizSpecification, Reason

import string
import json
import datetime


class QuestionOptionsWidget(forms.MultiWidget):
    def __init__(self, attrs=None):
        widgets = [
            bsforms.TextInputWithAddon(),
            bsforms.TextInputWithAddon(),
            bsforms.TextInputWithAddon(),
            bsforms.TextInputWithAddon(),
            bsforms.TextInputWithAddon(),
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

        output = []
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id', None)
        alphabet = string.ascii_uppercase
        for i, widget in enumerate(self.widgets):
            option_value = alphabet[i]
            try:
                widget_value = value[i]
            except IndexError:
                widget_value = None
            if id_:
                final_attrs = dict(final_attrs, id='%s_%s' % (id_, option_value))
            widget.add_on = option_value
            widget.group_class = "options-group"
            output.append(widget.render(name + '_%s' % i, widget_value, final_attrs))
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
    widget = QuestionOptionsWidget(attrs={'class': 'options-field'})

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
        if self.instance:
            if not self.instance.explanation_dict():
                explanation = []
                for character in string.ascii_uppercase[:5]:
                    if self.instance.answer == character:
                        explanation.append((character, self.instance.explanation))
                    else:
                        explanation.append((character, ""))
                print "Setting explanation %s" % json.dumps(dict(explanation))
                self.initial["explanation"] = json.dumps(dict(explanation))
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
        exclude = ('status', 'approver', 'exemplary_question', 'requires_special_formatting', 'date_assigned', 'date_completed')


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
    start = forms.DateField(widget=forms.DateInput(attrs={"class": "date-input"}), help_text="The first day that students can assign themselves to activities in this block.", label="Start date")
    end = forms.DateField(widget=forms.DateInput(attrs={"class": "date-input"}), help_text="The last day that students can assign themselves to activities in this block.", label="End date")
    close = forms.DateField(widget=forms.DateInput(attrs={"class": "date-input"}), help_text="The last day that students can write questions for activities in this block.", label="Close date")
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
    active = forms.BooleanField(widget=bsforms.CheckboxInput())
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


class ReasonForFlaggingForm(bsforms.NewBootstrapModelForm):
    body = forms.CharField(widget=forms.Textarea(), label="Reason")
    reason_type = forms.ChoiceField(choices=Reason.REASON_TYPES, widget=forms.HiddenInput())
    creator = forms.ModelChoiceField(queryset=Student.objects.all(), widget=forms.HiddenInput())

    class Meta:
        model = Reason
        exclude = ('related_object_id', 'related_object_content_type')

# class ReasonForFlaggingForm(bsforms.NewBootstrapForm):
#     reason = forms.CharField(widget=forms.Textarea())

class QuestionAttributesForm(bsforms.NewBootstrapModelForm):
    exemplary_question = forms.BooleanField(widget=bsforms.CheckboxInput(), label="This is an exemplary question for this block.", required=False)
    requires_special_formatting = forms.BooleanField(widget=bsforms.CheckboxInput(), label="This question requires special formatting.", required=False)

    class Meta:
        model = Question
        exclude = ('body', 'options', 'answer', 'explanation', 'date_created', 'creator', 'approver', 'teaching_activity_year', 'status')


class SettingEditForm(SettingEditForm):
    main_text = forms.CharField(required=False)
    secondary_text = forms.CharField(required=False)
    image = forms.ImageField(required=False)

    def __init__(self, *args, **kwargs):
        setting_instance = kwargs["instance"]
        kwargs['initial'].update({"main_text": setting_instance.main_text(), "secondary_text": setting_instance.secondary_text()})
        super(SettingEditForm, self).__init__(*args, **kwargs)

    class Meta(SettingEditForm.Meta):
        exclude = ['value',]


class QuestionForm(bsforms.NewBootstrapForm):
    question_id = forms.ModelChoiceField(widget=forms.TextInput(), label="Question ID", queryset=Question.objects.all())
    questions_selected = forms.ModelMultipleChoiceField(widget=forms.MultipleHiddenInput(), queryset=Question.objects.all(), required=False)


class ConfirmQuestionSelectionForm(bsforms.NewBootstrapForm):
    question_id = forms.ModelMultipleChoiceField(queryset=Question.objects.all())

class CustomQuizSpecificationForm(bsforms.NewBootstrapForm):
    form_widget_width=2

    QUIZ_TYPE_CHOICES = (
        ("individual", "individual"),
        ("classic", "classic"),
    )

    quiz_type = forms.ChoiceField(choices=QUIZ_TYPE_CHOICES, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        blocks = kwargs.pop("blocks", None)
        super(CustomQuizSpecificationForm, self).__init__(*args, **kwargs)
        self.block_fields = []
        for block in blocks:
            self.fields[block.name_for_form_fields()] = forms.IntegerField(label=block.name, required=False, min_value=0)
            self.block_fields.append(block.name_for_form_fields())

    def clean(self):
        c = self.cleaned_data

        # If none of the blocks have any cleaned data, the form is not valid.
        if all(not c[block] for block in self.block_fields if block in c):
            raise forms.ValidationError("At least one of the blocks must be filled in.")

        return c


class PresetQuizSpecificationForm(bsforms.NewBootstrapForm):
    QUIZ_TYPE_CHOICES = CustomQuizSpecificationForm.QUIZ_TYPE_CHOICES

    quiz_type = forms.ChoiceField(choices=QUIZ_TYPE_CHOICES, widget=forms.HiddenInput())
    quiz_specification = forms.ModelChoiceField(queryset=QuizSpecification.objects.all(), to_field_name="slug", widget=forms.HiddenInput())


BOOLEAN_CHOICES = (
    (True, 'Yes'),
    (False, 'No'),
)

class QuestionApprovalForm(bsforms.NewBootstrapModelForm):
    exemplary_question = forms.TypedChoiceField(choices=BOOLEAN_CHOICES, coerce=lambda x: (x == "True"), widget=bsforms.ButtonGroupWithToggle)

    new_status = forms.TypedChoiceField(choices=Question.STATUS_TO_ACTION, widget=bsforms.ButtonGroupWithToggle, coerce=int)

    def __init__(self, *args, **kwargs):
        super(QuestionApprovalForm, self).__init__(*args, **kwargs)
        print self.fields
        question_status = self.instance.status

        NEW_STATUS_TO_ACTION = []
        for status, action in Question.STATUS_TO_ACTION:
            if question_status == status:
                continue

            NEW_STATUS_TO_ACTION.append((status, action))

        self.fields['new_status'].choices = tuple(NEW_STATUS_TO_ACTION)

    class Meta:
        model = Question
        exclude = ('body', 'options', 'answer', 'explanation', 'date_created', 'creator', 'approver', 'teaching_activity_year', 'status', 'requires_special_formatting', 'date_assigned', 'date_completed', 'approver')


class TeachingBlockActivityUploadForm(bsforms.NewBootstrapForm):
    upload_file = forms.FileField(label="Activity file")


class AssignPreviousActivityForm(bsforms.NewBootstrapModelForm):
    previous_activity = forms.ModelChoiceField(to_field_name="reference_id", widget=forms.TextInput(), queryset=TeachingActivity.objects.all(), help_text="Type in the reference ID of the previous activity to assign it as the old version of the current activity.")

    class Meta:
        model = TeachingActivity
        exclude = ('name', 'activity_type', 'reference_id')
