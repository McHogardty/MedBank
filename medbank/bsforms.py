from django import forms
from django_localflavor_au import forms as auforms
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from django.forms.util import flatatt
from django.utils.html import format_html
from django.utils.encoding import force_text

# Required for _html_output. Should go away in the future.
from django.utils import six

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


class BoundField(forms.forms.BoundField):
    def css_classes(self, extra_classes=None):
        if hasattr(extra_classes, 'split'):
            extra_classes = extra_classes.split()
        extra_classes = set(extra_classes or [])
        extra_classes.add("form-group")
        return super(BoundField, self).css_classes(extra_classes)

    def label_tag(self, contents=None, attrs=None):
        if self.field.widget.__class__.__name__ in ["CheckboxInput",]:
            return ""

        attrs = attrs or {}
        c = attrs['class'].split() if 'class' in attrs else []
        # if attrs:
        #     if 'class' in attrs:
        #         c = attrs['class'].split()
        #         c.append('control-label')
        #         c.append('col-md-2')
        #         c.append()
        #         attrs['class'] = " ".join(c)
        #     else:
        #         attrs['class'] = 'control-label col-md-2'
        # else:
        #     attrs = {'class': 'control-label col-md-2'}
        c.append('control-label')
        c.append('col-md-2')
        attrs['class'] = " ".join(c)
        return super(BoundField, self).label_tag(contents, attrs)

    def size_classes(self):
        classes = ['col-md-6']
        if self.field.widget.__class__.__name__ in ["CheckboxInput",]:
            classes.append('col-md-offset-2')
        return " ".join(classes)

    def as_widget(self, widget=None, attrs=None, only_initial=False):
        if self.field.widget.__class__.__name__ in ["RadioSelect", "ClearableFileInput", "CheckboxInput"]:
            self.field.widget.label = self.label
            return super(BoundField, self).as_widget(widget, attrs, only_initial)

        widget = widget or self.field.widget
        a = widget.attrs

        if 'class' in a:
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

    def _html_output(self, normal_row, error_row, row_ender, help_text_html, errors_on_separate_row):
        "Helper function for outputting HTML. Used by as_table(), as_ul(), as_p()."
        top_errors = self.non_field_errors() # Errors that should be displayed above all fields.
        output, hidden_fields = [], []

        for name, field in self.fields.items():
            html_class_attr = ''
            size_class_attr = ''
            bf = self[name]
            bf_errors = self.error_class([conditional_escape(error) for error in bf.errors]) # Escape and cache in local variable.
            if bf.is_hidden:
                if bf_errors:
                    top_errors.extend(['(Hidden field %s) %s' % (name, force_text(e)) for e in bf_errors])
                hidden_fields.append(six.text_type(bf))
            else:
                # Create a 'class="..."' atribute if the row should have any
                # CSS classes applied.
                css_classes = bf.css_classes()
                if css_classes:
                    html_class_attr = ' class="%s"' % css_classes

                size_classes = bf.size_classes()
                if size_classes:
                    size_class_attr = ' class="%s"' % size_classes

                if errors_on_separate_row and bf_errors:
                    output.append(error_row % force_text(bf_errors))

                if bf.label:
                    label = conditional_escape(force_text(bf.label))
                    # Only add the suffix if the label does not end in
                    # punctuation.
                    if self.label_suffix:
                        if label[-1] not in ':?.!':
                            label = format_html('{0}{1}', label, self.label_suffix)
                    label = bf.label_tag(label) or ''
                else:
                    label = ''

                help_text = force_text(field.help_text) if field.help_text else ""
                messages = help_text_html % help_text

                error_text = force_text(bf_errors) if bf_errors else ""
                if field.help_text and error_text:
                    error_text += " "
                messages = messages % {'errors': error_text}


                output.append(normal_row % {
                    'errors': force_text(bf_errors),
                    'label': force_text(label),
                    'field': six.text_type(bf),
                    # 'help_text': help_text,
                    'html_class_attr': html_class_attr,
                    'size_class_attr': size_class_attr,
                    'messages': messages
                })

        if top_errors:
            output.insert(0, error_row % force_text(top_errors))

        if hidden_fields: # Insert any hidden fields in the last row.
            str_hidden = ''.join(hidden_fields)
            if output:
                last_row = output[-1]
                # Chop off the trailing row_ender (e.g. '</td></tr>') and
                # insert the hidden fields.
                if not last_row.endswith(row_ender):
                    # This can happen in the as_p() case (and possibly others
                    # that users write): if there are only top errors, we may
                    # not be able to conscript the last row for our purposes,
                    # so insert a new, empty row.
                    last_row = (normal_row % {'errors': '', 'label': '',
                                              'field': '', 'help_text':'',
                                              'html_class_attr': html_class_attr})
                    output.append(last_row)
                output[-1] = last_row[:-len(row_ender)] + str_hidden + row_ender
            else:
                # If there aren't any rows in the output, just append the
                # hidden fields.
                output.append(str_hidden)
        return mark_safe('\n'.join(output))

    def as_bootstrap(self):
        return self._html_output(
            normal_row="<div%(html_class_attr)s>%(label)s<div%(size_class_attr)s>%(field)s %(messages)s</div></div>",
            error_row="<span class='help-block'>%s</span>",
            row_ender="</div>",
            help_text_html="<span class='help-block'>%%(errors)s%s</span>",
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
            value = 'None'
        final_attrs = self.build_attrs(attrs, name=name, type='hidden')
        if value != '':
            value = force_text(self._format_value(value))
            final_attrs['value'] = value

        return format_html('<p class="form-control-static">{1}<input{0}/></p>', flatatt(final_attrs), value)


class RichTextarea(forms.Textarea):
    def render(self, name, value, attrs=None):
        area = super(RichTextarea, self).render(name, value, attrs)

        toolbar = """
        <div class="btn-toolbar" style="margin-bottom:10px;">
            <div class="btn-group">
                <button type="button" class="btn btn-default" data-event="bold">
                    <i class="fa fa-bold"></i>
                </button>
                <button type="button" class="btn btn-default" data-event="italic">
                    <i class="fa fa-italic"></i>
                </button>
            </div>
            <div class="btn-group note-style">
                <button type="button" class="btn btn-default" data-event="insertUnorderedList">
                    <i class="fa fa-list-ul"></i>
                </button>
                <button type="button" class="btn btn-default" data-event="insertOrderedList">
                    <i class="fa fa-list-ol"></i>
                </button>
            </div>
        </div><div class="form-control" style="resize:both;overflow:auto;height:200px;" contenteditable="true"></div>{0}"""

        return format_html(toolbar, area)


class TextInputWithAddon(forms.TextInput):
    def __init__(self, add_on=None, post_add_on=None, **kwargs):
        self.add_on = add_on
        self.post_add_on = post_add_on
        super(TextInputWithAddon, self).__init__(**kwargs)

    def render(self, name, value, attrs=None):
        i = super(TextInputWithAddon, self).render(name, value, attrs)
        if self.add_on and not self.post_add_on:
            i = format_html('<div class="input-group"><span class="input-group-addon">{0}</span>{1}</div>', self.add_on, i)
        if self.post_add_on and not self.add_on:
            i = format_html('<div class="input-group">{0}<span class="input-group-addon">{1}</span></div>', i, self.post_add_on)
        return i

class CheckboxInput(forms.CheckboxInput):
    def render(self, name, value, attrs=None):
        checkbox_input = super(CheckboxInput, self).render(name, value, attrs)
        checkbox = """
        <div class="checkbox">
            <label>
                {0} {1}
            </label>
        </div>
        """
        return format_html(checkbox, checkbox_input, self.label)

