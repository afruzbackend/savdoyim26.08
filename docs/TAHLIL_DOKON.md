# Savdoyim (do'kon tizimi) — to'liq tahlil (16.10.2026)

> **Asosiy fokus — shu loyiha.** Bozor tizimi (Bozor Nazorat) tahlili alohida:
> `savdoyimbozor/docs/TAHLIL_BOZOR.md`.

> Manbalar: 4 ta mustaqil audit/tadqiqot agenti + 2 ta qayta tekshiruv (xavfsizlik topilmalari kod
> o'qib tasdiqlandi; qonun/narx faktlari ikkinchi mustaqil manba bilan tekshirildi).
> [T] = tasdiqlangan manba bilan, [B] = baho (taxmin). Valyuta: 1 $ ≈ 11 809 so'm (MB, 01.10.2026).
> Qonun bo'yicha xulosalarni ishga tushirishdan oldin yurist bilan tasdiqlang.

---

## 0. Eng muhim 10 ta xulosa (hech kim aytmagan narsalar)

1. **Sizda bitta emas, 3 ta loyiha bor**, va ular bir-biriga xalaqit beryapti:
   - `savdoyim/savdoyim26.08` — do'kon egasi uchun POS (Django 4.2, SQLite, **git yo'q**, 42 test).
   - `savdo20` — "DokonTizim" nomli investor pitch (pptx, TAQDIMOT.md).
   - `savdoyimbozor` — "Bozor Nazorat" (davlat/inspektor uchun, 189 commit, Django 5.2, Docker,
     PostgreSQL, Celery, **468 test o'tadi**).
   Uchta nom (Savdoyim / DokonTizim / Bozor Nazorat) — brend yo'q. Bitta nomni tanlang.
2. **Bozor Nazorat'ning sotuvchi qismi Savdoyim'dan texnik jihatdan yetukroq** (offline navbat,
   2FA, throttling, Docker, preflight, zaxira). Savdoyim'da esa egasi uchun funksiyalar ko'p
   (hisobot, AI, Telegram, prognoz). Ikkalasini parallel rivojlantirish — vaqtni ikkiga bo'lish.
3. **Ikki mahsulot g'oyasi bir-biriga zid**: Savdoyim "sotuvchiga xizmat qiladi", Bozor Nazorat esa
   "sotuvchini davlatga tekshiradi" (rostlik %, prokuror roli, "jinoyat darajasi"). Agar bozordagi
   sotuvchilar POS ma'lumoti soliqqa "rostlik bali" sifatida ketishini bilsa — Savdoyim'ga ishonch
   yo'qoladi. Bitta brend ostida birlashtirmang.
4. **Davlat o'zi "E-bozor" platformasini qilyapti** — VMQ №358 (02.07.2026), Soliq qo'mitasi
   boshqaradi. Ilovasida **"Piskent dehqon bozori" MChJ (372 do'kon)** ham bor. Ya'ni Bozor
   Nazorat'ni davlatga sotish — davlatning o'z tizimi bilan raqobat. Real yo'l: bozor operatoriga
   (Piskent bozori MChJ) "E-bozor talablariga moslashish konsoli" sifatida sotish [T].
5. **GitHub'dagi `afruzbackend/savdoyimbozor` repozitoriyasi OCHIQ (public)** — rostlik formulasi,
   chegaralar, kamera mantig'i hammaga ko'rinadi; sotuvchilar uni aylanib o'tishni o'rganadi.
   Darhol **private** qiling. (Sirlar topilmadi.)
6. **Savdoyim'ning QR "chek"i fiskal chek emas.** O'zbekistonda har bir naqd/karta savdo ro'yxatdagi
   onlayn-NKM yoki virtual kassa orqali fiskal chek bilan bo'lishi shart (VMQ 943). Do'kon sizning
   chekingizni berib qo'ysa — jarima: chek bermaslik 5 mln so'm, takroriy — choraklik tushumning 20%
   gacha [T]. Mijozlar jarimani sizdan ko'radi. → MVP'da chekka "Fiskal chek emas" yozing va
   Rahmat (sobiq Multikassa) / E-POS / UzKassa API orqali fiskalizatsiya qiling.
7. **Shaxsiy ma'lumotlar qonuni 2026-yilda yumshadi** [T]: ZRU-1125 (26.03.2026) dan keyin faqat
   biometrik, genetik va telekom abonent ma'lumotlari O'zbekistonda saqlanishi shart. VMQ (29.07.2026)
   49 davlatni (AQSH, Germaniya, Finlyandiya...) "adekvat" deb tasdiqladi. Ya'ni Hetzner qonuniy
   jihatdan mumkin. Lekin: **ro'yxatdan o'tishda pasport va JSHSHR so'ramang** — sizga kerak emas,
   faqat xavf. AI'ga mijoz ism/telefonini yubormang, faqat agregat raqamlar.
8. **IT Park imtiyozlari 2028-yilda tugaydi** (faqat >50% eksport qilganlar uchun 2040 gacha uzayadi,
   QQSsiz) [T]. YaTT IT Park rezidenti bo'la olmaydi — faqat MChJ [T]. Ya'ni IT Park — 2 yillik bonus,
   strategiya emas.
9. **Pitch deck'dagi "Backend 90% (complete & tested)" haqiqatga to'g'ri kelmaydi** — xavfsizlik
   teshiklari, fiskalizatsiya, to'lov, billing yo'q. $50–150K so'rash hozir erta: investor birinchi
   savol — "nechta to'layotgan do'kon bor?". Avval 20–50 to'layotgan do'kon, keyin investitsiya.
10. **Claude Code'ingizdagi "Pixel Agents" hook'i** har bir amaldan oldin/keyin `node` ishga
    tushiradi; 8-oktabrgacha 600+ marta xato bergan, endi esa ~6 soniyalik timeout bilan
    ishni sekinlashtiryapti (23 marta). Pixel Agents'dan foydalanmasangiz — olib tashlang.

---

## 1. Loyiha holati (Savdoyim, kod auditi)

**Hajm:** ~11.1k qator Python, 43 model, ~127 URL, 55 shablon. 42/42 test o'tadi.
`db.sqlite3` bo'sh (foydalanuvchi yo'q). `.env` yo'q. `../.venv` yo'q (`launch.json` buzilgan).

| Funksiya | Holat |
|---|---|
| Kassa sotuvi (naqd/karta/qarz), QR chek | Ishlaydi. Karta — soxta UI. Chegirma UI yo'q |
| Smena / Z-hisobot | Ishlaydi, lekin web versiyada naqd qarz to'lovi hisobga olinmaydi (M2) |
| Qaytarish | Ishlaydi, poyga holati bor (M1) |
| Qarz daftar | Faqat to'liq to'lash, qisman yo'q |
| Mahsulot, import, inventarizatsiya | Ishlaydi (inventarizatsiya yakunida sotuvlar yo'qoladi — M11) |
| Hisobot, PDF/Excel, prognoz | Ishlaydi |
| Telegram bot / avto-hisobot | Faqat `runserver` ichida ishlaydi; gunicorn'da ishlamaydi |
| AI tahlil | Kalit bo'lsa ishlaydi, limit yo'q |
| Onlayn buyurtma (Click&Collect) | Ishlaydi, lekin suiiste'molga ochiq (H6) |
| Sodiqlik ballari | Yig'iladi, lekin sarflab bo'lmaydi |
| Soliq moduli | Stub (float bilan oddiy %) |
| PWA / offline | Faqat sahifa keshlanadi, offline sotuv YO'Q |
| Rus tili | Qisman (faqat JS almashtirish) |
| Multi-filial, billing, fiskal, to'lov, markirovka, e-faktura | **Yo'q** |
| USB skaner, 58/80mm printer (ESC/POS) | **Yo'q** (faqat telefon kamera skaneri, `window.print()`) |

### Xavfsizlik (mustaqil qayta tekshirilgan)
**Critical**
- **C3 — Parolni tiklash orqali akkauntni egallash.** SMTP sozlanmagan bo'lsa (standart holat),
  tiklash kodi so'ragan odamning ekraniga chiqadi (`users/views.py:450-452`). SMTP bo'lsa ham kodga
  urinishlar soni cheklanmagan (`:460-471`). `BREVO_API_KEY` umuman o'qilmaydi.
  → Django'ning `PasswordResetView` ga o'ting yoki kodni kesh+TTL+5 urinish bilan saqlang.

**High**
- **C1** — Tasdiqlanmagan sotuvchi Telegram bot orqali do'kon tushumi, qarzlar, PDF/Excel'ni oladi
  (`telegram_bot.py:216-231`, `hisobot_service.py:38-40`). Do'kon egasining loginini bilish kifoya.
- **C2** — Rad etilgan/ishdan bo'shatilgan sotuvchining eski sessiyasi 2 hafta ishlayveradi
  (`kassa/views.py:73-84`, `mahsulot/views.py:53-64`). API qismi to'g'ri (`api/utils.py:19`) —
  shu helper'ni hamma joyda ishlating.
- **C4** — `settings.py` xavfli standartlar: `SECRET_KEY` kodda, `DEBUG=True`, `ALLOWED_HOSTS=['*']`.
  Xato sahifasida `SMTP_PAROL` ochiq ko'rinadi.
- **H1** — XSS: `innerHTML` bilan himoyasiz chiqarish — marketplace (`mijoz/dashboard.html`),
  umumiy barkod katalogi (`mahsulot/qoshish.html` — bitta do'kon hammaga zahar qo'yadi), chat.
- **H2** — Istalgan fayl yuklash: `evil.html` yuklanadi va saytdan `text/html` sifatida beriladi.
- **H4** — Brute-force himoyasi yo'q (API login, bot, admin), `X-Forwarded-For` soxtalashtiriladi,
  `CACHES` yo'q.
- **H5** — Django 4.2 xavfsizlik qo'llab-quvvatlashi 2026-aprelda tugagan → Django 5.2 LTS.
- **H6** — Har qanday foydalanuvchi to'lanmagan buyurtma bilan omborni "band" qilib qo'yadi.

**Medium:** H3 (kassir pulni qaytarishi, qarzni yopishi, egasining Telegram hisobotini o'chirishi
mumkin — audit log qisman), H7 (soxta karta UI), M1 (poyga holatlari), M2, M4, M6, M7 (service
worker logout'da keshni tozalamaydi), M8, M11. **Low:** M3 (UTC sana) va boshqalar.

---

## 2. Raqobatchilar va ular sizdan qayerda ustun

| Mahsulot | Boshlang'ich narx (oy) | Fiskal | Markirovka | Kuchli tomoni |
|---|---|---|---|---|
| **Billz** | 299k (~$25), 499k, 999k [T] | aniq emas | aniq emas | 7000+ do'kon, TBC Bank ~$12M ga 60% sotib oldi, kredit beradi, shaxsiy menejer |
| **Regos** | 69k–859k + POS litsenziya 1.2M [T] | o'z virtual kassasi | ha | 10+ yil, ulgurji, self-checkout |
| **MoySklad** | **Bepul** (2 kassa) → 196k [T] | E-POS orqali | ha | Bepul tarif, Didox, Uzum Market |
| **Bito ERP** | ochiq emas | ? | ha | Nasiya, ulgurji, $10M baho (MOST Ventures) [T] |
| **VelionPOS** (yangi) | 199k + 499k o'rnatish [T] | Rahmat orqali | ? | **Sizning eng yaqin nusxangiz**: nasiya + fiskal |
| **Rahmat (Multikassa)** | 100–124k | o'zi fiskal | ha | Sherik bo'lishi mumkin, raqib emas |
| Payme/Click/Paynet | komissiya | ha | yo'q | To'lov — ombor/qarz yo'q |
| Smartup | ochiq emas | | ha | Katta distributorlar (50+ xodim) |

**Ular sizdan ustun:** fiskal chek, markirovka, to'lov integratsiyasi, offline kassa, USB skaner +
printer, mobil ilova, ko'p filial, savdo jamoasi, dilerlar, brend, investitsiya.
**Siz ulardan ustun bo'lishingiz mumkin:** o'zbekcha birinchi, qarz daftar + SMS/Telegram eslatma,
Telegram'da egasiga hisobot, kichik do'kon uchun arzon narx, viloyatlarda yaqinlik, ulgurji→do'kon
buyurtma zanjiri (Billz ulgurjini qilmaydi, Smartup kichiklarni qilmaydi).

---

## 3. Qaysi bozor

**Raqamlar [T]:** 88–101 ming chakana yuridik shaxs; 375 ming YaTT (85% Toshkent shahridan
tashqarida; 2024 da ~49% chakana savdoda). Chakana aylanma 2025: 482 trln so'm (+11%).
Bulutli POS qamrovi ~5–15% [B] — bozor hali bo'sh.

**Majburiy talablar sotuvni tezlashtiradi [T]:** UzQR (01.07.2026 dan yuridik shaxslar), YaTT
uchun maxsus QR (01.01.2026), markirovka kodini sotuvdan oldin tekshirish (01.03.2026),
naqd pul taqiqlari (UP-246, 01.04.2026). Do'kon egalari chalkash → "talablarga mos + boshqaruv" sotiladi.

**Tavsiya — birinchi bozor:**
1. **Toshkent viloyati (Piskent, Bekobod, Ohangaron, Olmaliq, Chirchiq) dagi mahalla oziq-ovqat
   do'konlari** — qarz daftar asosiy og'riq, Billz ular uchun qimmat va moda yo'nalishida.
2. Ikkinchi navbat: **qurilish mollari / avto ehtiyot qismlar** (ko'p SKU, qarz, metr/kg, ulgurji+chakana).
3. Keyin: **kichik ulgurjichilar va ularning do'konlari** (B2B buyurtma + qarz limiti).
4. **Qozog'iston/Qirg'iziston — hozir emas** (Kaspi Kassa bepul, lid $8–12, til, boshqa fiskal qoidalar).
5. **Bozor Nazorat** — davlatga emas, **Piskent dehqon bozori MChJ** ga (E-bozor majburiyati
   o'zlarining puli hisobidan). Avval direktor bilan gaplashing: vendor tanlab bo'lganmi?
   Kamera natijalarini ko'rsatishdan oldin 2 hafta qo'lda sanash bilan solishtiring.

**Narx [B]:** 99–149k so'm/oy (fiskal kassa alohida, do'kon Rahmat'ga ~100k to'laydi).
Bepul 14 kun sinov, yillik to'lovga 20% chegirma.

---

## 4. MVP: nima kerak, nima kerak EMAS

### KERAK (to'lov olishdan oldin)
1. Xavfsizlik: C1–C4, H1, H2, H4, H5 tuzatilgan; git + private remote.
2. Fiskalizatsiya — **sherik orqali** (Rahmat/E-POS/UzKassa API). O'zingiz virtual kassa
   reyestriga kirishga hozir urinmang (Kiberxavfsizlik markazi xulosasi, texnik xizmat markazi,
   MChJ — oylar).
3. IKPU/MXIK kod har bir mahsulotda (tasnif.soliq.uz).
4. USB/HID barkod skaner (skan → Enter → savatga), AJAX savat (sahifa qayta yuklanmasin).
5. 58/80 mm chek shabloni (STIR, manzil, "Fiskal chek emas" — fiskalizatsiya ulanguncha).
6. Qarz daftar: qisman to'lov, mijoz bo'yicha balans, SMS/Telegram eslatma.
7. Rollar: kassir vs egasi (qaytarish, qarzni yopish, hisobot, sozlamalar — faqat egasi yoki PIN).
8. Telegram avto-hisobot — alohida servis (systemd/Celery beat), `runserver` ichida emas.
9. Production: PostgreSQL + gunicorn + nginx + HTTPS, Sentry, kunlik `pg_dump` boshqa joyga.
10. Oddiy billing (boshida qo'lda: Payme/Click havola + admin'da "to'langan gacha" sana).
11. Ommaviy oferta + maxfiylik siyosati + rozilik belgisi.
12. Rus tili (Toshkent viloyatida ko'p egalar ruscha ishlaydi) — kamida asosiy ekranlar.

### KERAK EMAS (MVP'dan olib tashlang yoki o'chirib qo'ying)
- Flutter ilova (PWA yetadi; mobil dasturchi yollamang).
- Mijoz marketplace / Click&Collect / sodiqlik ballari (12.12.2026 dan e-tijorat qonuni
  "agregator" majburiyatlari qo'shiladi; suiiste'mol H6; XSS H1).
- Zavod → yetkazuvchi → do'kon zanjiri, GPS xarita, chat, reyting, sharhlar.
- AI chat (qimmat, limitsiz) — oddiy "haftalik xulosa" bilan almashtiring yoki o'chiring.
- Soliq kalkulyatori (noto'g'ri hisoblasa — javobgarlik).
- Pasport/JSHSHR maydonlari.
- Kamera/AI (Bozor Nazorat) — alohida mahsulot, alohida vaqtda.

---

## 5. O'zim eplay olamanmi? Jamoa

**Kod tomoni — ha, o'zingiz eplaysiz.** Siz 4 haftada 189 commit qildingiz, 468 test yozdingiz.
Muammo kodda emas — **sotuv, o'rnatish va qo'llab-quvvatlashda**. Do'kon egasi telefonda gaplashib,
yonida o'tirib o'rgatilishini kutadi (MoySklad: "email ishlamaydi, qo'ng'iroq ishlaydi" [T]).

**Tavsiya:**
- **Hozir dasturchi yollamang.** Middle Django 8–15 mln so'm/oy [T] — pul yo'q paytda eng katta xarajat.
- **Birinchi odam — savdo agenti/hamkor** (komissiya: birinchi to'lov yoki birinchi yilning
  10–30% [B]; agent maoshi $500–800 [T]). Yaxshisi — ulush bilan savdo bo'yicha **ko-founder**.
- 20–30 to'layotgan do'kondan keyin: qo'llab-quvvatlash operatori (2.5–7 mln so'm [T]).
- 100+ do'kondan keyin: 2-dasturchi (junior/middle).
- Buxgalter — MChJ ochilgan kundan (autsors 1–3 mln so'm/oy [B]).
- Dizayner — loyiha asosida $200–800 [B].

---

## 6. Xarajatlar (MVP va birinchi 6 oy)

### Bir martalik
| Narsa | Narx |
|---|---|
| MChJ ro'yxatdan o'tkazish (onlayn) | ~396–440 ming so'm [B: 2024 qo'llanma + BHM] |
| Yurist (ustav, oferta, maxfiylik) | 1.5–7.5 mln so'm [T] |
| Dastur guvohnomasi (Adliya, my.gov.uz) | 220 ming so'm (0.5 BHM) [T] |
| Tovar belgisi "Savdoyim" (1 sinf, yuridik shaxs) | ~2.64 mln + ~$430 ro'yxat [qisman T] |
| .uz domen | 27 ming so'm/yil [T] |
| E-IMZO kaliti, bank hisob raqami | kichik summa [B] |
| Test uchun USB skaner + 58mm printer | ~0.5–1.5 mln so'm [B] |
| **Jami** | **≈ 6–13 mln so'm (~$500–1100)** |

### Oylik
| Narsa | Narx |
|---|---|
| Server O'zbekistonda: UzCloud 2vCPU/4GB/50GB | ~368 ming so'm [T] (yoki Ahost 320k [T]) |
| Zaxira saqlash (boshqa joyda) | ~50–100 ming [B] |
| SMS (Eskiz, 95 so'm, faqat yuridik shaxs) | 1000 SMS ≈ 95 ming [T] |
| AI API | ~$10–30 [B] |
| Buxgalter (autsors) | 1–3 mln [B] |
| Reklama (Telegram/Instagram, lid ~$2 [T]) | 1–3 mln [B] |
| **Jami (o'zingiz ishlasangiz)** | **≈ 3–7 mln so'm (~$250–600)/oy** |
| + savdo agenti | +$500–800 yoki komissiya |

Fiskal modul (1 BHM = 440k/yil) va virtual kassa (Rahmat ~100–124k/oy) — **do'konning** xarajati.

### Soliq [T]
- YaTT: aylanmadan 1% (1 mlrd gacha). MChJ: 4%. QQS chegarasi ~5.28 mlrd so'mga ko'tarildi.
- IT Park (faqat MChJ): 2028 gacha soliqlardan ozod, xodimlarga 7.5% JShDS, badal ~1% tushumdan.
- **Tavsiya: MChJ** (IT Park, Eskiz SMS, Payme, keyinchalik reyestr — hammasi yuridik shaxs talab qiladi).

### Daromad hisobi [B]
120k × 50 do'kon = 6 mln/oy → xarajatni qoplaydi. 120k × 200 = 24 mln/oy → 1 dasturchi + 1 agent.

---

## 7. Kerakli hujjatlar ro'yxati
1. MChJ: ustav, ta'sischi qarori, STIR, bank hisob raqami, direktor E-IMZO kaliti.
2. IT Park rezidentligi arizasi (my.it-park.uz) — ixtiyoriy, 15 ish kuni.
3. Ommaviy oferta (obuna shartlari, to'lov, SLA, javobgarlik chegarasi, ma'lumotlar egasi do'kon).
4. Maxfiylik siyosati + shaxsiy ma'lumotlarga rozilik (checkbox).
5. Fiskal sherik bilan hamkorlik/integratsiya shartnomasi (Rahmat / E-POS / UzKassa).
6. Payme/Click merchant shartnomasi (Didox orqali elektron, ERI bilan).
7. Xizmatingiz uchun IKPU kodi + e-faktura (Didox/Faktura.uz) — do'konlarga hisob-faktura.
8. EHM dasturi guvohnomasi (Adliya) va tovar belgisi arizasi (IMA, 9/35/42-sinflar).
9. Eskiz SMS shartnomasi + jo'natuvchi nomini tasdiqlash (1–2 oy oldin boshlang!).
10. Ichki: pilot do'kon bilan kelishuv (bepul davr, fikr-mulohaza, keyingi narx).

---

## 8. Hozir nima qilish kerak — 10 haftalik reja

**Bu hafta (1–3 kun):**
1. `savdoyimbozor` GitHub repo → **Private**.
2. `savdoyim26.08` ni git'ga oling, private GitHub'ga yuklang.
3. **Qaror qiling:** asosiy mahsulot = do'kon egasi POS'i. Bozor Nazorat — muzlatiladi
   (faqat Piskent bozori direktori bilan bitta suhbat).
4. **Qaror qiling:** qaysi kod bazasi asos bo'ladi. Mening tavsiyam: `savdoyimbozor` ning
   texnik poydevori (Django 5.2, Docker, PostgreSQL, offline navbat, throttling, 2FA, testlar)
   ustiga Savdoyim'ning egasi funksiyalarini (Telegram hisobot, prognoz, qarz) ko'chirish —
   yoki aksincha Savdoyim'ni o'sha darajaga yetkazish. 1 kun solishtirib, bittasini tanlang.
5. Bitta brend nomi.

**1–2-hafta:** xavfsizlik (C1–C4, H1, H2, H4, H5), MVP'ga kerak bo'lmagan modullarni o'chirish.
**3–5-hafta:** fiskal sherik API, IKPU, USB skaner + AJAX savat, 58/80mm chek, qisman qarz,
rollar, rus tili.
**Parallel (huquqiy):** MChJ, bank, E-IMZO, Eskiz (sender nomi 1–2 oy!), yurist bilan oferta.
**6-hafta:** deploy (UzCloud/Ahost), Sentry, zaxira, tiklashni sinash.
**7–10-hafta:** 5–10 ta do'konda **bepul pilot**, har kuni borib ko'rish, 10-haftadan pullik.
**Maqsad (3 oy):** 20–30 to'layotgan do'kon. Shundan keyin investor bilan gaplashing.

**Qilmang:** yangi funksiya qo'shish (to'layotgan mijozsiz), Flutter, uchinchi versiya boshlash,
"davlat buyurtmasini kutish".

---

## 9. Claude Code sozlamalari (doctor)
- O'rnatish: Claude Desktop orqali, takroriy o'rnatmalar yo'q — sog'lom.
- Sozlama fayllari (`~/.claude/settings.json`, `~/.claude.json`) to'g'ri o'qiladi.
- Ishlatilmagan skill/plugin/MCP: foydalanuvchi o'rnatgani yo'q — tozalashga narsa yo'q.
- CLAUDE.md: bu loyihada yo'q; kontekst xotira orqali `LOYIHA_AI.md` ga ishora qiladi — yaxshi.
- **Ogohlantirish:** Pixel Agents hook'i (12 ta hodisa, sinxron `node`, 5s timeout) —
  PreToolUse'da 23 marta ~6s timeout. Ishlatmasangiz olib tashlashni so'rang.
- Versiya: This session runs Claude Code 2.1.299, and updates arrive with Claude Desktop.
  On an SSH host, an update reaches new sessions there, not this one. If the session uses a copy
  of Claude Code that was already on the SSH host or in the WSL distribution, update that copy,
  then start a new session there.
- Taklif: standart ruxsat rejimini "auto" qilish (`~/.claude/settings.json`).
