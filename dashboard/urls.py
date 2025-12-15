from django.contrib import admin
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LoginView,LogoutView
from django.urls import path,include
from django.conf.urls.i18n import i18n_patterns

urlpatterns = [
    path('index',views.index,name='index'),
    path('i18n/', include('django.conf.urls.i18n')),   # برای set_language   
    path('home',views.Home,name='Home'),
    path('',views.login_view,name='login'),
    path('partners',views.partner_list,name="partners"),
    path('partners/next-code/', views.get_next_partner_code, name='get_next_partner_code'),
    
    path('add-partner/', views.add_partner, name='add_partner'),
    path("add_or_edit_partner/", views.add_or_edit_partner, name="add_or_edit_partner"),

    path('logout',views.logout_view,name='logout'),
    path('product',views.product_view,name='product'),
    path('products/<int:pk>/update/', views.product_update, name='product_update'),
    # urls.py
    path('products/<int:id>/edit/', views.edit_product, name='edit_product'),
    path('gallery',views.gallery,name='gallery'),
    path('products/<int:pk>/delete/', views.delete_product, name='delete_product'),
    path("products/<int:pk>/detail/", views.product_detail, name="product_detail"),
    path('products/add/', views.add_product, name='add_product'),
    path('reports',views.reports,name='reports'),
    path('calender',views.calender,name='calender'),
    path('forms',views.forms,name='forms'),
    path('icons',views.icons,name='icons'),
    path('profile',views.profile,name='profile'),
    path('register',views.register,name='register'),
    path('tables',views.tables,name='tables'),
    
    path('journal_entries/', views.journal_entries_list, name='journal_entries_list'),
    path('journal_entry/<int:entry_id>/', views.journal_entry_detail, name='journal_entry_detail'),
    path('ledger/<int:account_id>/', views.ledger_view, name='ledger'),
    path('ledger_cash/<int:account_id>/', views.ledger_view_cash, name='ledger_cash'),
    
    path('invoice',views.invoice_view,name='invoice'),
    path('invoice/ab/', views.invoice_ab, name='invoice_ab'),

    path('invoice_purchase',views.invoice_purchase,name='invoice_purchase'),
    path('add_purchase_invoice',views.add_purchase_invoice,name="add_purchase_invoice"),
    path('get_product_info/', views.get_product_info, name='get_product_info'),
    path('save_purchase_items',views.save_purchase_items,name='save_purchase_items'),
    path('save-purchase2/', views.save_purchase2, name='save_purchase2'),
    path('save-purchase3/', views.save_purchase3, name='save_purchase3'),

    path('customers/check/', views.get_customer_by_phone, name='get_customer_by_phone'),
    path("invoice/<int:invoice_id>/pdf/", views.generate_invoice_pdf, name="generate_invoice_pdf"),
    path("invoice/<int:invoice_id>/pdf2/", views.generate_invoice_pdf_2, name="generate_invoice_pdf_2"),
    path("calender",views.calender,name='calender'),
    
    path("test",views.invoice_test,name='test'),
    
    # urls.py
    path("invoices/search/", views.invoice_search, name="invoice_search"),
    path("purchase/search/", views.purchase_search, name="purchase_search"),
    path('product/<int:pk>/print-label/', views.print_label, name='print_label'),
    
    path('invoice/<int:invoice_id>/print-labels/', views.print_invoice_labels, name='print_invoice_labels'),
    path('invoice/<int:invoice_id>/download-pdf/',views.download_invoice_pdf, name='download_invoice_pdf'),
    path('create_invoice_with_payment',views.create_invoice_with_payment, name='create_invoice_with_payment'),
   
   path("daily-report/pdf/", views.daily_report_pdf_view, name="daily_report_pdf"),

    path('invoices/by_date/', views.invoices_by_date, name='invoices_by_date'),
    path('crm',views.crm,name='crm'),
    path('campaign/create/', views.create_or_edit_campaign, name='create_campaign'),
    path('campaign/<int:pk>/edit/', views.create_or_edit_campaign, name='edit_campaign'),

    path('campaign/<int:pk>/json/', views.campaign_json, name='campaign_json'),
    path('products/get_next_code/<str:category>/', views.get_next_code, name='get_next_code'),
    path("campaign/<int:campaign_id>/send-test/", views.send_test_sms, name="send_test_sms"),
    path('meltedgold/', views.melted_gold_list, name='meltedgold'),
    path('melted_gold_add_ajax/', views.melted_gold_add_ajax, name='melted_gold_add_ajax'),
    path("melted-gold-sale/add-ajax/", views.melted_gold_sale_add_ajax, name="melted_gold_sale_add_ajax"),
    
    path('dashboard/', views.financial_dashboard, name='financial_dashboard'),
    
    #path('banks/', views.banks_view, name='banks'),
    path('banks/', views.bank_accounts_list, name='banks'),
    path('save-bank_account/', views.save_bank_account, name='save_bank_account'),
    path('save_transaction/', views.save_transaction, name='save_transaction'),
    
    path('bank_ledger/<int:bank_account_id>/', views.bank_ledger, name='bank_ledger'),
    path('banks/<int:bank_account_id>/deposit/', views.bank_deposit_withdraw, name='bank_deposit'),
    path('banks/<int:bank_account_id>/reconcile/', views.bank_reconcile, name='bank_reconcile'),
    path('banks/reconcile/import_csv/', views.import_bank_statement_csv, name='import_bank_csv'),
    
    
    
    #path('dashboard/customer/<int:customer_id>/', views.customer_ledger_view, name='customer_ledger'),
    #path('dashboard/customer/<int:customer_id>/pdf/', views.customer_ledger_pdf, name='customer_ledger_pdf'),
    #path('dashboard/account/<int:account_id>/pdf/', views.account_ledger_pdf, name='account_ledger_pdf'),
    #path('dashboard/sales/', views.sales_report, name='sales_report'),
    #path('dashboard/purchases/', views.purchase_report, name='purchase_report'),
    
    path('accounting_setup', views.accounting_setup, name='accounting_setup'),
    path('add_cash_account', views.add_cash_account, name='add_cash_account'),
    path('add_edit_bank', views.add_edit_bank, name='add_edit_bank'),
    path('add_edit_cash', views.add_edit_cash, name='add_edit_cash'),
    path('add_edit_expense', views.add_edit_expense, name='add_edit_expense'),
    path('transaction', views.transaction_view, name='transaction'),
    path("reports/bank/<int:bank_id>/", views.bank_transactions_report, name="bank_report"),



]
