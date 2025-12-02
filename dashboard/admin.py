from dataclasses import fields
from django.contrib import admin
from .models import ExpenseAccount, Product,Invoice,InvoiceItem,Customer
from .models import UserProfile,Product,Person,PurchaseInvoice,PurchaseItem,CustomerCRM,CampaignLog,RetentionCampaign
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Account,JournalEntry,JournalItem,MeltedGoldTransaction,BankAccount,CashAccount
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget

#admin.site.register(UserProfile)
#admin.site.register(InvoiceItem)
#admin.site.register(Invoice)
#admin.site.register(Customer)
#admin.site.register(CustomerCRM)
#admin.site.register(Person)
#admin.site.register(PurchaseItem)
#admin.site.register(PurchaseInvoice)
#admin.site.register(CampaignLog)
#admin.site.register(RetentionCampaign)
#admin.site.register(Account)
#admin.site.register(JournalItem)
#admin.site.register(JournalEntry)
#admin.site.register(MeltedGoldTransaction)
#admin.site.register(BankAccount)
#admin.site.register(CashAccount)
#admin.site.register(ExpenseAccount)



class ProductResource(resources.ModelResource):
    class Meta:
        model = Product
        import_id_fields = ['code']  # تا بر اساس کد، تکراری ثبت نشه
        fields = ('code', 'name', 'category' ,'weight', 'quantity', 'labor', 'description','purity','initial_weight','price','barcode_image')
        
@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    list_display = ('code', 'name', 'category', 'weight', 'quantity', 'labor','description','purity','initial_weight','price','barcode_image')

# ----------------------------------------------------
# 1) UserProfile
# ----------------------------------------------------
class UserProfileResource(resources.ModelResource):
    class Meta:
        model = UserProfile
        import_id_fields = ["user"]   # جلوگیری از تکرار
        fields = (
            "user",
            "role",
            "phone",
            "is_active",
            "created",
        )

@admin.register(UserProfile)
class UserProfileAdmin(ImportExportModelAdmin):
    resource_class = UserProfileResource
    list_display = ("user", "role", "phone", "is_active", "created")
    search_fields = ("user__username", "phone", "role")
    list_filter = ("role", "is_active")

# ----------------------------------------------------
# 2) Account
# ----------------------------------------------------
class AccountResource(resources.ModelResource):
    class Meta:
        model = Account
        import_id_fields = ["code"]
        fields = (
            "code", "name", "type", "parent",
            "description", "created"
        )

@admin.register(Account)
class AccountAdmin(ImportExportModelAdmin):
    resource_class = AccountResource
    list_display = ("code", "name", "type", "parent", "created")
    search_fields = ("code", "name", "type")
    list_filter = ("type",)


# ----------------------------------------------------
# 3) CashAccount
# ----------------------------------------------------
class CashAccountResource(resources.ModelResource):
    class Meta:
        model = CashAccount
        import_id_fields = ["code"]
        fields = (
            "name", "code", "account",
            "balance", "note", "created_at"
        )

@admin.register(CashAccount)
class CashAccountAdmin(ImportExportModelAdmin):
    resource_class = CashAccountResource
    list_display = ("name", "code", "balance", "created_at")
    search_fields = ("name", "code")
    list_filter = ("created_at",)


# ----------------------------------------------------
# 4) BankAccount
# ----------------------------------------------------
class BankAccountResource(resources.ModelResource):
    class Meta:
        model = BankAccount
        import_id_fields = ["code"]
        fields = (
            "name", "code", "owner", "branch_name",
            "account_number", "card_number", "iban",
            "account", "balance", "note", "created_at"
        )

@admin.register(BankAccount)
class BankAccountAdmin(ImportExportModelAdmin):
    resource_class = BankAccountResource
    list_display = ("name", "code", "owner", "balance", "created_at")
    search_fields = ("name", "code", "owner", "branch_name")
    list_filter = ("created_at",)


# ----------------------------------------------------
# 5) ExpenseAccount
# ----------------------------------------------------
class ExpenseAccountResource(resources.ModelResource):
    class Meta:
        model = ExpenseAccount
        import_id_fields = ["code"]
        fields = (
            "name", "code", "account",
            "balance", "note", "created_at"
        )

