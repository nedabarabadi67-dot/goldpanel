import csv
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import io
import json
import os
from pyexpat.errors import messages
import traceback
from django.forms import FloatField
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.timezone import now
import jdatetime
import requests
from weasyprint import CSS, HTML
from django.db.models import CharField
from django.conf import settings

from .models import  BankAccount, CashAccount, ExpenseAccount, Invoice, InvoiceItem, Payment, Product ,Customer, Receipt
from .forms import   BankStatementUploadForm, BankTransactionForm, CustomerForm, DateRangeForm
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.contrib.staticfiles.storage import staticfiles_storage
from django.contrib.staticfiles import finders
from django.shortcuts import render
from django.http import JsonResponse
from django.utils.timezone import now
from .models import Customer, Product, Invoice, InvoiceItem
from .forms import CustomerForm
from django.db.models import Sum,F,Count,ExpressionWrapper, DecimalField
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from .forms import UserForm,ProductForm
from .models import UserProfile,Product
from django.contrib.auth import authenticate,login,logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models.functions import TruncWeek
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from persiantools.jdatetime import JalaliDate
from .models import RetentionCampaign, CampaignLog, Customer
from .forms import RetentionCampaignForm
from django.utils import timezone
from kavenegar import KavenegarAPI, APIException, HTTPException
from django.shortcuts import render, get_object_or_404
from .models import RetentionCampaign, CampaignLog, Customer
from django.db.models import Count
from django.utils.decorators import method_decorator
from dashboard.models import CustomerCRM
from django.utils.dateparse import parse_date
from .models import MeltedGold, MeltedGoldSale,MeltedGoldTransaction
from .forms import MeltedGoldForm, MeltedGoldSaleForm,MeltedGoldTransactionForm
from jalali_date import date2jalali
from decimal import Decimal, InvalidOperation
from .models import Partner, PartnerMoneyTransaction, PartnerGoldTransaction
from .models import Person,PurchaseItem,PurchaseInvoice
from .forms import PersonForm,PurchaseInvoiceForm,PurchaseItemForm
from .forms import PartnerForm, PartnerMoneyTransactionForm, PartnerGoldTransactionForm
from django.db.models import Max, IntegerField
from django.db.models.functions import Cast
from django.db.models import Sum, F, Value as V
from django.db.models.functions import Coalesce
from decimal import Decimal
from .models import JournalEntry, JournalItem, Account
# Create your views here.
from django.db.models import Count, Sum, F, DateField
from django.db.models import Func
import requests
from collections import defaultdict
from django.db.models import Prefetch
from django.utils.timezone import make_naive
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import base64
from django.db.models.functions import ExtractYear, ExtractMonth
from django.db.models import DecimalField, Value

def print_label(request, pk):
    product = get_object_or_404(Product, pk=pk)

    barcode_data = product.barcode_image

    context = {
        "product": product,
        "barcode_data": barcode_data,
        "store_name": "Nasiri Gold",
    }
    return render(request, "label_template.html", context)


