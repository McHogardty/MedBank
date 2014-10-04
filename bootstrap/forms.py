from __future__ import unicode_literals

from django import forms
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.utils.encoding import force_text

# Required for _html_output. Should go away in the future.
from django.utils import six


__all__ = ('Form', 'ModelForm')


class BoundField(forms.forms.BoundField):
    def __init__(self, form, field, name, widget_size=6, label_size=2):
        super(BoundField, self).__init__(form, field, name)

        self.widget_size = widget_size
        self.label_size = label_size

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
        c.append('control-label')
        c.append('col-md-%s' % self.label_size)
        attrs['class'] = " ".join(c)
        return super(BoundField, self).label_tag(contents, attrs)

    def size_classes(self):
        classes = ['col-md-%s' % self.widget_size]
        if self.field.widget.__class__.__name__ in ["CheckboxInput",]:
            classes.append('col-md-offset-%s' % self.label_size)
        return " ".join(classes)

    def as_widget(self, widget=None, attrs=None, only_initial=False):
        if self.field.widget.__class__.__name__ in ["ButtonGroupWithToggle", "RadioSelect", "ClearableFileInput", "CheckboxInput"]:
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

        return super(BoundField, self).as_widget(widget, a, only_initial)


class NewErrorList(forms.util.ErrorList):
    def __unicode__(self):
        return self.as_paragraph()

    def as_paragraph(self):
        if not self: return ''

        return ' '.join(['%s' % force_text(e) for e in self])


class BootstrapFormMixin(object):
    error_css_class = "has-error"

    # Maximum 12. The width of the form in bootstrap column units.
    total_form_width = 8
    # The width of the form widgets in bootstrap column units. Cannot exceed total_form_width
    form_widget_width = 6
    form_label_width = 0
    def __init__(self, *args, **kwargs):
        super(BootstrapFormMixin, self).__init__(*args, **kwargs)
        self.error_class = NewErrorList
        self.needs_multipart = any(isinstance(field, forms.FileField) for field in self.fields.values())
        self.required = any(f.required for f in self.fields.values())

        for f in self:
            if isinstance(f.field, forms.models.ModelChoiceField) and not \
                    hasattr(self, 'get_%s_display' % (f.html_name, )):
                self.add_model_get_FOO_display_method(f)

    def add_model_get_FOO_display_method(self, f):
        def model_get_FOO_display_method():
            for k, c in f.field.choices:
                if f.value() == unicode(k):
                    return c
        model_get_FOO_display_method.__name__ = b"get_%s_display" % (f.name,)
        setattr(self, model_get_FOO_display_method.__name__, model_get_FOO_display_method)

    def __str__(self):
        return self.as_bootstrap()

    def __getitem__(self, name):
        try:
            field = self.fields[name]
        except KeyError:
            raise KeyError('Key %r not found in Form' % name)
        if self.form_widget_width >= self.total_form_width:
            raise ValueError("The form widget width should be less than the total form width.")
        if self.total_form_width > 12:
            raise ValueError("The form width cannot be larger than 12.")
        self.form_label_width = self.form_label_width or (self.total_form_width - self.form_widget_width)
        return BoundField(self, field, name, widget_size=self.form_widget_width, label_size=self.form_label_width)

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
                                              'html_class_attr': html_class_attr,
                                              'size_class_attr': size_class_attr,
                                              'messages': '',})
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
            error_row="<p class='text-danger'>%s</p>",
            row_ender="</div>",
            help_text_html="<span class='help-block'>%%(errors)s%s</span>",
            errors_on_separate_row=False
        )


class Form(BootstrapFormMixin, forms.Form):
    pass


class ModelForm(BootstrapFormMixin, forms.ModelForm):
    pass
