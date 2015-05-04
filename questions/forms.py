from __future__ import unicode_literals

from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import format_html, format_html_join
from django.utils.encoding import force_text
from django.conf import settings

import bootstrap
from medbank.forms import SettingEditForm
from .models import *

import string
import json
import datetime


class QuestionOptionsWidget(forms.MultiWidget):
    def __init__(self, attrs=None):
        widgets = [
            bootstrap.RichTextInputWithAddon(),
            bootstrap.RichTextInputWithAddon(),
            bootstrap.RichTextInputWithAddon(),
            bootstrap.RichTextInputWithAddon(),
            bootstrap.RichTextInputWithAddon(),
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
            values = [''] * 5
        return json.dumps(dict(zip(string.ascii_uppercase[:len(values)], values)))

    def validate(self, value):
        if self.required:
            json_value = json.loads(value)
            if not all(v.replace(" ", "") for v in json_value.values()):
                raise forms.ValidationError("Please make sure that you enter five options.")


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

ANSWER_CHOICES = list((x, x) for x in string.ascii_uppercase[:5])


class NewQuestionForm(bootstrap.ModelForm):
    """A form for creation and editing of questions."""
    # body = forms.CharField(label="Question body", widget=forms.Textarea(attrs={'class': 'summernote'}))
    body = bootstrap.RealTextField(label="Question body")
    #body = forms.CharField(label="Question body", widget=bsforms.RichTextarea())
    options = QuestionOptionsField()
    answer = forms.ChoiceField(choices=ANSWER_CHOICES, widget=forms.Select())
    #explanation = forms.CharField(widget=forms.Textarea())
    #explanation = forms.CharField(widget=bsforms.RichTextarea())
    explanation = QuestionOptionsField(required=False, help_text="Please explain why the answer is correct, or why all of the other options are incorrect.")
    creator = forms.ModelChoiceField(queryset=Student.objects.all(), widget=forms.HiddenInput())
    teaching_activity_year = forms.ModelChoiceField(queryset=TeachingActivityYear.objects.all(), widget=forms.HiddenInput())

    def __init__(self, edit_mode=False, change_student=False, *args, **kwargs):
        super(NewQuestionForm, self).__init__(*args, **kwargs)

        if change_student:
            self.fields['creator'] = forms.ModelChoiceField(queryset=Student.objects.select_related().order_by('user__username'), widget=forms.Select())
        if edit_mode:
            self.fields['reason'] = forms.CharField(label='Reason for editing')

    def clean(self):
        answer = self.cleaned_data['answer']
        if answer and 'explanation' in self.cleaned_data:
            explanations = json.loads(self.cleaned_data['explanation'])
            if not explanations[answer] and not all(explanations[x] for x, y in ANSWER_CHOICES if x != answer):
                # The user needs to complete the answer explanation, or all of the incorrect option explanations.
                self._errors['explanation'] = self.error_class(["You must complete the explanation.",])
        return super(NewQuestionForm, self).clean()

    class Meta:
        model = Question
        exclude = ('status', 'approver', 'exemplary_question', 'requires_special_formatting', 'date_assigned', 'date_completed')


class TeachingActivityValidationForm(bootstrap.ModelForm):
    class Meta:
        model = TeachingActivity
        fields = '__all__'


class TeachingActivityYearValidationForm(bootstrap.ModelForm):
    class Meta:
        model = TeachingActivityYear
        exclude = ('teaching_activity', 'block_week')


class BlockWeekValidationForm(bootstrap.ModelForm):
    class Meta:
        model = BlockWeek
        fields = ('name', )

class NewTeachingActivityForm(bootstrap.ModelForm):
    class Meta:
        model = TeachingActivity
        fields = '__all__'


class NewTeachingActivityYearForm(bootstrap.ModelForm):
    class Meta:
        model = TeachingActivityYear
        fields = ('position',)

class NewBlockWeekForm(bootstrap.ModelForm):
    class Meta:
        model = BlockWeek
        fields = ('name', 'sort_index')
        

class TeachingActivityBulkUploadForm(bootstrap.Form):
    ta_file = forms.FileField(label="Activity Information File")
    year = forms.IntegerField()


class BootstrapRadioFieldRenderer(forms.widgets.RadioFieldRenderer):
    def render(self):
        return format_html(format_html_join('\n', '<div class="radio">{0}</div>', [(force_text(w),) for w in self]))


class NewTeachingBlockForm(bootstrap.ModelForm):
    code = forms.RegexField(max_length=10, regex=r'^[a-zA-Z0-9]+$', help_text="A short identifying alphanumeric string which identifies the block. It must be unique and cannot contain spaces.")
    sort_index = forms.IntegerField(localize=True, help_text="Determines the order in which blocks are displayed. Blocks are ordered by increasing sort index.")
    code_includes_week = forms.BooleanField(required=False, widget=bootstrap.CheckboxInput(), label="The activities in this block are organised into weeks.")


    class Meta:
        model = TeachingBlock
        fields = ('name', 'code', 'sort_index', 'code_includes_week')

    def clean_code(self):
        data = self.cleaned_data['code']

        if TeachingBlock.objects.filter(code=data).exists():
            raise forms.ValidationError("A block with that code already exists.")

        return data


class NewTeachingBlockYearForm(bootstrap.ModelForm):
    # Localise=True is a cheating way of using a TextInput instead of a number input.
    block = forms.ModelChoiceField(queryset=TeachingBlock.objects.exclude(years__year__exact=datetime.datetime.now().year))#.order_by('sort_index'))
    year = forms.IntegerField(initial=datetime.datetime.now().year, widget=forms.HiddenInput())

    class Meta:
        model = TeachingBlockYear
        fields = ('block', 'year')

    def __init__(self, *args, **kwargs):
        super(NewTeachingBlockYearForm, self).__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields['block'].queryset = TeachingBlock.objects.exclude(years__year__exact=self.instance.year) | TeachingBlock.objects.filter(id=self.instance.block.id)


class NewQuestionWritingPeriodForm(bootstrap.ModelForm):
    block = forms.CharField(max_length=200, widget=bootstrap.StaticControl())
    activity_capacity = forms.IntegerField(localize=True, label="Maximum users per activity", initial=settings.USERS_PER_ACTIVITY)
    start = forms.DateField(widget=bootstrap.DatepickerInput(), help_text="The first day that students can assign themselves to activities in this block.", label="Start date")
    end = forms.DateField(widget=bootstrap.DatepickerInput(), help_text="The last day that students can assign themselves to activities in this block.", label="End date")
    close = forms.DateField(widget=bootstrap.DatepickerInput(), help_text="The last day that students can write questions for activities in this block.", label="Close date")

    class Meta:
        model = QuestionWritingPeriod
        fields = ('block', 'stage', 'activity_capacity', 'start', 'end', 'close')

    def __init__(self, *args, **kwargs):
        if 'block_year' in kwargs:
            initial = kwargs.setdefault('initial', {})
            initial['block'] = str(kwargs.pop('block_year'))

        super(NewQuestionWritingPeriodForm, self).__init__(*args, **kwargs)

    def clean(self):
        c = super(NewQuestionWritingPeriodForm, self).clean()
        start = c.get('start')
        end = c.get('end')
        close = c.get('close')

        if start and end and start > end:
            self._errors["end"] = self.error_class(["The end date should not be earlier than the start date."])
        if start and close and start > close:
            self._errors["close"] = self.error_class(["The close date should not be earlier than the start date."])
        if end and close and end > close:
            self._errors["close"] = self.error_class(["The close date should not be earlier than the end date."])

        return c


class NewTeachingBlockDetailsForm(bootstrap.ModelForm):
    class Meta:
        model = TeachingBlock
        exclude = ('name', 'year')


class TeachingBlockValidationForm(bootstrap.ModelForm):
    class Meta:
        model = TeachingBlock
        exclude = ('code',)


class NewQuizSpecificationForm(bootstrap.ModelForm):
    active = forms.BooleanField(widget=bootstrap.CheckboxInput(), required=False)
    class Meta:
        model = QuizSpecification
        exclude = ('slug', )


class QuestionQuizSpecificationForm(bootstrap.Form):
    specification = forms.ModelChoiceField(queryset=QuizSpecification.objects.all())


class EmailForm(bootstrap.Form):
    from_address = forms.CharField(widget=bootstrap.StaticControl())
    subject = forms.CharField(widget=bootstrap.TextInputWithAddon(add_on="[MedBank]", attrs={'class': 'span6'}))
    email = forms.CharField(widget=forms.Textarea(attrs={'class': 'span6'}))
    block = forms.ModelChoiceField(queryset=TeachingBlockYear.objects.all(), widget=forms.HiddenInput())


class CommentForm(bootstrap.ModelForm):
    creator = forms.ModelChoiceField(queryset=Student.objects.all(), widget=forms.HiddenInput())
    question = forms.ModelChoiceField(queryset=Question.objects.all(), widget=forms.HiddenInput())
    reply_to = forms.ModelChoiceField(required=False, queryset=Comment.objects.all(), widget=forms.HiddenInput())

    class Meta:
        model = Comment
        fields = '__all__'


class ReasonForFlaggingForm(bootstrap.ModelForm):
    body = forms.CharField(widget=forms.Textarea(), label="Reason")
    reason_type = forms.ChoiceField(choices=Reason.REASON_TYPES, widget=forms.HiddenInput())
    creator = forms.ModelChoiceField(queryset=Student.objects.all(), widget=forms.HiddenInput())

    class Meta:
        model = Reason
        exclude = ('related_object_id', 'related_object_content_type')

# class ReasonForFlaggingForm(bsforms.NewBootstrapForm):
#     reason = forms.CharField(widget=forms.Textarea())

class QuestionAttributesForm(bootstrap.ModelForm):
    exemplary_question = forms.BooleanField(widget=bootstrap.CheckboxInput(), label="This is an exemplary question for this block.", required=False)
    requires_special_formatting = forms.BooleanField(widget=bootstrap.CheckboxInput(), label="This question requires special formatting.", required=False)

    class Meta:
        model = Question
        exclude = ('body', 'options', 'answer', 'explanation', 'date_created', 'creator', 'approver', 'teaching_activity_year', 'status')


class SettingEditForm(SettingEditForm):
    main_text = forms.CharField(required=False)
    secondary_text = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        setting_instance = kwargs["instance"]
        kwargs['initial'].update({"main_text": setting_instance.main_text(), "secondary_text": setting_instance.secondary_text()})
        super(SettingEditForm, self).__init__(*args, **kwargs)

    class Meta(SettingEditForm.Meta):
        exclude = ['value',]


class QuestionForm(bootstrap.Form):
    question_queryset = Question.objects.filter(status=Question.APPROVED_STATUS)
    question_id = forms.ModelChoiceField(widget=forms.TextInput(), label="Question ID", queryset=question_queryset)
    questions_selected = forms.ModelMultipleChoiceField(widget=forms.MultipleHiddenInput(), queryset=question_queryset, required=False)


class ConfirmQuestionSelectionForm(bootstrap.Form):
    question_id = forms.ModelMultipleChoiceField(queryset=Question.objects.all())

class QuizTypeSelectionForm(bootstrap.Form):
    quiz_type = forms.ChoiceField(choices=QuizAttempt.QUIZ_TYPE_CHOICES, widget=bootstrap.ButtonGroup)


BOOLEAN_CHOICES = (
    (True, 'Yes'),
    (False, 'No'),
)

class CustomQuizSpecificationForm(bootstrap.Form):
    form_widget_width=2

    def __init__(self, *args, **kwargs):
        blocks = kwargs.pop("blocks", None)
        super(CustomQuizSpecificationForm, self).__init__(*args, **kwargs)
        self.block_fields = []
        for block in blocks:
            self.fields[block.name_for_form_fields()] = forms.IntegerField(label=block.name, required=False, min_value=0, localize=True)
            self.block_fields.append(block.name_for_form_fields())

        self.fields['repeat_questions'] = forms.TypedChoiceField(choices=BOOLEAN_CHOICES, coerce=lambda x: (x == "True"), widget=bootstrap.ButtonGroup, label="Do you want to see questions you've already answered?")

    def clean(self):
        c = self.cleaned_data

        # If none of the blocks have any cleaned data, the form is not valid.
        if all(block in c for block in self.block_fields) and all(not c[block] for block in self.block_fields):
            raise forms.ValidationError("Please enter a number of questions for at least one block.")

        return c


class PresetQuizSpecificationForm(bootstrap.Form):
    quiz_specification = forms.ModelChoiceField(queryset=QuizSpecification.objects.all(), to_field_name="slug", widget=forms.HiddenInput())

class QuestionApprovalForm(bootstrap.ModelForm):
    exemplary_question = forms.TypedChoiceField(choices=BOOLEAN_CHOICES, coerce=lambda x: (x == "True"), widget=bootstrap.ButtonGroup)

    new_status = forms.TypedChoiceField(choices=Question.STATUS_TO_ACTION, widget=bootstrap.ButtonGroup, coerce=int)

    def __init__(self, *args, **kwargs):
        super(QuestionApprovalForm, self).__init__(*args, **kwargs)
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


class TeachingBlockActivityUploadForm(bootstrap.Form):
    upload_file = forms.FileField(label="Activity file")


class QuestionWritingPeriodUploadForm(bootstrap.Form):
    upload_file = forms.FileField(label="Activity file")


class AssignPreviousActivityForm(bootstrap.ModelForm):
    previous_activity = forms.ModelChoiceField(to_field_name="reference_id", widget=forms.TextInput(), queryset=TeachingActivity.objects.all(), help_text="Type in the reference ID of the previous activity to assign it as the old version of the current activity.")

    def __init__(self, activity_queryset=None, activity_url=None, *args, **kwargs):
        super(AssignPreviousActivityForm, self).__init__(*args, **kwargs)
        if activity_queryset:
            self.fields['previous_activity'].queryset = activity_queryset

    class Meta:
        model = TeachingActivity
        exclude = ('name', 'activity_type', 'reference_id')


class TeachingBlockDownloadForm(bootstrap.Form):
    form_widget_width = 4
    form_label_width = 5

    QUESTION_TYPE = "question"
    ANSWER_TYPE = "answer"

    DOCUMENT_CHOICES = (
        (QUESTION_TYPE, 'Questions only'),
        (ANSWER_TYPE, 'Include answers'),
    )

    YEAR_CHOICES = ((datetime.datetime.now().year, datetime.datetime.now().year),)

    document_type = forms.ChoiceField(choices=DOCUMENT_CHOICES, widget=bootstrap.ButtonGroup(), label="Do you want the document to include answers?")
    years = forms.TypedMultipleChoiceField(coerce=lambda val: int(val), choices=YEAR_CHOICES, widget=bootstrap.ButtonGroup(multiple=True, vertical=True), label="For which years do you want to download questions?")

    def __init__(self, years=[], *args, **kwargs):
        if not years: raise ValueError("A teaching block is required to initialise this form.")

        super(TeachingBlockDownloadForm, self).__init__(*args, **kwargs)
        
        self.fields['years'].choices = years

class BlockFromYearChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, instance):
        return "%s" % instance.year