def print_label_2(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # اگر بارکد ندارد → تولید و ذخیره کن
    if not product.barcode_image:
        buffer = BytesIO()
        barcode_class = barcode.get_barcode_class('code128')
        code = barcode_class(str(product.code), writer=ImageWriter())
        code.write(buffer)
        barcode_data = base64.b64encode(buffer.getvalue()).decode()

        # ذخیره‌سازی در دیتابیس
        product.barcode_image = barcode_data
        product.save()
    else:
        barcode_data = product.barcode_image

    context = {
        "product": product,
        "barcode_data": barcode_data,
        "store_name": "Nasiri Gold",
    }
    return render(request, "label_template.html", context)


def print_label_old(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # ساخت بارکد از کد محصول
    buffer = BytesIO()
    barcode_class = barcode.get_barcode_class('code128')
    code = barcode_class(str(product.code), writer=ImageWriter())
    code.write(buffer)
    barcode_data = base64.b64encode(buffer.getvalue()).decode()

    context = {
        "product": product,
        "barcode_data": barcode_data,
        "store_name": "Nasiri Gold",  # نام فروشگاه
    }
    return render(request, "label_template.html", context)


def print_invoice_labels(request, invoice_id):
    invoice = get_object_or_404(PurchaseInvoice, id=invoice_id)
    items = PurchaseItem.objects.filter(invoice=invoice).select_related('product')
    print(items)
    context = {
        'store_name': "Nasiri Gold",
        'purchase_items': items,
    }
    return render(request, 'label-item.html', context)


def daily_report_pdf_view(request):
    # -------------------------------
    # تاریخ گزارش (امروز)
    # -------------------------------
    report_date = timezone.now().date()

    sales_qs = Invoice.objects.filter(
        date=report_date
    )

    sale_data = sales_qs.aggregate(
        total_customers=Count('customer', distinct=True),
        total_invoices=Count('id', distinct=True),
        total_amount=Coalesce(Sum('total_price'), Decimal('0')),
        profit_total=Coalesce(Sum('profit_total'), Decimal('0')),
    )

    total_weights = InvoiceItem.objects.filter(
        invoice__date=report_date
    ).aggregate(
        w=Coalesce(Sum('weight'), Decimal('0'))
    )['w']

    daily_sales = [{
        "date": report_date,
        "total_customers": sale_data["total_customers"],
        "total_invoices": sale_data["total_invoices"],
        "total_weights": total_weights,
        "total_amount": sale_data["total_amount"],
        "profit_total": sale_data["profit_total"],
    }]
        
        
    

    # -------------------------------
    # خرید روز
    # -------------------------------
    purchase_qs = PurchaseInvoice.objects.filter(
        date=report_date
    )

    purchase_weights = purchase_qs.values('type').annotate(
        total_weight=Coalesce(Sum('weight'), Decimal('0'))
    )

    # مقدار پیش‌فرض صفر
    buy_gold_weight = Decimal('0')
    buy_ab_weight = Decimal('0')
    buy_mot_weight = Decimal('0')

    # پر کردن مقادیر
    for row in purchase_weights:
        if row['type'] == 'gold':
            buy_gold_weight = row['total_weight']
        elif row['type'] == 'ab':
            buy_ab_weight = row['total_weight']
        elif row['type'] == 'mot':
            buy_mot_weight = row['total_weight']
    
    daily_purchase = {
    "date": report_date,
    "buy_gold_weight": buy_gold_weight,   # کالا
    "buy_ab_weight": buy_ab_weight,       # آبشده
    "buy_mot_weight": buy_mot_weight,     # متفرقه
    }
    
    print(daily_purchase)

        # ------------------------------------------------
    # 4) موجودی طلا
    # ------------------------------------------------
    inventory_account = Account.objects.get(code="14")  # موجودی طلا
    items = inventory_account.journal_items.all()
    balance_gold = Decimal('0')
    for row in items:
        debit_gold = row.debit_gold or 0
        credit_gold = row.credit_gold or 0
        balance_gold += debit_gold - credit_gold
    gold_stock_weight = balance_gold



    # ------------------------------------------------
    # 5) موجودی نقدی
    # ------------------------------------------------
    # صندوق
    cash_accounts = CashAccount.objects.select_related('account')
    cash_balance = Decimal('0')
    for cash in cash_accounts:
        items = cash.account.journal_items.all()
        balance = Decimal('0')
        for row in items:
            debit = row.debit_money or Decimal('0')
            credit = row.credit_money or Decimal('0')
            balance += debit - credit
        cash_balance += balance

    # بانک
    bank_accounts = BankAccount.objects.select_related('account')
    bank_balance = Decimal('0')
    for bank in bank_accounts:
        items = bank.account.journal_items.all()
        balance = Decimal('0')
        for row in items:
            debit = row.debit_money or Decimal('0')
            credit = row.credit_money or Decimal('0')
            balance += debit - credit
        bank_balance += balance



    # -------------------------------
    # کانتکست قالب PDF
    # -------------------------------
    context = {
        "report_date": report_date,
        "daily_sales" : daily_sales ,
        "daily_purchase" : daily_purchase ,

        "bank_balance": bank_balance,
        "cash_balance": cash_balance,
        "gold_balance": balance_gold,
    }

    # -------------------------------
    # رندر HTML
    # -------------------------------
    html_string = render_to_string(
        "whatsupp-report.html",
        context
    )

    # -------------------------------
    # ساخت PDF
    # -------------------------------
    pdf_file = HTML(
        string=html_string,
        base_url=request.build_absolute_uri('/')
    ).write_pdf()

    # -------------------------------
    # پاسخ PDF
    # -------------------------------
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="daily_report.pdf"'

    return response


def download_invoice_pdf(request, invoice_id):
    purchase = get_object_or_404(PurchaseInvoice, id=invoice_id)
    total_weight = sum(item.product.weight * item.quantity for item in purchase.items.all())
    
    print(total_weight)
    context = {
    "purchase": purchase,
    "items": purchase.items.all() if purchase.type not in ['ab', 'mot'] else None,
    "is_gold": purchase.type not in ['ab', 'mot'], # یعنی فاکتور طلای معمولی است
    "today": timezone.now(),
    'seller': purchase.seller,
}

    html_string = render_to_string('purchase-pdf.html', {
        "purchase": purchase,
        "items": purchase.items.all() if purchase.type not in ['ab', 'mot'] else None,
        "is_gold": purchase.type not in ['ab', 'mot'], # یعنی فاکتور طلای معمولی است
        "today": timezone.now(),
        'seller': purchase.seller,
        "total_weight" : total_weight,
    })

    html = HTML(string=html_string)
    pdf_file = html.write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename=invoice_{purchase.number}.pdf'
    return response

def get_gold_prices():
    # جایگذاری کلید اختصاصی شما
    api_key = "freerBV7TOeWTSbBExgYv2zFc83s53AX"
    url = f"https://api.navasan.tech/latest/?api_key={api_key}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json"
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()

        prices = {
            "دلار": data.get("usd", {}).get("value"),
            "یورو": data.get("eur", {}).get("value"),
            "طلای ۱۸ عیار": data.get("geram18", {}).get("value"),
            "سکه امامی": data.get("sekeb", {}).get("value"),
        }

        return {
            "status": "success",
            "data": prices
        }

    except Exception as e:
        return {"status": "error", "message": f"خطا در اتصال به Navasan: {e}"}

 
def send_sms(to, message):
    try:
        api = KavenegarAPI('YOUR_API_KEY')  # 👈 API Key رو از پنل کاوه‌نگار بذار
        params = {
            'sender': '',       # اگه خط اختصاصی داری بذار، در غیر این صورت خالی بذار
            'receptor': to,     # شماره مشتری
            'message': message, # متن پیامک
        }
        response = api.sms_send(params)
        return True, response
    except APIException as e:
        print("API Error:", e)
        return False, str(e)
    except HTTPException as e:
        print("HTTP Error:", e)
        return False, str(e)


#Main page
@login_required(login_url='/')  # مسیر صفحه لاگین شما
def Home(request):
     # فیلتر تاریخ از فرم GET
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not end_date:
        end_date = date.today()

# حالا می‌توانیم start_date را محاسبه کنیم
    if not start_date:
        start_date = end_date - timedelta(days=7)

    invoices = Invoice.objects.all()
    if start_date:
        invoices = invoices.filter(date__gte=start_date)
    if end_date:
        invoices = invoices.filter(date__lte=end_date)

    # فروش روزانه (کل)
    daily_sales = invoices.filter(date=now().date()).aggregate(total=Sum('total_price'))['total'] or 0

    daily_invoices_count = invoices.filter(date=now().date()).count()

    top_products = (
    InvoiceItem.objects
    .filter(invoice__in=invoices)
    .exclude(product__category__in=['ab', 'mot'])  # 🚫 حذف دسته‌های ab و mot
    .values(
        'product__id',
        'product__name',
        'product__category',
        'product__code',
        'product__weight',
        'product__image',
        'product__description',
    )
    .annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum('total')
    )
    .order_by('-total_sold')
    # 🔟 ده محصول پرفروش
)

    top_product = top_products[0] if top_products else None

        # مشتریان با بیشترین خرید
    top_customers = (
    invoices.filter(customer__type_partner='customer')  # ✅ فقط مشتری‌ها
    .values('customer__name', 'customer__phone')
    .annotate(
        total_spent=Sum('total_price'),
        invoice_count=Count('id')
    )
    .order_by('-total_spent')[:10]
    )

    top_customer = top_customers[0] if top_customers else None

    
    # نمودار فروش ماهانه
    monthly_sales = invoices.annotate(month=TruncMonth('date')).values('month').annotate(
        total=Sum('total_price')
    ).order_by('month')

    monthly_labels = [s['month'].strftime("%b %Y") for s in monthly_sales]
    monthly_data = [float(s['total']) for s in monthly_sales]
    
    # فروش هفتگی
    weekly_sales = invoices.annotate(week=TruncWeek('date')).values('week').annotate(
    total=Sum('total_price')
    ).order_by('-week')[:4]  # 4 هفته اخیر

    weekly_data_list = []
    previous_total = None
    for w in weekly_sales:
        total = float(w['total'])
        if previous_total:
            change = ((total - previous_total) / previous_total) * 100
        else:
            change = 0
        weekly_data_list.append({
            'week': w['week'].strftime("%d %b"),
            'total': total,
            'change_percent': round(change, 2),
        })
        previous_total = total

            # محدوده زمانی (مثلاً هفته گذشته)
        end_date = date.today()
    start_date = end_date - timedelta(days=7)
    
    # فروش هر محصول در هفته گذشته، با استفاده از تاریخ فاکتور
    sales_data = (
        InvoiceItem.objects.filter(invoice__date__range=[start_date, end_date])
        .values('product__id', 'product__name', 'product__code', 'product__image','product__category')
        .annotate(
            units_sold=Sum('quantity'),
            total_amount=Sum('total')
        )
        .order_by('-units_sold')[:10]
    )
    
    # هفته قبل برای درصد تغییر
    prev_start = start_date - timedelta(days=7)
    prev_end = start_date - timedelta(days=1)
    
    prev_sales = (
        InvoiceItem.objects.filter(invoice__date__range=[prev_start, prev_end])
        .values('product')
        .annotate(units_sold=Sum('quantity'))
    )
    
    prev_sales_dict = {item['product']: item['units_sold'] for item in prev_sales}
    
    top_products = []
    for item in sales_data:
        prev_units = prev_sales_dict.get(item['product__id'], 0)
        change_percent = ((item['units_sold'] - prev_units) / prev_units * 100) if prev_units else 100
        top_products.append({
            'name': item['product__name'],
            'code': item['product__code'],
            'category':item['product__category'],
            'image': item['product__image'],
            'units_sold': item['units_sold'],
            'total_amount': item['total_amount'],
            'change_percent': round(change_percent, 2),
        })
    #نموار جدید روزانه هفتگی
    
    today = timezone.now().date()

    # ---- 🔹 فروش روزانه ۳۰ روز اخیر ----
    start_date = today - timedelta(days=29)
    daily_sales2 = (
        Invoice.objects
        .filter(date__gte=start_date)
        .values('date')
        .annotate(total=Sum('total_price'))
        .order_by('date')
    )

    daily_labels = [
        jdatetime.date.fromgregorian(date=item['date']).strftime("%d %b") for item in daily_sales2
    ]
    daily_data = [float(item['total']) for item in daily_sales2]



    # ---- 🔹 فروش هفتگی ۸ هفته اخیر ----
    start_week = today - timedelta(weeks=7)
    weekly_sales = (
        Invoice.objects
        .filter(date__gte=start_week)
        .annotate(week=TruncWeek('date'))
        .values('week')
        .annotate(total=Sum('total_price'))
        .order_by('week')
    )

    # ساخت لیبل برای هر هفته
    weekly_labels = []
    weekly_data = []
    for i, w in enumerate(weekly_sales):
        start = w['week']
        end = start + timedelta(days=6)
        start_j = jdatetime.date.fromgregorian(date=start)
        end_j = jdatetime.date.fromgregorian(date=end)
        label = f"{start_j.strftime('%d %b')} تا {end_j.strftime('%d %b')}"
        weekly_labels.append(label)
        weekly_data = [float(w['total']) for w in weekly_sales]




    
    # اخر نمودار
   
    context={
        'daily_sales': daily_sales,
        'daily_invoices_count': daily_invoices_count,
        'top_products': top_products,
        'top_product':top_product,
        'top_customer':top_customer,
        'monthly_labels': monthly_labels,
        'monthly_data': monthly_data,
        'start_date': start_date,
        'end_date': end_date,
        'weekly_data_list': weekly_data_list,
        'top_selling_products': top_products,
        'daily_labels': json.dumps(daily_labels, ensure_ascii=False),
        'daily_data': json.dumps(daily_data, ensure_ascii=False),
        'weekly_labels': json.dumps(weekly_labels, ensure_ascii=False),
        'weekly_data': json.dumps(weekly_data, ensure_ascii=False),
        
    }
    
    print("🟡 daily_labels:", daily_labels)
    print("🟡 daily_data:", daily_data)
    print("🟡 weekly_labels:", weekly_labels)
    print("🟡 weekly_data:", weekly_sales)

    
    #print(top_products)
    return render(request,'index.html',context)


#login page
def login_view(request):
    #print("login")
    # اگر کاربر از قبل لاگین باشد → مستقیم Home
    if request.user.is_authenticated:
        return redirect("Home")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        remember_me = request.POST.get("remember_me")  # مقدار "on" اگر تیک خورده باشد
        #print(remember_me)
        #print(username)
        # authenticate بهتر است از check_password جدا شود
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # بررسی وضعیت اکانت
            if hasattr(user, "userprofile") and user.userprofile.is_active:
                login(request, user)

                if remember_me == "on":
                    #print("tik")
                    request.session.set_expiry(1209600)  # دو هفته
                else:
                    #print("notik")
                    request.session.set_expiry(None)  # با بستن مرورگر حذف میشه
                    

                return JsonResponse({"status": "success", "redirect_url": "/home/"})
            else:
                return JsonResponse({
                    "status": "inactive",
                    "message": "اکانت شما غیر فعال است. لطفا با ادمین تماس بگیرید."
                })
        else:
            return JsonResponse({
                "status": "error",
                "message": "نام کاربری یا رمز عبور اشتباه است."
            })

    # اگر GET باشد → صفحه ورود
    return render(request, "login.html")

"""
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # چک کردن پروفایل فعال
            if hasattr(user, "userprofile") and user.userprofile.is_active:
                login(request, user)  # لاگین واقعی کاربر

                # تنظیم session بر اساس remember_me
                if remember_me == "on":
                    request.session.set_expiry(1209600)  # دو هفته
                else:
                    request.session.set_expiry(0)  # با بستن مرورگر حذف میشه

                # پاسخ موفقیت با اطلاعات ریدایرکت
                return JsonResponse({"status": "success", "redirect_url": "/home/"})

            # کاربر غیرفعال
            return JsonResponse({"status": "inactive", "message": " .اکانت شما غیر فعال هست . لطفا با ادمین تماس بگیرید "})

        # نام کاربری یا رمز اشتباه
        return JsonResponse({"status": "error", "message": "نام کاربری یا رمز عبور اشتباه است . لطفا دوباره تلاش کنید ."})

    # اگر GET بود → فقط template لاگین
    return render(request, "login.html")
"""



#User Managment
@login_required(login_url='/')  # مسیر صفحه لاگین شما
def register(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        if user_id:  # ویرایش
            user = get_object_or_404(User, id=user_id)
            profile = getattr(user, 'userprofile', None)

            # مستقیم از POST مقداردهی کنیم
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)

            # فقط اگر پسورد جدید داد
            password = request.POST.get('password', '').strip()
            if password:
                user.set_password(password)

            user.save()

            if profile is None:
                profile = UserProfile(user=user)

            profile.phone = request.POST.get('phone', profile.phone)
            profile.role = request.POST.get('role', profile.role)
            profile.is_active = True if request.POST.get('is_active') == 'on' else False
            profile.save()

        else:  # اضافه کردن کاربر جدید
            form = UserForm(request.POST)
            if form.is_valid():
                user_instance = form.save(commit=False)
                password = form.cleaned_data.get('password')
                if password and password.strip() != "":
                    user_instance.set_password(password)
                user_instance.save()

                profile = UserProfile.objects.create(
                    user=user_instance,
                    phone=form.cleaned_data['phone'],
                    role=form.cleaned_data['role'],
                    is_active=True
                )
            else:
                print(form.errors)

        return redirect('register')

    else:
        form = UserForm()

    users = User.objects.all().select_related('userprofile')
    return render(request, 'register.html', {'form': form, 'users': users})

#Register Page
category_map = {
    'bracelet': 'دستبند',
    'ring': 'انگشتر',
    'neckles': 'گردنبند',
    'earing': 'گوشواره',
    'set': 'سرویس',
    'nimset':"نیم ست",
    'brba':'دستبند النگو',
    'bangle':'النگو',
    'medal':'مدال',
    'zanjir':'زنجیر',
    'ab':'آبشده',
    'mot':'متفرقه',
    'coine': 'سکه',
    'other': 'سایر'
}

#Product Page
@login_required(login_url='/')  # مسیر صفحه لاگین شما
def product_view(request):
    if request.method=='POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('product')
        else:
            print(form.errors)
            print('notvalid')
    else:
        form = ProductForm()

    products = list(Product.objects.all())

    # مرتب‌سازی: محصول با name='متفرقه' اول باشد
    products.sort(key=lambda x: 0 if x.code == '1' else 1)

    categories = category_map
    return render(request,'product.html',{'form':form,'products':products,'categories':categories})


#Add product
@csrf_exempt
def add_product(request):
    if request.method == "POST":
        labor_amount = Decimal("0")
        labor_total = Decimal("0")
        form = ProductForm(request.POST, request.FILES)
        code=request.POST.get('code') or ""
        name=request.POST.get('name') or ""
        category=request.POST.get('category') or ""
        weight=request.POST.get('weight') or 0
        labor=request.POST.get('labor') or 0
        laborprice=request.POST.get('laborprice') or 0
        purity=request.POST.get('purity') or 750
        quantity=request.POST.get('quantity') or 0
        description = request.POST.get("description")
        image = request.FILES.get("image", None)
        
        weight=to_decimal(weight)
        labor=to_decimal(labor)
        laborprice=to_decimal(laborprice)
        quantity=to_decimal(quantity)
        purity=to_decimal(purity)

        try:
            with transaction.atomic():
                #product = form.save()
                product=Product.objects.create(
                    code=code,
                    name=name,
                    category=category,
                    weight=weight,
                    labor=labor,
                    laborprice=laborprice,
                    purity=purity,
                    quantity=quantity,
                    description=description,
                    image=image
                    
                )

                # سند حسابداری موجودی اولیه سرمایه بستانکار
                if quantity > 0 :
                    gold_account=Account.objects.get(code='14')
                    capital_account=Account.objects.get(code='3')
                    labor_account=Account.objects.get(code='51')
                    labor_amount = 0
                    print("labor",labor)
                    print("laborprice" , laborprice)
                    if labor > 0 :
                        labor_amount=(weight * labor) /100   
                    if laborprice > 0 :
                        print("if")
                        if purity != 750 :
                            weightpurity=(weight * purity )/750
                            labor_amount= ( weightpurity * laborprice )
                        else : 
                            labor_amount= ( weight * laborprice )
                                
                    if quantity > 0 :
                        weight_total= weight * quantity
                        labor_total= labor_amount * quantity
                        
                    else :
                        weight_total = weight
                        labor_total= labor_amount
                    
                    print("labor",labor_total)
                    
                        # 🔸 ایجاد سند حسابداری
                    entry = JournalEntry.objects.create(
                        date=timezone.now().date(),
                        description=f"ثبت موجودی اولیه کالا {name}",
                    )

                        # 🔸 بدهکار: موجودی طلا (با وزن)
                    JournalItem.objects.create(
                        entry=entry,
                        account=gold_account,
                        debit_gold=weight_total,
                        description=f"ورود اولیه کالای {name}"
                    )
                    
                    if labor== 0 and laborprice==0 :
                        # 🔸 بستانکار: سرمایه (با وزن)
                        JournalItem.objects.create(
                            entry=entry,
                            account=capital_account,
                            credit_gold=weight_total,
                            description="تأمین از سرمایه طلا"
                        )
                    elif labor> 0 : 
                        JournalItem.objects.create(
                            entry=entry,
                            account=labor_account,
                            debit_gold=labor_total,
                            description=f"هزینه اجرت {labor}% برای {name}"
                        )
                        # 🔸 بستانکار: سرمایه (با درصد اجرت و وزن)
                        JournalItem.objects.create(
                            entry=entry,
                            account=capital_account,
                            credit_gold=weight_total + labor_total ,
                            description="تأمین از سرمایه (طلا + اجرت)"
                            )
                    elif laborprice > 0 :
                        JournalItem.objects.create(
                            entry=entry,
                            account=labor_account,
                            debit_money=labor_total,
                            description=f"هزینه اجرت پولی  {laborprice} برای {name}"
                        )
                        # 🔸 بستانکار: سرمایه (با پول اجرت و وزن)
                        JournalItem.objects.create(
                            entry=entry,
                            account=capital_account,
                            credit_gold=weight_total,
                            credit_money=labor_total,
                            description="تأمین از سرمایه (طلا + اجرت پولی)"
                            )

                        print(f"✅ سند طلایی برای {name} ثبت شد ")
                
                return JsonResponse({
                    "success": True,
                    "id": product.id,
                    "code": product.code,
                    "name": product.name,
                    # برگردوندن متن فارسی
                    "category": category_map.get(product.category, product.category),
                    "weight": product.weight,
                    "quantity": product.quantity,
                    "labor":product.labor,
                    "laborprice":product.laborprice,
                    'purity':product.purity,
                    "description": product.description,
                    "image": product.image.url if product.image else ""
                })
        except Exception as e:
            return JsonResponse({"success": False, "errors": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"})

#update product
@require_POST
def product_update(request, pk):
    
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
                        # mapping برای نمایش فارسی
            CATEGORY_CHOICES = {
                "bracelet": "دستبند",
                "earing": "گوشواره",
                "neckles": "گردنبند",
                "ring": "انگشتر",
                "set":"سرویس",
                "coine":"سکه",
                "other": "سایر",
            }
            data = {
                "success": True,
                "id": product.id,
                "code": product.code,
                "name": product.name,

                "category": category_map.get(product.category, product.category),
                #"category": product.category,
                "weight": product.weight,
                "labor":product.labor,
                "quantity": product.quantity,
                "purity":product.purity,
                "description": product.description,
                "image": product.image.url if product.image else ""
            }
            return JsonResponse(data)
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)

def edit_product(request, id):
    if request.method == "POST":
        try:
            product = Product.objects.get(id=id)
            product.code = request.POST.get("code", product.code)
            product.name = request.POST.get("name", product.name)
            product.category = request.POST.get("category", product.category)
            product.weight = request.POST.get("weight", product.weight)
            product.labor = request.POST.get("labor", product.labor)
            product.quantity = request.POST.get("quantity", product.quantity)
            product.purity = request.POST.get("purity", product.purity)
            product.description = request.POST.get("description", product.description)

            if "image" in request.FILES:
                product.image = request.FILES["image"]

            product.save()

            category_map = {
                "bracelet":"دستبند",
                "earing":"گوشواره",
                "neckles":"گردنبند",
                "ring":"انگشتر",
                "set":"سرویس",
                "coine":"سکه",
                "other":"سایر"
            }

            return JsonResponse({
                "success": True,
                "code": product.code,
                "name": product.name,
                "category": category_map.get(product.category, ""),
                "weight": str(product.weight),
                "quantity": str(product.quantity),
                "labor": str(product.labor),
                "purity":str(product.purity),
                "description": product.description,
                "image": product.image.url if product.image else ""
            })
        except Product.DoesNotExist:
            return JsonResponse({"success": False, "errors": "محصول یافت نشد"})
    return JsonResponse({"success": False, "errors": "درخواست نامعتبر"})

#product detail
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    print(product)
    data = {
        'id': product.id,
        'code':product.code,
        'name': product.name,
        'purity':product.purity,
        'category': product.category,
        'weight': product.weight,
        'labor':product.labor,
        'quantity': product.quantity,
        'description': product.description,
        "image": product.image.url if product.image else "",
    }
    print(data)
    return JsonResponse(data)

@csrf_exempt
def delete_product(request, pk):
    if request.method == "POST":
        try:
            product = Product.objects.get(pk=pk)
            product.delete()
            return JsonResponse({"success": True})
        except Product.DoesNotExist:
            return JsonResponse({"success": False, "error": "Product not found"})
    return JsonResponse({"success": False, "error": "Invalid request"})

# views.py
def get_next_code(request, category):
    # آخرین محصول از اون دسته
    print("nextcode")
    print(category)
    last_product = Product.objects.filter(category=category).order_by('-id').first()
    print(last_product)
    if last_product and last_product.code:
        try:
            # جدا کردن عدد از انتهای کد
            last_num = int(''.join(filter(str.isdigit, last_product.code)))
            next_number = last_num + 1
        except:
            next_number = 1
    else:
        next_number = 1

    # عدد رو سه رقمی کن (مثل 001, 002,...)
    return JsonResponse({"next_number": str(next_number).zfill(3)})

#login page
def tables(request):
    return render(request,'tables.html')

#login page
def profile(request):
    return render (request,'test2.html')

#login page
def icons(request):
    return render (request,'icons.html')

#login page
def forms(request):
    return render (request,'_ensidebar.html')

#login page
def calender(request):
    return render (request,'test2.html')

#logout
def logout_view(request):
    logout(request)
    return redirect('login')


def index(request):
    return render(request,'profile.html')

def generate_invoice_pdf(request, invoice_id):
    print(invoice_id)
    invoice = Invoice.objects.get(id=invoice_id)  # مدل خودت
    context = {
            "customer": invoice.customer,
            "invoice": invoice,
            "items": invoice.items.all(),
            "logo_url":static('images/logo.jpg'),
    }
    for item in invoice.items.all():
        print("item:", item.gold_price_per_gram, item.labor_per_gram, item.profit_percent, item.total)

    html_string = render_to_string("invoice_pdf.html", context)
    html = HTML(string=html_string)
    #pdf_file = html.write_pdf()
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="invoice_{invoice.id}.pdf"'
    return response

def generate_invoice_pdf_2(request, invoice_id):
    print(invoice_id)
    invoice = Invoice.objects.get(id=invoice_id)  # مدل خودت
    context = {
            "customer": invoice.customer,
            "invoice": invoice,
            "items": invoice.items.all(),
            "logo_url":static('images/logo.jpg'),
    }
    for item in invoice.items.all():
        print("item:", item.gold_price_per_gram, item.labor_per_gram, item.profit_percent, item.total)

    html_string = render_to_string("invoice-pdf-2.html", context)
    html = HTML(string=html_string)
    #pdf_file = html.write_pdf()
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="invoice_{invoice.id}.pdf"'
    return response

# --- گرفتن اطلاعات مشتری با شماره تلفن ---
def get_customer_by_phone(request):
    print('customer')
    phone = request.GET.get('phone')
    print(phone)
    try:
        customer = Person.objects.get(phone=phone)
        print(customer)
        print("✅ Customer found:", customer.birth_date)
        birth_date_shamsi = ""
        if customer.birth_date:
            birth_date_shamsi = jdatetime.date.fromgregorian(date=customer.birth_date).strftime("%Y/%m/%d")
        print(birth_date_shamsi)
        data = {
            "exists": True,
            "name": customer.name,
            "birth_date": birth_date_shamsi,
        }
        
    except Customer.DoesNotExist:
        print("❌ Customer not found:", phone)
        data = {"exists": False}
    return JsonResponse(data)

def get_product_price(request):
    product_id = request.GET.get('product_id')
    try:
        product = Product.objects.get(id=product_id)
        data = {
            "price": product.price,
        }
    except Product.DoesNotExist:
        data = {"price": 0}
    return JsonResponse(data)

def persian_to_english_digits(s):
    persian = '۰۱۲۳۴۵۶۷۸۹'
    english = '0123456789'
    for i in range(10):
        s = s.replace(persian[i], english[i])
    return s

#new check shode
def create_sale_journal(invoice,bank_payments,bank_ids,cash_payments,cash_ids,type):
    print("🚨 ENTERED create_sale_journal_new 🚨")
    customer=invoice.customer
    items = invoice.items.all()
    print(items)
    if not items.exists():
        raise ValueError("Invoice has no items — cannot create sale journal.")
    print('sale')
    print(items)
    
    # حساب‌ها
    inventory_account = Account.objects.get(code="14")  # موجودی طلا
    sales_account = Account.objects.get(code="41")      # درآمد فروش طلا
    cogs_account = Account.objects.get(code="61")       # بهای تمام‌شده
    profit_account = Account.objects.get(code="43")     # سود فروش طلا
    labor_account_p = Account.objects.get(code="51")     # خرید اجرت طلاهزینه
    labor_account_s = Account.objects.get(code="42")     #فروش اجرت طلاهزینه
    profit_account = Account.objects.get(code="43")       # سود فروش

    # جمع کل پرداخت‌ها
    total_bank= sum(to_decimal(x or 0) for x in bank_payments)
    total_cash= sum(to_decimal(x or 0) for x in cash_payments)
    total_paid = total_bank + total_cash
    invoice_total = invoice.total_price
    remaining = invoice_total - total_paid  # مبلغ باقی‌مانده که مشتری بدهکار است
    print('remaining ',remaining)   
    
    weight_gold=0
    weight_labor=0
    weight_seller=0
    money_gold=0
    money_labor=0
    money_seller=0
    #weight_purity = ( weight * purity ) / 750
    
    if type == 'abshode' :
        desc_entry = f"سند فروش آبشده فاکتور {invoice.number} به {invoice.customer.name}"
        desc_gold=f" خروج طلا بابت فروش آبشده فاکتور : {invoice.number}"
        desc_labor_p=f" هزینه اجرت خرید برای فروش آبشده فاکتور  {invoice.number}"
        desc_labor_s=f" درامد اجرت فروش آبشده فاکتور  {invoice.number}"
        desc_customer=f"فروش آبشده فاکتور  {invoice.number}"
        desc_cogs=f"بهای تمام شده فروش آبشده فاکتور  {invoice.number}"
        desc_bank=f"دریافت  برای فاکتور فروش آبشده {invoice.number}"
        desc_cash=f"دریافت نقدی برای فاکتور فروش آبشده {invoice.number}"
        desc_price= f"درآمد فروش آبشده فاکتور {invoice.number}"
        desc_profit = f"سود فروش آبشده فاکتور {invoice.number}"
        
    else :
        desc_entry = f"سند فروش طلا فاکتور {invoice.number} به {invoice.customer.name}"
        desc_gold=f" خروج طلا بابت فروش طلا فاکتور : {invoice.number}"
        desc_labor_p=f" هزینه اجرت خرید برای فروش طلا فاکتور  {invoice.number}"
        desc_labor_s=f"درامد اجرت فروش طلا فاکتور  {invoice.number}"
        desc_customer=f"فروش طلا فاکتور  {invoice.number}"
        desc_cogs=f"بهای تمام شده فروش طلا فاکتور  {invoice.number}"
        desc_bank=f"دریافت  برای فاکتور فروش  طلا {invoice.number}"
        desc_cash=f"دریافت نقدی برای فاکتور فروش  طلا {invoice.number}"
        desc_price= f"درآمد فروش طلا فاکتور {invoice.number}"
        desc_profit = f"سود فروش طلا فاکتور {invoice.number}"
    
    total_gold_weight = 0
    total_sale_money = 0
    total_profit = 0
    labor_buy_total = 0
    labor_sell_total = 0
    labor_amount_p = 0
    labor_amount_s =0 
    total_buy_money = 0
    total_labor = 0 
    total_labor_price = 0
       
    with transaction.atomic():

            entry = JournalEntry.objects.create(
                date = invoice.date or timezone.now().date(),
                description = desc_entry,
                related_sale=invoice
            )
            print(entry)
            for it in items:
                price = to_decimal(str(it.gold_price_per_gram or 0))
                mesghal = to_decimal(str(it.gold_price_mesghal or 0))
                weight = to_decimal(str(it.weight or 0))
                labor_p=to_decimal(str(it.product.labor))
                laborprice_p=to_decimal(str(it.product.laborprice))
                total_price = to_decimal(str(it.total or 0))
                profit = to_decimal (str(it.profit_total or 0))    
                labor_s = to_decimal(str(it.labor_per_gram or 0))
                laborprice_s = to_decimal (str(it.labor_price or 0))
                #product_price = to_decimal(it.product.price)
                purity = to_decimal(str(it.purity))
                if mesghal > 0 :
                    price = mesghal / Decimal('4.608')
                    price = price.quantize(Decimal('1'))  # معادل round()
                    
                if price > 0 and total_price > 0 :
                    if laborprice_p > 0 :
                        labor_amount_p = ((weight* purity ) / 750 )* laborprice_p
                    if labor_p > 0 :
                        labor_amount_p = (( labor_p * weight) / 100) * price
                        
                    if laborprice_s > 0 :
                        labor_amount_s = weight* laborprice_s
                    if labor_s > 0 :
                        labor_amount_s = (( labor_s * weight) / 100) * price
                    
                    total_gold_weight += weight
                    total_sale_money += total_price
                    total_profit += profit
                    labor_buy_total += labor_amount_p
                    labor_sell_total += labor_amount_s
                
                if total_price == 0 : 
                    total_gold_weight +=weight 
                    print(laborprice_s)
                    print(labor_s)
                    if laborprice_s > 0 :
                        labor_price_amount_s = ((weight* purity ) / 750 )* laborprice_s
                        total_labor_price +=labor_price_amount_s 
                    if labor_s > 0 :
                        labor_amount_s = (( labor_s * weight) / 100)   
                        total_labor += labor_amount_s
                    
                
            
            COGS = Decimal(total_sale_money) - Decimal(total_profit)
                
            # --------------------------------------------
            # 3) کاهش موجودی طلا (وزنی)
            # --------------------------------------------
            JournalItem.objects.create(
                entry=entry,
                account=inventory_account,
                debit_gold=Decimal('0'),
                credit_gold=Decimal(total_gold_weight),
                description=desc_gold
            )
            print('tala')
            
            if price > 0 and total_price > 0 :
                # --------------------------------------------
                # 4) ثبت بهای تمام‌شده
                # --------------------------------------------
                if COGS > 0 :
                    JournalItem.objects.create(
                        entry=entry,
                        account=cogs_account,
                        debit_money=COGS,
                        description= desc_cogs
                    )   
                    print('baha')
                # --------------------------------------------
                # 5) ثبت هزینه اجرت خرید (اگر وجود دارد)
                # --------------------------------------------
                if labor_amount_p >  0:
                    JournalItem.objects.create(
                        entry=entry,
                        account=labor_account_p,
                        debit_money=labor_amount_p,
                        credit_money=0,
                        description= desc_labor_p
                    )
                print('labor')
                # --------------------------------------------
                # 6) درآمد فروش طلا
                # --------------------------------------------
                if total_sale_money > 0 :
                    JournalItem.objects.create(
                        entry=entry,
                        account=sales_account,
                        credit_money=total_sale_money,
                        description="درآمد فروش طلا"
                    )
                    print('forosh')
                # --------------------------------------------
                # 7) درآمد اجرت فروش (اگر وجود دارد)
                # --------------------------------------------
                if labor_amount_s > 0:
                    JournalItem.objects.create(
                        entry=entry,
                        account=labor_account_s,
                        credit_money=labor_amount_s,
                        description=desc_labor_s
                    )
                print('daramad')
                # --------------------------------------------
                # 8) ثبت سود
                # --------------------------------------------
                if total_profit > 0 :
                    JournalItem.objects.create(
                        entry=entry,
                        account=profit_account,
                        credit_money=total_profit,
                        description="سود فروش طلا"
                    )
                    print('sood')
                # --------------------------------------------
                # 9) بدهکار مشتری
                # --------------------------------------------
                if total_sale_money > 0 :
                    JournalItem.objects.create(
                        entry=entry,
                        account=customer.account,
                        debit_money=total_sale_money,
                        description=desc_customer
                    )
                    print('customer')
                
                if total_paid > 0 :
                    # 2️⃣ ایجاد سند حسابداری خودکار
                    entry = JournalEntry.objects.create(
                            date = invoice.date or timezone.now().date(),
                            description=f"پرداخت فاکتور فروش {invoice.number}",
                            related_sale=invoice
                        )
                    
                    for i in range(len(bank_payments)): 
                        amt = to_decimal(bank_payments[i] or 0) 
                        print(amt)
                        if amt <= 0:  
                            continue
                        bank_id = bank_ids[i]
                        bank = BankAccount.objects.get(id=bank_id)
                        bank_account = bank.account
                        
                        # 4️⃣ بستانکار: صندوق/بانک (کاهش موجودی)
                        JournalItem.objects.create(
                            entry=entry,
                            account=bank_account,
                            debit_money=amt,
                            description= desc_bank
                        )
                        # 3️⃣ بدهکار: حساب پرداختنی فروشنده (کاهش بدهی)          
                        JournalItem.objects.create(
                            entry=entry,
                            account=customer.account,
                            credit_money=amt,
                            description= desc_bank,
                        )
                        print('hala')
                        
                        
                    for i in range(len(cash_payments)): 
                        amt = to_decimal(cash_payments[i] or 0) 
                        print(amt)
                        if amt <= 0:  
                            continue
                        cash_id = cash_ids[i]
                        cash = CashAccount.objects.get(id=cash_id)
                        cash_account = cash.account

                        # بدهکار cash
                        JournalItem.objects.create(
                            entry=entry,
                            account=cash_account,
                            debit_money=amt,
                            description= desc_cash
                        )
                        # بستانکار فروشنده            
                        JournalItem.objects.create(
                            entry=entry,
                            account=customer.account,
                            credit_money=amt,
                            description= desc_cash,
                        )
                        print('inja')
                    
            if total_price == 0 : 
                gold = total_gold_weight + total_labor
                money = total_labor_price
                JournalItem.objects.create(
                    entry=entry,
                    account=customer.account,
                    debit_gold=gold,
                    debit_money = money,
                    description=desc_customer
                    )
                if total_labor_price >  0 or total_labor > 0 :
                    JournalItem.objects.create(
                        entry=entry,
                        account=labor_account_s,
                        credit_gold=total_labor,
                        credit_money=total_labor_price,
                        description=desc_labor_s
                    )
                print('daramad')
                print('customer')
        
    return entry 

@login_required(login_url='/')  # مسیر صفحه لاگین شما
def create_invoice_with_payment(request):
    mgtransaction = None

    # گرفتن آخرین شماره فاکتور و تولید شماره بعدی
    last_invoice = Invoice.objects.order_by('-id').first()  # بهتر است بر اساس id آخرین را بگیریم
    if last_invoice and last_invoice.number.isdigit():       # فقط اگر number عددی است
        invoice_number = str(int(last_invoice.number) + 1)
    else:
        invoice_number = "1000"  # شماره شروع

    now = timezone.localtime()  # زمان محلی فعلی
    date = now.date()   # فقط تاریخ
    
    invoice_time = now.strftime("%H:%M")  # فقط ساعت به صورت string
    # تبدیل تاریخ میلادی به شمسی
    invoice_date = jdatetime.date.fromgregorian(date=now.date()).strftime("%Y/%m/%d")
    print(date)
    print(invoice_date)
    
    if request.method == 'POST':
        print('post')
        try:
            with transaction.atomic():

                # مدیریت مشتری
                customer_id = request.POST.get('customer_select')  # اگر از سلکت انتخاب شده
                invoice_d=request.POST.get('invoice_date')
                i_n=request.POST.get('invoice_number')
                print("tarikh ",invoice_d)
                phone = request.POST.get('phone')
                birth_date_shamsi = request.POST.get("birth_date")  # YYYY/MM/DD
                print("customerid ",customer_id)
                print(phone)
                print("shamsi",birth_date_shamsi)
                date_gregorian = None
                if invoice_d:
                    try:
                        # تبدیل رشته به jdatetime.date
                        parts = invoice_d.split("/")
                        if len(parts) == 3:
                            jy, jm, jd = map(int, parts)
                            date_gregorian = jdatetime.date(jy, jm, jd).togregorian()
                    except Exception as e:
                        return JsonResponse({"success": False, "errors": {"invoice_date": ["تاریخ فاکتور نامعتبر است"]}})
                birth_date_gregorian = None
                if birth_date_shamsi:
                    try:
                        # تبدیل رشته به jdatetime.date
                        parts = birth_date_shamsi.split("/")
                        if len(parts) == 3:
                            jy, jm, jd = map(int, parts)
                            birth_date_gregorian = jdatetime.date(jy, jm, jd).togregorian()
                    except Exception as e:
                        return JsonResponse({"success": False, "errors": {"birth_date": ["تاریخ تولد نامعتبر است"]}})

                print("میلادی",birth_date_gregorian)
                customer = None
                if customer_id =="" and phone =="" :
                    print("nist")
                    return JsonResponse({
                        "success": False,
                        "errors": "لطفا مشتری رو وارد کنید . "
                    })
                    
                if customer_id:
                    # از سلکت انتخاب شده
                    customer = Person.objects.filter(id=customer_id).first()
                else:
                    if phone:
                        phone = persian_to_english_digits(phone)
                        customer = Person.objects.filter(phone=phone).first()
                        if customer:
                            # بروزرسانی اطلاعات
                            customer.name = request.POST.get('name') or customer.name
                            if birth_date_gregorian:
                                customer.birth_date = birth_date_gregorian
                            customer.save()
                        else:
                            #customer_code=generate_next_person_code()
                            data = request.POST.copy()
                            data['birth_date'] = birth_date_gregorian  # تاریخ میلادی به فرم بده
                            data['type_partner'] = 'customer'
                            #data['code'] = customer_code  # ← اضافه کردن کد به فرم
                            customer_form = PersonForm(data)
                            if customer_form.is_valid():
                                customer = customer_form.save()
                            else:
                                return JsonResponse({"success": False, "errors": customer_form.errors})
                                        # تعیین جنسیت خودکار بر اساس نام
                    if customer:
                        if customer.name:
                            if 'خانم' in customer.name:
                                customer.gender = 'female'
                            else:
                                customer.gender = 'male'
                            customer.save()
                    else:
                        return JsonResponse({
                            "success": False,
                            "errors": "مشتری پیدا نشد. لطفاً شماره تلفن یا انتخاب مشتری را وارد کنید."
                        })

                # گرفتن اطلاعات محصولات
                products = request.POST.getlist('product[]')
                quantities = request.POST.getlist('quantity[]')
                prices = request.POST.getlist('price[]')
                weights = request.POST.getlist('weight[]')
                labors = request.POST.getlist('labor_per_g[]')
                puritys = request.POST.getlist('purity[]')
                laborsprice = request.POST.getlist('labor_price[]')
                profits = request.POST.getlist('profit[]')
                totals = request.POST.getlist('total[]')
                weightkasrs=request.POST.getlist('weightkasr[]')
                p_ts=request.POST.getlist('total_gallery[]')
                print(totals)
                print(p_ts)
                print(laborsprice)
                total_invoice = 0
                total_profit=0
            #with transaction.atomic():
                invoice = Invoice.objects.create(
                    number=str(i_n),
                    customer=customer,
                    date=date_gregorian,
                    time=invoice_time,
                    user=request.user,
                    total_price=0,
                    profit_total=0,
                )
                

                for i in range(len(products)):
                    if not products[i]:
                        continue

                    product = Product.objects.get(id=products[i])
                    qty = int(quantities[i])
                    print("qty: ",qty)
                    weightkasr = to_decimal(weightkasrs[i])
                    price = to_decimal(prices[i] or 0)

                    #price = float(prices[i] or 0)
                    weight =to_decimal(weights[i] or 0)
                    #weightkasr=float(weightkasrs[i] or 0)
                    labor = to_decimal(labors[i] or 0)
                    print(labor)
                    laborprice = to_decimal(laborsprice[i] or 0)
                    print(laborprice)
                    purity = to_decimal(puritys[i] or 0)
                    profit = to_decimal(profits[i])
                    total = to_decimal(totals[i])
                    x = to_decimal(p_ts[i])
                    print("total ",total)
                    print('x ',x)
                    p_t=total-x
                    print(p_t)
                    
                    if weightkasr:
                            # گرفتن محصول آب‌شده فروشگاه (کد 1)
                        product_melted, created = Product.objects.get_or_create(
                            code='1',
                            defaults={
                                'name': 'آب‌شده فروشگاه',
                                'category': 'mot',  # متفرقه یا آب‌شده
                                'weight': 0,
                                'purity': '750',
                                'labor': 0,
                                'quantity': 1
                            }
                        )
                        # اضافه کردن وزن کسری به وزن محصول آب‌شده
                        product_melted.weight += to_decimal(weightkasr)
                        product_melted.save()
                        weightkasr = to_decimal(weightkasr)
                        price = to_decimal(price)

                        x = weightkasr * price
                        print("x ",x)
                        p_t += x
                        print("pt ",p_t)
                        # ثبت تراکنش آب‌شده فروشگاه
                        mgtransaction = MeltedGoldTransaction.objects.create(
                            melted_gold=product_melted,
                            transaction_type="IN",
                            source=f"کسری فاکتور {invoice.number}",
                            destination="فروشگاه",
                            weight=weightkasr,
                            price_per_gram=price,  # قیمت هر گرم (می‌توانی انتخابی باشد)
                            total_price=weightkasr * Decimal(str(price)),  # محاسبه کل مبلغ
                            date=date,
                            note=f" اضافه شده از کسری فاکتور فروش {invoice.number}"
                        )
                    
                    print(product.category)
                    # اگر دسته‌بندی 'ab' یا 'متفرقه' است → کاهش وزن
                    if product.category in ['ab', 'mot']:
                        print("category")
                        product.weight -= Decimal(str(weightkasr))
                        product.save()
                        
                    # بررسی موجودی
                    if qty > product.quantity:
                        return JsonResponse({
                            "success": False,
                            "stock_error": True,
                            "message": f"کالا '{product.name}' موجودی کافی ندارد. موجودی فعلی: "
                        })
                    print('here')
                    
                    # ایجاد آیتم فاکتور با تمام فیلدها
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        product=product,
                        quantity=qty,
                        purity=purity,
                        gold_price_per_gram=price,
                        weight=weight,
                        labor_per_gram=labor,
                        labor_price=laborprice,
                        profit_percent=profit,
                        profit_total=p_t,
                        total=total
                    )
                    

                    # کاهش موجودی
                    product.quantity -= qty
                    product.save()
                    print('total item',total)
                    total_invoice += total
                    total_profit += p_t
                    

                print(total_invoice)
                invoice.total_price = total_invoice
                invoice.profit_total=total_profit
                invoice.save()
                #save_payment_for_invoice(request, invoice)
                
                bank_payments = request.POST.getlist('bank_amount[]')
                bank_ids = request.POST.getlist('bank_id[]')         # لیست آیدی هر بانک
                cash_payments = request.POST.getlist('cash_amount[]')
                cash_ids = request.POST.getlist('cash_id[]') 
                create_sale_journal(invoice,bank_payments,bank_ids,cash_payments,cash_ids,"tala")
                print("✅ Journal created")
                
                #create_sale_journal(invoice)
                # --- آپدیت امتیاز مشتری ---
                customer_crm, created = CustomerCRM.objects.get_or_create(customer=customer)

                # آپدیت مجموع خریدها
                customer_crm.total_purchases += Decimal(total_invoice)

                # ذخیره تاریخ آخرین خرید
                customer_crm.last_purchase = timezone.now().date()

                # محاسبه امتیاز: هر 10 میلیون = 1 امتیاز
                points_earned = int(total_invoice // 10_000_000)
                if points_earned > 0:
                    customer_crm.loyalty_points += points_earned

                customer_crm.save()
                print(f"✅ {points_earned} امتیاز جدید به {customer.name} اضافه شد. مجموع امتیاز: {customer_crm.loyalty_points}")

                
                # --- ارسال SMS ---
                
                if customer and customer.phone:
                    message = (
                        f"Dear {customer.name}, thank you for your purchase! "
                        f"Your invoice #{invoice.number} has been issued. "
                        f"Total amount: {int(invoice.total_price):,} $. "
                        f"We look forward to serving you again.MIRA JEWELLERY"
                    )
                    send_sms(customer.phone, message)
            # ta  inja tab fonvi  
            print('✅ Invoice successfully saved')
            return JsonResponse({
                "success": True,
                'result':True,
                "invoice_id": invoice.id,
                "invoice_number": invoice.number
            })
        except Exception as e:
            print("خطای پایگاه داده:", e)
            print("customer:", customer)
            return JsonResponse({"success": False, "errors": str(e)})

    else:
        banks = BankAccount.objects.select_related('bank', 'account')
        cash_account = Account.objects.get(code="101")  # صندوق کد 101
        customer_form = PersonForm()
        products = Product.objects.all()
        product=Product.objects.filter(category__in=['ab','mot'])
        persons = Person.objects.filter(type_partner__in=['partner', 'supplier'])
        return render(request, 'invoice.html', {
            'invoice_number': invoice_number,
            'invoice_date': invoice_date,
            'current_time': invoice_time,
            'customer_form': customer_form,
            'persons':persons,
            'products': products,
            'product2': product,
            'banks':banks,
            'cash_account':cash_account,
        })



def to_decimal(val):
    if not val or str(val).strip() == "":
        return Decimal(0)

    # تبدیل ارقام فارسی
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"
    val = str(val)
    for p, e in zip(persian_digits, english_digits):
        val = val.replace(p, e)

    # حذف کاما
    val = val.replace(",", "")

    return Decimal(val)




@login_required(login_url='/')  # مسیر صفحه لاگین شما
def invoice_view(request):
    data = get_gold_prices()  # داده‌ها از API گرفته می‌شود

    # اگر فقط می‌خوای در console چاپ شود
    import json
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    mgtransaction = None
    


    # گرفتن آخرین شماره فاکتور و تولید شماره بعدی
    last_invoice = Invoice.objects.order_by('-id').first()  # بهتر است بر اساس id آخرین را بگیریم
    if last_invoice and last_invoice.number.isdigit():       # فقط اگر number عددی است
        invoice_number = str(int(last_invoice.number) + 1)
    else:
        invoice_number = "1000"  # شماره شروع

    now = timezone.localtime()  # زمان محلی فعلی
    date = now.date()   # فقط تاریخ
    
    invoice_time = now.strftime("%H:%M")  # فقط ساعت به صورت string
    # تبدیل تاریخ میلادی به شمسی
    invoice_date = jdatetime.date.fromgregorian(date=now.date()).strftime("%Y/%m/%d")
    print(date)
    print(invoice_date)
    
    if request.method == 'POST':
        print('post')
        try:
            # مدیریت مشتری
            customer_id = request.POST.get('customer_select')  # اگر از سلکت انتخاب شده
            invoice_d=request.POST.get('invoice_date')
            i_n=request.POST.get('invoice_number')
            print("tarikh ",invoice_d)
            phone = request.POST.get('phone')
            birth_date_shamsi = request.POST.get("birth_date")  # YYYY/MM/DD
            print("customerid ",customer_id)
            print(phone)
            print("shamsi",birth_date_shamsi)
            date_gregorian = None
            if invoice_d:
                try:
                    # تبدیل رشته به jdatetime.date
                    parts = invoice_d.split("/")
                    if len(parts) == 3:
                        jy, jm, jd = map(int, parts)
                        date_gregorian = jdatetime.date(jy, jm, jd).togregorian()
                except Exception as e:
                    return JsonResponse({"success": False, "errors": {"invoice_date": ["تاریخ فاکتور نامعتبر است"]}})
            birth_date_gregorian = None
            if birth_date_shamsi:
                try:
                    # تبدیل رشته به jdatetime.date
                    parts = birth_date_shamsi.split("/")
                    if len(parts) == 3:
                        jy, jm, jd = map(int, parts)
                        birth_date_gregorian = jdatetime.date(jy, jm, jd).togregorian()
                except Exception as e:
                    return JsonResponse({"success": False, "errors": {"birth_date": ["تاریخ تولد نامعتبر است"]}})

            print("میلادی",birth_date_gregorian)
            customer = None
            if customer_id:
                # از سلکت انتخاب شده
                customer = Person.objects.filter(id=customer_id).first()
            else:
                if phone:
                    phone = persian_to_english_digits(phone)
                    customer = Person.objects.filter(phone=phone).first()
                    if customer:
                        # بروزرسانی اطلاعات
                        customer.name = request.POST.get('name') or customer.name
                        if birth_date_gregorian:
                            customer.birth_date = birth_date_gregorian
                        customer.save()
                    else:
                        customer_code=generate_next_person_code()
                        data = request.POST.copy()
                        data['birth_date'] = birth_date_gregorian  # تاریخ میلادی به فرم بده
                        data['type_partner'] = 'customer'
                        data['code'] = customer_code  # ← اضافه کردن کد به فرم
                        customer_form = PersonForm(data)
                        if customer_form.is_valid():
                            customer = customer_form.save()
                        else:
                            return JsonResponse({"success": False, "errors": customer_form.errors})
                                    # تعیین جنسیت خودکار بر اساس نام
                if customer:
                    if customer.name:
                        if 'خانم' in customer.name:
                            customer.gender = 'female'
                        else:
                            customer.gender = 'male'
                        customer.save()
                else:
                    return JsonResponse({
                        "success": False,
                        "errors": "مشتری پیدا نشد. لطفاً شماره تلفن یا انتخاب مشتری را وارد کنید."
                    })

            # گرفتن اطلاعات محصولات
            products = request.POST.getlist('product[]')
            quantities = request.POST.getlist('quantity[]')
            prices = request.POST.getlist('price[]')
            weights = request.POST.getlist('weight[]')
            labors = request.POST.getlist('labor_per_g[]')
            profits = request.POST.getlist('profit[]')
            totals = request.POST.getlist('total[]')
            weightkasrs=request.POST.getlist('weightkasr[]')
            p_ts=request.POST.getlist('total_gallery[]')
            print(totals)
            print(p_ts)
            total_invoice = 0
            total_profit=0
            with transaction.atomic():
                invoice = Invoice.objects.create(
                    number=str(i_n),
                    customer=customer,
                    date=date_gregorian,
                    time=invoice_time,
                    user=request.user,
                    total_price=0,
                    profit_total=0,
                )
                

                for i in range(len(products)):
                    if not products[i]:
                        continue

                    product = Product.objects.get(id=products[i])
                    qty = int(quantities[i])
                    print("qty: ",qty)
                    weightkasr = Decimal(str(weightkasrs[i] or 0))
                    price = Decimal(str(prices[i] or 0))

                    #price = float(prices[i] or 0)
                    weight = Decimal(str(weights[i] or 0))
                    #weightkasr=float(weightkasrs[i] or 0)
                    labor = Decimal(str(labors[i] or 0))
                    profit = Decimal(str(profits[i] or 0))
                    total = Decimal(str(totals[i] or 0))
                    x=Decimal(str(p_ts[i] or 0))
                    print(x)
                    p_t=total-x
                    print(p_t)
                    
            
                    if weightkasr:
                            # گرفتن محصول آب‌شده فروشگاه (کد 1)
                        product_melted, created = Product.objects.get_or_create(
                            code='1',
                            defaults={
                                'name': 'آب‌شده فروشگاه',
                                'category': 'mot',  # متفرقه یا آب‌شده
                                'weight': 0,
                                'purity': '750',
                                'labor': 0,
                                'quantity': 1
                            }
                        )
                        # اضافه کردن وزن کسری به وزن محصول آب‌شده
                        product_melted.weight += Decimal(str(weightkasr))
                        product_melted.save()
                        weightkasr = Decimal(str(weightkasr))
                        price = Decimal(str(price))

                        x = weightkasr * price
                        print("x ",x)
                        p_t += x
                        print("pt ",p_t)
                        # ثبت تراکنش آب‌شده فروشگاه
                        mgtransaction = MeltedGoldTransaction.objects.create(
                            melted_gold=product_melted,
                            transaction_type="IN",
                            source=f"کسری فاکتور {invoice_number}",
                            destination="فروشگاه",
                            weight=weightkasr,
                            price_per_gram=price,  # قیمت هر گرم (می‌توانی انتخابی باشد)
                            total_price=weightkasr * Decimal(str(price)),  # محاسبه کل مبلغ
                            date=date,
                            note=f" اضافه شده از کسری فاکتور فروش {invoice.number}"
                        )
                    
                    print(product.category)
                    # اگر دسته‌بندی 'ab' یا 'متفرقه' است → کاهش وزن
                    if product.category in ['ab', 'mot']:
                        print("category")
                        product.weight -= Decimal(str(weightkasr))
                        product.save()
                        
                    # بررسی موجودی
                    if qty > product.quantity:
                        return JsonResponse({
                            "success": False,
                            "stock_error": True,
                            "message": f"کالا '{product.name}' موجودی کافی ندارد. موجودی فعلی: "
                        })
                    
                    # ایجاد آیتم فاکتور با تمام فیلدها
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        product=product,
                        quantity=qty,
                        gold_price_per_gram=price,
                        weight=weight,
                        labor_per_gram=labor,
                        profit_percent=profit,
                        profit_total=p_t,
                        total=total
                    )
                    

                    # کاهش موجودی
                    product.quantity -= qty
                    product.save()
                    print('total item',total)
                    total_invoice += total
                    total_profit += p_t
                    

                print(total_invoice)
                invoice.total_price = total_invoice
                invoice.profit_total=total_profit
                invoice.save()
                #save_payment_for_invoice(request, invoice)
                try:
                    #create_sale_journal_new(invoice)
                    print("✅ Journal created")
                except Exception as e:
                    import traceback
                    print("❌ Error in journal creation:")
                    traceback.print_exc()

                #create_sale_journal(invoice)
                # --- آپدیت امتیاز مشتری ---
                customer_crm, created = CustomerCRM.objects.get_or_create(customer=customer)

                # آپدیت مجموع خریدها
                customer_crm.total_purchases += Decimal(total_invoice)

                # ذخیره تاریخ آخرین خرید
                customer_crm.last_purchase = timezone.now().date()

                # محاسبه امتیاز: هر 10 میلیون = 1 امتیاز
                points_earned = int(total_invoice // 10_000_000)
                if points_earned > 0:
                    customer_crm.loyalty_points += points_earned

                customer_crm.save()
                print(f"✅ {points_earned} امتیاز جدید به {customer.name} اضافه شد. مجموع امتیاز: {customer_crm.loyalty_points}")

                
                # --- ارسال SMS ---
                
                if customer and customer.phone:
                    message = (
                        f"Dear {customer.name}, thank you for your purchase! "
                        f"Your invoice #{invoice.number} has been issued. "
                        f"Total amount: {int(invoice.total_price):,} $. "
                        f"We look forward to serving you again.MIRA JEWELLERY"
                    )
                    send_sms(customer.phone, message)
                

            return JsonResponse({
                "success": True,
                "invoice_id": invoice.id,
                "invoice_number": invoice.number
            })
        except Exception as e:
            print("خطای پایگاه داده:", e)
            print("customer:", customer)
            #print("product_ids:", product)
            return JsonResponse({"success": False, "errors": str(e)})


    else:
        banks = BankAccount.objects.all()
        cash_account = CashAccount.objects.all()
        customer_form = PersonForm()
        products = Product.objects.exclude(category__in=['ab', 'mot'])
        product=Product.objects.filter(category__in=['ab','mot'])
        persons = Person.objects.filter(type_partner__in=['partner', 'supplier'])
        return render(request, 'invoice.html', {
            'invoice_number': invoice_number,
            'invoice_date': invoice_date,
            'current_time': invoice_time,
            'customer_form': customer_form,
            'persons':persons,
            'products': products,
            'product2': product,
            'banks':banks,
            'cash_account':cash_account,
        })

def invoice_test(request):
    product=request.POST.getlist('product[]')
    total=request.POST.getlist('total[]')
    print(product)
    print(total)
    return JsonResponse({
                    "success": False,
                    "errors": "مشتری پیدا نشد. لطفاً شماره تلفن یا انتخاب مشتری را وارد کنید."
                })
    
    
@login_required(login_url='/')
def invoice_ab(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():   # ⭐ کل فرآیند 100% اتمیک
                date = request.POST.get('invoice_date2')
                time = request.POST.get('current_time2')
                number = request.POST.get('invoice_number2')
                print(date)
                print(number)
                print(time)
                # دریافت اطلاعات مشتری
                customer_id = request.POST.get('customer_select2')
                phone = request.POST.get('phone2')
                birth_sh = request.POST.get("birth_date2")
                invoice_d = request.POST.get('invoice_date2')
                invoice_n = request.POST.get('invoice_number2')
                print(customer_id)
                print(phone)
                print(birth_sh)
                # تبدیل تاریخ‌ها
                def sh_to_gr(s):
                    if not s: return None
                    jy, jm, jd = map(int, s.split("/"))
                    return jdatetime.date(jy, jm, jd).togregorian()

                birth_gr = sh_to_gr(birth_sh)
                invoice_date_gr = sh_to_gr(invoice_d)
                print(birth_gr)
                print(invoice_date_gr)
                # مدیریت مشتری
                if customer_id =="" and phone =="" :
                    print("nist")
                    return JsonResponse({
                        "success": False,
                        "errors": "لطفا مشتری رو وارد کنید . "
                    })
                if customer_id:
                    customer = Person.objects.filter(id=customer_id).first()
                    print(customer)
                if phone:
                        phone = persian_to_english_digits(phone)
                        customer = Person.objects.filter(phone=phone).first()
                        print(customer)
                        if customer:
                            # بروزرسانی اطلاعات
                            customer.name = request.POST.get('name') or customer.name
                            if birth_gr:
                                customer.birth_date = birth_gr
                            customer.save()
                        else:
                            
                            person_data = {
                                
                                "name": request.POST.get("name2"),
                                "phone": phone,
                                "type_partner":"customer",
                            }
                            print(person_data)
                            customer_form = PersonForm(person_data)

                            if customer_form.is_valid():
                                customer = customer_form.save()
                            else:
                                return JsonResponse({"success": False, "errors": customer_form.errors})
                                        # تعیین جنسیت خودکار بر اساس نام
                if customer:
                    if customer.name:
                        if 'خانم' in customer.name:
                            customer.gender = 'female'
                        else:
                            customer.gender = 'male'
                        customer.save()
                else:
                    return JsonResponse({
                        "success": False,
                        "errors": "مشتری پیدا نشد. لطفاً شماره تلفن یا انتخاب مشتری را وارد کنید."
                    })
                
                print("here")
                # دریافت لیست آیتم‌ها
                products = request.POST.getlist('product2[]')
                weights = request.POST.getlist('weight2[]')
                weight_sells = request.POST.getlist('weightkasr2[]')
                puritys = request.POST.getlist('purity2[]')
                labors = request.POST.getlist('labor2[]')
                laborsprice = request.POST.getlist('laborprice2[]')
                prices = request.POST.getlist('price2[]')
                mesghals = request.POST.getlist('mesghal2[]')
                totals = request.POST.getlist('total2[]')
                print(prices)
                print(totals)
                total_invoice = 0

            #with transaction.atomic():
                invoice = Invoice.objects.create(
                    number=str(invoice_n),
                    customer=customer,
                    date=invoice_date_gr,
                    time=time,
                    user=request.user,
                    total_price=0,
                )

                for i in range(len(products)):
                    if not products[i]: continue
                    
                    product = Product.objects.get(id=products[i])
                    weight = to_decimal((weights[i] or 0))
                    weight_sell = to_decimal(weight_sells[i] or 0)
                    purity = to_decimal(puritys[i] or 0)
                    labor = to_decimal(labors[i] or 0)
                    laborprice = to_decimal(laborsprice[i] or 0)
                    price = to_decimal(prices[i] or 0)
                    mesghal = to_decimal(mesghals[i] or 0)
                    total = to_decimal(totals[i] or 0)
                    print(total)
                    # کاهش وزن موجودی
                    if product.category in ['ab', 'mot']:
                        product.weight -= weight_sell
                        product.save()
                    print('ksrvazn')
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        product=product,
                        weight=weight_sell,
                        purity=purity,
                        labor_per_gram=labor,
                        labor_price=laborprice,
                        gold_price_per_gram=price,
                        gold_price_mesghal = mesghal ,
                        quantity=1,
                        total=total,
                    )
                    print('item')
                    if customer_id:
                        flag = f"همکار - {customer.name}"
                    else:
                        flag = f"مشتری - {customer.name}"
                    
                    mgtransaction = MeltedGoldTransaction.objects.create(
                            melted_gold=product,
                            transaction_type="OUT",
                            source=f" فروش فاکتور {number}",
                            destination=flag,
                            weight=weight_sell,
                            price_per_gram=price,  # قیمت هر گرم (می‌توانی انتخابی باشد)
                            price_per_mesghal = mesghal , 
                            total_price=total,  # محاسبه کل مبلغ
                            date=invoice_date_gr,
                            note="کسر شده از فروش آبشده"
                        )

                    total_invoice += total

                invoice.total_price = total_invoice
                invoice.save()
                bank_payments = request.POST.getlist('bank_amount2[]')
                bank_ids = request.POST.getlist('bank_id2[]')         # لیست آیدی هر بانک
                cash_payments = request.POST.getlist('cash_amount2[]')
                cash_ids = request.POST.getlist('cash_id2[]') 
                create_sale_journal(invoice,bank_payments,bank_ids,cash_payments,cash_ids,"abshode")
                
                #create_sale_journal_for_melted(invoice)
                
                print("create")

            return JsonResponse({"success": True,"result":True, "invoice_id": invoice.id})

        except Exception as e:
            print("❌ ERROR:", e)
            return JsonResponse({"success": False, "errors": str(e)})

    # GET
    customers = Person.objects.filter(type_partner='customer')
    products = Product.objects.filter(category__in=['ab','mot'])

    return render(request, 'invoice.html', {
        'invoice_number2': number,
        'invoice_date2': date,
        'customers': customers,
        'product2': products
    })
   
 
def reports_dashboard(request):
    # فیلتر تاریخ از فرم GET
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    invoices = Invoice.objects.all()
    if start_date:
        invoices = invoices.filter(date__gte=start_date)
    if end_date:
        invoices = invoices.filter(date__lte=end_date)

    # فروش روزانه (کل)
    daily_sales = invoices.filter(date=now().date()).aggregate(total=Sum('total'))['total'] or 0
    daily_invoices_count = invoices.filter(date=now().date()).count()

    # پرفروش‌ترین محصولات
    top_products = InvoiceItem.objects.filter(invoice__in=invoices).values('product__name').annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum(F('quantity') * F('unit_price'))
    ).order_by('-total_sold')[:10]

    # مشتریان با بیشترین خرید
    top_customers = invoices.values('customer__name').annotate(
        total_spent=Sum('total'),
        invoice_count=Count('id')
    ).order_by('-total_spent')[:10]

    # نمودار فروش ماهانه
    monthly_sales = invoices.annotate(month=TruncMonth('date')).values('month').annotate(
        total=Sum('total')
    ).order_by('month')

    monthly_labels = [s['month'].strftime("%b %Y") for s in monthly_sales]
    monthly_data = [float(s['total']) for s in monthly_sales]

    context = {
        'daily_sales': daily_sales,
        'daily_invoices_count': daily_invoices_count,
        'top_products': top_products,
        'top_customers': top_customers,
        'monthly_labels': monthly_labels,
        'monthly_data': monthly_data,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'reports/dashboard.html', context)


#calender
def calender(request):
    return render(request,'calendar.html')

def invoices_by_date(request):
    date = request.GET.get("date")
    invoices = Invoice.objects.filter(invoice_date=date).select_related("customer")
    data = [
        {
            "number": inv.invoice_number,
            "customer_name": inv.customer.name,
            "total": inv.total_amount
        } for inv in invoices
    ]
    return JsonResponse({"invoices": data})

#CRM
@login_required(login_url='/')  # مسیر صفحه لاگین شما
def crm(request):
    # همه کمپین‌ها
    campaigns = RetentionCampaign.objects.all()

    # فیلترها
    search = request.GET.get('search', '')
    campaign_type = request.GET.get('campaign_type', '')
    active = request.GET.get('active', '')

    if search:
        campaigns = campaigns.filter(name__icontains=search)
    if campaign_type:
        campaigns = campaigns.filter(campaign_type=campaign_type)
    if active != '':
        campaigns = campaigns.filter(active=bool(int(active)))

    # KPI ها
    active_campaigns = RetentionCampaign.objects.filter(active=True).count()
    total_customers = Person.objects.filter(type_partner='customer').count()
    total_messages = CampaignLog.objects.count()
    # مشتریان بازگشتی (بیش از یک خرید)
    returning_customers = Person.objects.annotate(
        invoice_count=Count('invoice')
    ).filter(invoice_count__gt=1).count()
    #returning_customers = Customer.objects.filter(loyalty_points__gte=10).count()  # یا معیار وفاداری خودت

    # گزارش پیامک‌ها
    logs = CampaignLog.objects.select_related("campaign","customer").order_by("-sent_at")[:50]

    context = {
        "campaigns": campaigns,
        "logs": logs,
        "campaign_type_choices": RetentionCampaign.CAMPAIGN_TYPE,
        "active_campaigns": active_campaigns,
        "total_customers": total_customers,
        "total_messages": total_messages,
        "returning_customers": returning_customers,
    }

    return render(request,'crm.html',context)

# ساخت یا ویرایش کمپین
@csrf_exempt
def create_or_edit_campaign(request, pk=None):

    if pk:
        campaign = get_object_or_404(RetentionCampaign, pk=pk)
    else:
        campaign = None
    if request.method == "POST":
        data = request.POST.copy()  # نسخه قابل تغییر POST
        # تبدیل تاریخ شمسی به میلادی
        specific_date_shamsi = request.POST.get('specific_date')  # مثال: '1404/07/20'
        if specific_date_shamsi:
            try:
                jy, jm, jd = map(int, specific_date_shamsi.split("/"))
                specific_date_miladi = jdatetime.date(jy, jm, jd).togregorian()
                data['specific_date'] = specific_date_miladi  # جایگزین تاریخ میلادی
            except Exception as e:
                return JsonResponse({"success": False, "errors": {"specific_date": ["تاریخ نامعتبر است"]}})
        
        
        print(specific_date_shamsi)
        print(specific_date_miladi)
        form = RetentionCampaignForm(data, instance=campaign)
        print(form.errors)
        if form.is_valid():
            c = form.save()
            print(c.specific_date)
            return JsonResponse({
                "success": True,
                "id": c.id,
                "name": c.name,
                "campaign_type": c.campaign_type,
                "campaign_type_display": c.get_campaign_type_display(),
                "send_days_after_purchase": c.send_days_after_purchase,
                "specific_date": jdatetime.date.fromgregorian(date=c.specific_date).strftime("%Y/%m/%d") if c.specific_date else None,
                "loyalty_points": c.loyalty_points,
                "inactive_days": c.inactive_days,
                "message": c.message,
                "active": c.active
            })
        else:
            return JsonResponse({"success": False, "errors": form.errors})

@login_required
@csrf_exempt
def send_test_sms(request, campaign_id):
    try:
        campaign = RetentionCampaign.objects.get(id=campaign_id)
        user = request.user
        phone = getattr(user.userprofile, "phone", None)
        print("شماره موبایل:", phone)
        if not phone:
            return JsonResponse({"success": False, "error": "شماره تلفن برای کاربر لاگین شده ثبت نشده."})

        send_sms(phone, f"(تست) {campaign.message}")
        return JsonResponse({"success": True})

    except RetentionCampaign.DoesNotExist:
        return JsonResponse({"success": False, "error": "کمپین یافت نشد."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})
    
    
def campaign_json(request, pk):
    campaign = get_object_or_404(RetentionCampaign, pk=pk)
    return JsonResponse({
        "id": campaign.id,
        "name": campaign.name,
        "campaign_type": campaign.campaign_type,
        "send_days_after_purchase": campaign.send_days_after_purchase,
        "specific_date": jdatetime.date.fromgregorian(date=campaign.specific_date).strftime("%Y/%m/%d") if campaign.specific_date else None,
        "loyalty_points": campaign.loyalty_points,
        "inactive_days": campaign.inactive_days,
        "message": campaign.message,
        "active": campaign.active,
    })
    
@login_required(login_url='/')  # مسیر صفحه لاگین شما  
def reports(request):
    monthly_sales = []  # ← این خط اضافه شود قبل از هر عملیاتی روی invoices
    monthly_user_sales = []  # ← همین‌طور

    #invoices = Invoice.objects.all().order_by('-date')
    invoices = (
        Invoice.objects
        .annotate(
            total_weight=Coalesce(
                Sum('items__weight'),
                Value(0),
                output_field=DecimalField()
            )
        )
        .order_by('-date')
    )
    
    purchase = PurchaseInvoice.objects.all().order_by('-date')

    top_products = (
    InvoiceItem.objects
    .filter(invoice__in=invoices)
    .exclude(product__category__in=['ab', 'mot'])  # 🚫 حذف دسته‌های ab و mot
    .values(
        'product__name',
        'product__category',
        'product__weight',
        'product__code',
        'product__image',
        'product__description'
    )
    .annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum('total')
    )
    .order_by('-total_sold')[:100]
    )

    

        # مشتریان با بیشترین خرید
    top_customers = (
    invoices
    .filter(customer__type_partner='customer')  # فقط مشتری‌ها
    .values('customer__name', 'customer__phone')
    .annotate(
        total_spent=Sum('total_price'),
        invoice_count=Count('id')
    )
    .order_by('-total_spent')[:100]
)
    
    # --------- فروش روزانه ---------
        # گروه‌بندی بر اساس روز
    daily_sales_qs = (
        Invoice.objects
        .annotate(day=TruncDay('date'))
        .values('day')  # فقط روز
        .annotate(
            total_customers=Count('customer', distinct=True),  # تعداد مشتریان متمایز
            total_invoices=Count('id', distinct=True),  # تعداد فاکتورها
            #total_weights=Sum('items__weight'), # ← جمع وزن از آیتم‌ها
            total_amount=Sum('total_price') , # جمع کل مبلغ
            profit_total=Sum('profit_total'),
        )
        .order_by('-day')
    )
    
    # جمع وزن: کوئری جداگانه
    weight_qs = (
        InvoiceItem.objects
            .annotate(day=TruncDay('invoice__date'))
            .values('day')
            .annotate(total_weights=Sum('weight'))
    )

    # تبدیل weight_qs به دیکشنری روز → وزن
    weights_by_day = {w['day']: w['total_weights'] for w in weight_qs}

    # تبدیل QuerySet به لیست دیکشنری برای قالب
    daily_sales = []
    for sale in daily_sales_qs:
        day = sale['day']
        daily_sales.append({
            'date': sale['day'].strftime('%Y-%m-%d'),
            'total_customers': sale['total_customers'],
            'total_invoices': sale['total_invoices'],
            'total_weights': weights_by_day.get(day, 0),  # ← وزن اضافه شد
            'total_amount': sale['total_amount'],
            'profit_total':sale['profit_total']
        })
    # --------- فروش ماهانه  ---------
        monthly_data = {}
        for inv in invoices:
            jdate = JalaliDate.to_jalali(inv.date)
            key = (jdate.year, jdate.month)  # کلید گروه‌بندی

            if key not in monthly_data:
                monthly_data[key] = {
                    "total_customers": set(),
                    "total_invoices": 0,
                    "total_amount": 0,
                    "profit_total":0,
                }

            monthly_data[key]["total_customers"].add(inv.customer_id)
            monthly_data[key]["total_invoices"] += 1
            monthly_data[key]["total_amount"] += inv.total_price
            monthly_data[key]["profit_total"] += inv.profit_total

        # اسم ماه‌ها
        months_fa = [
            "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
            "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
        ]
        
        monthly_weights = {}

        for item in InvoiceItem.objects.select_related('invoice'):
            if not item.invoice.date:
                continue

            jdate = JalaliDate.to_jalali(item.invoice.date)
            key = (jdate.year, jdate.month)

            if key not in monthly_weights:
                monthly_weights[key] = 0

            monthly_weights[key] += item.weight or 0


        # مرتب‌سازی و آماده برای context
        monthly_sales = []
        for (year, month), data in sorted(monthly_data.items(), reverse=True):
            monthly_sales.append({
                "month": f"{months_fa[month - 1]} {year}",
                "total_customers": len(data["total_customers"]),
                "total_invoices": data["total_invoices"],
                "total_amount": data["total_amount"],
                "profit_total":data["profit_total"],
                "total_weights": monthly_weights.get((year, month), 0),  # ✅ درست
            })
            
        #Monthly User Sale
        monthly_user_data = {}
        
        for inv in invoices:


            #print(inv.user.id)
            jdate = JalaliDate.to_jalali(inv.date)
            
            key = (jdate.year, jdate.month, inv.user.id)

            if key not in monthly_user_data:
                monthly_user_data[key] = {
                    "user": inv.user.get_full_name() or inv.user.username,
                    "total_amount": 0,
                    "total_invoices": 0,
                    "profit_total":0,
                }

            monthly_user_data[key]["total_amount"] += inv.total_price
            monthly_user_data[key]["profit_total"] += inv.profit_total
            monthly_user_data[key]["total_invoices"] += 1

    # لیست ماه‌های فارسی
        months_fa = [
            "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
            "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
        ]
        
        monthly_user_weights = {}

        items = (
            InvoiceItem.objects
            .select_related('invoice', 'invoice__user')
        )

        for item in items:
            if not item.invoice or not item.invoice.date or not item.invoice.user:
                continue

            jdate = JalaliDate.to_jalali(item.invoice.date)
            key = (jdate.year, jdate.month, item.invoice.user_id)

            if key not in monthly_user_weights:
                monthly_user_weights[key] = 0

            monthly_user_weights[key] += item.weight or 0


    # خروجی مرتب
        monthly_user_sales = []
        for (year, month, user_id), data in sorted(monthly_user_data.items(), reverse=True):
            monthly_user_sales.append({
                "month": f"{months_fa[month - 1]} {year}",
                "user": data["user"],
                "total_invoices": data["total_invoices"],
                "total_amount": data["total_amount"],
                "profit_total":data["profit_total"],
                "total_weights": monthly_user_weights.get((year, month, user_id), 0),  # ✅ وزن
            })
    
    context = {
        'top_products': top_products,
        'top_customers': top_customers,
        'invoices': invoices,
        'purchase':purchase,
        'daily_sales': daily_sales,
        'monthly_sales': monthly_sales,
        'monthly_user_sales':monthly_user_sales,
    }

    return render(request, 'reports.html', context)



