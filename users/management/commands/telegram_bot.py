# -*- coding: utf-8 -*-
"""
Savdoyim Telegram bot.

Ishga tushirish:
    python manage.py telegram_bot

Shart: .env faylida TELEGRAM_BOT_TOKEN to'ldirilgan bo'lishi kerak.
Tokenni @BotFather dan olasiz.

Imkoniyatlar:
  • Tizim login/parol bilan kirish (bazaga ulangan)
  • 📊 Bugungi hisobot (PDF / Excel)
  • 📅 Istalgan sana bo'yicha hisobot (o'sha kungi savdo, kassaga tushgan pul)
  • 🏆 Eng ko'p sotilgan mahsulotlar
  • 💰 Kassa holati va qarzlar
"""
import datetime as dt
import threading
import time as _time_mod

from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import authenticate
from django.utils import timezone

from users.models import CustomUser, TelegramLink
from kassa.hisobot_service import (
    dokon_aniqla, kunlik_hisobot, oraliq_top, kassa_holati,
    ombor_prognoz, hisobot_pdf, hisobot_excel, pul, qarz_eslatma_matn,
)

# Login jarayonidagi vaqtinchalik holat (chat_id -> {...})
HOLAT = {}


# ═══════════════════════════════════════════════════════════
#  YORDAMCHILAR
# ═══════════════════════════════════════════════════════════
def sana_pars(matn):
    """'15.07.2026' kabi matndan sanani o'qiydi. Bo'lmasa None."""
    matn = (matn or '').strip()
    for fmt in ('%d.%m.%Y', '%d.%m.%y', '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'):
        try:
            return dt.datetime.strptime(matn, fmt).date()
        except ValueError:
            continue
    return None


def bogliq_user(chat_id):
    """chat_id bo'yicha bog'langan foydalanuvchini qaytaradi (yoki None)."""
    link = (TelegramLink.objects
            .select_related('foydalanuvchi')
            .filter(chat_id=chat_id)
            .first())
    if not link:
        return None
    TelegramLink.objects.filter(pk=link.pk).update(oxirgi_faollik=timezone.now())
    return link.foydalanuvchi


