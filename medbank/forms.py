from django.contrib.auth.forms import AuthenticationForm


import bsforms


class BootstrapAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(BootstrapAuthenticationForm, self).__init__(self, *args, **kwargs)
        self.required = False
        for fs in self:
            print fs.__dict__
        if any(fs.field.required for fs in self):
                self.required = True
        self.is_horizontal = True
