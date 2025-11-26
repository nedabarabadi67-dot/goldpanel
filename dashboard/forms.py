
# crm/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import  Account, BankAccount, JournalEntry, JournalItem, PurchaseItem, UserProfile,Product,Customer,Invoice,InvoiceItem
from django_jalali.forms import jDateField,jdatetime
from django_jalali.admin.widgets import AdminjDateWidget


class UserForm(forms.ModelForm):
    phone=forms.CharField(max_length=15,required=True,
                        widget=forms.TextInput(attrs={'class':'form-control ' , 'placeholder' :'Phone Number'}))
    role = forms.ChoiceField(
    choices=[('admin', 'Admin'), ('seller', 'Seller'), ('accountant', 'Accountant')], 
    required=True,
    widget=forms.Select(attrs={'class':'form-control','placeholder':'Role'}))
    is_active = forms.BooleanField(required=False)
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
        required=False  # برای ویرایش اختیاری باشه
    )
    
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]
        widgets={
            'first_name':forms.TextInput(attrs={'class':'form-control ' , 'placeholder' :'First Name'}),
            'last_name':forms.TextInput(attrs={'class':'form-control ' , 'placeholder' :'Last Name'}),
            'email':forms.EmailInput(attrs={'class':'form-control ' , 'placeholder' :'Email'}),
            'username':forms.TextInput(attrs={'class':'form-control ' , 'placeholder' :'Username'}),
            #'password':forms.PasswordInput(attrs={'class':'form-control ' , 'placeholder' :'Password'}),   
        }
    


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['code','name', 'category', 'weight', 'quantity','labor','laborprice','purity', 'image','description']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control','placeholder' :'Code'}),
            'name': forms.TextInput(attrs={'class': 'form-control','placeholder' :'Name'}),
            'category': forms.Select(attrs={'class': 'form-control','placeholder' :'Category','id': 'id_category'}),
            'initial_weight':forms.NumberInput(attrs={'class': 'form-control','placeholder' :'Weight'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control','placeholder' :'Weight'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control','placeholder' :'Quantity'}),
            'labor': forms.NumberInput(attrs={'class': 'form-control','placeholder' :'Labor'}),
            'laborprice': forms.TextInput(attrs={'class': 'form-control','placeholder' :'Laborprice'}),
            'purity': forms.NumberInput(attrs={'class': 'form-control','placeholder' :'purity'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control','placeholder' :'Image'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,'placeholder' :'Description'}),
        }
    
    def clean_code(self):
        code = self.cleaned_data.get("code")
        if Product.objects.filter(code=code).exists():
            raise forms.ValidationError("کد کالا تکراری است.")
        return code
    
    def clean_laborprice(self):
        value = self.cleaned_data.get('laborprice')
        if value in [None, '']:
            return None
        # اگر کاربر عدد را با کاما وارد کرده
        if isinstance(value, str):
            value = value.replace(',', '')
        try:
            return float(value)
        except ValueError:
            raise forms.ValidationError("مقدار نامعتبر است.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].empty_label = "انتخاب کنید..."


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone', 'address','birth_date','gender']


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['product', 'quantity','profit_total', 'gold_price_per_gram', 'labor_per_gram', 'profit_percent']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'gold_price_per_gram': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'labor_per_gram': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'profit_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

from django import forms
from .models import RetentionCampaign

class RetentionCampaignForm(forms.ModelForm):
    class Meta:
        model = RetentionCampaign
        fields = ['name', 'campaign_type', 'message', 'send_days_after_purchase','loyalty_points',
            'inactive_days', 'active','specific_date']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام کمپین'}),
            'campaign_type': forms.Select(attrs={'class': 'form-select'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'متن پیامک'}),
            'send_days_after_purchase': forms.NumberInput(attrs={'class': 'form-control', 'min':0}),
            "specific_date": forms.TextInput(attrs={"type": "date", "class": "form-control"}),
            'loyalty_points': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': 0,
                'placeholder': 'امتیاز وفاداری'
            }),
            'inactive_days': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': 0,
                'placeholder': 'روز غیر فعال'
            }),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
        }


from .models import MeltedGold

class MeltedGoldForm(forms.ModelForm):
    class Meta:
        model = MeltedGold
        fields = ["code", "weight_first","weight", "purity", "seller_name", "seller_phone", "assay_office", "date"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "weight_first": forms.NumberInput(attrs={"class": "form-control"}),
            "weight": forms.NumberInput(attrs={"class": "form-control"}),
            "purity": forms.TextInput(attrs={"class": "form-control"}),
            "seller_name": forms.TextInput(attrs={"class": "form-control"}),
            "seller_phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "مثلاً 09121234567"}),
            "assay_office": forms.TextInput(attrs={"class": "form-control"}),
        }


from .models import MeltedGoldSale

class MeltedGoldSaleForm(forms.ModelForm):
    class Meta:
        model = MeltedGoldSale
        fields = ["code", "customer", "weight", "date"]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "customer": forms.TextInput(attrs={"class": "form-control"}),
            "weight": forms.NumberInput(attrs={"class": "form-control"}),
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }


from .models import MeltedGoldTransaction