@admin.register(ExpenseAccount)
class ExpenseAccountAdmin(ImportExportModelAdmin):
    resource_class = ExpenseAccountResource
    list_display = ("name", "code", "balance", "created_at")
    search_fields = ("name", "code")
    list_filter = ("created_at",)  
    
class PersonResource(resources.ModelResource):
    account = fields.Field(
        column_name='account',
        attribute='account',
        widget=ForeignKeyWidget(Account, 'code')
    )

    class Meta:
        model = Person
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ['code']
        fields = (
            'code', 'name', 'type_partner', 'gender', 'birth_date',
            'phone', 'store', 'note', 'account_number', 'account'
        )

@admin.register(Person)
class PersonAdmin(ImportExportModelAdmin):
    resource_class = PersonResource
    list_display = ('code', 'name', 'type_partner', 'phone', 'store', 'created_at')
    search_fields = ('name', 'phone', 'code')
    list_filter = ('type_partner', 'gender')


class JournalEntryResource(resources.ModelResource):
    class Meta:
        model = JournalEntry
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ['id']
        fields = (
            'id',
            'date',
            'description',
        )

@admin.register(JournalEntry)
class JournalEntryAdmin(ImportExportModelAdmin):
    resource_class = JournalEntryResource
    list_display = ('id', 'date', 'description')
    search_fields = ('description',)

class JournalItemResource(resources.ModelResource):

    entry = fields.Field(
        column_name='entry',
        attribute='entry',
        widget=ForeignKeyWidget(JournalEntry, 'id')
    )

    account = fields.Field(
        column_name='account',
        attribute='account',
        widget=ForeignKeyWidget(Account, 'code')
    )

    bank_account = fields.Field(
        column_name='bank_account',
        attribute='bank_account',
        widget=ForeignKeyWidget(BankAccount, 'code')
    )

    class Meta:
        model = JournalItem
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ['id']
        fields = (
            'id', 'entry',
            'debit_money', 'credit_money',
            'debit_gold', 'credit_gold',
            'description',
            'account', 'bank_account',
            'reconciled', 'reconciled_date', 'bank_statement_ref',
        )
@admin.register(JournalItem)
class JournalItemAdmin(ImportExportModelAdmin):
    resource_class = JournalItemResource
    list_display = (
        'id', 'entry', 'debit_money', 'credit_money',
        'debit_gold', 'credit_gold', 'account', 'bank_account'
    )
    list_filter = ('reconciled',)
    search_fields = ('description',)
    
class InvoiceResource(resources.ModelResource):
    customer = fields.Field(
        column_name='customer',
        attribute='customer',
        widget=ForeignKeyWidget(Person, 'code')
    )

    class Meta:
        model = Invoice
        import_id_fields = ['number']
        fields = ('number', 'date', 'time', 'customer', 'total_price', 'profit_total')


class InvoiceItemResource(resources.ModelResource):
    invoice = fields.Field(
        column_name='invoice',
        attribute='invoice',
        widget=ForeignKeyWidget(Invoice, 'number')
    )
    product = fields.Field(
        column_name='product',
        attribute='product',
        widget=ForeignKeyWidget(Product, 'code')
    )

    class Meta:
        model = InvoiceItem
        import_id_fields = ['id']
        fields = (
            'id', 'invoice', 'product', 'quantity', 'gold_price_per_gram',
            'labor_per_gram', 'profit_percent', 'profit_total', 'weight', 'purity', 'total'
        )
        
@admin.register(Invoice)
class InvoiceAdmin(ImportExportModelAdmin):
    resource_class = InvoiceResource
    list_display = ('number', 'customer', 'date', 'total_price', 'profit_total')


@admin.register(InvoiceItem)
class InvoiceItemAdmin(ImportExportModelAdmin):
    resource_class = InvoiceItemResource
    list_display = ('invoice', 'product', 'quantity', 'weight', 'total')

class RetentionCampaignResource(resources.ModelResource):
    class Meta:
        model = RetentionCampaign
        import_id_fields = ['id']
        fields = (
            'id', 'name', 'campaign_type', 'message', 'send_days_after_purchase',
            'specific_date', 'loyalty_points', 'inactive_days', 'active'
        )

