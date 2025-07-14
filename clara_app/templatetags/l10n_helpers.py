from django import template
from ..models import LanguageMaster
register = template.Library()

@register.filter
def has_language_master(user, lang_code):
    return (getattr(user, 'userprofile', None) and
            (user.userprofile.is_admin or
             LanguageMaster.objects.filter(user=user, language=lang_code).exists()))

@register.filter
def get_item(d, key):
    return d.get(key)
