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


class BootstrapCharField(forms.fields.CharField):
    def widget_attrs(self, widget):
        attrs = super(BootstrapCharField, self).widget_attrs(widget)
        if self.required:
            if 'data-validate' in attrs:
                attrs['data-validate'] += u" required"
            else:
                attrs.update({'data-validate': u"required"})
        return attrs


class BootstrapEmailField(forms.fields.EmailField):
    def widget_attrs(self, widget):
        attrs = super(BootstrapEmailField, self).widget_attrs(widget)
        if self.required:
            if 'data-validate' in attrs:
                attrs['data-validate'] += u" required"
            else:
                attrs.update({'data-validate': u"required"})
        if 'data-validate' in attrs:
            attrs['data-validate'] += u" email"
        else:
            attrs.update({'data-validate': u'email', })
        return attrs


class BootstrapTypedChoiceField(forms.fields.TypedChoiceField):
    def widget_attrs(self, widget):
        attrs = super(BootstrapTypedChoiceField, self).widget_attrs(widget)
        if self.required:
            if 'data-validate' in attrs:
                attrs['data-validate'] += u" required"
            else:
                attrs.update({'data-validate': u"required"})
        return attrs


class BootstrapAUPhoneNumberField(auforms.AUPhoneNumberField):
    def widget_attrs(self, widget):
        attrs = super(BootstrapAUPhoneNumberField, self).widget_attrs(widget)
        if self.required:
            if 'data-validate' in attrs:
                attrs['data-validate'] += u" required"
            else:
                attrs.update({'data-validate': u"required"})
        return attrs


class BootstrapAUPostCodeField(auforms.AUPostCodeField):
    def widget_attrs(self, widget):
        attrs = super(BootstrapAUPostCodeField, self).widget_attrs(widget)
        if self.required:
            if 'data-validate' in attrs:
                attrs['data-validate'] += u" required"
            else:
                attrs.update({'data-validate': u"required"})
        return attrs


class BootstrapDateField(forms.DateField):
    def widget_attrs(self, widget):
        attrs = super(BootstrapDateField, self).widget_attrs(widget)
        if 'class' in attrs:
            attrs['class'] += u' datepicker'
        else:
            attrs['class'] = u'datepicker'

        return attrs


class BootstrapCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        if value is None:
            value = []
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)
        output = []
        # Normalize to strings
        str_values = set([force_unicode(v) for v in value])
        for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = u' for="%s"' % final_attrs['id']
            else:
                label_for = ''

            cb = forms.CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
            option_value = force_unicode(option_value)
            rendered_cb = cb.render(name, option_value)
            option_label = conditional_escape(force_unicode(option_label))
            output.append(u'<label class="checkbox"%s>%s %s</label>' % (label_for, rendered_cb, option_label))
        return mark_safe(u'\n'.join(output))

class BootstrapField(forms.Field):
    def widget_attrs(self, widget):
        if 'class' in widget.attrs:
            l = widget.attrs['class'].split()
            l.append("form-control")
            widget.attrs['class'] = " ".join(l)
        return super(BootstrapField, self).widget_attrs(widget)

class RegexField(BootstrapField, forms.RegexField):
    pass

class CharField(BootstrapField, forms.CharField):
    pass


class WYSIWYGArea(forms.Textarea):
    def render(self, name, value, attrs=None):
        if value is None: value = ''
        final_attrs = self.build_attrs(attrs, name=name)
        return format_html('<textarea{0}>\r\n{1}</textarea><div id="editor" class="span6"></div>',
                           flatatt(final_attrs),
                           force_text(value))