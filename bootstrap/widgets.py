from __future__ import unicode_literals

from django import forms
from django.utils.datastructures import MultiValueDict, MergeDict
from django.forms.utils import flatatt
from django.utils.html import format_html, format_html_join
from django.utils.encoding import force_text
from django.utils import datetime_safe, formats


__all__ = ("StaticControl", "TextInputWithAddon", "CheckboxInput", "ButtonGroup", "Typeahead", "DatepickerInput", "RichTextarea", "RichTextInputWithAddon",
    "CSSCheckboxSelectMultiple", "CSSRadioSelect",
    )


class StaticControl(forms.Widget):
    def _format_value(self, value):
        if hasattr(value, 'strftime'):
            value = datetime_safe.new_date(value)
            return value.strftime(formats.get_format('DATE_INPUT_FORMATS')[0])
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
        i = forms.HiddenInput().render(name, value, attrs)
        classes = attrs.get('class', [])
        if classes:
            classes = classes.split()
        classes.append("summernote")
        classes.append("summernote-textarea")
        attrs['class'] = " ".join(classes)
        return format_html('<div class="{0}" data-field="{2}"></div>{1}', attrs['class'], i, name)


class RichTextInput(forms.TextInput):
    def render(self, name, value, attrs=None):
        i = forms.HiddenInput().render(name, value, attrs)
        attrs = attrs.copy()
        classes = attrs.get('class', [])
        if classes:
            classes = classes.split()
        classes.append("summernote")
        classes.append("summernote-textinput")
        attrs['class'] = " ".join(classes)
        return format_html('{1}<div class="{0}" data-field="{2}"></div>', attrs['class'], i, name)


class RichTextInputWithAddon(RichTextInput):
    def __init__(self, add_on=None, post_add_on=None, group_class="", **kwargs):
        self.add_on = add_on
        self.post_add_on = post_add_on
        self.group_class = ""
        super(RichTextInputWithAddon, self).__init__(**kwargs)

    def render(self, name, value, attrs=None):
        classes = ['input-group', ]
        if self.group_class:
            classes += self.group_class.split()

        i = super(RichTextInputWithAddon, self).render(name, value, attrs)
        input_group_attrs = {'class': " ".join(classes)}
        if self.add_on and not self.post_add_on:
            i = format_html('<div{0}><span class="input-group-addon">{1}</span>{2}</div>', flatatt(input_group_attrs), self.add_on, i)
        if self.post_add_on and not self.add_on:
            i = format_html('<div{0}>{1}<span class="input-group-addon">{2}</span></div>', flatatt(input_group_attrs), i, self.post_add_on)
        return i


class TextInputWithAddon(forms.TextInput):
    def __init__(self, add_on=None, post_add_on=None, group_class="", **kwargs):
        self.add_on = add_on
        self.post_add_on = post_add_on
        self.group_class = ""
        super(TextInputWithAddon, self).__init__(**kwargs)

    def render(self, name, value, attrs=None):
        classes = ['input-group', ]
        if self.group_class:
            classes += self.group_class.split()

        i = super(TextInputWithAddon, self).render(name, value, attrs)
        input_group_attrs = {'class': " ".join(classes)}
        if self.add_on and not self.post_add_on:
            i = format_html('<div{0}><span class="input-group-addon">{1}</span>{2}</div>', flatatt(input_group_attrs), self.add_on, i)
        if self.post_add_on and not self.add_on:
            i = format_html('<div{0}>{1}<span class="input-group-addon">{2}</span></div>', flatatt(input_group_attrs), i, self.post_add_on)
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


class CSSCheckboxInput(forms.CheckboxInput):
    def render(self, name, value, attrs=None):
        checkbox_input = super(CSSCheckboxInput, self).render(name, value, attrs)
        final_attrs = self.build_attrs(attrs)
        checkbox = """
        <div class="mb-checkbox">
            {0}
            <label for="{2}">{1}</label>
        </div>
        """
        id_string = final_attrs.get('id', 'id_%s' % name)

        return format_html(checkbox, checkbox_input, self.label, id_string)


class CSSCheckboxChoiceInput(forms.widgets.CheckboxChoiceInput):
    def render(self, name=None, value=None, attrs=None, choices=()):
        if self.id_for_label:
            label_for = format_html(' for="{}"', self.id_for_label)
        else:
            label_for = ''
        attrs = dict(self.attrs, **attrs) if attrs else self.attrs
        return format_html (
            '{1}<label{0}>{2}</label>', label_for, self.tag(attrs), self.choice_label
        )


class CSSCheckboxInputRenderer(forms.widgets.CheckboxFieldRenderer):
    choice_input_class = CSSCheckboxChoiceInput
    outer_html = '{content}'
    inner_html = '<div class="mb-checkbox">{choice_value}</div>'


class CSSCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    renderer = CSSCheckboxInputRenderer


class CSSRadioChoiceInput(forms.widgets.RadioChoiceInput):
    def render(self, name=None, value=None, attrs=None, choices=()):
        if self.id_for_label:
            label_for = format_html(' for="{}"', self.id_for_label)
        else:
            label_for = ''
        attrs = dict(self.attrs, **attrs) if attrs else self.attrs
        return format_html (
            '{1}<label{0}>{2}</label>', label_for, self.tag(attrs), self.choice_label
        )