class Command(BaseCommand):
    help = "Savdoyim Telegram botni ishga tushiradi (long polling)."

    def handle(self, *args, **options):
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or ''
        if not token:
            self.stderr.write(self.style.ERROR(
                "[XATO] TELEGRAM_BOT_TOKEN topilmadi!\n"
                "   .env fayliga @BotFather dan olingan tokenni qo'ying:\n"
                "   TELEGRAM_BOT_TOKEN=1234567:AA...\n"
            ))
            return

        import telebot
        from telebot import types

        bot = telebot.TeleBot(token, parse_mode='HTML')

        # ── Menyu klaviaturasi ──
        def asosiy_menyu():
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.row("📊 Bugungi hisobot", "📅 Sana bo'yicha")
            kb.row("🏆 Top mahsulotlar", "📦 Ombor")
            kb.row("💰 Kassa holati", "👤 Profil")
            kb.row("🚪 Chiqish")
            return kb

        def format_hisobot(data):
            sana = data['sana'].strftime('%d.%m.%Y')
            q = [
                f"🧾 <b>{data['dokon_nomi']}</b>",
                f"📅 {sana}",
                "",
                f"💰 Jami savdo: <b>{pul(data['jami_savdo'])}</b>",
                f"🏦 Kassaga tushgan: <b>{pul(data['kassaga_tushgan'])}</b>",
                f"🧾 Cheklar: <b>{data['chek_soni']} ta</b>",
                "",
                f"💵 Naqd: {pul(data['naqd'])}",
                f"💳 Karta: {pul(data['karta'])}",
                f"📋 Qarz: {pul(data['qarz'])}",
            ]
            if data['top']:
                q.append("")
                q.append("🏆 <b>Eng ko'p sotilgan:</b>")
                for i, m in enumerate(data['top'][:5], 1):
                    q.append(f"  {i}. {m['mahsulot_nomi']} — {m['jami_soni']} dona · {pul(m['summa'])}")
            return "\n".join(q)

        def hujjat_tugmalari(sana):
            kb = types.InlineKeyboardMarkup()
            kb.row(
                types.InlineKeyboardButton("📄 PDF", callback_data=f"pdf|{sana.isoformat()}"),
                types.InlineKeyboardButton("📗 Excel", callback_data=f"xlsx|{sana.isoformat()}"),
            )
            return kb

        # ─────────────────────────────────────────
        #  /start
        # ─────────────────────────────────────────
        @bot.message_handler(commands=['start'])
        def start(msg):
            user = bogliq_user(msg.chat.id)
            if user:
                bot.send_message(
                    msg.chat.id,
                    f"Assalomu alaykum, <b>{user.first_name or user.username}</b>! 👋\n"
                    f"Savdoyim botiga xush kelibsiz.\nQuyidagi menyudan tanlang:",
                    reply_markup=asosiy_menyu())
            else:
                HOLAT[msg.chat.id] = {'step': 'username'}
                bot.send_message(
                    msg.chat.id,
                    "🔐 <b>Savdoyim botiga kirish</b>\n\n"
                    "Tizimga kirish uchun <b>login (username)</b> ingizni yuboring:",
                    reply_markup=types.ReplyKeyboardRemove())

        @bot.message_handler(commands=['login'])
        def login_cmd(msg):
            HOLAT[msg.chat.id] = {'step': 'username'}
            bot.send_message(msg.chat.id, "Login (username) ingizni yuboring:",
                             reply_markup=types.ReplyKeyboardRemove())

        @bot.message_handler(commands=['help'])
        def help_cmd(msg):
            bot.send_message(
                msg.chat.id,
                "ℹ️ <b>Savdoyim bot</b>\n\n"
                "/start — boshlash / menyu\n"
                "/login — qayta kirish\n"
                "/logout — chiqish\n\n"
                "Menyu tugmalari orqali hisobotlarni PDF yoki Excel'da olasiz.")

        @bot.message_handler(commands=['logout'])
        def logout_cmd(msg):
            TelegramLink.objects.filter(chat_id=msg.chat.id).delete()
            HOLAT.pop(msg.chat.id, None)
            bot.send_message(msg.chat.id, "🚪 Tizimdan chiqdingiz. Qayta kirish: /login",
                             reply_markup=types.ReplyKeyboardRemove())

        # ── Tezkor buyruqlar (menyusiz to'g'ridan-to'g'ri) ──
        def _talab_login(chat_id):
            user = bogliq_user(chat_id)
            if not user:
                HOLAT[chat_id] = {'step': 'username'}
                bot.send_message(chat_id, "🔐 Avval tizimga kiring. Login (username)ingizni yuboring:")
            return user

        @bot.message_handler(commands=['bugun'])
        def bugun_cmd(msg):
            if _talab_login(msg.chat.id):
                _hisobot_yubor(msg.chat.id, timezone.localdate())

        @bot.message_handler(commands=['top'])
        def top_cmd(msg):
            u = _talab_login(msg.chat.id)
            if u:
                _top_yubor(msg.chat.id, u)

        @bot.message_handler(commands=['ombor'])
        def ombor_cmd(msg):
            u = _talab_login(msg.chat.id)
            if u:
                _ombor_yubor(msg.chat.id, u)

        @bot.message_handler(commands=['kassa'])
        def kassa_cmd(msg):
            u = _talab_login(msg.chat.id)
            if u:
                _kassa_yubor(msg.chat.id, u)

        # ─────────────────────────────────────────
        #  Matnli xabarlar (login jarayoni + menyu)
        # ─────────────────────────────────────────
        @bot.message_handler(content_types=['text'])
        def matn(msg):
            chat_id = msg.chat.id
            text = (msg.text or '').strip()
            holat = HOLAT.get(chat_id)

            # ── LOGIN JARAYONI ──
            if holat and holat.get('step') == 'username':
                holat['username'] = text
                holat['step'] = 'password'
                bot.send_message(chat_id, "🔑 Endi <b>parol</b>ingizni yuboring:")
                return

            if holat and holat.get('step') == 'password':
                username = holat.get('username', '')
                # Parol xabarini xavfsizlik uchun o'chiramiz
                try:
                    bot.delete_message(chat_id, msg.message_id)
                except Exception:
                    pass
                user = authenticate(username=username, password=text)
                HOLAT.pop(chat_id, None)
                if not user:
                    bot.send_message(chat_id, "❌ Login yoki parol noto'g'ri. Qayta urinish: /login")
                    return
                if dokon_aniqla(user) is None:
                    bot.send_message(
                        chat_id,
                        "⚠️ Bu bot faqat <b>do'kon egasi</b> va <b>sotuvchilar</b> uchun.\n"
                        "Sizning hisobingiz do'konga bog'lanmagan.")
                    return
                TelegramLink.objects.update_or_create(
                    foydalanuvchi=user,
                    defaults={'chat_id': chat_id,
                              'telegram_username': msg.from_user.username or ''},
                )
                bot.send_message(
                    chat_id,
                    f"✅ Xush kelibsiz, <b>{user.first_name or user.username}</b>!\n"
                    f"Muvaffaqiyatli kirdingiz.",
                    reply_markup=asosiy_menyu())
                return

            # ── SANA KIRITISH ──
            if holat and holat.get('step') == 'sana':
                sana = sana_pars(text)
                if not sana:
                    bot.send_message(chat_id, "❌ Sana formati noto'g'ri. Masalan: <b>15.07.2026</b>")
                    return
                HOLAT.pop(chat_id, None)
                _hisobot_yubor(chat_id, sana)
                return

            # ── MENYU ──
            user = bogliq_user(chat_id)
            if not user:
                HOLAT[chat_id] = {'step': 'username'}
                bot.send_message(chat_id, "🔐 Avval tizimga kiring. Login (username) ingizni yuboring:")
                return

            if text.startswith("📊"):
                _hisobot_yubor(chat_id, timezone.localdate())
            elif text.startswith("📅"):
                HOLAT[chat_id] = {'step': 'sana'}
                bugun = timezone.localdate().strftime('%d.%m.%Y')
                bot.send_message(chat_id,
                                 f"📅 Qaysi kun hisoboti kerak?\nSanani yuboring (masalan: <b>{bugun}</b>)")
            elif text.startswith("🏆"):
                _top_yubor(chat_id, user)
            elif text.startswith("📦"):
                _ombor_yubor(chat_id, user)
            elif text.startswith("💰"):
                _kassa_yubor(chat_id, user)
            elif text.startswith("👤"):
                _profil_yubor(chat_id, user)
            elif text.startswith("🚪"):
                bot.send_message(chat_id, "Chiqish uchun /logout buyrug'ini yuboring.")
            else:
                bot.send_message(chat_id, "Menyudan tanlang 👇", reply_markup=asosiy_menyu())

        # ─────────────────────────────────────────
        #  Yordamchi funksiyalar (hisobot yuborish)
        # ─────────────────────────────────────────
        def _hisobot_yubor(chat_id, sana):
            user = bogliq_user(chat_id)
            if not user:
                return
            dokon = dokon_aniqla(user)
            data = kunlik_hisobot(dokon, sana)
            bot.send_message(chat_id, format_hisobot(data),
                             reply_markup=hujjat_tugmalari(sana))

        def _top_yubor(chat_id, user):
            dokon = dokon_aniqla(user)
            gacha = timezone.localdate()
            dan = gacha - dt.timedelta(days=30)
            data = oraliq_top(dokon, dan, gacha, top_limit=10)
            if not data['top']:
                bot.send_message(chat_id, "So'nggi 30 kunda savdo topilmadi.")
                return
            q = [f"🏆 <b>Eng ko'p sotilgan (30 kun)</b>",
                 f"{dan.strftime('%d.%m')} — {gacha.strftime('%d.%m.%Y')}",
                 f"Umumiy savdo: <b>{pul(data['jami_savdo'])}</b>", ""]
            for i, m in enumerate(data['top'], 1):
                q.append(f"{i}. {m['mahsulot_nomi']} — <b>{m['jami_soni']} dona</b> · {pul(m['summa'])}")
            bot.send_message(chat_id, "\n".join(q))

        def _ombor_yubor(chat_id, user):
            dokon = dokon_aniqla(user)
            royxat = ombor_prognoz(dokon, ogohlantirish_kun=7)
            if not royxat:
                bot.send_message(chat_id, "✅ Ombor to'liq. Yaqin kunlarda tugaydigan mahsulot yo'q.")
                return
            q = ["🤖 <b>Aqlli ombor bashorati</b>",
                 "So'nggi savdolar (talab) bo'yicha taxminan qachon tugaydi:\n"]
            for m in royxat:
                trend = {'osish': ' 📈', 'pasayish': ' 📉'}.get(m.get('trend'), '')
                if m['qolgan_kun'] is not None:
                    if m['qolgan_kun'] <= 2:
                        belgi = "🔴"
                    elif m['qolgan_kun'] <= 7:
                        belgi = "🟠"
                    else:
                        belgi = "🟡"
                    sana = m['tugash_sana'].strftime('%d.%m.%Y') if m.get('tugash_sana') else '—'
                    kun_matn = f"~{m['qolgan_kun']} kunda · {sana} da tugaydi"
                else:
                    belgi = "⚪️"
                    kun_matn = "minimumdan past"
                q.append(
                    f"{belgi} <b>{m['nomi']}</b>{trend}\n"
                    f"     Qoldi: {m['soni']} {m['birlik']} · kunlik talab: {m['kunlik_sotuv']} · {kun_matn}")
            q.append("\n💡 Tavsiya: 🔴/🟠 belgililariga zudlik bilan buyurtma bering.")
            q.append("📈 = talab o'smoqda, 📉 = pasaymoqda.")
            bot.send_message(chat_id, "\n".join(q))

        def _kassa_yubor(chat_id, user):
            dokon = dokon_aniqla(user)
            k = kassa_holati(dokon)
            bugun = kunlik_hisobot(dokon, timezone.localdate())
            bot.send_message(
                chat_id,
                f"💰 <b>Kassa holati</b>\n\n"
                f"🏦 Kassa balansi: <b>{pul(k['balans'])}</b>\n"
                f"📋 To'lanmagan qarzlar: <b>{pul(k['qarz_jami'])}</b>\n\n"
                f"📊 Bugun kassaga tushgan: <b>{pul(bugun['kassaga_tushgan'])}</b>\n"
                f"🧾 Bugungi cheklar: <b>{bugun['chek_soni']} ta</b>")

        def _profil_yubor(chat_id, user):
            dokon = dokon_aniqla(user)
            bot.send_message(
                chat_id,
                f"👤 <b>Profil</b>\n\n"
                f"Login: <b>{user.username}</b>\n"
                f"Ism: {user.first_name or '—'}\n"
                f"Rol: {user.get_rol_display() or '—'}\n"
                f"Do'kon: {getattr(dokon, 'dokon_nomi', '—')}")

        # ─────────────────────────────────────────
        #  Inline tugmalar (PDF / Excel)
        # ─────────────────────────────────────────
        @bot.callback_query_handler(func=lambda c: True)
        def callback(c):
            chat_id = c.message.chat.id
            user = bogliq_user(chat_id)
            if not user:
                bot.answer_callback_query(c.id, "Avval tizimga kiring: /login")
                return
            try:
                tur, sana_str = c.data.split('|', 1)
                sana = dt.date.fromisoformat(sana_str)
            except Exception:
                bot.answer_callback_query(c.id, "Xatolik")
                return

            dokon = dokon_aniqla(user)
            data = kunlik_hisobot(dokon, sana)
            nom_sana = sana.strftime('%Y-%m-%d')
            bot.answer_callback_query(c.id, "⏳ Hujjat tayyorlanmoqda...")
            try:
                if tur == 'pdf':
                    buf = hisobot_pdf(data)
                    bot.send_document(chat_id, buf,
                                      visible_file_name=f"hisobot_{nom_sana}.pdf",
                                      caption=f"📄 {sana.strftime('%d.%m.%Y')} hisoboti")
                elif tur == 'xlsx':
                    buf = hisobot_excel(data)
                    bot.send_document(chat_id, buf,
                                      visible_file_name=f"hisobot_{nom_sana}.xlsx",
                                      caption=f"📗 {sana.strftime('%d.%m.%Y')} hisoboti")
            except Exception as e:
                bot.send_message(chat_id, f"❌ Hujjat yasashda xatolik: {e}")

        # ─────────────────────────────────────────
        # ── Avtomatik hisobot rejalashtiruvchisi (scheduler) ──
        from kassa.models import AvtoHisobotSozlama

        def _ombor_matn(royxat):
            q = ["🌅 <b>Ertalabki aqlli ombor bashorati</b>", "Tez tugaydigan mahsulotlar:\n"]
            for m in royxat:
                trend = {'osish': ' 📈', 'pasayish': ' 📉'}.get(m.get('trend'), '')
                if m['qolgan_kun'] is not None:
                    belgi = "🔴" if m['qolgan_kun'] <= 2 else ("🟠" if m['qolgan_kun'] <= 7 else "🟡")
                    sana = m['tugash_sana'].strftime('%d.%m') if m.get('tugash_sana') else '—'
                    kun = f"~{m['qolgan_kun']} kun · {sana} da tugaydi"
                else:
                    belgi, kun = "⚪️", "minimumdan past"
                q.append(f"{belgi} <b>{m['nomi']}</b>{trend} — {m['soni']} {m['birlik']} · {kun}")
            return "\n".join(q)

        def _avto_tekshir():
            now = timezone.localtime()
            bugun = now.date()
            hozir = now.time().replace(second=0, microsecond=0)
            for s in AvtoHisobotSozlama.objects.select_related('dokon', 'dokon__foydalanuvchi'):
                link = TelegramLink.objects.filter(foydalanuvchi=s.dokon.foydalanuvchi).first()
                if not link:
                    continue
                # Kunlik savdo hisoboti
                if s.kunlik_yoq and hozir >= s.kunlik_vaqt and s.oxirgi_kunlik != bugun:
                    try:
                        data = kunlik_hisobot(s.dokon, bugun)
                        matn = "🕘 <b>Avtomatik kunlik hisobot</b>\n\n" + format_hisobot(data)
                        # Qarz eslatmasi (muddati o'tgan / bugun keladigan)
                        eslatma = qarz_eslatma_matn(s.dokon, bugun)
                        if eslatma:
                            matn += "\n\n" + eslatma
                        bot.send_message(link.chat_id, matn)
                        s.oxirgi_kunlik = bugun
                        s.save(update_fields=['oxirgi_kunlik'])
                    except Exception:
                        pass
                # Ertalabki ombor prognozi
                if s.ombor_yoq and hozir >= s.ombor_vaqt and s.oxirgi_ombor != bugun:
                    try:
                        royxat = ombor_prognoz(s.dokon, ogohlantirish_kun=7)
                        if royxat:
                            bot.send_message(link.chat_id, _ombor_matn(royxat))
                        s.oxirgi_ombor = bugun
                        s.save(update_fields=['oxirgi_ombor'])
                    except Exception:
                        pass

        def _scheduler_loop():
            while True:
                try:
                    _avto_tekshir()
                except Exception:
                    pass
                _time_mod.sleep(30)

        threading.Thread(target=_scheduler_loop, daemon=True).start()

        # "/" menyusidagi buyruqlar ro'yxati (Telegram UI da ko'rinadi)
        try:
            bot.set_my_commands([
                types.BotCommand("start", "Menyu / boshlash"),
                types.BotCommand("bugun", "Bugungi hisobot"),
                types.BotCommand("top", "Top sotilgan mahsulotlar"),
                types.BotCommand("ombor", "Ombor prognozi"),
                types.BotCommand("kassa", "Kassa holati"),
                types.BotCommand("login", "Tizimga kirish"),
                types.BotCommand("logout", "Tizimdan chiqish"),
                types.BotCommand("help", "Yordam"),
            ])
        except Exception:
            pass

        self.stdout.write(self.style.SUCCESS("Savdoyim bot ishga tushdi. To'xtatish: Ctrl+C"))
        bot.infinity_polling(skip_pending=True, timeout=30)
