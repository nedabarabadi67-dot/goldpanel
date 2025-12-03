from decimal import Decimal
from django.contrib.auth.models import User
from django.db import models
import django.utils.timezone
from django_jalali.db.models import jDateField,jDateTimeField
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

from django.db.models import Sum, F, Max
from django.utils.functional import cached_property

from io import BytesIO
import base64
import barcode
from barcode.writer import ImageWriter


class test(models.Model):
    name=models.CharField(max_length=20)
    date=models.DateField()
    time=models.TimeField()
    
class UserProfile(models.Model):
    ROLE_CHOICES = (
        ("Admin", "ادمین"),
        ("Seller", "قروشنده"),
        ("Accountant", "حسابدار"),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES,default='seller')
    phone = models.CharField(max_length=15, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.role}) - Active: {self.is_active}"

def generate_barcode_base64(product_code):
    buffer = BytesIO()
    barcode_class = barcode.get_barcode_class('code128')
    code = barcode_class(str(product_code), writer=ImageWriter())
    code.write(buffer)
    return base64.b64encode(buffer.getvalue()).decode()

class Product(models.Model):
    CATEGORY_CHOICES = [
        ('ab','آبشده'),
        ('mot','متفرقه'),
        ('bracelet', 'دستبند'),
        ('earing', 'گوشواره'),
        ('neckles', 'گردنبند'),
        ('set','سرویس'),
        ('ring', 'انگشتر'),
        ('bangle','النگو'),
        ('brba','دستند النگو'),
        ("coine","سکه"),
        ("nimset","نیم ست"),
        ("medal","مدال"),
        ("zanjir","زنجیر"),
        ('other','سایر')
    ]
    code=models.CharField(max_length=10,unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='bracelet')
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=False, blank=False)
    initial_weight = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True,verbose_name="وزن اولیه خرید")
    description = models.TextField(blank=True, null=True)
    quantity = models.PositiveIntegerField(null=True, blank=True,default=0)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    purity = models.CharField(max_length=10, verbose_name="عیار",default='750')
    labor = models.DecimalField(max_digits=4, decimal_places=1, default=0 , null=True, blank=True)  # اجرت هر گرم طلا
    laborprice = models.DecimalField(max_digits=14, decimal_places=0, default=0 , null=True, blank=True)  # اجرت هر گرم طلا
    price = models.DecimalField(max_digits=14, decimal_places=0, default=0 , null=True, blank=True)
    barcode_image = models.TextField(blank=True, null=True)  # ذخیره base64
    created = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.barcode_image and self.code:
            print("CODE:", repr(self.code))
            self.barcode_image = generate_barcode_base64(self.code)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.name

