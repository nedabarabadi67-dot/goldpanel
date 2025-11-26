from django import template
from persiantools.jdatetime import JalaliDate
from datetime import datetime
from django.contrib.humanize.templatetags.humanize import intcomma
from django import template
from decimal import Decimal, InvalidOperation



# yourapp/templatetags/custom_filters.py
# yourapp/templatetags/custom_filters.py
# yourapp/templatetags/custom_filters.py



register = template.Library()

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"

def to_persian_digits(value: str) -> str:
    """تبدیل همه ارقام انگلیسی به فارسی"""
    if value is None:
        return ""
    value = str(value)
    for i, d in enumerate("0123456789"):
        value = value.replace(d, PERSIAN_DIGITS[i])
    return value

@register.filter
def persian_digits(value):
    """تبدیل فقط ارقام به فارسی"""
    return to_persian_digits(value)

@register.filter
def persian_intcomma(value):
    """
    جدا کردن سه‌رقمی + تبدیل به فارسی
    پشتیبانی از int, float, Decimal و str
    """
    if value is None:
        return ""
    try:
        # تبدیل به Decimal برای دقت بیشتر
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return to_persian_digits(value)

    # جدا کردن بخش صحیح و اعشار
    parts = str(number).split(".")
    integer_part = int(parts[0])
    formatted_int = f"{integer_part:,}"  # سه رقم سه رقم جدا

    if len(parts) > 1:  # اگر اعشار داشت
        decimal_part = parts[1].rstrip("0")  # صفرهای اضافه آخر حذف بشه
        if decimal_part:
            formatted = f"{formatted_int}.{decimal_part}"
        else:
            formatted = formatted_int
    else:
        formatted = formatted_int

    return to_persian_digits(formatted)



@register.filter
def to_jalali(value):
    """تبدیل تاریخ میلادی (datetime یا str) به شمسی"""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return value  # اگر رشته فرمت درست نداشت، همونو برگردونه
    
    jalali_date = JalaliDate.to_jalali(value).strftime("%Y/%m/%d")
    return to_persian_digits(jalali_date)

@register.filter
def role_fa(value):
    mapping = {
        "admin": "ادمین",
        "seller": "فروشنده",
        "accountant": "حسابدار",
    }
    return mapping.get(value, value)

@register.filter
def cat_fa(value):
    mapping = {
        'bracelet': 'دستبند',
        'earing': 'گوشواره',
        'neckles': 'گردنبند',
        'ring': 'انگشتر',
        "coine":"سکه",
        "set":"سرویس",
        "nimset":"نیم ست",
        "medal":"مدال",
        "zanjir":"زنجیر",
        'ab':'آبشده',
        'mot':'متفرقه',
        'other':'سایر',

    }
    return mapping.get(value, value)

@register.filter
def balance_status(value):
    """
    بر اساس عدد مانده حساب، وضعیت فارسی را برمی‌گرداند.
    """
    try:
        value = float(value)
        if value > 0:
            return "بدهکار"
        elif value < 0:
            return "بستانکار"
        else:
            return "تسویه شده"
    except (TypeError, ValueError):
        return ""

@register.filter
def format_balance(value):
    try:
        val = float(value)
    except:
        return value

    abs_val = f"{abs(val):,.0f}"
    if val > 0:
        return f"{abs_val} بد"
    elif val < 0:
        return f"{abs_val} بس"
    return abs_val

@register.filter
def format_gold(value):
    value = float(value)
    abs_val = f"{abs(value):,.2f}"
    if value > 0:
        return f"{abs_val} بد"
    elif value < 0:
        return f"{abs_val} بس"
    return value


@register.filter
def type_fa(value):
    mapping = {
        'asset': 'دارایی',
        'liability': 'بدهی',
        'income': 'درآمد',
        'expense': 'هزینه',
        'capital': 'سرمایه',
        'cogs': 'بهای تمام‌شده',
    }
    return mapping.get(value,value)

@register.filter
def type_purchase(value):
    mapping = {
        'gold': 'کالا طلا',
        'ab': 'آبشده',
        'mot': 'متفرقه',
    }
    return mapping.get(value,value)

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except:
        return 0

@register.filter
def sum_weights(items):
    """جمع کل وزن × تعداد"""
    total = 0
    for item in items:
        weight = getattr(item.product, 'weight', 0) or 0
        qty = getattr(item, 'quantity', 0) or 0
        total += weight * qty
    return total