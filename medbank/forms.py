from __future__ import unicode_literals

from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

import bootstrap

from .models import Setting
from questions import models


class BootstrapAuthenticationForm(bootstrap.Form, AuthenticationForm):
    username = forms.CharField(max_length=254, widget=bootstrap.TextInputWithAddon(attrs={'class':'input-lg', 'placeholder':'Unikey'}, post_add_on="@uni.sydney.edu.au"))
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput(attrs={'class':'input-lg', 'placeholder':'Password'}))
    def __init__(self, *args, **kwargs):
        super(BootstrapAuthenticationForm, self).__init__(*args, **kwargs)
        self.required = False
        if any(fs.field.required for fs in self):
                self.required = True
        self.is_horizontal = True


class StudentCreationForm(bootstrap.ModelForm, UserCreationForm):
    username = forms.RegexField(label=_("Unikey"), max_length=20,
        regex=r'^(([a-z]{4}\d{4})|([a-z]+))$',
        help_text=_("We'll use your Unikey to email the questions to you when they're ready."),
        error_message=_("Your unikey should be either four lowercase letters followed by four digits, or all lowercase letters."),
        widget=bootstrap.TextInputWithAddon(post_add_on="@uni.sydney.edu.au"),
    )
    stage = forms.ModelChoiceField(queryset=models.Stage.objects.all(), empty_label=None)

    def clean_username(self):
        d = self.cleaned_data['username']

        r = self.fields['username'].regex
        if not r.match(d):
            raise(ValidationError(self.fields['username'].error_messages['invalid']))

        return d

class PasswordResetRequestForm(bootstrap.Form):
    username = forms.RegexField(max_length=20,
        regex=r'^([a-z]{4}\d{4})|[a-z]+$',
        error_messages={
            'invalid': _("Your unikey should be either four lowercase letters followed by four digits, or all lowercase letters")
        },
        label='Unikey'
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            u = User.objects.get(username__exact=username)
        except User.DoesNotExist:
            raise forms.ValidationError(_("That user could not be found."))

        self.cleaned_data['user'] = u

        return username

class PasswordResetForm(bootstrap.Form):
    password1 = forms.CharField(
        label=_('New password'),
        widget=forms.PasswordInput(),
    )
    password2 = forms.CharField(
        label=_('Password confirmation'),
        widget=forms.PasswordInput(),
    )

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1', '')
        password2 = self.cleaned_data['password2']
        if not password1 == password2:
            raise forms.ValidationError(_('The passwords you entered do not match. Please try again.'))


class FeedbackForm(bootstrap.Form):
    feedback = forms.CharField(widget=forms.Textarea(attrs={'class': 'span6'}))


class StageSelectionForm(bootstrap.Form):
    stage = forms.ModelChoiceField(queryset=models.Stage.objects.all(), empty_label=None, widget=forms.Select(attrs={'class':'input-lg'}))


class SettingEditForm(bootstrap.ModelForm):
    class Meta:
        model = Setting
        fields = '__all__'