def parse_jalali(date_str):
    """تبدیل رشته شمسی YYYY/MM/DD به تاریخ میلادی"""
    try:
        jy, jm, jd = map(int, date_str.split("/"))
        return jdatetime.date(jy, jm, jd).togregorian()
    except:
        return None

import re

# تبدیل اعداد فارسی به انگلیسی
def persian_to_english_digits(s):
    if not s:
        return s
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    english_digits = '0123456789'
    trans_table = str.maketrans(persian_digits, english_digits)
    return s.translate(trans_table)

def invoice_search(request):
    invoices = Invoice.objects.all()

    invoice_number = request.GET.get("invoicenumber")
    if invoice_number:
        invoice_number = persian_to_english_digits(invoice_number)
    print(invoice_number)
    start_date_shamsi = request.GET.get("startdate")
    end_date_shamsi = request.GET.get("enddate")

    if invoice_number:
        invoices = invoices.filter(number__icontains=invoice_number)

    if start_date_shamsi:
        start_date = parse_jalali(start_date_shamsi)
        if start_date:
            invoices = invoices.filter(date__gte=start_date)

    if end_date_shamsi:
        end_date = parse_jalali(end_date_shamsi)
        if end_date:
            invoices = invoices.filter(date__lte=end_date)

    data = []
    for i, invoice in enumerate(invoices, start=1):
        # تبدیل تاریخ میلادی ذخیره‌شده در DB به شمسی برای نمایش
        date_shamsi = jdatetime.date.fromgregorian(date=invoice.date).strftime("%Y/%m/%d")

        data.append({
            "id": invoice.id,  # 🔹 اضافه شد
            "row": i,
            "number": invoice.number,
            "customer": invoice.customer.name if invoice.customer else "",
            "date": date_shamsi,  # 🔹 تاریخ شمسی برگردونده میشه
            "total_price": f"{invoice.total_price:,} ",
            "profit_total":f"{invoice.profit_total:,} ",
            "user": f"{invoice.user.first_name} {invoice.user.last_name}",
        })
    print(data)
    return JsonResponse({"results": data})

