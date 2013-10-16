from django import forms
from django_localflavor_au import forms as auforms
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from django.forms.util import flatatt
from django.utils.html import format_html
from django.utils.encoding import force_text

from itertools import chain


class Fieldset:
    def __init__(self, form, fields, legend, name=None, description=None):
        self.form = form
        self.fields = fields
        self.legend = legend
        self.name = name
        self.description = description
        self.required = False
        if any(self.form.fields[f].required for f in self.fields):
            self.required = True

    def __iter__(self):
        for f in self.fields:
            field = self.form.fields[f]
            yield forms.forms.BoundField(self.form, field, f)

    def __len__(self):
        return len(self.fields)

    def auto_id(self):
        return u"id_%s" % (self.name,)


class BootstrapForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(BootstrapForm, self).__init__(*args, **kwargs)
        self.generate_fieldsets()
        self.required = False
        if self.fieldsets:
            if any(fs.required for fs in self.fieldsets):
                self.required = True
        else:
            if any(fs.required for fs in self):
                self.required = True

    def generate_fieldsets(self):
        meta = getattr(self, 'Meta', None)
        self._fieldsets = []
        try:
            fs = meta.fieldsets
        except AttributeError:
            return
        for name, properties in fs:
            desc = properties.get('description', None)
            self._fieldsets.append(Fieldset(self, properties['fields'], properties['legend'], name, desc))

    def fieldsets(self):
        for fs in self._fieldsets:
            yield fs
    fieldsets = property(fieldsets)


class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(BootstrapModelForm, self).__init__(*args, **kwargs)
        self.generate_fieldsets()
        self.required = False
        if self.fieldsets:
            if any(fs.required for fs in self.fieldsets):
                self.required = True
        else:
            if any(fs.required for fs in self):
                self.required = True

        for f in self:
            if isinstance(f.field, forms.models.ModelChoiceField) and not \
                    hasattr(self, 'get_%s_display' % (f.html_name, )):
                self.add_model_get_FOO_display_method(f)

        print "Form init"

    def add_model_get_FOO_display_method(self, f):
        def model_get_FOO_display_method():
            for k, c in f.field.choices:
                if f.value() == unicode(k):
                    return c
        model_get_FOO_display_method.__name__ = "get_%s_display" % (f.name,)
        setattr(self, model_get_FOO_display_method.__name__, model_get_FOO_display_method)

    def generate_fieldsets(self):
        meta = getattr(self, 'Meta', None)
        self._fieldsets = []
        try:
            fs = meta.fieldsets
        except AttributeError:
            return
        for name, properties in fs:
            desc = properties.get('description', None)
            self._fieldsets.append(Fieldset(self, properties['fields'], properties['legend'], name, desc))

    def fieldsets(self):
        for fs in self._fieldsets:
            yield fs
    fieldsets = property(fieldsets)


class BootstrapHorizontalModelForm(BootstrapModelForm):
    def __init__(self, *args, **kwargs):
        super(BootstrapHorizontalModelForm, self).__init__(*args, **kwargs)
        self.is_horizontal = True


class BootstrapInlineModelForm(BootstrapModelForm):
    def __init__(self, *args, **kwargs):
        super(BootstrapInlineModelForm, self).__init__(*args, **kwargs)
        self.is_inline = True


class BootstrapHorizontalForm(BootstrapForm):
    def __init__(self, *args, **kwargs):
        super(BootstrapHorizontalForm, self).__init__(*args, **kwargs)
        self.is_horizontal = True


class BootstrapInlineForm(BootstrapForm):
    def __init__(self, *args, **kwargs):
        super(BootstrapInlineForm, self).__init__(*args, **kwargs)
        self.is_inline = True


class BoundField(forms.forms.BoundField):
    def css_classes(self, extra_classes=None):
        if hasattr(extra_classes, 'split'):
            extra_classes = extra_classes.split()
        extra_classes = set(extra_classes or [])
        extra_classes.add("form-group")
        c = super(BoundField, self).css_classes(extra_classes)
        return c

    def label_tag(self, contents=None, attrs=None):
        if attrs:
            if 'class' in attrs:
                c = attrs['class'].split()
                c.append('control-label')
                c.append('col-md-2')
                attrs['class'] = " ".join(c)
            else:
                attrs['class'] = 'control-label col-md-2'
        else:
            attrs = {'class': 'control-label col-md-2'}

        return super(BoundField, self).label_tag(contents, attrs)

    def as_widget(self, widget=None, attrs=None, only_initial=False):
        if widget:
            a = widget.attrs
        else:
            a = self.field.widget.attrs

        if a and 'class' in a:
            c = a['class'].split()
            c.append('form-control')
            a['class'] = " ".join(c)
        else:
            a.update({'class': 'form-control'})

        return super(BoundField, self).as_widget(widget, attrs, only_initial)


class NewErrorList(forms.util.ErrorList):
    def __unicode__(self):
        return self.as_paragraph()

    def as_paragraph(self):
        if not self: return ''

        return ' '.join(['%s' % force_text(e) for e in self])


class NewBootstrapFormMixin(object):
    error_css_class = "has-error"
    def __init__(self, *args, **kwargs):
        super(NewBootstrapFormMixin, self).__init__(*args, **kwargs)
        self.error_class = NewErrorList

    def __str__(self):
        return self.as_bootstrap()

    def __getitem__(self, name):
        try:
            field = self.fields[name]
        except KeyError:
            raise KeyError('Key %r not found in Form' % name)
        return BoundField(self, field, name)

    def as_bootstrap(self):
        return self._html_output(
            normal_row="<div%(html_class_attr)s>%(label)s<div class='col-md-6'>%(field)s<span class='help-block'>%(errors)s %(help_text)s</span></div></div>",
            error_row="<span class='help-block'>%s</span>",
            row_ender="</div>",
            help_text_html="%s",
            errors_on_separate_row=False
        )


class NewBootstrapForm(NewBootstrapFormMixin, BootstrapForm):
    pass


class NewBootstrapModelForm(NewBootstrapFormMixin, BootstrapModelForm):
    pass


class StaticControl(forms.Widget):
    def _format_value(self, value):
        return value

    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, name=name, type='hidden')
        if value != '':
            value = force_text(self._format_value(value))
            final_attrs['value'] = value

        return format_html('<p class="form-control-static">{1}<input{0}/></p>', flatatt(final_attrs), value)


class WYSIWYGArea(forms.Textarea):
    def render(self, name, value, attrs=None):
        if value is None: value = ''
        final_attrs = self.build_attrs(attrs, name=name)
        return format_html('<textarea{0}>\r\n{1}</textarea><div id="editor" class="span6"></div>',
                           flatatt(final_attrs),
                           force_text(value))