@admin.register(RetentionCampaign)
class RetentionCampaignAdmin(ImportExportModelAdmin):
    resource_class = RetentionCampaignResource
    list_display = ('name', 'campaign_type', 'active', 'created_at')


from .models import CampaignLog

class CampaignLogResource(resources.ModelResource):
    campaign = fields.Field(
        column_name='campaign',
        attribute='campaign',
        widget=ForeignKeyWidget(RetentionCampaign, 'id')
    )
    customer = fields.Field(
        column_name='customer',
        attribute='customer',
        widget=ForeignKeyWidget(Person, 'code')
    )

    class Meta:
        model = CampaignLog
        import_id_fields = ['id']
        fields = ('id', 'campaign', 'customer', 'message', 'sent_at', 'status')
@admin.register(CampaignLog)
class CampaignLogAdmin(ImportExportModelAdmin):
    resource_class = CampaignLogResource
    list_display = ('campaign', 'customer', 'status', 'sent_at')


from .models import CustomerCRM

class CustomerCRMResource(resources.ModelResource):
    customer = fields.Field(
        column_name='customer',
        attribute='customer',
        widget=ForeignKeyWidget(Person, 'code')
    )

    class Meta:
        model = CustomerCRM
        import_id_fields = ['id']
        fields = ('id', 'customer', 'last_purchase', 'total_purchases', 'loyalty_points')
@admin.register(CustomerCRM)
class CustomerCRMAdmin(ImportExportModelAdmin):
    resource_class = CustomerCRMResource
    list_display = ('customer', 'last_purchase', 'total_purchases', 'loyalty_points')


class MeltedGoldTransactionResource(resources.ModelResource):
    melted_gold = fields.Field(
        column_name='melted_gold',
        attribute='melted_gold',
        widget=ForeignKeyWidget(Product, 'code')
    )

    class Meta:
        model = MeltedGoldTransaction
        import_id_fields = ['id']
        fields = (
            'id', 'melted_gold', 'transaction_type', 'source', 'destination',
            'weight', 'price_per_gram', 'price_per_mesghal', 'total_price',
            'date', 'note'
        )
@admin.register(MeltedGoldTransaction)
class MeltedGoldTransactionAdmin(ImportExportModelAdmin):
    resource_class = MeltedGoldTransactionResource
    list_display = ('melted_gold', 'transaction_type', 'weight', 'total_price', 'date')

class PurchaseInvoiceResource(resources.ModelResource):
    seller = fields.Field(
        column_name='seller',
        attribute='seller',
        widget=ForeignKeyWidget(Person, 'code')
    )

    class Meta:
        model = PurchaseInvoice
        import_id_fields = ['number']
        fields = (
            'number', 'number_store', 'date', 'seller', 'type',
            'weight', 'purity', 'labor', 'price', 'laborprice',
            'pricemesghal', 'total_price', 'note'
        )
        
@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(ImportExportModelAdmin):
    resource_class = PurchaseInvoiceResource
    list_display = ('number', 'seller', 'date', 'type', 'weight', 'total_price')


from .models import PurchaseItem

class PurchaseItemResource(resources.ModelResource):
    invoice = fields.Field(
        column_name='invoice',
        attribute='invoice',
        widget=ForeignKeyWidget(PurchaseInvoice, 'number')
    )
    product = fields.Field(
        column_name='product',
        attribute='product',
        widget=ForeignKeyWidget(Product, 'code')
    )

    class Meta:
        model = PurchaseItem
        import_id_fields = ['id']
        fields = ('id', 'invoice', 'product', 'quantity')


class PurchaseItemResource(resources.ModelResource):
    invoice = fields.Field(
        column_name='invoice',
        attribute='invoice',
        widget=ForeignKeyWidget(PurchaseInvoice, 'number')
    )
    product = fields.Field(
        column_name='product',
        attribute='product',
        widget=ForeignKeyWidget(Product, 'code')
    )

    class Meta:
        model = PurchaseItem
        import_id_fields = ['id']
        fields = ('id', 'invoice', 'product', 'quantity')


@admin.register(PurchaseItem)
class PurchaseItemAdmin(ImportExportModelAdmin):
    resource_class = PurchaseItemResource
    list_display = ('invoice', 'product', 'quantity')
        