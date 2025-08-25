from django import template
register = template.Library()

@register.filter
def to(start, end):
    """Usage: {% for i in 1|to:5 %} … {% endfor %} -> 1..5 inclusive"""
    start = int(start); end = int(end)
    return range(start, end + 1)

