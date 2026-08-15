# -*- coding: utf-8 -*-
"""Bepul AI agent — har do'kon uchun anomaliyalarni topib, Telegram botga yuboradi.

Ishlatish (masalan kuniga bir marta, Windows Task Scheduler orqali):
    python manage.py anomaliya_yubor
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from users.models import DokonEgasiProfil, TelegramLink
from kassa.anomaliya_service import anomaliya_matn


class Command(BaseCommand):
    help = "Do'konlar bo'yicha anomaliyalarni Telegram botga yuboradi (bepul, LLM'siz)."

    def handle(self, *args, **opts):
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or ''
        if not token:
            self.stderr.write("TELEGRAM_BOT_TOKEN topilmadi (.env).")
            return
        import telebot
        bot = telebot.TeleBot(token, parse_mode='HTML')

        yuborildi = 0
        for dokon in DokonEgasiProfil.objects.select_related('foydalanuvchi'):
            link = TelegramLink.objects.filter(foydalanuvchi=dokon.foydalanuvchi).first()
            if not link:
                continue
            matn = anomaliya_matn(dokon)
            if not matn:
                continue
            try:
                bot.send_message(link.chat_id, matn)
                yuborildi += 1
            except Exception as e:
                self.stderr.write(f"{dokon.dokon_nomi}: yuborilmadi ({e})")

        self.stdout.write(self.style.SUCCESS(f"Tugadi. {yuborildi} ta do'konga yuborildi."))