def purchase_search(request):
    invoices = PurchaseInvoice.objects.all()

    invoice_number = request.GET.get("purchasenumber")
    if invoice_number:
        invoice_number = persian_to_english_digits(invoice_number)
    print(invoice_number)
    start_date_shamsi = request.GET.get("startdate2")
    end_date_shamsi = request.GET.get("enddate2")

    if invoice_number:
        invoices = invoices.filter(number__icontains=invoice_number)

    if start_date_shamsi:
        start_date = parse_jalali(start_date_shamsi)
        if start_date:
            invoices = invoices.filter(date__gte=start_date)

    if end_date_shamsi:
        end_date = parse_jalali(end_date_shamsi)
        if end_date:
            invoices = invoices.filter(date__lte=end_date)

    data = []
    for i, invoice in enumerate(invoices, start=1):
        # تبدیل تاریخ میلادی ذخیره‌شده در DB به شمسی برای نمایش
        date_shamsi = jdatetime.date.fromgregorian(date=invoice.date).strftime("%Y/%m/%d")

        data.append({
            "id": invoice.id,  # 🔹 اضافه شد
            "row": i,
            "number": invoice.number,
            "seller": invoice.seller.name if invoice.seller else "",
            "type" : invoice.get_type_display(),  
            "weight" :invoice.weight , 
            "date": date_shamsi,  # 🔹 تاریخ شمسی برگردونده میشه
            "purity" : invoice.purity ,
            "price" : invoice.price ,
            "labor" : invoice.labor , 
            "laborprice" : invoice.laborprice , 
            "pricemesghal" : invoice.pricemesghal,
            "total_price": f"{invoice.total_price:,} ",
            #"user": f"{invoice.user.first_name} {invoice.user.last_name}",
        })
    print(data)
    return JsonResponse({"results": data})

# 🔹 صفحه اصلی: نمایش همه خریدها و فروش‌ها
def melted_gold_list(request):
   
    transactions = MeltedGoldTransaction.objects.filter(
        melted_gold__category='mot'
        ).order_by('-date', '-created_at')
    
    trans = MeltedGoldTransaction.objects.filter(
        melted_gold__category='ab'
    ).order_by('-date', '-created_at')
    all_ab_items = InvoiceItem.objects.select_related('invoice', 'product')\
        .filter(product__category__in=['ab'])\
        .order_by('-invoice__date')

    # تب 2: آب‌شده فروشگاه (می‌توان همان all_ab_items استفاده کرد یا فیلتر اضافه)
    store_ab_items = all_ab_items  # اگر نیاز به فیلتر فروشگاه داری، می‌توان اضافه کرد


    return render(request, 'meltedgold.html', {
       
        'transactions': transactions,
        'all_ab_items': all_ab_items,
        'store_ab_items': store_ab_items,
        'trans':trans
    })

# 🔹 افزودن خرید طلای آب‌شده
@csrf_exempt
def melted_gold_add_ajax(request):
    if request.method == "POST":
        code = request.POST.get("code")
        weight = request.POST.get("weight")
        purity = request.POST.get("purity")
        seller_name = request.POST.get("seller_name")
        seller_phone = request.POST.get("seller_phone")
        assay_office = request.POST.get("assay_office")
        date = request.POST.get("date") or timezone.now().date()

        # تبدیل وزن به Decimal
        try:
            weight = Decimal(weight)
        except (InvalidOperation, TypeError):
            return JsonResponse({"success": False, "error": "وزن نامعتبر است"})

        transaction_data = None  # برای ارسال به JS

        if code:  # کاربر کد تعریف کرده -> خرید جدید
            mg = MeltedGold.objects.create(
                code=code,
                weight_first=weight,
                weight=weight,
                purity=purity,
                seller_name=seller_name,
                seller_phone=seller_phone,
                assay_office=assay_office,
                date=date
            )
        else:  # کد وارد نشده -> اضافه کردن وزن به کد 1
            try:
                mg = MeltedGold.objects.get(code='1')  # یا فیلتر بر اساس code="1"
            except MeltedGold.DoesNotExist:
                return JsonResponse({"success": False, "error": "کد ۱ موجود نیست"})
            
            mg.weight += weight
            mg.save()

            # ثبت تراکنش ورود
            transaction = MeltedGoldTransaction.objects.create(
                melted_gold=mg,
                transaction_type="IN",
                source=seller_name or "نامشخص",
                weight=weight,
                date=date,
                note=f"خرید طلای آب‌ شده",
            )

            # تبدیل تاریخ به شمسی
            jalali_date_trans = date2jalali(transaction.date).strftime('%Y/%m/%d')
            transaction_data = {
                "transaction_type": transaction.transaction_type,
                "source": transaction.source,
                "destination": transaction.destination,
                "weight": str(transaction.weight),
                "date": jalali_date_trans,
                "note": transaction.note,
            }

        # تبدیل تاریخ به شمسی برای خرید
        jalali_date = date2jalali(date).strftime('%Y/%m/%d')

        return JsonResponse({
            "success": True,
            "id": mg.id,
            "code": mg.code,
            "weight_first": mg.weight if code else None,
            "weight": mg.weight,
            "purity": mg.purity if code else None,
            "seller_name": mg.seller_name if code else None,
            "seller_phone": mg.seller_phone if code else None,
            "assay_office": mg.assay_office if code else None,
            "date": jalali_date,
            "added_to_code_1": not bool(code),  # برای JS مشخص کنیم
            "transaction": transaction_data,    # ✅ ارسال تراکنش برای رفرش جدول
        })

    return JsonResponse({"success": False, "error": "درخواست نامعتبر است"})


# 🔹 افزودن فروش طلای آب‌شده

from django.db import transaction
@transaction.atomic
@csrf_exempt

def melted_gold_sale_add_ajax(request):
    if request.method == "POST":
        code = request.POST.get("code")
        name = request.POST.get("customer_name")
        phone_fa = request.POST.get("customer_phone")
        phone = persian_to_english_digits(phone_fa)
        weight = request.POST.get("weight")
        date = request.POST.get("date") or timezone.now().date()

        try:
            weight = Decimal(weight)
        except (TypeError, ValueError, InvalidOperation):
            return JsonResponse({"success": False, "error": "وزن معتبر نیست."})

        # پیدا کردن یا ساخت مشتری
        if phone and Customer.objects.filter(phone=phone).exists():
            customer = Customer.objects.get(phone=phone)
            customer.name = name
            customer.save()
        else:
            customer = Customer.objects.create(name=name, phone=phone)

        # تعیین جنسیت خودکار
        if 'خانم' in customer.name:
            customer.gender = 'female'
        else:
            customer.gender = 'male'
        customer.save(update_fields=["gender"])

        transactions_data = []

        if code:  # اگر کاربر کد وارد کرده
            try:
                melted_gold = MeltedGold.objects.get(code=code)
            except MeltedGold.DoesNotExist:
                return JsonResponse({"success": False, "error": "کد طلای آب‌شده یافت نشد."})

            if melted_gold.weight < weight:
                return JsonResponse({"success": False, "error": f"موجودی کافی نیست! وزن فعلی: {melted_gold.weight}"})

            # کاهش موجودی MeltedGold
            melted_gold.weight -= weight
            melted_gold.save()

            # ساخت رکورد فروش
            sale = MeltedGoldSale.objects.create(
                code=code,
                customer=customer,
                weight=weight,
                date=date
            )

            sale_data = {
                "code": sale.code,
                "customer_name": sale.customer.name,
                "customer_phone": sale.customer.phone,
                "weight": str(sale.weight),
                "date": date2jalali(sale.date).strftime('%Y/%m/%d'),
            }

            return JsonResponse({
                "success": True,
                "sale": sale_data,
                "remaining_weight": str(melted_gold.weight),
                "transactions": transactions_data,  # خالی، چون تراکنش نداریم
                "sell_to_code_1": False
            })

        else:  # اگر کاربر کد وارد نکرده → فروشگاه، کد ۱
            try:
                melted_gold = MeltedGold.objects.get(code='1')
            except MeltedGold.DoesNotExist:
                return JsonResponse({"success": False, "error": "کد پیش‌فرض فروشگاه موجود نیست."})

            if melted_gold.weight < weight:
                return JsonResponse({"success": False, "error": f"موجودی کافی نیست! وزن فعلی: {melted_gold.weight}"})

            # کاهش موجودی کد ۱
            melted_gold.weight -= weight
            melted_gold.save()

            # ایجاد تراکنش خروج
            transaction = MeltedGoldTransaction.objects.create(
                melted_gold=melted_gold,
                transaction_type="OUT",
                source="فروشگاه",
                destination=name,
                weight=weight,
                date=date,
                note="فروش به مشتری"
            )

            transactions_data.append({
                "transaction_type": transaction.transaction_type,
                "source": transaction.source,
                "destination": transaction.destination,
                "weight": str(transaction.weight),
                "date": date2jalali(transaction.date).strftime('%Y/%m/%d'),
                "note": transaction.note,
            })

            return JsonResponse({
                "success": True,
                "sale": None,  # هیچ سطر فروش اضافه نشود
                "remaining_weight": str(melted_gold.weight),
                "transactions": transactions_data,
                "sell_to_code_1": True
            })

    return JsonResponse({"success": False, "error": "درخواست نامعتبر است."})


def melted_gold_sale_add_ajax_خمی(request):
    if request.method == "POST":
        code = request.POST.get("code")
        name = request.POST.get("customer_name")
        phone_fa = request.POST.get("customer_phone")
        phone=persian_to_english_digits(phone_fa)
        print("phone: ",phone)
        weight = request.POST.get("weight")
        date = request.POST.get("date") or timezone.now().date()
        print(name)
        try:
            weight = Decimal(weight)
        except (TypeError, ValueError):
            return JsonResponse({"success": False, "error": "وزن معتبر نیست."})

        # ۱️⃣ پیدا کردن یا ساخت مشتری
        customer = None
        if phone and Customer.objects.filter(phone=phone).exists():
            customer = Customer.objects.get(phone=phone)
            customer.name = name
            customer.save()
        else:
            customer = Customer.objects.create(
                name=name,
                phone=phone
            )

            # ✅ تعیین جنسیت خودکار بر اساس نام
        if customer.name:
            if 'خانم' in customer.name:
                customer.gender = 'female'
            else:
                customer.gender = 'male'
            customer.save(update_fields=["gender"])
        

        # ۲️⃣ بررسی وجود طلای آب‌شده با این کد
        try:
            melted_gold = MeltedGold.objects.get(code=code)
        except MeltedGold.DoesNotExist:
            return JsonResponse({"success": False, "error": "کد طلای آب‌شده یافت نشد."})

        # ۳️⃣ بررسی موجودی کافی
        if melted_gold.weight < weight:
            return JsonResponse({
                "success": False,
                "error": f"موجودی کافی نیست! وزن فعلی: {melted_gold.weight} گرم"
            })

        # ۴️⃣ ساخت رکورد فروش
        sale = MeltedGoldSale.objects.create(
            code=code,
            customer=customer,
            weight=weight,
            date=timezone.now()
        )

        # ۵️⃣ کم کردن وزن از موجودی طلای آب‌شده
        melted_gold.weight -= weight
        melted_gold.save()
        jalali_date = date2jalali(sale.date).strftime('%Y/%m/%d')
        return JsonResponse({
            "success": True,
            "code": sale.code,
            "customer_name": sale.customer.name,
            "customer_phone": sale.customer.phone,
            "weight": str(sale.weight),
            "date": jalali_date,
            "remaining_weight": str(melted_gold.weight),
        })

    return JsonResponse({"success": False, "error": "درخواست نامعتبر است."})


def gallery(request):
    # گروه‌بندی بر اساس category
    summary = Product.objects.filter(quantity__gt=0).values('category').annotate(
        total_quantity=Sum('quantity'),      # مجموع تعداد
        total_weight=Sum('weight')           # مجموع وزن
    ).order_by('category')

    context = {
        'summary': summary
    }
    print (summary)
    return render(request,'gallery.html',context)

from django.db.models import Max

