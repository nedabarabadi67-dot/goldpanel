# myproject/celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

#celery -A gold_project worker -l info
#celery -A gold_project beat -l info

# تنظیمات Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gold_project.settings')

app = Celery('gold_project')

# خواندن تنظیمات از settings.py با prefix CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# اتوماتیک پیدا کردن tasks.py در هر اپ
app.autodiscover_tasks()