class MeltedGoldTransactionForm(forms.ModelForm):
    class Meta:
        model = MeltedGoldTransaction
        fields = ['melted_gold', 'transaction_type', 'source', 'destination', 'weight', 'date', 'note']

        labels = {
            'melted_gold': 'طلای آب‌شده',
            'transaction_type': 'نوع تراکنش',
            'source': 'منبع ورود',
            'destination': 'مقصد خروج',
            'weight': 'وزن (گرم)',
            'date': 'تاریخ',
            'note': 'توضیحات',
        }

        widgets = {
            'melted_gold': forms.Select(attrs={'class': 'form-select'}),
            'transaction_type': forms.Select(attrs={'class': 'form-select'}),
            'source': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثلاً خرید مستقیم یا کسری فاکتور'}),
            'destination': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثلاً مشتری یا فروشنده'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'مثلاً 5.25'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'توضیحات اضافی (اختیاری)'}),
        }

from django import forms
from .models import Person


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ['code','name', 'type_partner', 'phone', 'store', 'note','account_number','birth_date','gender']
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "کد"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "نام"}),
            'type_partner': forms.Select(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'national_id': forms.TextInput(attrs={'class': 'form-control'}),
            'store': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            "account_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "شماره حساب"}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
        
from django import forms
from .models import PurchaseInvoice
from django.utils import timezone



class PurchaseInvoiceForm(forms.ModelForm):

    class Meta:
        model = PurchaseInvoice
        fields = ['number', 'date', 'seller', 'weight', 'purity', 'price', 'note', 'image']
        labels = {
            'number': 'شماره فاکتور',
            'date':'تاریخ',
            'seller': 'فروشنده',
            'weight': 'مجموع وزن (گرم)',
            'purity': 'عیار',
            'price': 'قیمت هر گرم',
            'note': 'توضیحات',
            'image': 'عکس فاکتور',
        }
        widgets = {
            'number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثلاً F-1404-001'}),
            "date": forms.TextInput(attrs={"type": "date", "class": "form-control"}),
            'seller': forms.Select(attrs={'class': 'form-select'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'purity': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثلاً 750'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

class PurchaseItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseItem
        fields = ['product', 'quantity']
        widgets = {
            'product': forms.Select(
                attrs={
                    'class': 'form-control select2',
                    'style': 'width:100%;',
                }
            ),
            'quantity': forms.NumberInput(
                attrs={
                    'class': 'form-control text-center',
                    'min': 1,
                    'value': 1,
                    'oninput': "this.value=this.value.replace(/[^0-9۰-۹]/g,'')",  # فقط عدد فارسی
                }
            ),
        }
        labels = {
            'product': 'کالا',
            'quantity': 'تعداد',
        }



class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ['date','description']
        widgets = {
            "date": forms.TextInput(attrs={"type": "date", "class": "form-control"}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }


class JournalItemForm(forms.ModelForm):
    class Meta:
        model = JournalItem
        fields = [
            'account', 'debit_money', 'credit_money', 'debit_gold', 'credit_gold', 'description'
        ]
        widgets = {
            'account': forms.Select(attrs={'class': 'form-control'}),
            'debit_money': forms.NumberInput(attrs={'class': 'form-control'}),
            'credit_money': forms.NumberInput(attrs={'class': 'form-control'}),
            'debit_gold': forms.NumberInput(attrs={'class': 'form-control'}),
            'credit_gold': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }


class DateRangeForm(forms.Form):
    start_date = forms.DateField(required=False, label="از تاریخ")
    end_date = forms.DateField(required=False, label="تا تاریخ")
    
    
# -------------------------
# فرم حساب بانکی
# -------------------------

        
TX_CHOICES = (
    ('in', 'واریز'),
    ('out', 'برداشت'),
)

class BankTransactionForm(forms.Form):
    tx_type = forms.ChoiceField(choices=TX_CHOICES)
    amount = forms.DecimalField(max_digits=18, decimal_places=2)
    date = forms.DateField(required=False)
    description = forms.CharField(widget=forms.Textarea, required=False)
    #counter_account = forms.ModelChoiceField(queryset=Account.objects.all(), required=False)
    # انتخاب حساب بانکی
    bank_account = forms.ModelChoiceField(
        queryset=BankAccount.objects.all(),
        required=True,
        label="حساب بانکی"
    )

    # حساب مقابل (اختیاری)
    counter_account = forms.ModelChoiceField(
        queryset=Account.objects.all(),
        required=False,
        label="حساب مقابل در حسابداری"
    )

class BankStatementUploadForm(forms.Form):
    file = forms.FileField()
    
    
#fekr konam del       
from .models import Partner, PartnerMoneyTransaction, PartnerGoldTransaction
class PartnerForm(forms.ModelForm):
    class Meta:
        model = Partner
        fields = [
            "code",
            "name",
            "family",
            "phone",
            "account_number",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "کد"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "نام"}),
            "family": forms.TextInput(attrs={"class": "form-control", "placeholder": "نام خانوادگی"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "شماره تلفن"}),
            "account_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "شماره حساب"}),
            
        }

class PartnerMoneyTransactionForm(forms.ModelForm):
    class Meta:
        model = PartnerMoneyTransaction
        fields = ['partner', 'transaction_type', 'amount', 'date', 'note']
        widgets = {
            'partner': forms.Select(attrs={'class': 'form-select'}),
            'transaction_type': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        
class PartnerGoldTransactionForm(forms.ModelForm):
    class Meta:
        model = PartnerGoldTransaction
        fields = ['partner', 'transaction_type', 'weight', 'date', 'note']
        widgets = {
            'partner': forms.Select(attrs={'class': 'form-select'}),
            'transaction_type': forms.Select(attrs={'class': 'form-select'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