def get_next_partner_code(request):
    """
    خروجی: کد بعدی برای همکار یا بنکدار با پیش‌شماره h
    """
    prefix = 'h'
    
    # گرفتن آخرین شخص از بین همکار و بنکدار
    last_person = Person.objects.filter(
        type_partner__in=['partner', 'supplier'],
        code__startswith=prefix
    ).order_by('-id').first()

    if last_person and last_person.code[1:].isdigit():
        last_number = int(last_person.code[1:])
        next_number = last_number + 1
    else:
        next_number = 1

    return JsonResponse({'next_code': f"{prefix}{next_number:03d}"})

def partner_list(request):
    #partners = Person.objects.filter(type_partner__in=['partner', 'supplier']).order_by('-id')
    #return render(request, 'partner.html', {'partners': partners})
    partners = Person.objects.filter(type_partner__in=['partner', 'supplier']).order_by('-id')

    data = []
    for p in partners:
        totals = JournalItem.objects.filter(account=p.account).aggregate(
            debit_money=Sum("debit_money"),
            credit_money=Sum("credit_money"),
            debit_gold=Sum("debit_gold"),
            credit_gold=Sum("credit_gold")
        )

        dm = totals["debit_money"] or 0
        cm = totals["credit_money"] or 0
        dg = totals["debit_gold"] or 0
        cg = totals["credit_gold"] or 0
        
        money_balance = dm - cm
        gold_balance = dg - cg

        data.append({
            "person": p,
            "money_balance": money_balance,
            "balance_label": "بدهکار" if money_balance > 0 else "بستانکار" if money_balance < 0 else "تسویه",
            
            "gold_balance": gold_balance,
            "gold_label": "بدهکار" if gold_balance > 0 else "بستانکار" if gold_balance < 0 else "تسویه",
        })

    return render(request, 'partner.html', {"data": data})


# صفحه لیست همه سندها
def journal_entries_list(request):
    entries = JournalEntry.objects.all().order_by('-date')
    return render(request, "journal_entries_list.html", {"entries": entries})

# صفحه جزئیات یک سند
def journal_entry_detail(request, entry_id):
    entry = get_object_or_404(JournalEntry, id=entry_id)
    items = entry.items.all()
    return render(request, "journal_entry_detail.html", {"entry": entry, "items": items})

