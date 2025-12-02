from django.contrib import admin
from .models import ExpenseAccount, Product,Invoice,InvoiceItem,Customer
from .models import UserProfile,Product,Person,PurchaseInvoice,PurchaseItem,CustomerCRM,CampaignLog,RetentionCampaign
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Account,JournalEntry,JournalItem,MeltedGoldTransaction,BankAccount,CashAccount

admin.site.register(UserProfile)
admin.site.register(InvoiceItem)
admin.site.register(Invoice)
admin.site.register(Customer)
admin.site.register(CustomerCRM)
admin.site.register(Person)
admin.site.register(PurchaseItem)
admin.site.register(PurchaseInvoice)
admin.site.register(CampaignLog)
#admin.site.register(RetentionCampaign)
admin.site.register(Account)
admin.site.register(JournalItem)
admin.site.register(JournalEntry)
admin.site.register(MeltedGoldTransaction)
admin.site.register(BankAccount)
admin.site.register(CashAccount)
admin.site.register(ExpenseAccount)



class ProductResource(resources.ModelResource):
    class Meta:
        model = Product
        import_id_fields = ['code']  # تا بر اساس کد، تکراری ثبت نشه
        fields = ('code', 'name', 'category' ,'weight', 'quantity', 'labor', 'description','purity','initial_weight','price','barcode_image')
        
@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    list_display = ('code', 'name', 'category', 'weight', 'quantity', 'labor','description','purity','initial_weight','price','barcode_image')

class JournalResource(resources.ModelResource):
    class Meta:
        model = JournalEntry
        import_id_fields = ['id']  # تا بر اساس کد، تکراری ثبت نشه
        fields = ('id', 'date', 'description' ,'related_purchase', 'related_sale')
        
@admin.register(JournalEntry)
class JournalEntryAdmin(ImportExportModelAdmin):
    resource_class = JournalResource
    list_display = ('id', 'date', 'description' ,'related_purchase', 'related_sale')
  
"""  
class AccountResource(resources.ModelResource):
    class Meta:
        model = Account
        import_id_fields = ['code']  # بر اساس کد حساب، تکراری ثبت نشود
        fields = ('code', 'name', 'type','description', 'created')

@admin.register(Account)
class AccountAdmin(ImportExportModelAdmin):
    resource_class = AccountResource
    list_display = ('code', 'name', 'type','description', 'created')
"""
