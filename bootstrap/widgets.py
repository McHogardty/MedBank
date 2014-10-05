from __future__ import unicode_literals

from django import forms
from django.utils.datastructures import MultiValueDict, MergeDict
from django.forms.utils import flatatt
from django.utils.html import format_html, format_html_join
from django.utils.encoding import force_text
from django.utils import datetime_safe, formats


__all__ = ("StaticControl", "TextInputWithAddon", "CheckboxInput", "ButtonGroup", "Typeahead")


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


class RadioInputLikeButton(forms.widgets.RadioInput):
    def render(self, name=None, value=None, attrs=None, choices=()):
        choice_label = force_text(self.choice_label)

        label_classes = ["btn", "btn-default"]
        if self.is_checked(): label_classes.append("active")

        label_class = " ".join(label_classes)
        return format_html('<label{0}>{1} {2}</label>', flatatt({'class': label_class}), self.tag(), choice_label)


class CheckboxInputAsButton(forms.widgets.RadioInput):
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
    def render(self, name, value, attrs=None):
        class_attr = attrs.get("class", "").split()
        class_attr.append("typeahead")
        attrs['class'] = " ".join(class_attr)
        return super(Typeahead, self).render(name, value, attrs=attrs)