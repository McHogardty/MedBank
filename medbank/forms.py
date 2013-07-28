from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django import forms

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
    stage = forms.ModelChoiceField(queryset=models.Stage.objects.all(), empty_label=None)
