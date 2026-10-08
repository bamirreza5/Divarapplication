from django import template

register = template.Library()

@register.filter
def fa_number(value):
    return str(value).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))

@register.filter
def toman(value):
    if value is None:
        return "توافقی"
    return f"{int(value):,}".replace(",", "٬").translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