def safe_float(value, default=0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
    
@csrf_exempt
def add_partner(request):

    if request.method == "POST":
        code = request.POST.get('code')
        name = request.POST.get('name')
        family = request.POST.get('family')
        phone = persian_to_english_digits(request.POST.get('phone'))
        account_number =persian_to_english_digits(request.POST.get('account_number'))
        note=request.POST.get('note')
        store=request.POST.get('store')
        type_partner=request.POST.get('type')
        print(type_partner)
        partner = Partner.objects.create(
            code=code,
            name=name,
            family=family,
            phone=phone,
            account_number=account_number,
            note=note,
            store=store,
            type_partner=type_partner
        )
        print(partner)
        return JsonResponse({
            'status': 'success',
            'partner': {
            'id': partner.id,
            'code': partner.code,
            'name': partner.name,
            'family': partner.family,
            'phone': partner.phone,
            'note':partner.note,
            'type_partner':partner.get_type_partner_display(),
        
            'store':partner.store,
            'account_number': partner.account_number,
            'created_at': partner.created_at.strftime('%Y/%m/%d'),
        }
    })
    return JsonResponse({'error': 'Invalid request'}, status=400)



def partner(request):
    
    partner_form = PartnerForm()
    money_form = PartnerMoneyTransactionForm()
    gold_form = PartnerGoldTransactionForm()

    if request.method == "POST":
        if "add_partner" in request.POST:
            partner_form = PartnerForm(request.POST)
            if partner_form.is_valid():
                partner_form.save()
                return redirect('partners_dashboard')

        elif "add_money_transaction" in request.POST:
            money_form = PartnerMoneyTransactionForm(request.POST)
            if money_form.is_valid():
                money_form.save()
                return redirect('partners_dashboard')

        elif "add_gold_transaction" in request.POST:
            gold_form = PartnerGoldTransactionForm(request.POST)
            if gold_form.is_valid():
                gold_form.save()
                return redirect('partners_dashboard')

    # لیست همکارها و موجودی فعلی
    partners = Partner.objects.all()
    partners_data = []
    for p in partners:
        money_in = PartnerMoneyTransaction.objects.filter(partner=p, transaction_type='IN').aggregate(total=Sum('amount'))['total'] or 0
        money_out = PartnerMoneyTransaction.objects.filter(partner=p, transaction_type='OUT').aggregate(total=Sum('amount'))['total'] or 0
        gold_in = PartnerGoldTransaction.objects.filter(partner=p, transaction_type='IN').aggregate(total=Sum('weight'))['total'] or 0
        gold_out = PartnerGoldTransaction.objects.filter(partner=p, transaction_type='OUT').aggregate(total=Sum('weight'))['total'] or 0

        partners_data.append({
            'partner': p,
            'balance': p.initial_balance + money_in - money_out,
            'gold_balance': p.initial_gold + gold_in - gold_out
        })

    context = {
        'partner_form': partner_form,
        'money_form': money_form,
        'gold_form': gold_form,
        'partners_data': partners_data
    }
    return render(request,'partner.html',context)

def get_product_info(request):
    print('pp')
    product_id = request.GET.get('id')
    product = Product.objects.filter(id=product_id).first()
    if product:
        data = {
            "code":product.code,
            "name": product.name,
            "category":product.get_category_display() or "-",
            "weight": product.weight,
            "labor": product.labor,
            "laborprice" : product.laborprice,
            "purity":product.purity,
            "quantity":product.quantity,
            # هر فیلدی که می‌خوای برگرده
        }
        print(data)
        return JsonResponse(data)
    return JsonResponse({"error": "محصول یافت نشد"}, status=404)


def create_purchase_melted_journal(invoice,bank_payments,bank_ids,cash_payments,cash_ids,type):
    print("🚨 ENTERED create_sale_journal_new 🚨")
    # جمع کل پرداخت‌ها
    bank_paid = sum(to_decimal(x or 0) for x in bank_payments)
    cash_paid = sum(to_decimal(x or 0) for x in cash_payments)
    total_paid = bank_paid + cash_paid
    invoice_total = invoice.total_price
    remaining = invoice_total - total_paid  # مبلغ باقی‌مانده که مشتری بدهکار است
    print('remaining ',remaining)  
    seller = invoice.seller  # Person object
    print('buy')
    # حساب‌ها
    
    inventory_account = Account.objects.get(code="14")  # موجودی طلا
    labor_account = Account.objects.get(code="51")     # اجرت طلا

    paid_amount = getattr(invoice, 'paid_amount', None)
    weight = to_decimal(invoice.weight)
    labor = to_decimal(invoice.labor)
    total_price = to_decimal(invoice.total_price)
    price = to_decimal(invoice.price)
    laborprice = to_decimal(invoice.laborprice)
    total_price = to_decimal(invoice.total_price)
    mesghal = to_decimal(invoice.pricemesghal)
    purity = to_decimal(invoice.purity)
    vaznojrat=(weight * labor) /100
        
    print("weight",weight)
    print("labor ",labor)
    print("total_price" , total_price)
    print("fi ",price)
    print("vaznojrat" , vaznojrat)
    
    if mesghal > 0: 
        price = mesghal / Decimal('4.608')
        price = price.quantize(Decimal('1'))  # معادل round()
    
    print(price)
    
    weight_gold=weight
    weight_labor=0
    weight_seller=0
    money_gold=0
    money_labor=0
    money_seller=0
    weight_purity = ( weight * purity ) / 750
    
    if type == 'abshode' :
        desc_gold=f" ورود طلا بابت خرید آبشده فاکتور : {invoice.number}"
        desc_labor=f" هزینه اجرت خرید آبشده فاکتور  {invoice.number}"
        desc_seller=f"خرید آبشده فاکتور  {invoice.number}"
        desc_bank=f"پرداخت  برای فاکتور خرید آبشده {invoice.number}"
        desc_cash=f"پرداخت نقدی برای فاکتور خرید آبشده {invoice.number}"
        
    else :
        desc_gold=f" ورود طلا بابت خرید طلا فاکتور : {invoice.number}"
        desc_labor=f" هزینه اجرت خرید طلا فاکتور  {invoice.number}"
        desc_seller=f"خرید طلا فاکتور  {invoice.number}"
        desc_bank=f"پرداخت  برای فاکتور خرید طلا {invoice.number}"
        desc_cash=f"پرداخت نقدی برای فاکتور خرید طلا {invoice.number}"
        
     
    if total_price == 0 :
        
        if labor == 0 and laborprice == 0 :
            weight_gold=weight
            weight_seller=weight
            
        if labor > 0 :
            print('labor>0')
            weight_gold = weight
            weight_labor = ( weight * labor ) /100
            weight_seller = weight_gold + weight_labor
            print(weight_seller)
        
        if laborprice > 0 :
            weight_gold = weight
            money_labor = weight_purity * laborprice
            weight_seller= weight 
            money_seller = weight_purity * laborprice
                      
    else:
        
        if labor == 0 and laborprice == 0 :
            money_gold = total_price
            money_seller = total_price
            
        if labor > 0 :
            money_gold = total_price
            weight_labor = (weight * labor ) /100
            money_seller = total_price
            weight_seller = ( weight * labor ) /100
        
        if laborprice > 0 :
            money_gold=weight_purity * price
            money_labor=weight_purity * laborprice
            money_seller= money_gold + money_labor
    
        # ایجاد سربرگ سند

    with transaction.atomic():

        entry = JournalEntry.objects.create(
            date = invoice.date or timezone.now().date(),
            description = f"سند خرید آبشده فاکتور {invoice.number} از {seller.name}",
            related_purchase=invoice,
        )

        print(entry)
        
        #موجودی طلا بدهکار
        JournalItem.objects.create(
            entry=entry,
            account=inventory_account,
            debit_gold=weight_gold,
            debit_money=0,
            description=desc_gold
        )
        labor_amount = 0
        # سند اجرت بدهکار
        if weight_labor > 0 or money_labor > 0 :
            JournalItem.objects.create(
                entry=entry,
                account=labor_account,
                debit_gold=weight_labor,
                debit_money=money_labor,
                description=desc_labor
            )
        # فروشنده بستانکار
        JournalItem.objects.create(
            entry=entry,
            account=seller.account,
            credit_gold=weight_seller,
            credit_money=money_seller,
            description=desc_seller
        )
        
        if total_paid > 0 :
            # 2️⃣ ایجاد سند حسابداری خودکار
            entry = JournalEntry.objects.create(
                    date = invoice.date or timezone.now().date(),
                    description=f"پرداخت فاکتور خرید {invoice.number}",
                    related_purchase=invoice
                )
            
            for i in range(len(bank_payments)): 
                amt = to_decimal(bank_payments[i] or 0) 
                print(amt)
                if amt <= 0:  
                    continue
                bank_id = bank_ids[i]
                bank = BankAccount.objects.get(id=bank_id)
                bank_account = bank.account
                
                # 4️⃣ بستانکار: صندوق/بانک (کاهش موجودی)
                JournalItem.objects.create(
                    entry=entry,
                    account=bank_account,
                    credit_money=amt,
                    description= desc_bank
                )
                # 3️⃣ بدهکار: حساب پرداختنی فروشنده (کاهش بدهی)          
                JournalItem.objects.create(
                    entry=entry,
                    account=seller.account,
                    debit_money=amt,
                    description= desc_bank,
                )
                
                
            for i in range(len(cash_payments)): 
                amt = to_decimal(cash_payments[i] or 0) 
                print(amt)
                if amt <= 0:  
                    continue
                cash_id = cash_ids[i]
                cash = CashAccount.objects.get(id=cash_id)
                cash_account = cash.account

                # بدهکار cash
                JournalItem.objects.create(
                    entry=entry,
                    account=cash_account,
                    credit_money=amt,
                    description= desc_cash
                )
                # بستانکار فروشنده            
                JournalItem.objects.create(
                    entry=entry,
                    account=seller.account,
                    debit_money=amt,
                    description= desc_cash,
                )
                
    return entry


def invoice_purchase(request):
    max_number_dict = PurchaseInvoice.objects.annotate(
        number_int=Cast('number', IntegerField())
    ).aggregate(max_number=Max('number_int'))

    max_number = max_number_dict['max_number']
    print(max_number)
    try:
        next_number = int(max_number) + 1
    except (TypeError, ValueError):
        next_number = 1
    
    now = timezone.localtime()  # زمان محلی فعلی
    date = now.date()   # فقط تاریخ
    
    invoice_time = now.strftime("%H:%M")  # فقط ساعت به صورت string
    # تبدیل تاریخ میلادی به شمسی
    invoice_date = jdatetime.date.fromgregorian(date=now.date()).strftime("%Y/%m/%d")
    print(date)
    print(invoice_date)
    persons = Person.objects.filter(type_partner__in=['partner', 'supplier'])
    #products = Product.objects.all()
    products = Product.objects.exclude(category__in=['ab', 'mot'])
     # گرفتن لیست گروه‌ها
    #categories = Product.objects.values_list('category', flat=True).distinct()
    categories=category_map
    banks = BankAccount.objects.all()
    cash_account = CashAccount.objects.all()  # صندوق کد 101
    print(cash_account)
    return render(request,'invoice-purchase.html',{'persons':persons,'products':products,'next_number'
                                                   :next_number,'invoice_date':invoice_date,'banks':banks,
                                                   'cash_account':cash_account,
                                                   #cash_balance': cash_account.calculated_balance_recursive,
                                                   "categories":categories})


def add_purchase_invoice(request):
    if request.method == "POST":
        try:
            print("invoice purchase")
            with transaction.atomic():  # ✅ شروع تراکنش اتمیک
                date_shamsi = request.POST.get("date")  # YYYY/MM/DD
                date_gregorian = None
                if date_shamsi:
                        # تبدیل رشته به jdatetime.date
                    parts = date_shamsi.split("/")
                    if len(parts) == 3:
                        jy, jm, jd = map(int, parts)
                        date_gregorian = jdatetime.date(jy, jm, jd).togregorian()
                number=request.POST.get('number')
                print(number)
                number=persian_to_english_digits(number)
                weight=request.POST.get('weight') or 0
                purity=request.POST.get('purity') or '750'
                labor=request.POST.get('labor') or 0
                price=request.POST.get('price') or 0
                laborprice=request.POST.get('laborprice') or 0
                pricemesghal=request.POST.get('mesghal') or 0
                total_price=request.POST.get('totalprice') or 0
                seller_id=request.POST.get('seller')
                print(laborprice)
                print(total_price)
                # --- مدیریت فروشنده ---
                
                phone = request.POST.get("phone1")  # از input
                customer = None

                if seller_id:  
                    # ✅ اگر از سلکت انتخاب شده
                    customer = Person.objects.filter(id=seller_id).first()
                    flag='nocustomer'
                elif phone:  
                    flag='customer'
                    # ✅ اگر شماره تلفن وارد شده
                    phone = persian_to_english_digits(phone)
                    existing_person = Person.objects.filter(phone=phone).first()
                    if existing_person:
                        print("exist")
                        # اگر شخص وجود داشت → بروزرسانی نام
                        existing_person.name = request.POST.get("name1") or existing_person.name
                        existing_person.save()
                        customer = existing_person
                    else:
                        print("new person")
                        print(phone)
                        # اگر شخص جدید بود → بسازش
                        person_data = {
                            
                            "name": request.POST.get("nameseller1"),
                            "phone": phone,
                            "type_partner":"customer",
                        }
                        print(person_data)
                        customer_form = PersonForm(person_data)
                        #print(customer_form)
                        if customer_form.is_valid():
                            print("yes")
                            customer = customer_form.save()
                        else:
                            print(customer_form.errors)
                            return JsonResponse({"status": "error", "errors": customer_form.errors})

                    # تعیین جنسیت خودکار
                    if customer and customer.name:
                        if 'خانم' in customer.name:
                            customer.gender = 'female'
                        else:
                            customer.gender = 'male'
                        customer.save()

                if not customer:
                    return JsonResponse({'status': 'error', 'message': 'فروشنده مشخص نشده است.'})
                invoice = PurchaseInvoice.objects.create(
                    number=number,
                    number_store=request.POST.get('numberstore'),
                    type='gold',
                    date=date_gregorian or timezone.now().date(),
                    seller=customer,
                    weight=to_decimal(weight),
                    purity=to_decimal(purity),
                    labor=to_decimal(labor),
                    price=to_decimal(price),
                    laborprice=to_decimal(laborprice),
                    pricemesghal=to_decimal(pricemesghal),
                    total_price=to_decimal(total_price),
                    note=request.POST.get('note', ''),
                    image=request.FILES.get('image'),
                )
                bank_payments = request.POST.getlist('bank_amount[]')
                bank_ids = request.POST.getlist('bank_id[]')         # لیست آیدی هر بانک
                cash_payments = request.POST.getlist('cash_amount[]')
                cash_ids = request.POST.getlist('cash_id[]')         # لیست آیدی هر بانک
                
                create_purchase_melted_journal(invoice,bank_payments,bank_ids,cash_payments,cash_ids,"kala")
                #create_purchase_journal(invoice)
                print(invoice)
                print("inja error")
                products_codes = request.POST.getlist('product_code[]')
                print(products_codes)
                products_names = request.POST.getlist('product_name[]')
                categories = request.POST.getlist('product_group[]')
                weights = request.POST.getlist('product_weight[]')
                purities = request.POST.getlist('product_purity[]')
                labors = request.POST.getlist('product_labor[]')
                laborsprice=request.POST.getlist('product_laborprice[]')
                quantities = request.POST.getlist('product_quantity[]')
                #print("productname",products_names)
                for i, code in enumerate(products_codes):
                    code = code.strip()
                    print(code)
                    if not code:
                        continue
                        #code = to_decimal(code)                
                    qty = to_decimal(quantities[i]) or 1
                    print(qty)
                    #qty = int(persian_to_english_digits(qty))
                    labor=to_decimal(labors[i])
                    laborprice=to_decimal(laborsprice[i])
                    # 🔹 بررسی وجود محصول
                    product = Product.objects.filter(code=code).first()
                    if product:
                            # محصول موجود است → تعداد آن در Product افزایش یابد
                        product.quantity = (product.quantity or 0) + qty
                        product.labor=labor
                        product.laborprice=laborprice
                        product.save()
                    else:
                        
                        # محصول جدید → ایجاد در Product
                        product = Product.objects.create(
                            code=code,
                            name=products_names[i],
                            category=categories[i],
                            weight=to_decimal(weights[i]) if weights[i] else 0,
                            purity=to_decimal(purities[i]) if purities[i] else '750',
                            labor=to_decimal(labors[i]) if labors[i] else 0,
                            laborprice=to_decimal(laborsprice[i]) if laborsprice[i] else 0,
                            quantity=qty
                            )
                        print(product)
                        # 🔹 ایجاد یک ردیف جدید در PurchaseItem
                PurchaseItem.objects.create(
                        invoice=invoice,
                        product=product,
                        quantity=int(qty) if qty else 1
                        )

                return JsonResponse({'status': 'success', 'id': invoice.id})
        except Exception as e:
            print(str(e))
            return JsonResponse({'status': 'error', 'error': str(e)})
    return JsonResponse({'status': 'error', 'error': 'Invalid request'})

@csrf_exempt  # اگر از Ajax بدون csrftoken هم باشه، اما بهتر csrf_token استفاده شود
def save_purchase2(request):
    print('2')
    if request.method == "POST":
        print('post')
        try:
            with transaction.atomic():  # ✅ شروع تراکنش اتمیک
                date_shamsi = request.POST.get("date2")  # YYYY/MM/DD
                print(date_shamsi)
                date_gregorian = None
                if date_shamsi:
                        # تبدیل رشته به jdatetime.date
                    parts = date_shamsi.split("/")
                    if len(parts) == 3:
                        jy, jm, jd = map(int, parts)
                        date_gregorian = jdatetime.date(jy, jm, jd).togregorian()
                print(date_gregorian)
                s=request.POST.get("seller2")
                print(s)
                number=request.POST.get('number2')
                number=persian_to_english_digits(number)
                weight=request.POST.get('weight2') or 0
                purity=request.POST.get('purity2') or '750'
                labor=request.POST.get('labor2') or 0
                price=request.POST.get('price2') or 0
                laborprice=request.POST.get('laborprice2') or 0
                pricemesghal=request.POST.get('mesghal2') or 0
                total_price=request.POST.get('totalprice2') or 0
                #print(number)
                                # --- مدیریت فروشنده ---
                seller_id = request.POST.get("seller2")  # از سلکت
                phone = request.POST.get("phone2")  # از input
                customer = None

                if seller_id:  
                    # ✅ اگر از سلکت انتخاب شده
                    customer = Person.objects.filter(id=seller_id).first()
                    flag='nocustomer'
                elif phone:  
                    flag='customer'
                    # ✅ اگر شماره تلفن وارد شده
                    phone = persian_to_english_digits(phone)
                    existing_person = Person.objects.filter(phone=phone).first()
                    if existing_person:
                        print("exist")
                        # اگر شخص وجود داشت → بروزرسانی نام
                        existing_person.name = request.POST.get("name2") or existing_person.name
                        existing_person.save()
                        customer = existing_person
                    else:
                        print("new person")
                        print(phone)
                        # اگر شخص جدید بود → بسازش
                        person_data = {
                            
                            "name": request.POST.get("nameseller"),
                            "phone": phone,
                            "type_partner":"customer",
                        }
                        print(person_data)
                        customer_form = PersonForm(person_data)
                        #print(customer_form)
                        if customer_form.is_valid():
                            print("yes")
                            customer = customer_form.save()
                        else:
                            print(customer_form.errors)
                            return JsonResponse({"status": "error", "errors": customer_form.errors})

                    # تعیین جنسیت خودکار
                    if customer and customer.name:
                        if 'خانم' in customer.name:
                            customer.gender = 'female'
                        else:
                            customer.gender = 'male'
                        customer.save()

                if not customer:
                    return JsonResponse({'status': 'error', 'message': 'فروشنده مشخص نشده است.'})

                invoice = PurchaseInvoice.objects.create(
                    number=number,
                    number_store=request.POST.get('numberstore2'),
                    type='ab',
                    date=date_gregorian or timezone.now().date(),
                    seller=customer,
                    weight=to_decimal(weight),
                    purity=to_decimal(purity),
                    labor=to_decimal(labor),
                    price=to_decimal(price),
                    laborprice=to_decimal(laborprice),
                    pricemesghal=to_decimal(pricemesghal),
                    total_price=to_decimal(total_price),
                    note=request.POST.get('note2', ''),
                    image=request.FILES.get('image2'),
                )
                
                bank_payments = request.POST.getlist('bank_amount[]')
                bank_ids = request.POST.getlist('bank_id[]')         # لیست آیدی هر بانک
                cash_payments = request.POST.getlist('cash_amount[]')
                cash_ids = request.POST.getlist('cash_id[]')         # لیست آیدی هر بانک
                create_purchase_melted_journal(invoice,bank_payments,bank_ids,cash_payments,cash_ids,"abshode")
                
                print(invoice)
                code=request.POST.get('code2') or '0'
                code=persian_to_english_digits(code)
                print(code)
                try:
                    product = Product.objects.create(
                                    code=code,
                                    name=request.POST.get('nameab') or '',
                                    category='ab',
                                    weight= to_decimal(weight),
                                    initial_weight = to_decimal(weight),  # وزن اولیه=وزن ورود
                                    purity=to_decimal(purity),
                                    labor= to_decimal(labor),
                                    laborprice= to_decimal(laborprice),
                                    quantity=1
                                    
                                )
                    print(product)
                    PurchaseItem.objects.create(
                                invoice=invoice,
                                product=product,
                                quantity=1
                            )
                    
                    print(number)
                    print(date)
                
                except Exception as e:
                    print(e)
                    return JsonResponse({'status': 'error', 'message': 'شماره انگ موجود است .'})
                
                #خطا میده بررسی کنم
                mgtransaction = MeltedGoldTransaction.objects.create(
                    melted_gold=product,
                    transaction_type="IN",
                    source=f"خرید فاکتور  از {invoice.seller.name}",
                    destination="فروشگاه",
                    weight=to_decimal(weight),
                    price_per_gram=to_decimal(price),  # قیمت هر گرم (می‌توانی انتخابی باشد)
                    price_per_mesghal = to_decimal(pricemesghal),
                    total_price=to_decimal(total_price),  # محاسبه کل مبلغ
                    date=date_gregorian or timezone.now().date(),
                    note="اضافه شده از خرید شمش آبشده"
                )
                print('error')
                return JsonResponse({'result':'success','id': invoice.id,'status': 'success', 'message': 'فاکتور با موفقیت ثبت شد!'})
        except Exception as e:
            print(e)
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر است'})

def generate_next_person_code():
    last_person = Person.objects.filter(code__startswith='c').order_by('-id').first()
    if last_person and last_person.code[1:].isdigit():
        last_number = int(last_person.code[1:])
        next_number = last_number + 1
    else:
        next_number = 1
    return f"c{next_number:03d}"  # فرمت c001, c002, ...


@csrf_exempt  # اگر از Ajax بدون csrftoken هم باشه، اما بهتر csrf_token استفاده شود
def save_purchase3(request):
    flag=None
    print("inja")
    if request.method == "POST":
        try:
            print('3')
            with transaction.atomic():  # ✅ شروع تراکنش اتمیک
                # --- تاریخ ---
                date_shamsi = request.POST.get("date3")
                date_gregorian = timezone.now().date()
                if date_shamsi:
                    try:
                        jy, jm, jd = map(int, date_shamsi.split("/"))
                        date_gregorian = jdatetime.date(jy, jm, jd).togregorian()
                    except:
                        pass

                # --- شماره فاکتور ---
                number = persian_to_english_digits(request.POST.get("number3"))
                number_store = request.POST.get("numberstore3")
                print(number)
                # --- قیمت‌ها ---
                price = request.POST.get("price3") or 0
                mesghal = request.POST.get("mesghal3") or 0
                labor = request.POST.get("labor3") or 0
                laborprice = request.POST.get("laborprice3") or 0
                total_price = request.POST.get("totalprice3") or 0

                # --- مشخصات عمومی ---
                #weight = request.POST.get("weight3") or 0
                weight = Decimal(persian_to_english_digits(request.POST.get("weight3") or "0"))
                purity = request.POST.get("purity3") or "750"
                note = request.POST.get("note3", "")
                image = request.FILES.get("image3")

                # --- مدیریت فروشنده ---
                seller_id = request.POST.get("seller3")  # از سلکت
                phone = request.POST.get("phone")  # از input
                customer = None

                if seller_id:  
                    # ✅ اگر از سلکت انتخاب شده
                    customer = Person.objects.filter(id=seller_id).first()
                    flag='nocustomer'
                elif phone:  
                    flag='customer'
                    # ✅ اگر شماره تلفن وارد شده
                    phone = persian_to_english_digits(phone)
                    existing_person = Person.objects.filter(phone=phone).first()
                    if existing_person:
                        print("exist")
                        # اگر شخص وجود داشت → بروزرسانی نام
                        existing_person.name = request.POST.get("name") or existing_person.name
                        existing_person.save()
                        customer = existing_person
                    else:
                        print("new person")
                        print(phone)
                        # اگر شخص جدید بود → بسازش
                        person_data = {
                            
                            "name": request.POST.get("nameseller"),
                            "phone": phone,
                            "type_partner":"customer",
                        }
                        print(person_data)
                        customer_form = PersonForm(person_data)
                        #print(customer_form)
                        if customer_form.is_valid():
                            print("yes")
                            customer = customer_form.save()
                        else:
                            print(customer_form.errors)
                            return JsonResponse({"status": "error", "errors": customer_form.errors})

                    # تعیین جنسیت خودکار
                    if customer and customer.name:
                        if 'خانم' in customer.name:
                            customer.gender = 'female'
                        else:
                            customer.gender = 'male'
                        customer.save()

                if not customer:
                    return JsonResponse({'status': 'error', 'message': 'فروشنده مشخص نشده است.'})

                # --- ساخت فاکتور ---
                invoice = PurchaseInvoice.objects.create(
                    number=number,
                    number_store=number_store,
                    type='mot',
                    date=date_gregorian,
                    seller=customer,
                    weight=to_decimal(weight),
                    purity=to_decimal(purity),
                    price=to_decimal(price),
                    pricemesghal=to_decimal(mesghal),
                    labor=to_decimal(labor),
                    laborprice=to_decimal(laborprice),
                    total_price=to_decimal(total_price),
                    note=note,
                    image=image,
                )
                bank_payments = request.POST.getlist('bank_amount[]')
                bank_ids = request.POST.getlist('bank_id[]')  # لیست آیدی هر بانک
                cash_payments = request.POST.getlist('cash_amount[]')
                cash_ids = request.POST.getlist('cash_id[]') 
                create_purchase_melted_journal(invoice,bank_payments,bank_ids,cash_payments,cash_ids,"abshode")
                print('badazsanad')
                # --- مدیریت محصول (به‌روزرسانی یا ایجاد) ---
                #from decimal import Decimal

                try:
                    product = Product.objects.get(code='1')
                    old_weight = product.weight or Decimal('0.00')
                    product.weight = old_weight + weight
                    product.save()
                    print(f"✅ وزن محصول با کد 1 آپدیت شد: {old_weight} → {product.weight}")
                except Product.DoesNotExist:
                    product = Product.objects.create(
                        code='1',
                        name=request.POST.get('name') or 'متفرقه',
                        category='mot',
                        weight=weight,
                        purity='750',
                        labor=0,
                        quantity=1,
                    )
                    print("🆕 محصول جدید با کد 1 ساخته شد")

                # --- ثبت آیتم در فاکتور ---
                PurchaseItem.objects.create(
                    invoice=invoice,
                    product=product,
                    quantity=1
                )
                mgtransaction = MeltedGoldTransaction.objects.create(
                    melted_gold=product,
                    transaction_type="IN",
                    source=f"خرید فاکتور {number}",
                    destination="فروشگاه",
                    weight=weight,
                    price_per_gram=to_decimal(price),  # قیمت هر گرم (می‌توانی انتخابی باشد)
                    total_price=to_decimal(total_price),  # محاسبه کل مبلغ
                    date=date_gregorian,
                    note="اضافه شده از خرید آبشده متفرقه"
                )
                print(number)
                invoice_new_number=int(number)+1
                print("newnumber",invoice_new_number)
                now = timezone.localtime()  # زمان محلی فعلی
                date = now.date()   # فقط تاریخ
                # تبدیل تاریخ میلادی به شمسی
                new_date = jdatetime.date.fromgregorian(date=now.date()).strftime("%Y/%m/%d")
                print(new_date)
                return JsonResponse({'result':'success','invoice_new_number':invoice_new_number,'new_date':new_date,'id': invoice.id,'status': 'success', 'message': 'فاکتور با موفقیت ثبت شد!'})

        except Exception as e:
            return JsonResponse({'result':'error','status': 'error', 'message': str(e)})

    return JsonResponse({'result':'error','status': 'error', 'message': 'درخواست نامعتبر است'})

# کد تکراری رد پیغام بده
def save_purchase_items(request):
    print("view jadid")
    if request.method == "POST":
        try:
            invoice_id = request.POST.get("invoice_id")
            print("🔹 invoice_id received:", invoice_id)  # این خط رو اضافه کن
            #invoice_number = request.POST.get('invoice_number')
            #print(invoice_number)
            #invoice_number=persian_to_english_digits(invoice_number)
            #s=to_decimal(invoice_number)
            #print(s)
            #invoice = PurchaseInvoice.objects.get(number=invoice_number)
            invoice = PurchaseInvoice.objects.get(id=invoice_id)
            print(invoice)
            products_codes = request.POST.getlist('product_code[]')
            products_names = request.POST.getlist('product_name[]')
            categories = request.POST.getlist('product_group[]')
            weights = request.POST.getlist('product_weight[]')
            purities = request.POST.getlist('product_purity[]')
            labors = request.POST.getlist('product_labor[]')
            laborsprice=request.POST.getlist('product_laborprice[]')
            quantities = request.POST.getlist('product_quantity[]')
            print("productname",products_names)
            with transaction.atomic():
                try:
                    for i, code in enumerate(products_codes):
                        code = code.strip()
                        print(code)
                        if not code:
                            continue
                        #code = to_decimal(code)
                        
                        qty = to_decimal(quantities[i]) or 1
                        print(qty)
                        #qty = int(persian_to_english_digits(qty))
                        labor=to_decimal(labors[i])
                        laborprice=to_decimal(laborsprice[i])
                        # 🔹 بررسی وجود محصول
                        product = Product.objects.filter(code=code).first()
                        if product:
                            # محصول موجود است → تعداد آن در Product افزایش یابد
                            product.quantity = (product.quantity or 0) + qty
                            product.labor=labor
                            product.laborprice=laborprice
                            product.save()
                        else:
                            # محصول جدید → ایجاد در Product
                            product = Product.objects.create(
                                code=to_decimal(code),
                                name=products_names[i],
                                category=categories[i],
                                weight=to_decimal(weights[i]) if weights[i] else 0,
                                purity=to_decimal(purities[i]) if purities[i] else '750',
                                labor=to_decimal(labors[i]) if labors[i] else 0,
                                laborprice=to_decimal(laborsprice[i]) if laborsprice[i] else 0,
                                quantity=qty
                            )
                        print(product)
                        # 🔹 ایجاد یک ردیف جدید در PurchaseItem
                    PurchaseItem.objects.create(
                            invoice=invoice,
                            product=product,
                            quantity=int(qty) if qty else 1
                        )
                except Exception as e:
                    print(str(e))
                    return JsonResponse({'status': 'error', 'message': ' کد کالا موجود است .'}, status=400)

                    

            return JsonResponse({'status': 'success'})

        except Exception as e:
            print(e)
            return JsonResponse({'status': 'error', 'error': str(e)})

    return JsonResponse({'status': 'error', 'error': 'Invalid request'})


def account_ledger(account_id):
    items = (
        JournalItem.objects
        .filter(account_id=account_id)
        .select_related('entry')
        .annotate(
            date=F('entry__date'),
            entry_description=F('entry__description'),
            debit_gold_val=Coalesce('debit_gold', V(0, output_field=DecimalField())),
            credit_gold_val=Coalesce('credit_gold', V(0, output_field=DecimalField())),
            debit_money_val=Coalesce('debit_money', V(0, output_field=DecimalField())),
            credit_money_val=Coalesce('credit_money', V(0, output_field=DecimalField())),
        )
        .order_by('entry__date', 'id')
    )

    ledger = []
    balance_money = 0
    balance_gold = 0

    for row in items:
        balance_money += row.debit_money_val - row.credit_money_val
        balance_gold += row.debit_gold_val - row.credit_gold_val
        
        ledger.append({
            "date": row.date,
            "description": row.entry_description,
            "debit_money": row.debit_money_val,
            "credit_money": row.credit_money_val,
            "balance_money": balance_money,
            "debit_gold": row.debit_gold_val,
            "credit_gold": row.credit_gold_val,
            "balance_gold": balance_gold,
        })

    return ledger



def ledger_view(request, account_id):
    #account = Account.objects.get(id=account_id)
    #ledger = account_ledger(account_id)
    #return render(request, "ledger.html", {"account": account, "ledger": ledger})
    print("ledgercash")
    account = get_object_or_404(Account, id=account_id)
    now = timezone.localtime()
    date = now.date()
    final_balance_money = 0
    final_balance_gold = 0 
    # پیش‌بارگذاری entry و روابط ممکن برای جلوگیری از N+1
    items_qs = account.journal_items.select_related(
        'entry',
        'entry__related_purchase',
        'entry__related_sale'
    ).order_by('entry__date', 'id')

    ledger = []
    balance_money = Decimal('0')
    balance_gold = Decimal('0')
    total_debit_money = Decimal('0')
    total_credit_money = Decimal('0')
    total_debit_gold = Decimal('0')
    total_credit_gold = Decimal('0')

    for row in items_qs:
        entry_obj = getattr(row, 'entry', None)
        price_value = None
        mesghal_value = None

        if entry_obj is not None:
            # --- اگر سند به فاکتور خرید متصل است ---
            if getattr(entry_obj, 'related_purchase', None):
                pur = entry_obj.related_purchase
                # PurchaseInvoice دارای فیلد price و pricemesghal است
                price_value = pur.price if pur.price is not None else None
                mesghal_value = pur.pricemesghal if getattr(pur, 'pricemesghal', None) is not None else None

            # --- اگر سند به فاکتور فروش متصل است ---
            elif getattr(entry_obj, 'related_sale', None):
                sale = entry_obj.related_sale
                sale_items = sale.items.all()  # Invoice.items -> InvoiceItem

                if sale_items.exists():
                    # میانگین فی هر گرم (gold_price_per_gram)
                    sum_price = Decimal('0')
                    sum_mesghal = Decimal('0')
                    cnt = 0
                    for it in sale_items:
                        try:
                            sum_price += (it.gold_price_per_gram or Decimal('0'))
                        except InvalidOperation:
                            sum_price += Decimal('0')
                        try:
                            sum_mesghal += (it.gold_price_mesghal or Decimal('0'))
                        except InvalidOperation:
                            sum_mesghal += Decimal('0')
                        cnt += 1
                    if cnt:
                        price_value = (sum_price / cnt).quantize(Decimal('1'))  # بدون اعشار
                        mesghal_value = (sum_mesghal / cnt).quantize(Decimal('1'))
        print('mesghal' ,mesghal_value)
        # محاسبات بدهکار/بستانکار/مانده
        debit_money_val = getattr(row, 'debit_money', Decimal('0')) or Decimal('0')
        credit_money_val = getattr(row, 'credit_money', Decimal('0')) or Decimal('0')
        debit_gold_val = getattr(row, 'debit_gold', Decimal('0')) or Decimal('0')
        credit_gold_val = getattr(row, 'credit_gold', Decimal('0')) or Decimal('0')

        balance_money += debit_money_val - credit_money_val
        balance_gold += debit_gold_val - credit_gold_val

        total_debit_money += debit_money_val
        total_credit_money += credit_money_val
        total_debit_gold += debit_gold_val
        total_credit_gold += credit_gold_val

        item_description = row.description or ''
        final_balance_money = total_debit_money - total_credit_money
        final_balance_gold = total_debit_gold - total_credit_gold

        ledger.append({
            "date": getattr(entry_obj, 'date', None),
            "number": getattr(entry_obj, 'id', None),
            "description": getattr(entry_obj, 'description', '') or '',
            "item_description": item_description,
            "debit_money": debit_money_val,
            "credit_money": credit_money_val,
            "balance_money": balance_money,
            "debit_gold": debit_gold_val,
            "credit_gold": credit_gold_val,
            "balance_gold": balance_gold,
            "price_value": price_value,
            "mesghal_value": mesghal_value,
        })
    # مسیر مطلق لوگو روی سرور
    logo_path = os.path.join(settings.BASE_DIR, 'static/assets/images/logo_nasiri.png')
    print("path" , logo_path)
    html_string = render_to_string('ledger.html', {
        'account': account,
        'ledger': ledger,
        'total_debit_money': total_debit_money,
        'total_credit_money': total_credit_money,
        'total_debit_gold': total_debit_gold,
        'total_credit_gold': total_credit_gold,
        "final_balance_money": final_balance_money,
        "final_balance_gold": final_balance_gold,
        "now": date,
        "company_logo_url": logo_path,  # لوگو
        #'company_name': 'Mira Jewellery',
        #'company_logo_url': request.build_absolute_uri('/static/images/logo.png'),
    })
    
    
    css_string = f"""
        @font-face {{
            font-family: 'IRANYekan';
            src: url('/usr/share/fonts/iranyekan/iranyekanwebregular.ttf') format('truetype');
            font-weight: normal;
        }}
        @font-face {{
            font-family: 'IRANYekan';
            src: url('/usr/share/fonts/iranyekan/iranyekanwebbold.ttf') format('truetype');
            font-weight: bold;
        }}
        @font-face {{
            font-family: 'IRANYekan';
            src: url('/usr/share/fonts/iranyekan/iranyekanweblight.ttf') format('truetype');
            font-weight: normal;
        }}
        body {{
            font-family: 'IRANYekan', Tahoma, sans-serif;
            direction: rtl;
        }}
        """

    pdf_file = HTML(
        string=html_string,
        base_url=request.build_absolute_uri('/')
    ).write_pdf(
        stylesheets=[CSS(string=css_string)]
    )
    
    """
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(
        stylesheets=[CSS(string='@page { size: A4; margin: 1cm; font-family:IRANYekan,Tahoma; direction: rtl; }')]
    )
    """
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'filename=ledger_{account.id}.pdf'
    return response

def ledger_view_cash(request, account_id):
    #account = Account.objects.get(id=account_id)
    #ledger = account_ledger(account_id)
    #return render(request, "ledger.html", {"account": account, "ledger": ledger})
    print("ledger")
    account = get_object_or_404(Account, id=account_id)
    now = timezone.localtime()  # زمان محلی فعلی
    date = now.date()
    final_balance_money = 0
    final_balance_gold = 0 
    # گرفتن آیتم‌ها و محاسبه بدهکار، بستانکار و مانده‌ها
    items = (
         account.journal_items.select_related('entry')
        .annotate(
            date=F('entry__date'),
            entry_description=F('entry__description'),
            debit_money_val=Coalesce('debit_money', V(0,output_field=DecimalField())),
            credit_money_val=Coalesce('credit_money', V(0,output_field=DecimalField())),
            debit_gold_val=Coalesce('debit_gold', V(0,output_field=DecimalField())),
            credit_gold_val=Coalesce('credit_gold', V(0,output_field=DecimalField())),
        )
        .order_by('entry__date', 'id')
    )

    ledger = []
    balance_money = 0
    balance_gold = 0
    total_debit_money = 0
    total_credit_money = 0
    total_debit_gold = 0
    total_credit_gold = 0

    for row in items:
        balance_money += row.debit_money_val - row.credit_money_val
        balance_gold += row.debit_gold_val - row.credit_gold_val

        total_debit_money += row.debit_money_val
        total_credit_money += row.credit_money_val
        total_debit_gold += row.debit_gold_val
        total_credit_gold += row.credit_gold_val
        item_description=row.description
        final_balance_money = total_debit_money - total_credit_money

        ledger.append({
            "date": row.date,
            "number": row.entry.id,
            "description": row.entry_description,
            "item_description": item_description,
            "final_balance_money" : final_balance_money,
            "debit_money": row.debit_money_val,
            "credit_money": row.credit_money_val,
            "balance_money": balance_money,
            "debit_gold": row.debit_gold_val,
            "credit_gold": row.credit_gold_val,
            "balance_gold": balance_gold,
        })

    html_string = render_to_string('ledger_cash.html', {
        'account': account,
        'ledger': ledger,
        'total_debit_money': total_debit_money,
        'total_credit_money': total_credit_money,
        'total_debit_gold': total_debit_gold,
        'total_credit_gold': total_credit_gold,
        "final_balance_money" : final_balance_money,
        "now": date,
        #'company_name': 'Mira Jewellery',
        #'company_logo_url': request.build_absolute_uri('/static/images/logo.png'),
    })

    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(
        stylesheets=[CSS(string='@page { size: A4; margin: 1cm; font-family: Tahoma; direction: rtl; }')]
    )

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'filename=ledger_{account.id}.pdf'
    return response

def download_invoice_pdf(request, invoice_id):
    purchase = get_object_or_404(PurchaseInvoice, id=invoice_id)
    
    total_weight = 0
    
    
    for it in purchase.items.all() :
        x = to_decimal(it.product.weight)
        total_weight += x
    context = {
    "purchase": purchase,
    "items": purchase.items.all() if purchase.type not in ['ab', 'mot'] else None,
    "is_gold": purchase.type not in ['ab', 'mot'], # یعنی فاکتور طلای معمولی است
    "today": timezone.now(),
    'seller': purchase.seller,
}

    html_string = render_to_string('purchase-pdf.html', {
        "purchase": purchase,
        "items": purchase.items.all() if purchase.type not in ['ab', 'mot'] else None,
        "is_gold": purchase.type not in ['ab', 'mot'], # یعنی فاکتور طلای معمولی است
        "today": timezone.now(),
        'seller': purchase.seller,
        "total_weight" : total_weight ,
    })
    
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(
        stylesheets=[CSS(string='@page { size: A5; margin: 1cm; font-family: Tahoma; direction: rtl; }')]
    )

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'filename=PurchaseInvoice_{purchase.id}.pdf'
    return response

    #html = HTML(string=html_string)
    #pdf_file = html.write_pdf()

    #response = HttpResponse(pdf_file, content_type='application/pdf')
    #response['Content-Disposition'] = f'inline; filename=invoice_{purchase.number}.pdf'
    #return response

@login_required(login_url='/')
def financial_dashboard(request):
    inventory_account = Account.objects.get(code="14")  # موجودی طلا
    sales_account = Account.objects.get(code="41")      # درآمد فروش طلا
    cogs_account = Account.objects.get(code="61")       # بهای تمام‌شده
    profit_account = Account.objects.get(code="43")     # سود فروش طلا
    labor_account = Account.objects.get(code="51")     # اجرت طلاهزینه
    gold=inventory_account.calculated_balance_gold()
    print(gold,"gold")
       # -------------------------------
    # دفتر کل (Ledger)
    # -------------------------------
    ledger_items = (
        JournalItem.objects
        .select_related('entry', 'account')
        .annotate(
            date=F('entry__date'),
            entry_number=F('entry__id'),
            entry_description=F('entry__description'),
            debit_gold_val=Coalesce('debit_gold', V(0, output_field=DecimalField())),
            credit_gold_val=Coalesce('credit_gold', V(0, output_field=DecimalField())),
            debit_money_val=Coalesce('debit_money', V(0, output_field=DecimalField())),
            credit_money_val=Coalesce('credit_money', V(0, output_field=DecimalField())),
        )
        .order_by('entry__date', 'id')
    )

    ledger = []
    balance_money = 0
    balance_gold = 0
    total_debit_money = total_credit_money = total_debit_gold = total_credit_gold = 0

    for row in ledger_items:
        balance_money += row.debit_money_val - row.credit_money_val
        balance_gold += row.debit_gold_val - row.credit_gold_val

        total_debit_money += row.debit_money_val
        total_credit_money += row.credit_money_val
        total_debit_gold += row.debit_gold_val
        total_credit_gold += row.credit_gold_val

        ledger.append({
            "date": row.date,
            "entry_number": row.entry_number,
            "description": row.entry_description,
            "debit_money": row.debit_money_val,
            "credit_money": row.credit_money_val,
            "balance_money": balance_money,
            "debit_gold": row.debit_gold_val,
            "credit_gold": row.credit_gold_val,
            "balance_gold": balance_gold,
        })

    summary = {
        "total_debit_money": total_debit_money,
        "total_credit_money": total_credit_money,
        "balance_money": balance_money,
        "total_debit_gold": total_debit_gold,
        "total_credit_gold": total_credit_gold,
        "balance_gold": balance_gold,
    }
    # سود و زیان 
    # ------------------------------------------------
    # 1) فروش (Invoice)
    # ------------------------------------------------
    
    invoices = Invoice.objects.all()

    total_sale_amount = invoices.aggregate(total=Sum('total_price'))['total'] or 0
    total_sale_profit = invoices.aggregate(total=Sum('profit_total'))['total'] or 0
    total_sale_weight = InvoiceItem.objects.aggregate(total=Sum('weight'))['total'] or 0

    # ------------------------------------------------
    # 2) وزن فروش (InvoiceItem)
    # ------------------------------------------------
    try:
        total_sale_fee = InvoiceItem.objects.aggregate(total=Sum('gold_price_per_gram'))['total'] or 0
    except:
        total_sale_fee = 0

    # اگر اجرت در invoiceItem هست:
    if hasattr(InvoiceItem, "gold_price_per_gram"):
        total_sale_fee = InvoiceItem.objects.aggregate(
            total=Sum('gold_price_per_gram')
        )['total'] or 0
    else:
        total_sale_fee = 0

    # ------------------------------------------------
    # 3) خرید طلا
    # ------------------------------------------------
    # اگر خرید هم invoiceItem مشابه دارد:
    total_buy_weight = PurchaseInvoice.objects.aggregate(
        total=Sum('weight')
    )['total'] or 0

    total_buy_fee = PurchaseInvoice.objects.filter.aggregate(
        total=Sum('price')
    )['total'] or 0 if hasattr(InvoiceItem, "price") else 0


    # ------------------------------------------------
    # 4) موجودی طلا
    # ------------------------------------------------
    items = inventory_account.journal_items.all()
    balance_gold = Decimal('0')
    for row in items:
        debit_gold = row.debit_gold or 0
        credit_gold = row.credit_gold or 0
        balance_gold += debit_gold - credit_gold
    gold_stock_weight = balance_gold



    # ------------------------------------------------
    # 5) موجودی نقدی
    # ------------------------------------------------
    # صندوق
    cash_accounts = CashAccount.objects.select_related('account')
    cash_balance = Decimal('0')
    for cash in cash_accounts:
        items = cash.account.journal_items.all()
        balance = Decimal('0')
        for row in items:
            debit = row.debit_money or Decimal('0')
            credit = row.credit_money or Decimal('0')
            balance += debit - credit
        cash_balance += balance

    # بانک
    bank_accounts = BankAccount.objects.select_related('account')
    bank_balance = Decimal('0')
    for bank in bank_accounts:
        items = bank.account.journal_items.all()
        balance = Decimal('0')
        for row in items:
            debit = row.debit_money or Decimal('0')
            credit = row.credit_money or Decimal('0')
            balance += debit - credit
        bank_balance += balance


    # ------------------------------------------------
    # 6) سود و زیان
    # ------------------------------------------------
    gross_profit = total_sale_profit - total_sale_fee - total_buy_fee
    net_profit = gross_profit


    sood = {
        "total_sale_weight": total_sale_weight,
        "total_sale_amount": total_sale_amount,
        "total_sale_profit": total_sale_profit,
        "total_sale_fee": total_sale_fee,

        "total_buy_weight": total_buy_weight,
        "total_buy_fee": total_buy_fee,

        "gold_stock_weight": gold_stock_weight,
        "cash_balance": cash_balance,
        "bank_balance" : bank_balance , 

        "gross_profit": gross_profit,
        "net_profit": net_profit,
    }

    # -------------------------------
    # مانده حساب‌ها (Trial Balance)
    # -------------------------------
    accounts = []
    for acc in Account.objects.all():
        items_acc = JournalItem.objects.filter(account=acc)
        total_debit = items_acc.aggregate(
            d=Coalesce(Sum('debit_money'), V(0, output_field=DecimalField()))
        )['d']
        total_credit = items_acc.aggregate(
            c=Coalesce(Sum('credit_money'), V(0, output_field=DecimalField()))
        )['c']
        balance = total_debit - total_credit
        accounts.append({
            "code": acc.code,
            "name": acc.name,
            "type": acc.type,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "balance": balance
        })

    # -------------------------------
    # درآمد و هزینه‌ها (P&L)
    # -------------------------------
    pl_data = []
    pl_data_labor = []
    income_accounts = Account.objects.filter(type='income')
    expense_accounts = Account.objects.filter(type='expense')
    labor_accounts = Account.objects.get(code="51")     # اجرت طلاهزینه
    
    for acc in income_accounts:
        if acc.code != '4' :
            items_acc = JournalItem.objects.filter(account=acc)
            debit = items_acc.aggregate(
                d=Coalesce(Sum('debit_money'), V(0, output_field=DecimalField()))
            )['d']
            credit = items_acc.aggregate(
                c=Coalesce(Sum('credit_money'), V(0, output_field=DecimalField()))
            )['c']
            pl_data.append({
                "id": acc.id,
                "category": "درآمد",
                "description": acc.name,
                "debit": debit,
                "credit": credit,
                "total": credit - debit
            })
    
    items_acc = JournalItem.objects.filter(account=labor_accounts)
    debit_money = items_acc.aggregate(
        d=Coalesce(Sum('debit_money'), V(0, output_field=DecimalField()))
    )['d']
    credit_money = items_acc.aggregate(
        c=Coalesce(Sum('credit_money'), V(0, output_field=DecimalField()))
    )['c']
    debit_gold = items_acc.aggregate(
        d=Coalesce(Sum('debit_gold'), V(0, output_field=DecimalField()))
    )['d']
    credit_gold = items_acc.aggregate(
        c=Coalesce(Sum('credit_gold'), V(0, output_field=DecimalField()))
    )['c']
    pl_data_labor.append({
        "id": acc.id,
        "category": "هزینه",
        "description": acc.name,
        "debit_money": debit_money,
        "credit_money": credit_money,
        "total_money": credit_money - debit_money,
        "debit_gold": debit_gold,
        "credit_gold": credit_gold,
        "total_gold": credit_gold - debit_gold
    })
    
    for acc in expense_accounts:
        items_acc = JournalItem.objects.filter(account=acc)
        debit = items_acc.aggregate(
            d=Coalesce(Sum('debit_money'), V(0, output_field=DecimalField()))
        )['d']
        credit = items_acc.aggregate(
            c=Coalesce(Sum('credit_money'), V(0, output_field=DecimalField()))
        )['c']
        if debit > 0 or credit > 0 :
            pl_data.append({
                "id" : acc.id ,
                "category": "هزینه",
                "description": acc.name,
                "debit": debit,
                "credit": credit,
                "total": debit - credit
            })

    # -------------------------------
    # موجودی نقد و طلا (Cash & Gold)
    # -------------------------------
    cash_data = []
    gold_data = []
    items_acc = JournalItem.objects.filter(account=inventory_account).order_by('entry__date')
    print(items_acc)
    balance_money_acc = balance_gold_acc = 0
    for row in items_acc:
        if row.debit_gold > 0  or row.credit_gold > 0 :
            debit_money = row.debit_money or 0
            credit_money = row.credit_money or 0
            debit_gold = row.debit_gold or 0
            credit_gold = row.credit_gold or 0

        balance_money_acc += debit_money - credit_money
        balance_gold_acc += debit_gold - credit_gold
        print(acc.name)
        gold_data.append({
            "date": row.entry.date,
            "account_name": row.account.name,
            "description": row.entry.description,
            "in_money": debit_money,
            "out_money": credit_money,
            "balance_money": balance_money_acc,
            "in_gold": debit_gold,
            "out_gold": credit_gold,
            "balance_gold": balance_gold_acc
        })
        
    # همه صندوق‌ها
    for cash in CashAccount.objects.select_related('account').all():
        acc = cash.account
        items_acc = JournalItem.objects.filter(account=acc).order_by('entry__date')
        balance_money_acc = Decimal('0')

        for row in items_acc:
            debit_money = row.debit_money or Decimal('0')
            credit_money = row.credit_money or Decimal('0')
            balance_money_acc += debit_money - credit_money

            cash_data.append({
                "date": row.entry.date,
                "account_name": acc.name,   # نام حساب صندوق
                "description": row.entry.description,
                "in_money": debit_money,
                "out_money": credit_money,
                "balance_money": balance_money_acc,
                "type": "cash",
            })

    # همه بانک‌ها
    for bank in BankAccount.objects.select_related('account').all():
        acc = bank.account
        items_acc = JournalItem.objects.filter(account=acc).order_by('entry__date')
        balance_money_acc = Decimal('0')

        for row in items_acc:
            debit_money = row.debit_money or Decimal('0')
            credit_money = row.credit_money or Decimal('0')
            balance_money_acc += debit_money - credit_money

            cash_data.append({
                "date": row.entry.date,
                "account_name": acc.name,   # نام حساب بانک
                "description": row.entry.description,
                "in_money": debit_money,
                "out_money": credit_money,
                "balance_money": balance_money_acc,
                "type": "bank",
            })

    # -------------------------------
    # طرف‌حساب‌ها (Customers / Partners)
    # -------------------------------
    partners = []
    persons = Person.objects.filter(type_partner__in=['supplier','partner'])
    for p in persons:
        items_p = JournalItem.objects.filter(account=p.account)

        debit_money = items_p.aggregate(
            d=Coalesce(Sum('debit_money'), V(0, output_field=DecimalField()))
        )['d']
        credit_money = items_p.aggregate(
            c=Coalesce(Sum('credit_money'), V(0, output_field=DecimalField()))
        )['c']
        debit_gold = items_p.aggregate(
            dg=Coalesce(Sum('debit_gold'), V(0, output_field=DecimalField()))
        )['dg']
        credit_gold = items_p.aggregate(
            cg=Coalesce(Sum('credit_gold'), V(0, output_field=DecimalField()))
        )['cg']

        balance_money = debit_money - credit_money
        balance_gold = debit_gold - credit_gold

        # -------------------------------
        #   شرط فیلتر مشتری‌ها
        #   فقط زمانی نمایش بده اگر:
        #   1) نوع شریک ≠ customer
        #   یا
        #   2) مشتری باشد ولی مانده ≠ ۰
        # -------------------------------
        #if p.type_partner == "customer" and balance_money == 0 and balance_gold == 0:
        if balance_money == 0 and balance_gold == 0 :
            continue  # این مشتری صفر صفر است → نمایش نده

        partners.append({
            "id" : p.account.id,
            "name": p.name,
            "code": p.code,
            "type": p.type_partner,
            "debit_money": debit_money,
            "credit_money": credit_money,
            "debit_gold": debit_gold,
            "credit_gold": credit_gold,
            "balance": balance_money,
            "balance_gold": balance_gold,
        })
        
    customers = []
    persons = Person.objects.filter(type_partner__in=['customer'])
    for p in persons:
        items_p = JournalItem.objects.filter(account=p.account)

        debit_money = items_p.aggregate(
            d=Coalesce(Sum('debit_money'), V(0, output_field=DecimalField()))
        )['d']
        credit_money = items_p.aggregate(
            c=Coalesce(Sum('credit_money'), V(0, output_field=DecimalField()))
        )['c']
        debit_gold = items_p.aggregate(
            dg=Coalesce(Sum('debit_gold'), V(0, output_field=DecimalField()))
        )['dg']
        credit_gold = items_p.aggregate(
            cg=Coalesce(Sum('credit_gold'), V(0, output_field=DecimalField()))
        )['cg']

        balance_money = debit_money - credit_money
        balance_gold = debit_gold - credit_gold

        # -------------------------------
        #   شرط فیلتر مشتری‌ها
        #   فقط زمانی نمایش بده اگر:
        #   1) نوع شریک ≠ customer
        #   یا
        #   2) مشتری باشد ولی مانده ≠ ۰
        # -------------------------------
        #if p.type_partner == "customer" and balance_money == 0 and balance_gold == 0:
        if balance_money == 0 and balance_gold == 0 :
            continue  # این مشتری صفر صفر است → نمایش نده

        customers.append({
            "id" : p.account.id,
            "name": p.name,
            "code": p.code,
            "type": p.type_partner,
            "debit_money": debit_money,
            "credit_money": credit_money,
            "debit_gold": debit_gold,
            "credit_gold": credit_gold,
            "balance": balance_money,
            "balance_gold": balance_gold,
        })

    
    products = Product.objects.filter(quantity__gt=0).values('category').annotate(
        total_quantity=Sum('quantity'),      # مجموع تعداد
        total_weight=Sum('weight')           # مجموع وزن
    ).order_by('category')

    products = Product.objects.filter(quantity__gt=0).values('category').annotate(
    total_quantity=Sum('quantity'),
    total_weight=Sum(
        ExpressionWrapper(F('weight') * F('quantity'), output_field=DecimalField(max_digits=10, decimal_places=2))
    )
    ).order_by('category')
    print('pl_labor' , pl_data_labor)
    context = {
        "gold" : gold,
        'gold_inventory' : products,
        "customers" : customers ,
        "ledger": ledger,
        "summary": summary,
        "accounts": accounts,
        "pl_data": pl_data,
        "pl_data_labor": pl_data_labor ,
        "cash_data": cash_data,
        "gold_data" : gold_data,
        "partners": partners,
        "sood" : sood,
    }
    print("sood",customers)
    return render(request, "financial_dashboard.html", context)

def financial_dashboard_chatgpt(request):
    # ------------------------------------------------
    # 🔹 1) اطلاعات فروش
    # ------------------------------------------------
    # ------------------------------------------------
    # 1) فروش (Invoice)
    # ------------------------------------------------
    invoices = Invoice.objects.all()

    total_sale_amount = invoices.aggregate(total=Sum('total_price'))['total'] or 0
    total_sale_profit = invoices.aggregate(total=Sum('profit_total'))['total'] or 0

    # ------------------------------------------------
    # 2) وزن فروش (InvoiceItem)
    # ------------------------------------------------
    total_sale_weight = InvoiceItem.objects.aggregate(
        total=Sum('weight')
    )['total'] or 0

    # اگر اجرت در invoiceItem هست:
    if hasattr(InvoiceItem, "fee_amount"):
        total_sale_fee = InvoiceItem.objects.aggregate(
            total=Sum('fee_amount')
        )['total'] or 0
    else:
        total_sale_fee = 0

    # ------------------------------------------------
    # 🔹 2) اطلاعات خرید
    # ------------------------------------------------
    purchases = PurchaseInvoice.objects.all()

    total_buy_weight = purchases.aggregate(total=Sum('weight'))['total'] or 0
    total_buy_fee = purchases.aggregate(total=Sum('price'))['total'] or 0


    # ------------------------------------------------
    # 🔹 3) موجودی طلا (وزنی)
    # ------------------------------------------------
    # اگر مدل موجودی دارید
    GoldInventory = Account.objects.get(code="14")  # موجودی طلا
    gold_stock_weight =GoldInventory.calculated_balance_gold()
    

    # ------------------------------------------------
    # 🔹 4) موجودی نقدی (حساب‌ها)
    # ------------------------------------------------
    cash_account = CashAccount.objects.get(code="11")     
    cash_balance= cash_account.calculated_balance_money()
    print("cash",cash_balance)
    bank_account = Account.objects.get(code="12")
    bank_balance = bank_account.calculated_balance_money()

    # ------------------------------------------------
    # 🔹 5) محاسبات سود و زیان
    # ------------------------------------------------
    gross_profit = total_sale_profit - total_sale_fee - total_buy_fee
    net_profit = gross_profit  # چون هزینه دیگری فعلاً ندارید


    # ------------------------------------------------
    # 🔹 Context — ارسال به تمپلیت
    # ------------------------------------------------
    context = {
        # 📌 Summary Cards
        "gold_stock_weight": gold_stock_weight,
        "cash_balance": cash_balance,
        "bank_balance" : bank_balance,
        "total_sale_weight": total_sale_weight,
        "total_sale_amount": total_sale_amount,
        "total_sale_profit": total_sale_profit,
        "total_buy_weight": total_buy_weight,

        # 📌 Report section
        "total_sale_fee": total_sale_fee,
        "total_buy_fee": total_buy_fee,
        "gross_profit": gross_profit,
        "net_profit": net_profit,
    }
    return render(request, "financial_dashboard.html", context)


@login_required(login_url='/')
def banks_view(request):  
    return render(request,'bank.html')  

@login_required
def bank_accounts_list(request):

    accounts = Account.objects.all()  # همه حساب‌ها برای انتخاب

    banks = BankAccount.objects.select_related('bank', 'account')
    cash_account = Account.objects.get(code="101")      # بانک/صندوق

    # محاسبه مانده هر حساب بانکی
    accounts_data = []
    for ba in banks:
        items = JournalItem.objects.filter(bank_account=ba)

        debit = items.aggregate(
            d=Coalesce(Sum('debit_money'), V(0, output_field=DecimalField()))
        )['d']

        credit = items.aggregate(
            c=Coalesce(Sum('credit_money'), V(0, output_field=DecimalField()))
        )['c']

        balance = debit - credit

        accounts_data.append({
            'bank_account': ba,
            'balance': balance,
            
        })

    # 🔹 محاسبه صندوق (Cash)
    cash_items = JournalItem.objects.filter(account=cash_account)

    cash_debit = cash_items.aggregate(
        d=Coalesce(Sum('debit_money'), V(0, output_field=DecimalField()))
    )['d']
    cash_credit = cash_items.aggregate(
        c=Coalesce(Sum('credit_money'), V(0, output_field=DecimalField()))
    )['c']

    cash_balance = cash_debit - cash_credit

    # 🔸 اضافه کردن اطلاعات صندوق به عنوان متغیر مستقل
    cash_info = {
        'account': cash_account,
        'balance': cash_balance,
        'type': 'cash',
    }


    bank_transactions = JournalItem.objects.filter(bank_account__isnull=False).select_related(
        'entry', 'bank_account', 'account'
    ).order_by('-entry__date', '-id')


    return render(request, 'bank.html', {
        'accounts_data': accounts_data,
        'cash_info':cash_info,
        'accounts': accounts,
        'bank_transactions': bank_transactions,  # ✅ اضافه شد
    })



@login_required
def save_bank_account(request):
    if request.method == "POST":
        bank_id = request.POST.get('bank')
        account_number = request.POST.get('account_number', '').replace(',', '')
        card_number = request.POST.get('card_number', '')
        owner = request.POST.get('owner', '')
        opening_balance = request.POST.get('opening_balance', '0').replace(',', '')
        print(opening_balance)

        # تبدیل اعداد به Decimal
        try:
            opening_balance = Decimal(opening_balance)
        except:
            opening_balance = Decimal('0')

        # بررسی بانک


        # ایجاد حساب بانکی
        bank_account = BankAccount.objects.create(

            account_number=account_number,
            card_number=card_number,
            owner=owner,
            balance_money=opening_balance,

        )

        #bank_account.account = account
        bank_account.save()
        data = {
            "status": "success",
            "message": "حساب بانکی با موفقیت ثبت شد.",
            "bank_account": {
                "id": bank_account.id,
                "account_number": bank_account.account_number,
                "card_number": bank_account.card_number,
                "owner": bank_account.owner,
                "balance_money": str(bank_account.balance_money),
            }
        }
        print(data)
        return JsonResponse(data)
    
    return JsonResponse({"status": "error", "message": "درخواست نامعتبر است"})

def persian_to_decimal(value):
    from decimal import Decimal
    if not value:
        return Decimal("0")
    # تبدیل اعداد فارسی به انگلیسی
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"
    for p, e in zip(persian_digits, english_digits):
        value = value.replace(p, e)
    # حذف ویرگول یا جداکننده هزار
    value = value.replace(",", "").replace("٬", "")
    return Decimal(value)




    
    
@login_required
def save_transaction(request):
        
        if request.method != "POST":
            return JsonResponse({"status": "error", "message": "درخواست نامعتبر است"}, status=400)

        try:
            bank_id = request.POST.get("bank_account_id")
            tr_type = request.POST.get("type")
            money = persian_to_decimal(request.POST.get("money"))
            print(money)

            desc = request.POST.get("description", "")
            counter_acc_id = request.POST.get("counter_account")

            if money is None:
                return JsonResponse({"status": "error", "message": "مقدار پول وارد شده نامعتبر است."})

            if not bank_id or not counter_acc_id:
                return JsonResponse({"status": "error", "message": "حساب بانک یا حساب مقابل مشخص نشده است."})

            bank = BankAccount.objects.get(id=bank_id)
            counter_account = Account.objects.get(id=counter_acc_id)
            bank_account = bank.account
            print(bank_account.name)
            print(counter_account.name)
            print(tr_type)
            # ✅ چک موجودی در صورت برداشت
            if tr_type == "withdraw_money":
                if money > bank.balance_money:
                    return JsonResponse({"status": "error", "message": "موجودی پول کافی نیست!"})


            with transaction.atomic():

                if tr_type == "deposit_money":
                    
                    entry = JournalEntry.objects.create(
                        date=timezone.now().date(),
                        description=f"واریز وجه توسط   {counter_account.name} به {bank_account.name}"
                    )
                    print(entry)
                    # ✅ واریز
                    JournalItem.objects.create(
                        entry=entry,
                        account=bank_account,
                        debit_money=money,
                        bank_account=bank,
                        description=f"واریز وجه  {desc}"
                    )

                    JournalItem.objects.create(
                        entry=entry,
                        account=counter_account,
                        credit_money=money,
                        bank_account=bank,
                        description=f"واریز توسط   {counter_account.name}  {desc}"
                    )
                    bank.balance_money += money


                elif tr_type == "withdraw_money":
                    
                    entry = JournalEntry.objects.create(
                        date=timezone.now(),
                        description=f" پرداخت به  {counter_account.name} از {bank_account.name}"
                    )
                    # ✅ برداشت
                    JournalItem.objects.create(
                        entry=entry,
                        account=bank_account,
                        credit_money=money,
                        bank_account=bank,
                        description=f" پرداخت وجه  {desc}"
                    )
                    JournalItem.objects.create(
                        entry=entry,
                        account=counter_account,
                        debit_money=money,
                        bank_account=bank,
                        description=f"پرداخت به   {counter_account.name}  {desc}"
                    )
                    bank.balance_money -= money

                else:
                    return JsonResponse({"status": "error", "message": "نوع تراکنش نامعتبر است."})

                bank.save()

            return JsonResponse({"status": "success", "message": "تراکنش با موفقیت ثبت شد."})

        except BankAccount.DoesNotExist:
            return JsonResponse({"status": "error", "message": "حساب بانکی یافت نشد."})
        except Account.DoesNotExist:
            return JsonResponse({"status": "error", "message": "حساب مقابل یافت نشد."})
        except Exception as e:
            tb = traceback.format_exc()
            print(tb)
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    
@login_required
def bank_ledger(request, bank_account_id):
    ledger = []
    balance_money = 0
    balance_gold = 0
    total_debit_money = 0
    total_credit_money = 0

    now = timezone.localtime()
    current_date = now.date()
    
    account_type = request.GET.get("type", "bank")  # مقدار پیشفرض 'bank'
    is_cash = account_type == "cash"

    print(is_cash)
    if is_cash:
        # صندوق: فقط پول محاسبه می‌شود، طلا صفر
        account = get_object_or_404(Account, code="101")  # صندوق همیشه با code=101
        bank = None  # بانک نداریم
        items = account.journal_items.select_related('entry').annotate(
            date=F('entry__date'),
            entry_description=F('entry__description'),
            debit_money_val=Coalesce('debit_money', V(0, output_field=DecimalField())),
            credit_money_val=Coalesce('credit_money', V(0, output_field=DecimalField())),
        ).order_by('entry__date', 'id')
    else:
        bank = get_object_or_404(BankAccount, id=bank_account_id)
        print(bank)
        account = bank.account  # حساب اتصال به بانک
        items = (
            JournalItem.objects.filter(account=account)
            .select_related('entry')
            .annotate(
                date=F('entry__date'),
                entry_description=F('entry__description'),
                debit_money_val=Coalesce('debit_money', V(0, output_field=DecimalField())),
                credit_money_val=Coalesce('credit_money', V(0, output_field=DecimalField())),
            )
            .order_by('entry__date', 'id')
        )

    for row in items:
        balance_money += row.debit_money_val - row.credit_money_val
        total_debit_money += row.debit_money_val
        total_credit_money += row.credit_money_val
        item_description= row.description

        ledger.append({
            "date": row.date,
            "description": row.entry_description,
            "item_description": item_description,
            "debit_money": row.debit_money_val,
            "credit_money": row.credit_money_val,
            "balance_money": balance_money,
        })

    html_string = render_to_string('ledger-bank.html', {
        'bank': bank,
        'account': account,
        'ledger': ledger,
        'total_debit_money': total_debit_money,
        'total_credit_money': total_credit_money,
        'now': current_date,
    })

    pdf = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(
        stylesheets=[CSS(string='''
            @page { size: A4; margin: 1cm; direction: rtl; font-family: Tahoma; }
            body { font-family: Tahoma; direction: rtl; }
        ''')]
    )

    response = HttpResponse(pdf, content_type='application/pdf')
    if bank is None:
        response['Content-Disposition'] = f'filename=cash_ledger.pdf'
    else:
        response['Content-Disposition'] = f'filename=bank_ledger_{bank.id}.pdf'
    return response

@login_required
def bank_deposit_withdraw(request, bank_account_id):
    ba = get_object_or_404(BankAccount, id=bank_account_id)
    if request.method == 'POST':
        form = BankTransactionForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            tx_type = form.cleaned_data['tx_type']  # 'in' or 'out'
            description = form.cleaned_data['description']
            date = form.cleaned_data['date'] or timezone.now().date()
            # Create JournalEntry and JournalItems
            je = JournalEntry.objects.create(date=date, description=description)
            if tx_type == 'in':
                # Debit bank account
                JournalItem.objects.create(entry=je, account=ba.account, debit_money=amount, bank_account=ba)
                # Credit counter-account (e.g. cash income or specific account)
                other_acc = form.cleaned_data.get('counter_account') or Account.objects.get(code='4100')  # example fallback
                JournalItem.objects.create(entry=je, account=other_acc, credit_money=amount)
            else:
                # Withdraw: credit bank, debit something
                JournalItem.objects.create(entry=je, account=ba.account, credit_money=amount, bank_account=ba)
                other_acc = form.cleaned_data.get('counter_account') or Account.objects.get(code='2100')
                JournalItem.objects.create(entry=je, account=other_acc, debit_money=amount)
            messages.success(request, 'تراکنش بانکی ثبت شد.')
            return redirect('bank_ledger', bank_account_id=ba.id)
    else:
        form = BankTransactionForm(initial={'date': timezone.now().date()})
    return render(request, 'banks/deposit_form.html', {'form': form, 'bank_account': ba})

@login_required
def import_bank_statement_csv(request):
    if request.method == 'POST':
        form = BankStatementUploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['file']
            data = f.read().decode('utf-8')
            csvfile = io.StringIO(data)
            reader = csv.DictReader(csvfile)
            # expected columns: date, description, amount, type(in/out), account_number(optional), reference(optional)
            parsed = []
            for row in reader:
                parsed.append(row)
            request.session['bank_csv_rows'] = parsed  # store in session for review
            return redirect('bank_reconcile')
    else:
        form = BankStatementUploadForm()
    return render(request, 'banks/import_csv.html', {'form': form})

@login_required
def bank_reconcile(request, bank_account_id=None):
    # If bank_account_id provided, focus on that, else show session rows
    bank_accounts = BankAccount.objects.select_related('bank', 'account')
    csv_rows = request.session.get('bank_csv_rows', [])
    matches = []
    unmatched = []
    # simple auto-match: match by amount and date within 1 day and same account if provided
    for r in csv_rows:
        try:
            amount = Decimal(r.get('amount','0').replace(',',''))
        except:
            amount = Decimal('0')
        date_str = r.get('date')
        # parse date - user should provide proper format; you can enhance parsing
        from datetime import datetime, timedelta
        try:
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            parsed_date = None

        found = None
        q = JournalItem.objects.filter(debit_money=amount) | JournalItem.objects.filter(credit_money=amount)
        if parsed_date:
            q = q.filter(entry__date__range=(parsed_date - timedelta(days=1), parsed_date + timedelta(days=1)))
        q = q.filter(reconciled=False)
        # optionally filter by bank_account if provided in CSV
        acct_num = r.get('account_number')
        if acct_num:
            q = q.filter(bank_account__account_number__icontains=acct_num)
        q = q.select_related('entry','bank_account')[:5]
        if q.exists():
            found = q.first()
            matches.append((r, found))
        else:
            unmatched.append(r)

    # handle POST to mark matched rows
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'confirm_match':
            # expected: journal_item_id and csv_row_index
            ji_id = int(request.POST.get('journal_item_id'))
            row_index = int(request.POST.get('row_index'))
            ji = JournalItem.objects.get(id=ji_id)
            ji.reconciled = True
            ji.reconciled_date = timezone.now().date()
            ji.bank_statement_ref = f"CSV_row_{row_index}"
            ji.save()
            messages.success(request, 'ردیف مطابقت زد شد.')
            # remove row from session
            rows = request.session.get('bank_csv_rows', [])
            if 0 <= row_index < len(rows):
                rows.pop(row_index)
                request.session['bank_csv_rows'] = rows
            return redirect('bank_reconcile')

    return render(request, 'banks/reconcile.html', {
        'bank_accounts': bank_accounts,
        'matches': matches,
        'unmatched': unmatched,
        'csv_rows': csv_rows,
    })
    
    
@login_required
def accounting_setup(request):
    persons = (
    Person.objects
    .select_related('account')
    .exclude(type_partner='customer')   # فقط کسانی که مشتری نیستند
    .order_by('-id')                    # جدیدترین‌ها اول
)
    cash_accounts = CashAccount.objects.select_related('account').all()
    bank_accounts = BankAccount.objects.select_related('account').all().order_by('-id')
    expense_accounts = ExpenseAccount.objects.select_related('account').all()
    return render(request, 'accounting_setup.html', {
        'persons': persons,
        'cash_accounts': cash_accounts,
        'bank_accounts': bank_accounts,
        'expense_accounts':expense_accounts

    })
    

@require_POST
def add_or_edit_partner(request):
    print("add")
    """
    افزودن یا ویرایش شریک (طرف حساب)
    اگر id در POST ارسال شده باشد → ویرایش
    در غیر این صورت → ایجاد جدید
    """
    entry = None
    if request.method == "POST":
        try:
            with transaction.atomic():
                code = request.POST.get('code') or ''
                print('code',code)
                c=to_decimal(code)
                print(c)
                store = request.POST.get('store') or ""
                name = request.POST.get('name') or ""
                type_partner = request.POST.get('type_partner') or ""
                phone = request.POST.get('phone') or ""
                account_number = request.POST.get('account_number') or ""
                note = request.POST.get('note') or ""
                bedcash = request.POST.get('bedcash') 
                bescash = request.POST.get('bescash') 
                bedgold = request.POST.get('bedgold') 
                besgold = request.POST.get('besgold') 
                bedcash = to_decimal(bedcash)
                bescash = to_decimal(bescash)
                bedgold = to_decimal(bedgold)
                besgold = to_decimal(besgold)
                print(bedgold)
                print(besgold)
                print(bescash)
                print(bedcash)
                if bescash > 0 or besgold > 0 :
                    desc=" تعریف  "
                else :
                    desc=" تعریف "
                
                # ✅ بررسی وجود Partner با این کد
                partner = Person.objects.filter(code=c).first()
                print(partner)
                if partner:
                    # 🔁 ویرایش رکورد موجود
                    partner.name = name
                    partner.phone = phone
                    partner.account_number = account_number
                    partner.note = note
                    partner.store = store
                    partner.type_partner = type_partner
                    partner.save()
                    action = "updated"
                else:
                    # ➕ ایجاد رکورد جدید
                    partner = Person.objects.create(
                        name=name,
                        phone=phone,
                        account_number=account_number,
                        note=note,
                        store=store,
                        type_partner=type_partner,
                        created_at=timezone.now()
                    )
                    action = "created"
                    if bescash > 0 or bedcash > 0 or bedgold > 0 or besgold > 0 :
                        print("if")
                        entry = JournalEntry.objects.create(
                            date=timezone.now(),
                            description=f"سند افتتاحیه برای {partner.name}",
                        )
                        JournalItem.objects.create(
                            entry=entry,
                            account=partner.account ,  # حساب شخص
                            debit_money =bedcash ,
                            credit_money = bescash ,
                            debit_gold = bedgold ,
                            credit_gold = besgold ,
                            description= desc + partner.name,
                        )
                        print("journalitem")
                        # 🔸 سطر سرمایه (طرف مقابل سند)
                        capital_account = Account.objects.get(code='3')  # حساب سرمایه

                        # محاسبه مانده شخص
                        person_gold_balance  = (bedgold or 0) - (besgold or 0)
                        person_money_balance = (bedcash or 0) - (bescash or 0)

                        # اگر شخص بدهکار باشد → سرمایه بستانکار
                        # اگر شخص بستانکار باشد → سرمایه بدهکار
                        JournalItem.objects.create(
                            entry=entry,
                            account=capital_account,
                            
                            # پول:
                            debit_money =  abs(person_money_balance) if person_money_balance < 0 else 0,
                            credit_money = abs(person_money_balance) if person_money_balance > 0 else 0,

                            # طلا:
                            debit_gold =  abs(person_gold_balance) if person_gold_balance < 0 else 0,
                            credit_gold = abs(person_gold_balance) if person_gold_balance > 0 else 0,

                            description=f"طرف مقابل سند افتتاحیه {partner.name}",
                        )
                        print('sarmayeh')

    
                print(partner)
            return JsonResponse({
                "status": "success",
                "action": action,
                "partner": {
                    "id": partner.id,
                    "account_id" : partner.account.id ,
                    "code": partner.code,
                    "name": partner.name,
                    "phone": partner.phone,
                    "account_number": partner.account_number,
                    "note": partner.note or "-",
                    "store": partner.store or "-",
                    "cash" : partner.account.calculated_balance_money(),
                    "gold" : partner.account.calculated_balance_gold() ,
                    "type_partner": partner.get_type_partner_display() or "-",
                    "created_at": partner.created_at.strftime("%Y/%m/%d")
                }
            })

        except Exception as e:
            print("❌ ERROR while saving partner:")
            print(e)
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)

    
@csrf_exempt
@require_POST
def add_cash_account(request):
    try:
        name = request.POST.get("name")
        balance = request.POST.get("balance") or 0
        money=to_decimal(balance)
        note = request.POST.get("note")

        cash = CashAccount.objects.create(
            name=name,
            balance=money,
            note=note
        )
        print(cash)
        return JsonResponse({"status": "success", "cash_id": cash.id})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})

