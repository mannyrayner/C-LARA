from django import template

from clara_app.models import SatisfactionQuestionnaire
from clara_app.clara_utils import absolute_file_name

register = template.Library()

@register.filter
def zip_lists(a, b):
    return zip(a, b)

@register.filter(name='titlecase')
def titlecase(value):
    return value.title()

@register.filter(name='base_name')
def base_name(file_path):
    if not file_path:
        return None
    else:
        abs_file_path = absolute_file_name(file_path)
        return abs_file_path.split('/')[-1]

@register.filter
def ai_generated_display(value):
    return dict(SatisfactionQuestionnaire.GENERATED_BY_AI_CHOICES).get(value, "Unknown")

# Filters for translating choice codes to human-readable text
@register.filter
def text_type_display(value):
    return dict(SatisfactionQuestionnaire.TEXT_TYPE_CHOICES).get(value, "Unknown")

@register.filter
def time_spent_display(value):
    return dict(SatisfactionQuestionnaire.TIME_SPENT_CHOICES + SatisfactionQuestionnaire.TIME_SPENT_CHOICES_IMAGES).get(value, "Unknown")

@register.filter
def share_choice_display(value):
    return dict(SatisfactionQuestionnaire.SHARE_CHOICES).get(value, "Unknown")

@register.filter
def clara_type_display(value):
    return dict(SatisfactionQuestionnaire.CLARA_VERSION_CHOICES).get(value, "Unknown")
