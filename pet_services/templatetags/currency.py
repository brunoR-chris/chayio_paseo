from django import template

register = template.Library()


@register.filter
def currency(value):
    formatted = format(value, ',.2f')
    return formatted.replace(',', '\0').replace('.', ',').replace('\0', '.')
