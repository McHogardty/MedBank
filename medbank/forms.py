from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django import forms
from django.utils.translation import ugettext, ugettext_lazy as _

import bsforms

from questions import models


class BootstrapAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(BootstrapAuthenticationForm, self).__init__(self, *args, **kwargs)
        self.required = False
        for fs in self:
            print fs.__dict__
        if any(fs.field.required for fs in self):
                self.required = True
        self.is_horizontal = True


class StudentCreationForm(UserCreationForm):
    username = forms.RegexField(label=_("Unikey"), max_length=8,
        regex=r'^[a-z]{4}\d{4}$',
        help_text=_("We'll use your Unikey to email the questions to you when they're ready."),
        error_messages={
            'invalid': _("Your unikey should be four lowercase letters followed by four digits.")}
    )
    stage = forms.ModelChoiceField(queryset=models.Stage.objects.all(), empty_label=None)
