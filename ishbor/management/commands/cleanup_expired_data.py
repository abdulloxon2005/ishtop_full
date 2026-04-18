"""
O3-FIX: GDPR — Ma'lumotlarni saqlash muddati tugagan ma'lumotlarni tozalash.
DATA_RETENTION_DAYS o'tgan harakatsiz hisoblarni aniqlaydi va admin ga xabar beradi.

Ishlatish:
    python manage.py cleanup_expired_data          # Faqat tekshirish (dry-run)
    python manage.py cleanup_expired_data --delete  # Haqiqatan o'chirish
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from ishbor.models import User, Consent


class Command(BaseCommand):
    help = "GDPR: Saqlash muddati o'tgan foydalanuvchi ma'lumotlarini tozalash"

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            help="Haqiqatan o'chirish (aks holda faqat report ko'rsatiladi)",
        )

    def handle(self, *args, **options):
        retention_days = getattr(settings, 'DATA_RETENTION_DAYS', 730)
        cutoff_date = timezone.now() - timedelta(days=retention_days)
        do_delete = options['delete']

        self.stdout.write(self.style.HTTP_INFO(
            f"\n{'=' * 60}\n"
            f"GDPR Ma'lumotlarni tozalash\n"
            f"Saqlash muddati: {retention_days} kun\n"
            f"Chegaraviy sana: {cutoff_date.strftime('%Y-%m-%d')}\n"
            f"Rejim: {'O\\'CHIRISH' if do_delete else 'TEKSHIRISH (dry-run)'}\n"
            f"{'=' * 60}\n"
        ))

        # Oxirgi login sanasi muddatdan o'tgan foydalanuvchilar
        expired_users = User.objects.filter(
            last_login__lt=cutoff_date,
            is_staff=False,
            is_superuser=False,
        )

        count = expired_users.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS(
                "Muddati o'tgan foydalanuvchi topilmadi. Hammasi yaxshi!"
            ))
            return

        self.stdout.write(self.style.WARNING(
            f"Muddati o'tgan foydalanuvchilar soni: {count}"
        ))

        for user in expired_users[:20]:  # Faqat birinchi 20 tasini ko'rsatamiz
            self.stdout.write(
                f"  - {user.username} (oxirgi login: {user.last_login}, rol: {user.role})"
            )

        if count > 20:
            self.stdout.write(f"  ... va yana {count - 20} ta")

        if do_delete:
            # O'chirishdan oldin rozilik jurnalini yozish
            for user in expired_users:
                Consent.objects.create(
                    user=user,
                    consent_type='gdpr',
                    consent_text=f"Foydalanuvchi '{user.username}' hisobi saqlash muddati "
                                 f"({retention_days} kun) o'tganligi sababli avtomatik o'chirildi.",
                    ip_address='127.0.0.1',
                )

            deleted_count, _ = expired_users.delete()
            self.stdout.write(self.style.SUCCESS(
                f"\n{deleted_count} ta foydalanuvchi va bog'liq ma'lumotlar o'chirildi."
            ))
        else:
            self.stdout.write(self.style.NOTICE(
                f"\nHaqiqatan o'chirish uchun: python manage.py cleanup_expired_data --delete"
            ))
