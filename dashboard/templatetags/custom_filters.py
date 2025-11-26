# yourapp/templatetags/custom_filters.py
from django import template
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"

@register.filter
def intcomma_fa(value):
    """
    اعداد صحیح و اعشاری را سه‌رقم جدا و فارسی می‌کند.
    مثال:
      1234567      -> ۱٬۲۳۴٬۵۶۷
      1234567.89   -> ۱٬۲۳۴٬۵۶۷.۸۹
    """
    try:
        # اگر عدد اعشاری باشد
        if isinstance(value, float):
            integer_part = int(value)
            decimal_part = str(value).split(".")[1]  # قسمت اعشار
            s = intcomma(integer_part)
            # تبدیل ارقام به فارسی
            for i, digit in enumerate("0123456789"):
                s = s.replace(digit, PERSIAN_DIGITS[i])
                decimal_part = decimal_part.replace(digit, PERSIAN_DIGITS[i])
            return f"{s}.{decimal_part}"
        else:
            value = float(value)
            if value.is_integer():
                value = int(value)
                s = intcomma(value)
                for i, digit in enumerate("0123456789"):
                    s = s.replace(digit, PERSIAN_DIGITS[i])
                return s
            else:
                integer_part = int(value)
                decimal_part = str(value).split(".")[1]
                s = intcomma(integer_part)
                for i, digit in enumerate("0123456789"):
                    s = s.replace(digit, PERSIAN_DIGITS[i])
                    decimal_part = decimal_part.replace(digit, PERSIAN_DIGITS[i])
                return f"{s}.{decimal_part}"
    except (ValueError, TypeError):
        return value