@csrf_exempt
@require_POST
def add_edit_cash(request):
    """
    افزودن یا ویرایش بانک
    اگر id در POST ارسال شده باشد → ویرایش
    در غیر این صورت → ایجاد جدید
    """
    try:
        cash_id = request.POST.get('cash')
        print(cash_id)
        code= request.POST.get('code')
        code=to_decimal(code)
        name = request.POST.get('name')
        
        note = request.POST.get('note')

            # ویرایش بانک موجود
        cash = CashAccount.objects.get(code=code)
        cash.name = name
            #bank.balance = balance
        cash.note = note
        cash.save()
        action = "updated"
       
            

        return JsonResponse({
            "status": "success",
            "action": action,
            "cash": {
                "id": cash.id,
                "name": cash.name,
                "account_id":cash.account.id,
                "account_code": cash.account.code if cash.account else "",
                "balance": cash.account.calculated_balance_money(),  # سه رقمی و فارسی با JS بعداً
                "note": cash.note
            }
        })
    except Exception as e:
        print("❌ ERROR while saving bank:")
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
@require_POST
def add_edit_bank(request):
    """
    افزودن یا ویرایش بانک
    اگر id در POST ارسال شده باشد → ویرایش
    در غیر این صورت → ایجاد جدید
    """
    try:
        bank_id = request.POST.get('id')
        print(bank_id)
        name = request.POST.get('name')
        owner_name = request.POST.get('owner_name')
        branch_name = request.POST.get('branch_name')
        card_number = request.POST.get('card_number')
        account_number = request.POST.get('account_number')
        balance = request.POST.get('balance') or 0
        iban = request.POST.get('iban') 
        note = request.POST.get('note')

        if bank_id:
            # ویرایش بانک موجود
            bank = BankAccount.objects.get(pk=bank_id)
            bank.name = name
            bank.branch_name = branch_name
            bank.owner = owner_name
            bank.account_number = to_decimal(account_number)
            bank.card_number = to_decimal(card_number)
            bank.iban=to_decimal(iban)
            #bank.balance = balance
            bank.note = note
            bank.save()
            action = "updated"
        else:
            # ایجاد بانک جدید
            bank = BankAccount.objects.create(
                name=name,
                branch_name=branch_name,
                owner = owner_name,
                account_number = to_decimal(account_number),
                card_number = to_decimal(card_number),
                iban=to_decimal(iban),
                balance=to_decimal(balance),
                note=note,
                created_at=timezone.now()
            )
            action = "created"

        return JsonResponse({
            "status": "success",
            "action": action,
            "bank": {
                "id": bank.id,
                "name": bank.name,
                "owner": bank.owner,
                "branch_name": bank.branch_name,
                "account_number": bank.account_number,
                "card_number": bank.card_number,
                "iban": bank.iban,
                "account_code": bank.account.code if bank.account else "",
                "balance": bank.account.calculated_balance_money(),  # سه رقمی و فارسی با JS بعداً
                "note": bank.note
            }
        })
    except Exception as e:
        print("❌ ERROR while saving bank:")
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@csrf_exempt
@require_POST
def add_edit_expense(request):
    """
    افزودن یا ویرایش بانک
    اگر id در POST ارسال شده باشد → ویرایش
    در غیر این صورت → ایجاد جدید
    """
    try:
        print('expense')
        expense_id = request.POST.get('id')
        print(expense_id)
        name = request.POST.get('name')
        note = request.POST.get('note')

        if expense_id:
            # ویرایش بانک موجود
            expense = ExpenseAccount.objects.get(pk=expense_id)
            expense.name = name
            expense.note = note
            expense.save()
            action = "updated"
        else:
            # ایجاد بانک جدید
            expense = ExpenseAccount.objects.create(
                name=name,
                note=note,
                created_at=timezone.now()
            )
            action = "created"

        return JsonResponse({
            "status": "success",
            "action": action,
            "expense": {
                "id": expense.id,
                "name": expense.name,
                "account_id" : expense.account.id , 
                "balance_money" : expense.account.calculated_balance_money() , 
                "note": expense.note,
                "account_code": expense.account.code if expense.account else "",
            }
        })
    except Exception as e:
        print("❌ ERROR while saving bank:")
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def transaction_view(request):
    persons = Person.objects.all()
    banks = BankAccount.objects.all()
    cashes = CashAccount.objects.all()
    expenses = ExpenseAccount.objects.all()
    accounts = Account.objects.all()  # همه حساب‌ها برای انتخاب
    date = timezone.now().date()
    
    # ساخت لیست ترکیبی از همه انواع «اکانت»
    all_accounts = []
    payment_account_source= []
    payment_account_destination= []
    recieve_account_source= []
    recieve_account_destination= []
    
    # بانک‌ها
    for b in banks:
        all_accounts.append({
            "id": f"bank-{b.id}",
            "label": f"💳 {b.name}",
            "meta": getattr(b, "account", None)
        })
        payment_account_source.append(b)
        payment_account_destination.append(b)
        recieve_account_source.append(b)
        recieve_account_destination.append(b)
    
    
    # صندوق‌ها
    for c in cashes:
        all_accounts.append({
            "id": f"cash-{c.id}",
            "label": f"💰 {c.name}",
            "meta": getattr(c, "account", None)
        })
        payment_account_source.append(c)
        payment_account_destination.append(c)
        recieve_account_source.append(c)
        recieve_account_destination.append(c)
    
    
    # هزینه‌ها (به‌عنوان مقصد پرداخت)
    for e in expenses:
        all_accounts.append({
            "id": f"expense-{e.id}",
            "label": f"🧾 {e.name}",
            "meta": getattr(e, "account", None)
        })
        payment_account_destination.append(e)
        recieve_account_destination.append(e)
    
    
    # پرسن‌ها (مثلاً برای دریافت از مشتری یا پرداخت به شخص)
    for p in persons:
        all_accounts.append({
            "id": f"person-{p.id}",
            "label": f"👤 {p.full_name if hasattr(p,'full_name') else p.name}",
            "meta": getattr(p, "account", None)  # نگه داشتن مرجع حساب در صورت نیاز
        })
        payment_account_destination.append(p)
        recieve_account_source.append(p)
        recieve_account_destination.append(p)
    

    if request.method == "POST":
        type_ = request.POST.get('type')
        amount = request.POST.get('amount')
        desc = request.POST.get('note') or ""
        amount = to_decimal(amount)


        if type_ == "receive":
            date = request.POST.get('datehidden1')
            source_code = request.POST.get('recieve_account_source')
            dest_code = request.POST.get('recieve_account_destination')
        elif type_== "payment":
            date = request.POST.get('datehidden2')
            source_code = request.POST.get('payment_account_source')
            dest_code = request.POST.get('payment_account_destination')
        else:
            date = request.POST.get('date3')
            source_code = "14"
            dest_code = request.POST.get('exit_account_destination')
            p_code = request.POST.get('p_account_source')
        print(date)
        if date:
                        # تبدیل رشته به jdatetime.date
                    parts = date.split("/")
                    if len(parts) == 3:
                        jy, jm, jd = map(int, parts)
                        date = jdatetime.date(jy, jm, jd).togregorian()
        print(date)
        source_code = source_code.strip()  # حذف فاصله اضافی
        dest_code = dest_code.strip()  # حذف فاصله اضافی
        p_code = p_code.strip()  # حذف فاصله اضافی
        print("source_code",source_code)
        print("source_code",dest_code)
        source_account = Account.objects.get(code=source_code)
        dest_account = Account.objects.get(code=dest_code)
        product = Product.objects.get(code=p_code)
        # 🔹 چک یکی بودن حساب‌ها
        print(source_account.code)
        print(dest_account.code)
        if source_account.code == dest_account.code:
            print("error")
            return JsonResponse({"success": False, "error": "حساب مبدا و حساب مقصد نمی‌توانند یکسان باشند!"})
        
        # بررسی موجودی در صورت پرداخت
        if type_ == "payment" and amount > source_account.calculated_balance_recursive:
            return JsonResponse({"success": False, "error": f"موجودی حساب {source_account.name} کافی نیست!"})
        
        
         
        try:
            with transaction.atomic():
                if type_ == 'receive':
                    # ✅ ایجاد سند حسابداری
                    entry = JournalEntry.objects.create(
                        #date=timezone.now().date(),
                        date=date,
                        description=f"{'دریافت' if type_=='receive' else 'پرداخت'} وجه - {desc}")


                    # دریافت وجه: بدهکار مبدا، بستانکار مقصد
                    JournalItem.objects.create(
                        entry=entry, 
                        account=dest_account, 
                        debit_money=to_decimal(amount),
                        description=f" پرداخت وجه  {desc}"
                        
                    )
                    JournalItem.objects.create(
                        entry=entry, 
                        account=source_account, 
                        credit_money=to_decimal(amount),
                        description=f"پرداخت به   {dest_account.name}  {desc}"
                        )
                elif type_ == "payment":
                    entry = JournalEntry.objects.create(
                                #date=timezone.now().date(),
                                date=date,
                                description=f"واریز وجه توسط   {source_account.name} به {dest_account.name}"
                    )
                    # پرداخت وجه: بدهکار مقصد، بستانکار مبدا
                    JournalItem.objects.create(
                        entry=entry, 
                        account=dest_account, 
                        debit_money=to_decimal(amount),
                        description=f"واریز وجه از {source_account.name} {desc}"
                    )
                    JournalItem.objects.create(
                        entry=entry, 
                        account=source_account, 
                        credit_money=to_decimal(amount),
                        description=f"واریز توسط   {source_account.name}  {desc}"
                    )
                    
                else : 
                    
                    entry = JournalEntry.objects.create(
                                #date=timezone.now().date(),
                                date=date,
                                description=f" خروج طلا به {dest_account.name}"
                    )
                    # پرداخت وجه: بدهکار مقصد، بستانکار مبدا
                    JournalItem.objects.create(
                        entry=entry, 
                        account=dest_account, 
                        debit_money=to_decimal(amount),
                        description=f" برداشت طلا  {desc}"
                    )
                    JournalItem.objects.create(
                        entry=entry, 
                        account=source_account, 
                        credit_money=to_decimal(amount),
                        description=f"خروج طلا   {dest_account.name}  {desc}"
                    )
                    
                    #product = Product.objects.get(code='1')
                    #if product.category == 'ab' or product.category == 'mot' :
                    if product.category in ['ab', 'mot']:
                        mgtransaction = MeltedGoldTransaction.objects.create(
                                melted_gold=product,
                                transaction_type="OUT",
                                source=f" خروج طلا ",
                                destination = dest_account.name,
                                weight=amount,
                                price_per_gram=0,  # قیمت هر گرم (می‌توانی انتخابی باشد)
                                price_per_mesghal = 0 , 
                                total_price=0,  # محاسبه کل مبلغ
                                date= date,
                                note=desc
                            )
                        print(product.weight)
                        product.weight -= amount
                        product.save()
                        print(product.weight)
                    else: 
                    # بررسی موجودی
                        if product.quantity == 0:
                            return JsonResponse({
                                "success": False,
                                "stock_error": True,
                                "message": f"کالا '{product.name}' موجودی کافی ندارد. موجودی فعلی: "
                            })
                        else :
                            # کاهش موجودی
                            product.quantity -= 1
                            product.save()

                return JsonResponse({"success": True, "message": "تراکنش با موفقیت ثبت شد!"})
                
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    products = Product.objects.all()
    context = {
        "date": date,
        "persons": persons,
        "products": products ,
        "banks": banks,
        "cashes": cashes,
        "expenses": expenses,
        "all_accounts": all_accounts,
        "accounts" : accounts,
        'payment_account_source' : payment_account_source,
        'payment_account_destination' : payment_account_destination,
        'recieve_account_source' : recieve_account_source,
        'recieve_account_destination' : recieve_account_destination , 
    }
    print(payment_account_destination)
    return render(request, "transactions.html", context)

