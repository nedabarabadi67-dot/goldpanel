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



