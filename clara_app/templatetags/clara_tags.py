from django import template

from clara_app.models import SatisfactionQuestionnaire

register = template.Library()

@register.filter
def zip_lists(a, b):
    return zip(a, b)

@register.filter(name='titlecase')
def titlecase(value):
    return value.title()  # Converts to title case

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