# -------------------------------
# حساب‌ها (Accounts)
# -------------------------------
class Account(models.Model):
    """تعریف حساب‌ها در سیستم حسابداری"""
    
    ACCOUNT_TYPES = [
        ('asset', 'دارایی'),
        ('liability', 'بدهی'),
        ('income', 'درآمد'),
        ('expense', 'هزینه'),
        ('capital', 'سرمایه'),
        ('cogs', 'بهای تمام‌شده')  # مخصوص طلافروشی
    ]

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    description = models.CharField(max_length=255, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

    # ---------------------------------------------
    # تولید خودکار کد حساب
    # ---------------------------------------------
    @classmethod
    def generate_code(cls, prefix='11'):
        """
        تولید خودکار کد حساب بر اساس prefix.
        prefix مثال: 11 = صندوق، 12 = بانک، 21 = فروشنده، 14 = موجودی طلا
        """
        last = cls.objects.filter(code__startswith=prefix).aggregate(Max('code'))['code__max']
        print('lastcode',last)
        if last!='11' and last!='12' and last!='14' and last!='52':
            return str(int(last) + 1)
        return prefix + '01'

    @classmethod
    def generate_person_code(cls, person_type='customer'):
        """
        تولید کد حساب برای اشخاص
        person_type: 'customer' یا 'supplier'
        """
        prefix = '13' if person_type == 'customer' else '21'
        last = cls.objects.filter(code__startswith=prefix).aggregate(Max('code'))['code__max']
        print(last)
        if last != '21' and last != '13':
            try:
                return str(int(last) + 1)
            except ValueError:
                # اگر کد قبلی رشته‌ای ناصحیح بود
                return prefix + '001'
        else:
            # 🟢 اگر هیچ کدی وجود ندارد (اولین شخص)
            return prefix + '001'


    @classmethod
    def generate_cash_code(cls):
        return cls.generate_code('11')

    @classmethod
    def generate_bank_code(cls):
        return cls.generate_code('12')
    
    @classmethod
    def generate_expense_code(cls):
        return cls.generate_code('52')
    
    @classmethod
    def generate_inventory_code(cls):
        return cls.generate_code('14')
    
    @classmethod
    def generate_child_code(cls, parent):
        """
        تولید خودکار کد برای حساب فرعی بر اساس والد
        """
        prefix = parent.code
        last_child = cls.objects.filter(parent=parent).aggregate(Max('code'))['code__max']
        #print('last child',last_child)
        if last_child:
            return str(int(last_child) + 1)
        else:
            # اگه اولین حساب زیرمجموعه والد باشه
            return prefix + '01'

    # ---------------------------------------------
    # محاسبه بالانس حساب (فقط خودش)
    # ---------------------------------------------
    def calculated_balance_money(self):
        result = self.journal_items.aggregate(
            balance=Sum(F("debit_money") - F("credit_money"))
        )["balance"]
        #print("balancemoney ",result)
        return result or 0
    
    def calculated_balance_gold(self):
        result = self.journal_items.aggregate(
            balance=Sum(F("debit_gold") - F("credit_gold"))
        )["balance"]
        #print("balancegold ",result)
        return result or 0

    # 🧮 محاسبه مانده حساب
    def get_balance(self):
        totals = self.journal_items.aggregate(
            debit_sum=Sum('debit_money'),
            credit_sum=Sum('credit_money')
        )

        debit = totals['debit_sum'] or Decimal('0')
        credit = totals['credit_sum'] or Decimal('0')

        balance = debit - credit  # فرمول حسابداری

        return balance
    # ---------------------------------------------
    # محاسبه بالانس شامل فرزندان (recursive)
    # ---------------------------------------------
    @cached_property
    def calculated_balance_recursive(self):
        total = self.calculated_balance_money()
        for child in self.children.all():
            total += child.calculated_balance_recursive
        return total

    def __str__(self):
        return f"{self.code} - {self.name}"
    

# ===========================
# 💰 صندوق‌ها (CashAccount)
# ===========================
class CashAccount(models.Model):
    name = models.CharField("نام صندوق", max_length=100)
    code = models.CharField("کد صندوق", max_length=10, unique=True, blank=True, null=True)
    account = models.OneToOneField('Account', on_delete=models.SET_NULL, null=True, blank=True, related_name='cash_account')
    balance = models.DecimalField("موجودی اولیه", max_digits=15, decimal_places=0, default=0)
    note = models.TextField("توضیحات", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "صندوق"
        verbose_name_plural = "صندوق‌ها"
        ordering = ['code']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        from .models import Account

        # 🟢 تولید کد صندوق در صورت خالی بودن
        if not self.code:
            prefix = '11'  # پیشوند مخصوص دارایی‌های نقدی
            last_code = CashAccount.objects.filter(code__startswith=prefix).aggregate(Max('code'))['code__max']
            self.code = str(int(last_code) + 1) if last_code else prefix + '01'

        # 🟢 ساخت حساب دفتر مربوط به صندوق
        if not self.account:
            # بررسی حساب والد "صندوق‌ها"
            try:
                parent = Account.objects.get(code='11')
            except Account.DoesNotExist:
                parent = Account.objects.create(
                    code='11',
                    name='صندوق‌ها',
                    type='asset'
                )
            account = Account.objects.create(
                code=Account.generate_cash_code(),
                name=f"صندوق {self.name}",
                type='asset',
                parent=parent,
                description=f"حساب خودکار صندوق {self.name}"
            )
            self.account = account

        super().save(*args, **kwargs)


# -------------------------------
# بانک‌ها (BankAccount)
# -------------------------------
class BankAccount(models.Model):
    name = models.CharField("نام بانک", max_length=100)
    code = models.CharField("کد بانک", max_length=10, unique=True, blank=True, null=True)
    owner = models.CharField("نام صاحب حساب", max_length=100,default="")
    branch_name = models.CharField("نام شعبه", max_length=100, blank=True, null=True)
    account_number = models.CharField("شماره حساب", max_length=50, blank=True, null=True)
    card_number = models.CharField("شماره کارت", max_length=50, blank=True, null=True,default="")
    iban = models.CharField("شماره شبا", max_length=26, blank=True, null=True)
    account = models.OneToOneField('Account', on_delete=models.SET_NULL, null=True, blank=True, related_name='bank_account')
    balance = models.DecimalField("موجودی اولیه", max_digits=15, decimal_places=0, default=0)
    note = models.TextField("توضیحات", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "حساب بانکی"
        verbose_name_plural = "حساب‌های بانکی"
        ordering = ['code']

    def __str__(self):
        return f"{self.name} ({self.branch_name or ''})"

    def save(self, *args, **kwargs):
        from .models import Account

        # 🟢 تولید کد بانک در صورت خالی بودن
        if not self.code:
            prefix = '12'  # پیشوند مخصوص بانک‌ها
            last_code = BankAccount.objects.filter(code__startswith=prefix).aggregate(Max('code'))['code__max']
            self.code = str(int(last_code) + 1) if last_code else prefix + '01'

        # 🟢 ساخت حساب دفتر مربوط به بانک
        if not self.account:
             # بررسی حساب والد "بانک‌ها"
            try:
                parent = Account.objects.get(code='12')
                print(parent)
            except Account.DoesNotExist:
                parent = Account.objects.create(
                    code='12',
                    name='بانک‌ها',
                    type='asset'
                )
            account = Account.objects.create(
                code=Account.generate_bank_code(),
                name=f"بانک {self.name}",
                type='asset',
                parent=parent,
                description=f"حساب خودکار بانک {self.name}"
            )
            self.account = account

        super().save(*args, **kwargs)
        
        
class ExpenseAccount(models.Model):
    name = models.CharField("نام هزینه", max_length=100)
    code = models.CharField("کد هزینه", max_length=10, unique=True, blank=True, null=True)
    account = models.OneToOneField('Account', on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses_account')
    balance = models.DecimalField("موجودی اولیه", max_digits=15, decimal_places=0, default=0)
    note = models.TextField("توضیحات", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "هزینه"
        verbose_name_plural = "هزینه ها"
        ordering = ['code']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        from .models import Account

        # 🟢 تولید کد صندوق در صورت خالی بودن
        if not self.code:
            prefix = '52'  # پیشوند مخصوص دارایی‌های نقدی
            last_code = ExpenseAccount.objects.filter(code__startswith=prefix).aggregate(Max('code'))['code__max']
            #self.code = str(int(last_code) + 1) if last_code else prefix + '01'
            self.code = f"{prefix}{int(last_code[-2:]) + 1:02d}" if last_code else prefix + '01'


        # 🟢 ساخت حساب دفتر مربوط به صندوق
        if not self.account:
            # بررسی حساب والد "صندوق‌ها"
            try:
                parent = Account.objects.get(code='52')
            except Account.DoesNotExist:
                parent = Account.objects.create(
                    code='52',
                    name='هزینه ها',
                    type='expense'
                )
            account = Account.objects.create(
                code=Account.generate_expense_code(),
                name=f"هزینه {self.name}",
                type='expense',
                parent=parent,
                description=f"حساب خودکار هزینه {self.name}"
            )
            self.account = account

        super().save(*args, **kwargs)



class Person(models.Model):
    TYPE_CHOICES = [
        ('customer', 'مشتری'),
        ('partner', 'طرف‌ حساب'),
        ('supplier', 'بنکدار'),
    ]    
    GENDER_CHOICES = [
        ('male', 'آقا'),
        ('female', 'خانم'),
    ]

    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True, verbose_name="تاریخ تولد")  # فیلد تاریخ تولد
    code = models.CharField(max_length=10, unique=True, blank=True)
    name = models.CharField("نام",max_length=100)
    type_partner = models.CharField("نوع شخص", max_length=20, choices=TYPE_CHOICES )
    phone = models.CharField("شماره تماس", max_length=20, blank=True, null=True)
    store = models.CharField("نام مجموعه",max_length=100, blank=True, null=True)
    note = models.TextField("توضیحات", blank=True, null=True)
    account_number = models.CharField("شماره حساب بانکی", max_length=50, blank=True, null=True)
     # ✅ اتصال به حساب دفتر
    # ✅ اتصال به حساب دفتر
    account = models.OneToOneField('Account', on_delete=models.SET_NULL, null=True, blank=True, related_name='person_account')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "شخص"
        verbose_name_plural = "اشخاص"
        ordering = ['code']

    def __str__(self):
        return f"{self.name} ({self.get_type_partner_display()})"
    
    # ✅ تولید خودکار کد
    def save(self, *args, **kwargs):
        from .models import Account  # جلوگیری از import loop

        # 🟢 تولید کد شخص در صورت خالی بودن
        if not self.code:
            prefix = {'customer': '13', 'partner': '21', 'supplier': '21'}.get(self.type_partner, '99')
            last_code = Person.objects.filter(code__startswith=prefix).aggregate(Max('code'))['code__max']
            self.code = str(int(last_code) + 1) if last_code else prefix + '001'

        # 🟢 ایجاد حساب دفتر مخصوص شخص (در اولین ذخیره)
        if not self.account:
            # نوع حساب را مشخص کن
            acc_type = 'asset' if self.type_partner == 'customer' else 'liability'
            
            # تعیین حساب والد مناسب
            parent_code = '13' if self.type_partner == 'customer' else '21'  # '13'=مشتریان، '21'=فروشندگان
            try:
                parent = Account.objects.get(code=parent_code)
            except Account.DoesNotExist:
                # اگر حساب والد وجود ندارد، ایجادش کن
                if self.type_partner == 'customer':
                    parent = Account.objects.create(
                        code=parent_code,
                        name='حساب‌های دریافتنی' ,
                        type='asset',
                        
                    )
                else:
                    parent = Account.objects.create(
                        code=parent_code,
                        name='حساب‌های پرداختنی' ,
                        type='liability',
                        
                    )
            # ساخت حساب دفتر
            account = Account.objects.create(
                code=Account.generate_person_code(self.type_partner),
                name=f"حساب {self.name}",
                type=acc_type,
                parent=parent,
                description=f"حساب خودکار برای {self.get_type_partner_display()} {self.name}"
            )
            self.account = account

        super().save(*args, **kwargs)
        


class JournalEntry(models.Model):
    """سند حسابداری"""

    date = models.DateField(blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)

    # اتصال سند به فاکتور خرید یا فروش
    related_purchase = models.ForeignKey(
        'PurchaseInvoice', on_delete=models.SET_NULL, null=True, blank=True
    )
    related_sale = models.ForeignKey(
        'Invoice', on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f"سند {self.id} - {self.date}"


class JournalItem(models.Model):
    """آیتم سند (سطری)"""

    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="items")


    # چون طلافروشی داری → دو نوع گردش داریم
    debit_money = models.DecimalField("بدهکار پول",max_digits=18, decimal_places=0, default=Decimal('0'))
    credit_money = models.DecimalField("بستانکار پول",max_digits=18, decimal_places=0, default=Decimal('0'))

    debit_gold = models.DecimalField("بدهکار طلا",max_digits=12, decimal_places=2, default=Decimal('0'))
    credit_gold = models.DecimalField("بستانکار طلا",max_digits=12, decimal_places=2, default=Decimal('0'))

    description = models.CharField(max_length=255, blank=True, null=True)
    
    bank_account = models.ForeignKey('BankAccount', null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name='journal_items')
    account = models.ForeignKey('Account',on_delete=models.CASCADE,null=True,blank=True,related_name="journal_items")

    reconciled = models.BooleanField(default=False)
    reconciled_date = models.DateField(null=True, blank=True)
    bank_statement_ref = models.CharField(max_length=255, null=True, blank=True)
    
    @property
    def counter_party_account(self):
        # آیتم های سند
        siblings = self.entry.items.exclude(id=self.id)

        # اگر این خط بانک است
        if self.bank_account:

            # اگر بانک بدهکار است → طرف مقابل بستانکار
            if self.debit_money > 0:
                other = siblings.filter(credit_money__gt=0).first()
            else:  # بانک بستانکار است → طرف مقابل بدهکار
                other = siblings.filter(debit_money__gt=0).first()

            if other:
                # اگر طرف مقابل حساب دارد
                if other.account:
                    return other.account
                # اگر طرف مقابل بانک است → حساب بانکی آن
                if other.bank_account:
                    return other.bank_account.account

        return None




    def __str__(self):
        return f"آیتم سند {self.entry.id}- "
    #{self.entry.related_sale.number}" 


class Payment(models.Model):
    date = models.DateField("تاریخ پرداخت", auto_now_add=True)
    expense = models.ForeignKey('ExpenseAccount', on_delete=models.PROTECT, verbose_name="هزینه")
    bank_account = models.ForeignKey('Account', on_delete=models.PROTECT, verbose_name="صندوق/بانک", related_name='payments')
    amount = models.DecimalField("مبلغ", max_digits=15, decimal_places=0)
    note = models.CharField("توضیحات", max_length=255, blank=True, null=True)
    journal_entry = models.OneToOneField(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "پرداخت وجه"
        verbose_name_plural = "پرداخت‌ها"
        ordering = ['-date']

    def __str__(self):
        return f"پرداخت {self.amount} بابت {self.expense.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # ✅ ایجاد سند حسابداری خودکار
        if not self.journal_entry:
            entry = JournalEntry.objects.create(
                description=f"پرداخت بابت {self.expense.name}"
            )
            JournalItem.objects.create(
                entry=entry,
                account=self.expense.account,
                debit=self.amount,  # هزینه بدهکار می‌شود
                note=f"هزینه {self.expense.name}"
            )
            JournalItem.objects.create(
                entry=entry,
                account=self.bank_account,
                credit=self.amount,  # بانک بستانکار می‌شود
                note="پرداخت وجه"
            )
            self.journal_entry = entry
            super().save(update_fields=['journal_entry'])

class Receipt(models.Model):
    date = models.DateField("تاریخ دریافت", auto_now_add=True)
    source_account = models.ForeignKey('Account', on_delete=models.PROTECT, verbose_name="حساب طرف مقابل")
    bank_account = models.ForeignKey('Account', on_delete=models.PROTECT, verbose_name="صندوق/بانک دریافت‌کننده", related_name='receipts')
    amount = models.DecimalField("مبلغ", max_digits=15, decimal_places=0)
    note = models.CharField("توضیحات", max_length=255, blank=True, null=True)
    journal_entry = models.OneToOneField(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "دریافت وجه"
        verbose_name_plural = "دریافت‌ها"
        ordering = ['-date']

    def __str__(self):
        return f"دریافت {self.amount} از {self.source_account.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # ✅ ایجاد سند حسابداری خودکار
        if not self.journal_entry:
            entry = JournalEntry.objects.create(
                description=f"دریافت وجه از {self.source_account.name}"
            )
            JournalItem.objects.create(
                entry=entry,
                account=self.bank_account,
                debit=self.amount,  # بانک بدهکار می‌شود
                note="دریافت وجه"
            )
            JournalItem.objects.create(
                entry=entry,
                account=self.source_account,
                credit=self.amount,  # طرف مقابل بستانکار می‌شود
                note="طرف حساب"
            )
            self.journal_entry = entry
            super().save(update_fields=['journal_entry'])


CAPITAL_ACCOUNT_CODE = 3  # کد حساب سرمایه

#  سرمایه اولیه بانک
@receiver(post_save, sender=BankAccount)
def create_initial_bank_transaction(sender, instance, created, **kwargs):
    if created and instance.balance > 0:
        print(instance.name)
        # گرفتن حساب سرمایه
        capital_account = Account.objects.get(code=CAPITAL_ACCOUNT_CODE)

        # ایجاد سند
        entry = JournalEntry.objects.create(
            date=timezone.now().date(),
            description=f"سرمایه اولیه بانک {instance.name}"
        )
        print(entry)

        # بانک بدهکار
        JournalItem.objects.create(
            entry=entry,
            account=instance.account,  # حساب بانکی که در save ساخته شده
            debit_money=instance.balance,
            description=f"موجودی اولیه بانک {instance.name}"
        )

        # سرمایه بستانکار
        JournalItem.objects.create(
            entry=entry,
            account=capital_account,
            credit_money=instance.balance,
            description="سرمایه اولیه"
        )
        
        
# صندوق سرمایه اولیه
@receiver(post_save, sender=CashAccount)
def create_initial_cash_transaction(sender, instance, created, **kwargs):
    print(instance.balance)
    if created and instance.balance > 0:
        capital_account = Account.objects.get(code=CAPITAL_ACCOUNT_CODE)
        print(capital_account)
        entry = JournalEntry.objects.create(
            date=timezone.now().date(),
            description=f"سرمایه اولیه صندوق {instance.name}"
        )
        print(entry)
        # صندوق بدهکار
        JournalItem.objects.create(
            entry=entry,
            account=instance.account,  # صندوق
            debit_money=instance.balance,
            description=f"موجودی اولیه صندوق {instance.name}"
        )
        # سرمایه بستانکار
        JournalItem.objects.create(
            entry=entry,
            account=capital_account,
            credit_money=instance.balance,
            description="سرمایه اولیه"
        )

class Customer(models.Model):
    GENDER_CHOICES = [
        ('male', 'آقا'),
        ('female', 'خانم'),
    ]
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True, verbose_name="تاریخ تولد")  # فیلد تاریخ تولد
    def __str__(self):
        return self.name


class Invoice(models.Model):
    number = models.CharField(max_length=50, unique=True)
    date = models.DateField(blank=True, null=True)
    time = models.TimeField(auto_now_add=True)
    customer = models.ForeignKey(Person, on_delete=models.CASCADE)
    total_price = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    profit_total=models.DecimalField(max_digits=12, decimal_places=0, default=0)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    #created = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    
    def calculate_total(self):
        total = sum(item.total_price() for item in self.items.all())
        self.total_price = total
        self.save()
        return total
    
    def __str__(self):
        return f"Invoice {self.number}"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    gold_price_per_gram = models.DecimalField(max_digits=12, decimal_places=0,default=0)  # قیمت هر گرم طلا
    gold_price_mesghal = models.DecimalField(max_digits=12, decimal_places=0,default=0)  # قیمت هر گرم طلا
    labor_per_gram = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # اجرت هر گرم طلا
    labor_price = models.DecimalField(max_digits=12, decimal_places=0, default=0)  # اجرت هر گرم طلا
    profit_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # سود درصدی
    profit_total=models.DecimalField(max_digits=12, decimal_places=0, default=0)
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    purity = models.CharField(max_length=10, verbose_name="عیار",default='750')
    total=models.DecimalField(max_digits=12, decimal_places=0, default=0)
    #created = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def total_price(self):
    # وزن فروخته شده از فیلد خود آیتم
        weight = self.weight or 0  

        base_total = (weight * self.gold_price_per_gram + self.labor_per_gram) * self.quantity
        profit_total = base_total * (self.profit_percent / 100)
        return base_total + profit_total

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

class RetentionCampaign(models.Model):
    CAMPAIGN_TYPE = [
        ('BIRTHDAY', 'تولد'),
        ('LOYALTY', 'وفاداری'),
        ('INACTIVE', 'غیرفعال‌ها'),
        ('SEASONAL', 'فصلی'),
    ]

    name = models.CharField(max_length=200)
    campaign_type = models.CharField(max_length=20, choices=CAMPAIGN_TYPE, default='WELCOME')
    message = models.TextField()
    # فقط برای کمپین AFTER_PURCHASE و INACTIV
    send_days_after_purchase = models.PositiveIntegerField(default=0)  # روز بعد از خرید برای ارسال پیامک

    # فقط برای فصلی
    specific_date = models.DateField(null=True, blank=True, verbose_name="تاریخ ارسال فصلی")
   
    
    # فقط برای وفاداری
    loyalty_points = models.PositiveIntegerField(null=True, blank=True, verbose_name="امتیاز وفاداری")
    
    # فقط برای غیرفعال‌ها
    inactive_days = models.PositiveIntegerField(null=True, blank=True, verbose_name="روزهای غیر فعال")
    
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class CampaignLog(models.Model):
    STATUS_CHOICES = [
        ('SENT', 'ارسال شد'),
        ('FAILED', 'ناموفق'),
        ('PENDING', 'در صف'),
    ]

    campaign = models.ForeignKey(RetentionCampaign, on_delete=models.CASCADE, related_name="logs")
    customer = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="campaign_logs")
    message = models.TextField()
    sent_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    #created = models.DateTimeField(auto_now_add=True, null=True, blank=True)


    def __str__(self):
        return f"{self.campaign.name} → {self.customer.phone} ({self.status})"

class CustomerCRM(models.Model):
    customer = models.OneToOneField(Person, on_delete=models.CASCADE)
    last_purchase = models.DateField(blank=True, null=True)
    total_purchases = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    loyalty_points = models.PositiveIntegerField(default=0)
    #created = models.DateTimeField(auto_now_add=True, null=True, blank=True)


    def __str__(self):
        return f"{self.customer.name} ({self.loyalty_points} امتیاز)"




#fekr konam del

class MeltedGold(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="کد")
    weight_first = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="وزن (گرم)")
    weight = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="وزن الان (گرم)")
    purity = models.CharField(max_length=10, verbose_name="عیار",default='750')
    seller_name = models.CharField(max_length=100, verbose_name="نام فروشنده")
    seller_phone = models.CharField(max_length=20, verbose_name="شماره تلفن فروشنده", blank=True, null=True)
    assay_office = models.CharField(max_length=100, verbose_name="نام ری‌گیری")
    date = models.DateField(default=timezone.now, verbose_name="تاریخ")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = "طلای آب‌شده"
        verbose_name_plural = "طلای آب‌شده‌ها"
        ordering = ['-date']

    def __str__(self):
        return f"{self.code} - {self.seller_name}"
    


class MeltedGoldSale(models.Model):
    code = models.CharField(max_length=50, verbose_name="کد طلای آب‌شده")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    weight = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="وزن (گرم)")
    date = models.DateField(default=timezone.now, verbose_name="تاریخ فروش")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "فروش طلای آب‌شده"
        verbose_name_plural = "فروش‌های طلای آب‌شده"
        ordering = ['-date']

    def __str__(self):
        return f"{self.customer} - {self.code}"


class MeltedGoldTransaction(models.Model):
    TRANSACTION_TYPE = [
        ('IN', 'ورود به فروشگاه'),
        ('OUT', 'خروج از فروشگاه'),
    ]

    melted_gold = models.ForeignKey(
        'Product',  # اگر می‌خوای از همان جدول Product برای آب‌شده استفاده کنی
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='طلای آب‌شده'
    )

    transaction_type = models.CharField(
        max_length=3,
        choices=TRANSACTION_TYPE,
        verbose_name='نوع تراکنش'
    )

    source = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='منبع ورود (مثلاً خرید مستقیم یا کسری فاکتور)'
    )

    destination = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='مقصد خروج (مثلاً مشتری یا فروشنده)'
    )

    weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='وزن (گرم)'
    )

    price_per_gram = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='قیمت هر گرم (تومان)'
    )
    
    price_per_mesghal = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name='قیمت هر مثقال (تومان)'
    )

    total_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='مبلغ کل تراکنش (تومان)'
    )

    date = models.DateField(
        default=timezone.now,
        verbose_name='تاریخ تراکنش'
    )

    note = models.TextField(
        blank=True,
        null=True,
        verbose_name='توضیحات'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'تراکنش طلای آب‌شده فروشگاه'
        verbose_name_plural = 'تراکنش‌های طلای آب‌شده فروشگاه'
        ordering = ['-date', '-created_at']

    def save(self, *args, **kwargs):
        # اگر total_price مشخص نشده، خودکار محاسبه شود
        if not self.total_price and self.weight and self.price_per_gram:
            self.total_price = self.weight * self.price_per_gram
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.melted_gold.code} ({self.weight}g / {self.total_price} تومان)"



