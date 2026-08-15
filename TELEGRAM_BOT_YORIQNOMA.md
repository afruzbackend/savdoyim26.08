# 🤖 Savdoyim Telegram bot — yo'riqnoma

Bot bazaga ulangan. Do'kon egasi va sotuvchilar login/parol bilan kirib,
hisobotlarni **PDF yoki Excel** ko'rinishida oladi.

## 1. Bot yaratish (bir marta)

1. Telegramda [@BotFather](https://t.me/BotFather) ni oching
2. `/newbot` buyrug'ini yuboring
3. Botga nom bering (masalan: `Savdoyim Hisobot`)
4. Username bering (masalan: `savdoyim_hisobot_bot`)
5. BotFather sizga **token** beradi, masalan:
   `7712345678:AAH8k...zZ`

## 2. Tokenni ulash

`savdo_tizimi/.env` faylini oching va tokenni qo'ying:

```
TELEGRAM_BOT_TOKEN=7712345678:AAH8k...zZ
```

## 3. Botni ishga tushirish

Terminalda (loyiha papkasida):

```bash
python savdo_tizimi/manage.py telegram_bot
```

Ishga tushgach `🤖 Savdoyim bot ishga tushdi` deb yozadi.
Bot ishlashi uchun bu oyna **ochiq** turishi kerak
(server kabi). To'xtatish: `Ctrl + C`.

> Doimiy ishlashi uchun keyinchalik bu buyruqni server/xizmat
> (Windows Task Scheduler yoki NSSM) sifatida sozlash mumkin.

## 4. Foydalanish

Telegramda o'z botingizni oching → `/start`:

1. Bot login (username) so'raydi → tizim loginingizni yuboring
2. Parolni yuboring (bot uni xavfsizlik uchun avtomatik o'chiradi)
3. Menyu chiqadi:
   - 📊 **Bugungi hisobot** — bugungi savdo, PDF/Excel tugmalari bilan
   - 📅 **Sana bo'yicha** — istalgan kunni yozib (masalan `09.06.2026`),
     o'sha kungi savdo + kassaga tushgan pul + top mahsulotlar
   - 🏆 **Top mahsulotlar** — so'nggi 30 kunda eng ko'p sotilganlar
   - 💰 **Kassa holati** — balans, to'lanmagan qarzlar, bugungi tushum
   - 👤 **Profil** / 🚪 **Chiqish**

Har bir hisobotда 📄 PDF va 📗 Excel tugmalari chiqadi — bosilganda
tayyor hujjat yuboriladi.

## Xavfsizlik

- Faqat **do'kon egasi** va **sotuvchi** rolidagilar kira oladi.
- Parol xabari darhol o'chiriladi, bazada saqlanmaydi.
- `/logout` — ulanishni uzadi.
