from django import template

register = template.Library()

@register.filter
def zip_lists(a, b):
    return zip(a, b)

@register.filter(name='titlecase')
def titlecase(value):
    return value.title()  # Converts to title case