class PurchaseInvoice(models.Model):
    """فاکتور خرید طلا از فروشنده یا طرف‌حساب"""
    PURCHASE_TYPES = [
        ('gold', 'کالا طلا'),
        ('ab', 'آبشده'),
        ('mot', 'متفرقه'),
    ]
    
    type = models.CharField(
        "نوع خرید",
        max_length=10,
        choices=PURCHASE_TYPES,
        default='gold'
    )
    
    number = models.CharField("شماره فاکتور", max_length=30, unique=True)
    number_store = models.CharField(" فروشنده شماره فاکتور", max_length=30, default='0')
    date = models.DateField("تاریخ خرید", default=timezone.now)
    seller = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        limit_choices_to={'type_partner__in': ['partner', 'supplier','customer']},  # فقط طرف‌حساب یا تأمین‌کننده
        verbose_name="فروشنده"
    )
    weight = models.DecimalField("مجموع وزن (گرم)", max_digits=10, decimal_places=2, default=Decimal('0.00'))
    purity = models.CharField(max_length=10, verbose_name="عیار",default='750')
    labor = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    price = models.DecimalField("فی ", max_digits=14, decimal_places=0, default=0)
    laborprice = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    pricemesghal = models.DecimalField("فی ", max_digits=14, decimal_places=0, default=0)
    total_price = models.DecimalField("مبلغ کل ", max_digits=14, decimal_places=0, default=0)
    note = models.TextField("توضیحات", blank=True, null=True)
    image = models.ImageField("تصویر فاکتور", upload_to="purchases/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "فاکتور خرید"
        verbose_name_plural = "فاکتورهای خرید"
        ordering = ['-date', '-id']

    def __str__(self):
        return f"فاکتور خرید {self.number} - {self.seller.name} "


class PurchaseItem(models.Model):
    """اقلام خرید در فاکتور خرید"""
    invoice = models.ForeignKey(
        'PurchaseInvoice',
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="فاکتور خرید"
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        verbose_name="کالا"
    )
    quantity = models.PositiveIntegerField("تعداد", default=1)
        



#delete
class Partner(models.Model):
    code = models.CharField(max_length=10, unique=True, blank=True)
    name = models.CharField(max_length=100)
    family = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    #initial_balance = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    #initial_gold = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    #is_debtor_money = models.BooleanField(default=True)  # بدهکاری پول
    #is_debtor_gold = models.BooleanField(default=True)   # بدهکاری طلا
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.name} {self.family}"


class PartnerMoneyTransaction(models.Model):
    TRANSACTION_TYPE = [
        ('IN', 'واریز/دریافت'),
        ('OUT', 'پرداخت/خرج'),
    ]
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='money_transactions')
    transaction_type = models.CharField(max_length=3, choices=TRANSACTION_TYPE)
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    date = models.DateField(default=timezone.now)
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.partner} - {self.get_transaction_type_display()} - {self.amount}"


class PartnerGoldTransaction(models.Model):
    TRANSACTION_TYPE = [
        ('IN', 'دریافت طلا'),
        ('OUT', 'تحویل طلا'),
    ]
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='gold_transactions')
    transaction_type = models.CharField(max_length=3, choices=TRANSACTION_TYPE)
    weight = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(default=timezone.now)
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.partner} - {self.get_transaction_type_display()} - {self.weight}g"
