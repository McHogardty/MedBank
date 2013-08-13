from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django import forms
from django.utils.translation import ugettext, ugettext_lazy as _
from django.contrib.auth.models import User

import bsforms

from questions import models


class BootstrapAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(BootstrapAuthenticationForm, self).__init__(self, *args, **kwargs)
        self.required = False
        if any(fs.field.required for fs in self):
                self.required = True
        self.is_horizontal = True


class StudentCreationForm(UserCreationForm):
    username = forms.RegexField(label=_("Unikey"), max_length=20,
        regex=r'^([a-z]{4}\d{4})|[a-z]+$',
        help_text=_("We'll use your Unikey to email the questions to you when they're ready."),
        error_messages={
            'invalid': _("Your unikey should be either four lowercase letters followed by four digits, or all lowercase letters")}
    )
    stage = forms.ModelChoiceField(queryset=models.Stage.objects.all(), empty_label=None)


class PasswordResetRequestForm(bsforms.BootstrapHorizontalForm):
    username = forms.RegexField(max_length=20,
        regex=r'^([a-z]{4}\d{4})|[a-z]+$',
        error_messages={
            'invalid': _("Your unikey should be either four lowercase letters followed by four digits, or all lowercase letters")}
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            u = User.objects.get(username__exact=username)
        except User.DoesNotExist:
            raise forms.ValidationError(_("That user could not be found."))

        self.cleaned_data['user'] = u

        return username

class PasswordResetForm(bsforms.BootstrapHorizontalForm):
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
