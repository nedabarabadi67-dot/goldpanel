# crm/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import RetentionCampaign, CampaignLog, CustomerCRM
# dashboard/tasks.py
from dashboard.models import RetentionCampaign, CustomerCRM, CampaignLog
from dashboard.tasks import send_sms
from django.utils import timezone
import requests

def run_scheduled_campaigns_test():
    campaigns = RetentionCampaign.objects.filter(active=True)
    customers = CustomerCRM.objects.filter(last_purchase__isnull=False)

    for campaign in campaigns:
        for crm in customers:
            # ارسال بدون توجه به تاریخ
            send_sms(crm.customer.phone, campaign.message)
            CampaignLog.objects.create(
                campaign=campaign,
                customer=crm.customer,
                message=campaign.message,
                sent_at=timezone.now(),
                status='SENT'
            )
    print("✅ تست ارسال پیامک تمام شد.")


# تابع نمونه ارسال SMS
def send_sms(phone_number, message):
    """
    ارسال پیامک به مشتری
    اگر API واقعی داشته باشید، کد فراخوانی API رو اینجا قرار بدید.
    """

    # --- حالت تستی (لوکال) ---
    print(f"📩 تست SMS → به {phone_number}: {message}")

    # --- حالت واقعی (با API) ---
    try:
        # مثال با سامانه ملی پیامک (باید یوزرنیم/پسورد/خط اختصاصی خودتون رو بزنید)
        url = "https://rest.payamak-panel.com/api/SendSMS/SendSMS"
        payload = {
            "username": "USERNAME",
            "password": "PASSWORD",
            "to": phone_number,
            "from": "3000XXXXXXX",   # شماره خط اختصاصی شما
            "text": message,
            "isflash": False
        }
        response = requests.post(url, data=payload)
        print("✅ پاسخ سرور پیامک:", response.text)
        return response.status_code == 200
    except Exception as e:
        print("❌ خطا در ارسال پیامک:", e)
        return False

@shared_task
def run_scheduled_campaigns():
    today = timezone.now().date()
    campaigns = RetentionCampaign.objects.filter(active=True)

    for campaign in campaigns:
        customers = CustomerCRM.objects.filter(
            last_purchase__isnull=False
        )
        for crm in customers:
            send_date = crm.last_purchase + timedelta(days=campaign.send_days_after_purchase)
            if send_date == today:
                # بررسی اینکه آیا پیامک قبلاً ارسال شده
                if not CampaignLog.objects.filter(campaign=campaign, customer=crm.customer).exists():
                    success = send_sms(crm.customer.phone, campaign.message)
                    CampaignLog.objects.create(
                        campaign=campaign,
                        customer=crm.customer,
                        message=campaign.message,
                        sent_at=timezone.now(),
                        status='SENT' if success else 'FAILED'
                    )