class YearSelectionForm(bootstrap.Form):
    year = BlockFromYearChoiceField(queryset=TeachingBlockYear.objects.all(), to_field_name="year", empty_label=None, widget=bootstrap.ButtonGroup(multiple=False, vertical=True))

    def __init__(self, teaching_block=None, *args, **kwargs):
        if not teaching_block or not isinstance(teaching_block, TeachingBlock):
            raise ValueError("YearSelectionForm requires a valid teaching block.")

        super(YearSelectionForm, self).__init__(*args, **kwargs)

        self.fields['year'].queryset = teaching_block.years.order_by('-year')


class StudentSelectionForm(bootstrap.Form):
    activity = forms.ModelChoiceField(queryset=TeachingActivity.objects.all(), widget=forms.HiddenInput())
    user = forms.ModelChoiceField(queryset=User.objects.select_related().order_by("username"), to_field_name="username", widget=forms.TextInput(), label="Unikey")

    def __init__(self, user_url="", *args, **kwargs):
        super(StudentSelectionForm, self).__init__(*args, **kwargs)
        if user_url:
            self.fields['user'].widget = bootstrap.Typeahead(prefetch_url=user_url)

class StudentLookupForm(bootstrap.Form):
    user = forms.ModelChoiceField(queryset=User.objects.select_related().order_by("username"), to_field_name="username", widget=forms.TextInput(), label="Unikey")

    def __init__(self, user_url="", *args, **kwargs):
        super(StudentLookupForm, self).__init__(*args, **kwargs)
        if user_url:
            self.fields['user'].widget = bootstrap.Typeahead(prefetch_url=user_url)

class DeleteQuestionWritingPeriodForm(bootstrap.Form):
    CONFIRMED = "true"
    NOT_CONFIRMED = "false"

    CONFIRMATION_CHOICES = (
        (CONFIRMED, "True"),
        (NOT_CONFIRMED, "False")
    )
    confirmation = forms.ChoiceField(widget=forms.HiddenInput(), choices=CONFIRMATION_CHOICES, initial=CONFIRMED)

