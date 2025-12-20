from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from .models import RetentionCampaign, CampaignLog, CustomerCRM
from .services import send_sms   # ✅ درست

@shared_task
def run_scheduled_campaigns():
    today = timezone.now().date()
    campaigns = RetentionCampaign.objects.filter(active=True)

    for campaign in campaigns:
        customers = CustomerCRM.objects.filter(last_purchase__isnull=False)

        for crm in customers:
            send_date = crm.last_purchase + timedelta(
                days=campaign.send_days_after_purchase
            )

            if send_date == today:
                if not CampaignLog.objects.filter(
                    campaign=campaign,
                    customer=crm.customer
                ).exists():

                    success = send_sms(
                        crm.customer.phone,
                        campaign.message
                    )

                    CampaignLog.objects.create(
                        campaign=campaign,
                        customer=crm.customer,
                        message=campaign.message,
                        sent_at=timezone.now(),
                        status='SENT' if success else 'FAILED'
                    )
