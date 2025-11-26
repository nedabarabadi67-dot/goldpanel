# seed_accounts.py

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gold_project.settings')  # ← اسم پروژه‌ت رو جایگزین کن
django.setup()


from dashboard.models import Account  # مسیر درست مدل رو بنویس
from django.db import transaction

@transaction.atomic
def run():
    data = {
        'دارایی‌ها': {
            'code': '1', 'type': 'asset',
            'children': {
                'وجه نقد': {'code': '11', 'children': {
                    'صندوق مغازه': {},
                    'صندوق کارگاه': {},
                }},
                'بانک‌ها': {'code': '12', 'children': {
                    'بانک ملت': {},
                    'بانک ملی': {},
                }},
                'حساب‌های دریافتنی': {'code': '13', 'children': {
                    'مشتری پیش‌فرض': {},
                }},
                'موجودی طلا': {'code': '14', 'children': {
                    'طلای خام': {},
                    'طلای ساخته‌شده': {},
                }},
                'پیش‌پرداخت‌ها': {'code': '15'},
            }
        },
        'بدهی‌ها': {
            'code': '2', 'type': 'liability',
            'children': {
                'حساب‌های پرداختنی': {'code': '21', 'children': {
                    'بنکدار پیش‌فرض': {},
                }},
                'وام و تسهیلات': {'code': '22'},
            }
        },
        'سرمایه': {
            'code': '3', 'type': 'capital',
            'children': {
                'سرمایه مالک': {'code': '31'},
                'برداشت مالک': {'code': '32'},
            }
        },
        'درآمد': {
            'code': '4', 'type': 'income',
            'children': {
                'فروش طلا': {'code': '41'},
                'اجرت فروش': {'code': '42'},
                'درآمد متفرقه': {'code': '43'},
            }
        },
        'هزینه‌ها': {
            'code': '5', 'type': 'expense',
            'children': {
                'اجرت ساخت': {'code': '51'},
                'هزینه‌های عملیاتی': {'code': '52'},
                'سایر هزینه‌ها': {'code': '53'},
            }
        },
        'بهای تمام‌شده': {
            'code': '6', 'type': 'cogs',
            'children': {
                'بهای تمام‌شده طلا': {'code': '61'},
                'بهای تمام‌شده اجرت': {'code': '62'},
            }
        }
    }

    def create_account(name, info, parent=None, acc_type=None):
        acc_type = acc_type or info.get('type') or (parent.type if parent else None)
        acc = Account.objects.create(
            name=name,
            code=info['code'],
            parent=parent,
            type=acc_type
        )
        print(f"✅ ایجاد حساب: {acc}")
        for cname, cinfo in info.get('children', {}).items():
            cinfo['type'] = acc_type
            if 'code' not in cinfo:
                # ساخت کد فرعی خودکار
                last_child = Account.objects.filter(parent=acc).order_by('-code').first()
                cinfo['code'] = str(int(last_child.code) + 1) if last_child else acc.code + '01'
            create_account(cname, cinfo, acc, acc_type)

    for name, info in data.items():
        create_account(name, info)

if __name__ == "__main__":
    run()
    print("🎉 تمام حساب‌ها با موفقیت ساخته شدند!")