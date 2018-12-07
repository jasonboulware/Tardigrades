from django import template
from django.forms.widgets import (CheckboxInput, RadioSelect, Select,
                                  SelectMultiple)

register = template.Library()

@register.inclusion_tag("_form_field.html")
def smart_field_render(field):
    """
    Renders a form field in different label / input orders
    depending if it's a checkbox or not.
    Also knows to only output the help text paragraph if
    it exists on the field

    Usage:
    {% load form_helpers %}

    {% smart_field_render form.my_field %}'

    """

    widget_class = field.form.fields[field.name].widget.__class__

    widget_types = {
        CheckboxInput : 'checkbox'
    }
    widget_type= widget_types.get(widget_class, "")

    return {
        "field": field,
        "widget_type": widget_type
    }

@register.filter
def is_checkbox(field):
    try:
        return isinstance(field.field.widget, CheckboxInput)
    except StandardError:
        return False

@register.filter
def is_select(field):
    try:
        return isinstance(field.field.widget, (Select, SelectMultiple))
    except StandardError:
        return False

@register.filter
def is_radio_select(field):
    try:
        return isinstance(field.field.widget, RadioSelect)
    except StandardError:
        return False