def bank_transactions_report(request, bank_id):
    bank=get_object_or_404(BankAccount,pk=bank_id)
    account = bank.account
    
    items = JournalItem.objects.filter(account=account).select_related("entry").order_by("entry__date")

    form = DateRangeForm(request.GET or None)

    if form.is_valid():
        start = form.cleaned_data.get("start_date")
        end = form.cleaned_data.get("end_date")

        # فیلتر تاریخ فقط اگر مقدار دارد
        if start:
            items = items.filter(entry__date__date__gte=start)

        if end:
            items = items.filter(entry__date__date__lte=end)
            
    balance = 0
    total_debit = 0
    total_credit = 0
    rows = []

    for t in items:
        debit = t.debit_money or 0
        credit = t.credit_money or 0

        balance += debit - credit
        total_debit += debit
        total_credit += credit

        rows.append({
            "number" : t.entry.id ,
            "date": t.entry.date,
            "debit_money": debit,
            "credit_money": credit,
            "description": t.entry.description,
            "balance": balance,
        })

    # جمع کل‌ها
    total_debit = items.aggregate(total=Sum("debit_money"))["total"] or 0
    total_credit = items.aggregate(total=Sum("credit_money"))["total"] or 0
    final_balance = total_debit - total_credit
    
    html_string = render_to_string('bank_transactions_report.html', {
        "bank": bank,
        "today": timezone.now().date(),
        "rows" : rows,
        "account": account,
        "items": items,
        "form": form,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "final_balance": final_balance,
    })

    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(
        stylesheets=[CSS(string='@page { size: A4; margin: 1cm; font-family: Tahoma; direction: rtl; }')]
    )

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'filename=bank_transaction_{bank.name}.pdf'
    return response
"""
    context = {
        "bank": bank,
        "today": timezone.now().date(),
        "rows" : rows,
        "account": account,
        "items": items,
        "form": form,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "final_balance": final_balance,
    }
    return render(request, "bank_transactions_report.html", context)
"""
    

    

"""  
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Customer, Purchase, RetentionCampaign
from .utils import send_sms   # تابع سفارشی ارسال پیامک

@shared_task
def run_retention_campaigns():
    today = timezone.now().date()

    campaigns = RetentionCampaign.objects.filter(active=True)
    for campaign in campaigns:
        if campaign.campaign_type == "birthday":
            customers = Customer.objects.filter(birthday__day=today.day, birthday__month=today.month)
            for c in customers:
                send_sms(c.phone, campaign.message)

        elif campaign.campaign_type == "inactive":
            cutoff = today - timedelta(days=180)
            customers = Customer.objects.exclude(purchases__date__gte=cutoff)
            for c in customers:
                send_sms(c.phone, campaign.message)

        elif campaign.campaign_type == "anniversary":
            purchases = Purchase.objects.filter(date__month=today.month, date__day=today.day)
            for p in purchases:
                send_sms(p.customer.phone, campaign.message)

        elif campaign.campaign_type == "loyalty":
            customers = Customer.objects.filter(loyalty_points__gte=100)  # مثلا 100 امتیاز
            for c in customers:
                send_sms(c.phone, campaign.message)

        elif campaign.campaign_type == "seasonal":
            # مثلا فقط دستی فعال و غیرفعال میشه
            customers = Customer.objects.all()
            for c in customers:
                send_sms(c.phone, campaign.message)

import requests

def send_sms(phone, message):
    api_key = "API_KEY"
    url = "https://sms-provider.ir/api/v1/send"
    data = {
        "api_key": api_key,
        "to": phone,
        "message": message,
    }
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("SMS Error:", e)
"""




      
        
        
        