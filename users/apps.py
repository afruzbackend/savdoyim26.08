import os
import sys
import threading

from django.apps import AppConfig

# Bot faqat bir marta ishga tushishi uchun bayroq (autoreload / takror import himoyasi)
_BOT_ISHGA_TUSHDI = False


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'Foydalanuvchilar'

    def ready(self):
        _telegram_botni_avto_ishga_tushir()


def _telegram_botni_avto_ishga_tushir():
    """runserver ishga tushganda Telegram botni fon oqimida (daemon thread) ishga tushiradi.

    Himoyalar:
      • Faqat `runserver` da (migrate, shell, telegram_bot va h.k. da emas).
      • Autoreload ikki jarayon ochadi — bot faqat asosiy (worker) jarayonda ishga tushadi,
        aks holda Telegram 409 Conflict beradi.
      • Token bo'lmasa yoki sozlama o'chirilgan bo'lsa — jim o'tkazib yuboriladi.
    """
    global _BOT_ISHGA_TUSHDI

    from django.conf import settings

    if not getattr(settings, 'RUN_BOT_WITH_SERVER', True):
        return

    # Faqat web-server ishga tushganda (boshqa buyruqlarda emas)
    if 'runserver' not in sys.argv:
        return

    # Autoreload yoqilgan bo'lsa — bot faqat qayta yuklovchi worker jarayonida ishga tushsin
    if '--noreload' not in sys.argv and os.environ.get('RUN_MAIN') != 'true':
        return

    token = (getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or '').strip()
    if not token:
        return

    if _BOT_ISHGA_TUSHDI:
        return
    _BOT_ISHGA_TUSHDI = True

    def _ishga_tushir():
        from django.core.management import call_command
        try:
            call_command('telegram_bot')
        except Exception as e:  # bot yiqilsa server ishlashda davom etsin
            sys.stderr.write(f"[telegram_bot] fon oqimida to'xtadi: {e}\n")

    threading.Thread(target=_ishga_tushir, name='telegram-bot', daemon=True).start()
    sys.stdout.write("[telegram_bot] server bilan birga fon oqimida ishga tushmoqda...\n")
