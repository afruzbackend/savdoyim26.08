"""Savdo tizimi uchun shablon filtrlari."""
from decimal import Decimal, InvalidOperation
from django import template

register = template.Library()


@register.filter
def son(value):
    """Miqdorni chiroyli ko'rsatadi: butun→'15', kasrli→'5.5' / '0.75'
    (ortiqcha nollar kesiladi, o'nlik nuqta bilan). None/xato → o'zi qaytadi."""
    if value is None or value == '':
        return value
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return value
    if d == d.to_integral_value():
        d = d.quantize(Decimal('1'))
    else:
        d = d.normalize()
    return format(d, 'f')


@register.filter
def pul(value):
    """Pul summasini bo'sh joyli formatda: 2749500 -> '2 749 500'.
    Kasr qismini tashlaydi (butun so'm). None/xato -> '0'."""
    try:
        n = int(round(float(value or 0)))
    except (ValueError, TypeError):
        return '0'
    return f"{n:,}".replace(",", " ")
