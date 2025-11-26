import requests

SMS_API_URL = "https://api.smsprovider.com/v1/send"  # آدرس API سرویس‌دهنده
API_KEY = "YOUR_API_KEY"
SENDER_NUMBER = "YOUR_SENDER_NUMBER"  # شماره اختصاصی پنل

def send_sms(phone, message):
    payload = {
        "from": SENDER_NUMBER,
        "to": phone,
        "text": message
    }
    headers = {
        "Content-Type": "application/json",
        "apikey": API_KEY
    }
    response = requests.post(SMS_API_URL, json=payload, headers=headers)
    
    # بررسی نتیجه
    if response.status_code == 200:
        return True, response.json()
    return False, response.text