class CSSRadioInputRenderer(forms.widgets.RadioFieldRenderer):
    choice_input_class = CSSRadioChoiceInput
    outer_html = '{content}'
    inner_html = '<div class="mb-radio">{choice_value}</div>'


class CSSRadioSelect(forms.RadioSelect):
    renderer = CSSRadioInputRenderer


class RadioInputLikeButton(forms.widgets.RadioChoiceInput):
    def render(self, name=None, value=None, attrs=None, choices=()):
        choice_label = force_text(self.choice_label)

        label_classes = ["btn", "btn-default"]
        if self.is_checked(): label_classes.append("active")

        label_class = " ".join(label_classes)
        return format_html('<label{0}>{1} {2}</label>', flatatt({'class': label_class}), self.tag(), choice_label)


class CheckboxInputAsButton(forms.widgets.RadioChoiceInput):
    def tag(self):
        if 'id' in self.attrs:
            self.attrs['id'] = '%s_%s' % (self.attrs['id'], self.index)
        final_attrs = dict(self.attrs, type='checkbox', name=self.name, value=self.choice_value)
        if self.is_checked():
            final_attrs['checked'] = 'checked'
        return format_html('<input{0} />', flatatt(final_attrs))

    def render(self, name=None, value=None, attrs=None, choices=()):
        choice_label = force_text(self.choice_label)

        label_classes = ["btn", "btn-default"]
        if self.is_checked(): label_classes.append("active")

        label_class = " ".join(label_classes)
        return format_html('<label{0}>{1} {2}</label>', flatatt({'class': label_class}), self.tag(), choice_label)

class BaseButtonGroupRenderer(forms.widgets.RadioFieldRenderer):
    vertical = False

    def get_input(self, choice, index):
        pass

    def __iter__(self):
        for i, choice in enumerate(self.choices):
            yield self.get_input(choice, i)

    def __getitem__(self, idx):
        choice = self.choices[idx]
        return self.get_input(choice, idx)

    def render(self):
        radio_fields = format_html_join('\n', '{0}', [(force_text(w),) for w in self])
        attributes = {"data-toggle": "buttons"}
        attributes['class'] = "btn-group-vertical" if self.vertical else "btn-group"
        return format_html('<div{0} data-toggle="buttons">\n{1}\n</div>', flatatt(attributes), radio_fields)


class ButtonGroupCheckboxToggleRenderer(BaseButtonGroupRenderer):
    def get_input(self, choice, index):
        string_choice = force_text(choice[0])
        value = string_choice if string_choice in self.value else None
        return CheckboxInputAsButton(self.name, value, self.attrs.copy(), choice, index)


class ButtonGroupRadioToggleRenderer(BaseButtonGroupRenderer):
    def get_input(self, choice, index):
        return RadioInputLikeButton(self.name, self.value, self.attrs.copy(), choice, index)


class VerticalButtonGroupCheckboxToggleRenderer(ButtonGroupCheckboxToggleRenderer):
    vertical = True


class VerticalButtonGroupRadioToggleRenderer(ButtonGroupRadioToggleRenderer):
    vertical = True


class ButtonGroup(forms.RadioSelect):
    def __init__(self, multiple=False, vertical=False, *args, **kwargs):
        self.multiple = multiple
        if multiple:
            if vertical:
                self.renderer = VerticalButtonGroupCheckboxToggleRenderer
            else:
                self.renderer = ButtonGroupCheckboxToggleRenderer
        else:
            if vertical:
                self.renderer = VerticalButtonGroupRadioToggleRenderer
            else:
                self.renderer = ButtonGroupRadioToggleRenderer
        return super(ButtonGroup, self).__init__(*args, **kwargs)

    def value_from_datadict(self, data, files, name):
        if self.multiple and isinstance(data, (MultiValueDict, MergeDict)):
            return data.getlist(name)
        return data.get(name, None)

class Typeahead(forms.TextInput):
    def __init__(self, prefetch_url="", *args, **kwargs):
        self.prefetch_url = prefetch_url

        super(Typeahead, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None):
        class_attr = attrs.get("class", "").split()
        class_attr.append("typeahead")
        attrs['class'] = " ".join(class_attr)
        if self.prefetch_url:
            attrs['data-prefetch'] = self.prefetch_url
        return super(Typeahead, self).render(name, value, attrs=attrs)

    class Media:
        css = {
            'all': ('medbank/css/typeahead.custom.css', )
        }
        js = ('medbank/js/typeahead.bundle.min.js', 'medbank/js/widgets.js')


class DatepickerInput(forms.DateInput):
    def render(self, name, value, attrs=None):
        class_attr = attrs.get("class", "").split()
        class_attr.append("datepicker-input")
        attrs['class'] = " ".join(class_attr)
        return super(DatepickerInput, self).render(name, value, attrs=attrs)

    class Media:
        css = {
            'all': ('medbank/css/datepicker3.css', )
        }
        js = ('medbank/js/bootstrap-datepicker.js', 'medbank/js/widgets.js')


