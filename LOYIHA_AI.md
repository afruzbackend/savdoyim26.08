# Savdoyim — Loyiha hujjati (AI uchun to'liq kontekst)

> Bu fayl AI yordamchilarga (Claude Code, ChatGPT va h.k.) loyihani tez va to'liq
> tushunish uchun yozilgan. Kod o'zbek tilida — model/maydon/funksiya nomlari ham
> o'zbekcha. Shu atamalarni saqlab qoling; ingliz tiliga tarjima qilib yozmang.
>
> ⚠️ **`README.md` eskirgan — unga tayanmang.** Ishonchli manba: shu fayl va kodning o'zi.

---

## 1. Loyiha nima?

**Savdoyim** — Django asosidagi **do'kon boshqaruv (POS + biznes) tizimi**. Bir
platformada 5 xil rol ishlaydi: do'kon egasi, sotuvchi, zavod (ishlab chiqaruvchi),
yetkazib beruvchi va mijoz. Asosiy qism — **kassa (POS)**: sotuv, qaytarish,
smena/verka, qarz daftar, hisobot (PDF/Excel), AI tahlil, ombor bashorati,
Telegram avto-hisobot. Ustiga onlayn **mijoz buyurtmasi** (Click & Collect),
**B2B zanjir** (do'kon → zavod → yetkazuvchi → jo'natma) va sodiqlik ballari qo'shilgan.

Til: interfeys **o'zbekcha**. Vaqt zonasi: **Asia/Tashkent**. Pul birligi: **so'm (UZS)**.

---

## 2. Texnologiyalar

| Qatlam | Texnologiya |
|--------|-------------|
| Backend | Django 5.2 LTS (Python 3.12) |
| API | Django REST Framework (TokenAuth + SessionAuth) |
| DB | SQLite (default) yoki PostgreSQL (`DB_ENGINE=postgres`) |
| Frontend | Django templates + vanilla JS (SPA emas), PWA (offline, `sw.js`) |
| Statik | WhiteNoise (siqilgan, DEBUG=False da ham ishlaydi) |
| Rasm | Pillow (yuklashda avtomatik kichraytirish/siqish) |
| Hujjat | reportlab (PDF), openpyxl (Excel), qrcode (chek QR) |
| Telegram | pyTelegramBotAPI (bot) + to'g'ridan-to'g'ri HTTP API (xabar) |
| AI | `openai` SDK orqali OpenAI-mos endpoint (Novita / TokenRouter / Moonshot Kimi) |
| Email | SMTP (Brevo tavsiya) yoki Brevo API; parolsiz → konsolga chiqadi |

Ishga tushirish: `pip install -r requirements.txt` → `migrate` → `runserver`.
`RUN_BOT_WITH_SERVER=True` bo'lsa server bilan Telegram bot ham fon oqimida ishga tushadi.

---

## 3. Loyiha tuzilishi (Django app'lar)

Root: `savdoyim26.08/` (settings.py, urls.py, manage.py shu yerda; `ROOT_URLCONF='urls'`).

| App | Vazifasi |
|-----|----------|
| `users` | CustomUser (rollar), profillar, reyting, bildirishnoma, audit log, auth, PWA, Telegram link |
| `mahsulot` | Mahsulot, kategoriya, barkod katalog, sharh/baho, inventarizatsiya, narx tarixi, skanner log |
| `kassa` | POS sotuv, chek, qaytarish (refund), smena/verka, qarz daftar, hisobot (PDF/Excel), avto-hisobot |
| `buyurtma` | B2B buyurtma (do'kon→zavod) **va** mijoz buyurtmasi (savat, Click & Collect), sodiqlik ballari |
| `yetkazib_beruvchi` | Jo'natma (zavod→do'kon), yetkazuvchi so'rovi, GPS xarita, QR qabul |
| `soliq` | Soliq sozlamasi (QQS/patent/soddalashtirilgan) va hisoblash |
| `dokon` | Do'kon sozlamasi (ish vaqti, dam olish kuni) |
| `chat` | Rollar aro chat (xona + xabar) |
| `ai` | Hisobot AI tahlili va cheklangan chat (faqat hisobot bo'yicha) |
| `api` | Mobil/tashqi REST API (serializer, token) |

### Arxitektura qatlamlari
- **View** ingichka: kirish tekshiruvi + biznes servisga chaqiruv.
- **Service** (`*/services.py`) — biznes logika (masalan `OrderService`, `SodiqlikService`,
  `hisobot_service`, `anomaliya_service`). Qayta ishlatiladigan va testlanadigan.
- **Model** (`*/models.py`) — ma'lumot + hisoblanadigan `@property`'lar.
- Umumiy JSON javob konvensiyasi: `users/services.py` → `json_ok()`, `json_err()`,
  `ServiceError(message, code, errors)`.

---

## 4. Rollar va ruxsatlar

`CustomUser.rol` ∈ `{dokon_egasi, sotuvchi, zavod, mijoz, yetkazib_beruvchi}`.
Har rolga bitta profil (OneToOne):
- `DokonEgasiProfil` — do'kon nomi, soliq raqami, manzil, GPS, logo.
- `SotuvchiProfil` — `dokon` + `sorov_holati` (kutilmoqda/tasdiqlangan/rad_etilgan).
  **Sotuvchi tasdiqlanmaguncha do'konga bog'lanmaydi va kassada ishlay olmaydi.**
- `ZavodProfil`, `YetkazibBeruvchiProfil` (mashina turi/raqami), `MijozProfil` (sodiqlik ball, daraja).

Do'konni aniqlash helper'lari (ko'p joyda takrorlangan): `kassa.views._get_dokon`,
`buyurtma.services.sotuvchi_dokoni`, `hisobot_service.dokon_aniqla`. Barchasi:
do'kon egasi → o'z do'koni; **tasdiqlangan** sotuvchi → biriktirilgan do'kon.

---

## 5. Ma'lumot modellari (asosiylari)

### mahsulot
- **`Mahsulot`**: `nomi, kategoriya, dokon, zavod, barkod, narx, sotib_olish_narxi,
  soni (DecimalField 3 kasr — kg/litr uchun), minimum_son, birlik, yaroqlilik_muddati,
  rasm, faol`.
  - `@property kasrli` — birlik ∈ (kg, litr, gramm, metr) bo'lsa kasrli sotiladi.
  - `@property muddati_otgan` / `muddati_tugayapti` (7 kun) — yaroqlilik nazorati.
  - `@property foyda`, `foyda_foizi`, `kam_qoldi`, `ortacha_reyting`.
  - Constraint: `uniq_dokon_barkod` — barkod **har do'kon ichida** unikal (global emas).
- `BarkodKatalog` — markaziy barkod bazasi (do'konlar birgalikda to'ldiradi, `yangila()` upsert).
- `Inventarizatsiya` + `InventarizatsiyaItem` — ombor sanog'i: `tizim_soni` snapshot,
  egasi `real_soni` kiritadi, `farq` = real − tizim; yakunlanganda ombor real songa tuzatiladi.
- `MahsulotSharh` (+`SharhRasm`) — faqat mahsulotni **olib ketgan** mijoz yozadi; 1 user→1 mahsulot 1 faol sharh.
- `NarxTarix`, `SkannerLog`.

### kassa (POS — eng muhim modul)
- **`SavdoChek`**: `dokon, sotuvchi, jami (chegirmadan keyingi summa), chegirma,
  to_langan, qaytim, tolash_turi (naqd/karta/qarz), token (UUID — ochiq chek sahifasi)`.
  - `@property qaytarilgan_summa`, `qaytarish_holati` (yoq/qisman/toliq).
- **`SavdoChekMahsulot`**: chek qatori (`mahsulot_nomi, soni, narx, jami`).
  `qolgan_qaytarish` = sotilgan − qaytarilgan.
- **`Smena`**: sotuvchi smenasi. **Ochiq smena bo'lmasa kassada sotib bo'lmaydi.**
  Constraint `bitta_dokonda_faqat_bitta_ochiq_smena`. Pul verkasi (Z-hisobot):
  `boshlangich_naqd, real_naqd (kassir sanagan), kutilgan_naqd (tizim), naqd_farq`.
  `verka_holati` ∈ mos/kamomad/ortiqcha.
- **`Qaytarish`** (+`QaytarishItem`): refund audit yozuvi. **Asl chek o'zgarmaydi.**
  Tovar omborga qaytadi, pul kassadan (`kassadan=True`) yoki to'lanmagan qarzdan kamayadi.
- **`QarzDaftar`**: nasiya (`mijoz_ism/telefon, summa, to_langan, qaytarish_sana`).
- `Kassa` (do'kon balansi), `AvtoHisobotSozlama` (Telegram avto-hisobot vaqtlari).

### buyurtma
- **`Buyurtma`** (+`BuyurtmaMahsulot`) — B2B: do'kon → zavod. Holat oqimi:
  yangi→qabul_qilindi→tayyorlanmoqda→yolda→yetkazildi (yoki bekor).
- **`MijozBuyurtma`** (+`MijozBuyurtmaItem`) — mijoz onlayn buyurtmasi (Click & Collect).
  Holat oqimi (faqat oldinga): `yangi→tayyorlanmoqda→tayyor→olib_ketildi` (+bekor).
  SoftDelete. `tayyorlanish_daqiqa`, `taxminiy_tayyor_vaqt`, `oqim_bosqichlari` (stepper).
- `Savat`+`SavatItem` (mijoz savati, 1 mijoz = 1 savat), `BuyurtmaStatusTarix`, `SodiqlikTarix`.

### yetkazib_beruvchi
- **`Jonatma`** (+`JonatmaMahsulot`): zavod → do'kon jo'natmasi. `barkod` (avto UUID12),
  holat oqimi, `manzil_dokon`/GPS, `dokon_qabul` (do'kon QR bilan qabul qilib omborga qo'shdimi).
- `YetkazuvchiSorov`: yetkazuvchi → zavod ishlash so'rovi.

### users
- `CustomUser` (rol, telefon, jshshr, passport, GPS, rasm, sayt_bildirishnoma).
- `Reyting` (5 yulduz, baholovchi→baholanuvchi, unique together).
- `Bildirishnoma` (soft-delete, `yubor()` helper), `AuditLog`, `TelegramLink`.

### soliq / dokon / chat
- `SoliqSozlama` (stavka, tur), `DokonSozlama` (ish vaqti), `ChatXona`+`ChatXabar`.

---

## 6. Asosiy biznes oqimlari

### 6.1 Kassa sotuvi (`kassa.views.savdo_qilish`)
1. Ochiq smena bo'lishi shart, aks holda xato.
2. Savat yoki JSON'dan mahsulotlar; har biri uchun: son > 0, muddati o'tmagan, ombor yetarli.
3. `jami_chegirmali = max(0, jami − chegirma)`. **Diqqat:** chegirma faqat `qarz` uchun
   qoldiriladi, naqd/karta uchun 0 ga tushiriladi.
4. Naqd uchun `qaytim = max(0, berilgan − jami)`; "berilgan" ixtiyoriy.
5. **Atomik tranzaksiya**: chek yaratiladi → har mahsulot uchun ombor **faqat yetsa**
   kamayadi (`filter(soni__gte=soni).update(soni=F('soni')-soni)`); yetmasa
   `_OmborYetarliEmas` → 409. Naqd/karta bo'lsa kassa balansi oshadi; qarz bo'lsa
   `QarzDaftar` yoziladi (kassa oshmaydi).
6. Chek QR-kodli ochiq sahifa: `chek_korish(token)` (login talab qilmaydi).

### 6.2 Qaytarish / refund (`qaytarish_qil`)
- Chek raqami (#123) yoki token bo'yicha topiladi. Har qator uchun `qty_<id>`.
- `soni <= qolgan_qaytarish` bo'lishi shart. Atomik: `Qaytarish`+`QaytarishItem`,
  tovar omborga `F('soni')+soni`, pul: to'lanmagan qarz cheki bo'lsa qarzdan, aks holda kassadan.

### 6.3 Smena / Z-hisobot verka (`smena_ochish`, `smena_yopish`)
- Ochishda ixtiyoriy `boshlangich_naqd`. Yopishda `_yig()` bilan smena hisoboti.
- Verka: `kutilgan = boshlangich + naqd_sotuv − naqd_qaytarish`;
  `naqd_farq = real − kutilgan` (manfiy=kamomad, musbat=ortiqcha).
- Natija do'kon egasiga Telegram'ga yuboriladi + sotuvchiga `smena_natija.html`.

### 6.4 Hisobot va bashorat (`kassa.hisobot_service`)
- `_yig()` — davr statistikasi: sof savdo (qaytarish ayrilgan), to'lov turlari, top mahsulot.
- `_hisobot_grafik()` — soat/kun/oy grafiklari (bitta GROUP BY so'rov, N+1 emas).
- `ombor_prognoz()` / `_bashorat_yadro()` — **recency-weighted talab modeli**
  (yarim-umr 14 kun): har mahsulot taxminan qachon tugashini + trend (osish/pasayish).
- `olik_tovarlar()` — 30 kunda sotilmagan, pul bog'lab turgan tovarlar.
- PDF (`hisobot_pdf`, reportlab+Arial) va Excel (`hisobot_excel`, openpyxl) eksport.

### 6.5 Mijoz buyurtmasi (`buyurtma.services.OrderService`)
- `savatga_qoshish` → `SavatItem` (soni ombor bilan cheklanadi).
- `buyurtma_checkout` → `create_from_cart`: savatni **do'kon bo'yicha guruhlab**,
  har do'konga alohida `MijozBuyurtma` yaratadi; keyin savatni tozalaydi.
- `advance_status` — status faqat ketma-ket oldinga; `olib_ketildi` da sodiqlik bali.
- Sodiqlik: 1 ball = 1000 so'm xarid; ishlatishda 1 ball = 100 so'm chegirma
  (`BALL_TOPISH_NARXI=1000`, `BALL_QIYMATI=100`). Daraja: Bronza/Kumush(500)/Oltin(2000).

### 6.6 B2B zanjir
Do'kon egasi zavodga `Buyurtma` beradi → zavod `Jonatma` yaratadi → `YetkazibBeruvchi`
yetkazadi → do'kon QR bilan qabul qiladi (`dokon_qabul=True`) va **omborga qo'shiladi**
(`yetkazib_beruvchi/views.py` da `F('soni')+soni`).

### 6.7 AI yordamchisi (`ai.services`)
- `biznes_holati()` — foyda, tan narx, marja, to'lov, ombor, qarz — bitta dict.
- `hisobot_tahlil()` — "nega shunday + nima qilish"; `savol_javob()` — **cheklangan chat**
  (faqat hisobot mavzusida; boshqa savolga muloyim rad — `CHEKLOV` system prompt).
- Model `.env` orqali (`AI_BASE_URL`, `AI_MODEL`, `AI_API=chat|responses`).

---

## 7. URL xaritasi (root `urls.py`)

| Prefiks | App | Izoh |
|---------|-----|------|
| `/` | users | home_redirect (rolga qarab yo'naltiradi) |
| `/sw.js`, `/manifest.webmanifest` | users | PWA |
| `/admin/` | Django admin | |
| `/user/` | users | auth, dashboard, profil, sotuvchi boshqarish |
| `/product/` | mahsulot | mahsulot, skanner, inventarizatsiya, sharh |
| `/checkout/` | kassa | **kassa, qarzlar, hisobot, qaytarish, smena, KPI** |
| `/order/` | buyurtma | savat, checkout, mijoz/B2B buyurtma |
| `/tax/` | soliq | soliq hisoblash |
| `/delivery_person/`, `/zavod/` | yetkazib_beruvchi | jo'natma, xarita, so'rov |
| `/chat/` | chat | |
| `/api/` | api | REST |
| `/media/...` | — | yuklangan rasmlar (production'da ham) |

---

## 8. Sozlama / muhit (`.env`)

Muhim env o'zgaruvchilar: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`,
`DB_ENGINE` (+ `DB_*`), `TELEGRAM_BOT_TOKEN`, `RUN_BOT_WITH_SERVER`,
`TOKENROUTER_API_KEY` / `AI_BASE_URL` / `AI_MODEL` / `AI_API`,
SMTP (`SMTP_HOST/LOGIN/PAROL/FROM`) yoki `BREVO_API_KEY`.
Production'da (`DEBUG=False`): secure cookie, SSL redirect, HSTS (ixtiyoriy),
CORS cheklanadi. Lokal/telefon test uchun `CSRF_TRUSTED_ORIGINS` ga LAN IP avtomatik qo'shiladi.

---

## 9. Kod konvensiyalari (AI shularга rioya qilsin)

- **Til:** hamma nom, izoh, foydalanuvchi matni **o'zbekcha**. Yangi kod ham shunday.
- **Pul:** `DecimalField` bilan ishlang, `float` bilan hisob-kitob qilmang (grafik/AI'dan tashqari).
- **Ombor o'zgarishi:** doim atomik va poyga-himoyali — `transaction.atomic()` +
  `filter(soni__gte=...).update(soni=F('soni')±...)`. Python'da o'qib-yozib (`obj.soni -= x`) **qilmang**.
- **Miqdor tozalash:** `kassa.views._miqdor(value, birlik)` — dona→butun, kg/litr→3 kasr, manfiy→0.
- **JSON javob:** `json_ok/json_err/ServiceError` konvensiyasidan foydalaning.
- **Soft-delete:** `Bildirishnoma`, `MahsulotSharh`, `MijozBuyurtma` — `is_deleted`; o'chirmang, belgilang.
- **Telegram/email/audit** hech qachon asosiy oqimni buzmasin (`try/except: pass`).
- **Do'kon izolyatsiyasi:** har so'rovda `dokon=...` filtri majburiy (begona do'kon ma'lumotiga tegmaslik).

---

## 10. Ma'lum muammolar / ehtiyot bo'lish kerak bo'lgan joylar

> Bu bo'lim AI kelgusi o'zgarishlarda xatoni takrorlamasligi uchun.

1. **✅ TUZATILDI — Mijoz buyurtmasida ombor rezervlanadi.**
   `OrderService.create` endi omborni **atomik kamaytiradi** (rezerv):
   `filter(soni__gte=soni).update(soni=F('soni')-soni)`; yetmasa 409. `OrderService.cancel`
   qo'shildi — buyurtma bekor qilinsa rezerv omborga qaytadi (`F('soni')+soni`).
   `mijoz_buyurtma_holat` view'ida `holat='bekor'` → `cancel`. Sotuvchi sahifasida
   "Bekor qilish" tugmasi bor. Oversell endi bo'lmaydi.
2. **✅ TUZATILDI — Reorder / savat yangilash ombor bilan cheklanadi.**
   `qayta_buyurtma` va `savat_yangilash` savatdagi sonni `min(soni, mahsulot.soni)` bilan cheklaydi.
3. **✅ TUZATILDI — Onlayn buyurtma endi savdo/kassaga tushadi.**
   `advance_status` → `olib_ketildi` da `kassa.savdo_service.chek_buyurtmadan()` chaqiriladi:
   `SavdoChek` + `SavdoChekMahsulot` yaratiladi, kassa balansi oshadi (naqd, default).
   Ombor QAYTA kamaymaydi (rezerv `create` da kamaytirgan). Shu bilan onlayn savdo
   hisobotга tushadi va ombor↔daromad nomuvofiqligi yo'qoladi. Test: `OlibKetishChekTest`.
4. **✅ TUZATILDI — Verka naqd qarz to'lovини hisobga oladi.** `smena_yop` da smена
   davomida to'langan qarzlar (naqd deб) `kutilgan_naqd` ga qo'shiladi — soxta "ortiqcha" yo'q.
5. **✅ TUZATILDI — Qaytarish API takroriy `cm_id` xavfsiz** (`qaytarish_yarat` sonlarни
   cm_id bo'yicha yig'ib tekshiradi — over-refund yo'q). Savat 0 qolса o'chiriladi.

**🟡 Ochiq (kichik):** chegirma UI web'да yo'q (backend naqd/kartaга chegirmani 0 qiladi) —
runtime bug emas, UI qo'shилганда hal bo'ladi. Buyurtma olib ketilishida to'lov turi
har doim `naqd` (kelajakда tanlov qo'shish mumkin).

**🔒 Xavfsizlik qoidalari (audit 2026-10-16, buzmang):**
- Do'konni aniqlash — FAQAT `users.services.foydalanuvchi_dokoni` (boshqa `_get_dokon`/
  `dokon_aniqla`/`sotuvchi_dokoni` shunga yo'naltirilgan). Kutilayotgan/rad etilgan sotuvchi → None.
- Hisobot, eksport, AI, avto-hisobot, KPI, ombordan chiqarish — faqat do'kon egasi (`_egasi_dokoni`).
- Sotuvchi rad etilsa / parol o'zgarsa → `foydalanuvchi_kirishlarini_bekor_qil` (sessiya, token, Telegram).
- Parol tiklash kodi keshda hash bilan, 10 daqiqa, 5 urinish; kod faqat `DEBUG=True` da ekranda.
- `settings.py` fail-closed: `DEBUG` standart False; prod'da `DJANGO_SECRET_KEY` va
  `DJANGO_ALLOWED_HOSTS` bo'lmasa server ishga tushmaydi. Lokal: `ISHGA_TUSHIRISH.bat` DEBUG=True qo'yadi.
- JS'da server/foydalanuvchi matnini `innerHTML` ga faqat `escHtml()` orqali qo'ying (base.html).
- Media: faqat rasm kengaytmalari ochiq; rasm bo'lmagan yuklama saqlanmaydi; zavod hujjatlari faqat staff.
- Pasport/JSHSHR endi so'ralmaydi. Testlar: `users/tests_xavfsizlik.py`.

**🧾 MVP funksiyalari (2026-10-16):**
- `Mahsulot.ikpu` (17 raqam, `mahsulot.views._ikpu_tozala`) → sotuvda `SavdoChekMahsulot.ikpu` ga nusxalanadi; import ustuni `ikpu`.
- Qarz: `QarzDaftar.summa` = QOLGAN qarz, `tolangan_summa` = to'langan, `jami_qarz` = ikkalasi.
  Har to'lov `QarzTolov` (naqd/karta). `savdo_service.qarz_tolash_yadro(dokon, id, summa=None, tolov_turi)`
  qisman/to'liq. Verka faqat `QarzTolov(tolov_turi='naqd')` ni qo'shadi.
- Kassa savati AJAX: `savat_action` `X-Requested-With` bo'lsa `_cart_json` qaytaradi; `kassa_skan` ham `cart` beradi.
  USB/BT skaner — `kassa.html` dagi keydown tinglovchi (tez belgilar + Enter = barkod).
- Chek: `chek.html` `.termal` bloki 58/80 mm (@page, localStorage `chek_en`), `?print=1` avtomatik chop.

Yaxshi tomonlari (buzmang): kassa sotuvi, refund, smena va qarz to'lash oqimlari
**atomik va poyga-himoyali** yozilgan (`UniqueConstraint`, `F()`, atomik `update`).

---

## 11b. Mobil ilova (Flutter) va REST API

Mobil ilova alohida papkada: `savdoyim_mobile/` (loyiha ildizida, Django yonida).
Flutter bilan yozilgan, backend'ning `/api/` REST endpointlari bilan ishlaydi.
Rolga qarab: sotuvchi = POS (sotuv+smena+qarz+balans), mijoz = mahsulot+savat+buyurtma.

**Sotuv yadrosi `kassa/savdo_service.py` ga ajratilgan** (web view ham, API ham shundan
foydalanadi — bitta manba):
- `savdo_yarat(dokon, sotuvchi, mahsulotlar_data, tolash_turi, ...)` → atomik sotuv, `SavdoXato` ko'taradi
- `smena_och`, `smena_yop`, `ochiq_smena`
- Miqdor helperlari: `_miqdor`, `_son`, `_decimal` (kassa/views.py da ham nusxasi bor — savat/skan uchun)

**API endpointlar** (`api/` app, TokenAuth):
```
POST /api/auth/login/  ·  GET /api/me/  ·  POST /api/auth/logout/
GET  /api/mahsulotlar/?q=            (sotuvchi: o'z do'koni)
GET  /api/ommaviy/mahsulotlar/?q=    (mijoz: barcha do'kon, AllowAny)
GET  /api/qarzlar/  ·  GET /api/cheklar/  ·  GET /api/kassa/
GET  /api/smena/  ·  POST /api/smena/ochish/  ·  POST /api/smena/yopish/
POST /api/savdo/                     -> kassa.savdo_service.savdo_yarat
POST /api/qarz/<id>/tolash/          -> savdo_service.qarz_tolash_yadro
GET  /api/mahsulot/barkod/<barkod>/  (sotuvchi skaner)
GET  /api/chek/topish/?q=            -> savdo_service.chek_topish
POST /api/qaytarish/                 -> savdo_service.qaytarish_yarat (refund)
GET  /api/mijoz/buyurtmalar/
POST /api/mijoz/buyurtma/            -> buyurtma.OrderService.create (ombor rezerv)
POST /api/mijoz/buyurtma/<id>/bekor/ -> OrderService.cancel (ombor qaytadi)
GET  /api/mijoz/sodiqlik/
GET|POST /api/mahsulot/<id>/sharh/   -> mahsulot.ReviewService (POST: baho yozish)
```

**Refactoring eslatmasi:** kassa `savdo_qilish`, `qarz_tolash`, `qaytarish_qil` web
view'lari endi `savdo_service` yadrosini chaqiradi (takror kod yo'q). Barcha 40 test o'tadi.
Ishga tushirish: Django `runserver 0.0.0.0:8000` + `savdoyim_mobile/README.md`.

## 11. Tez ishga tushirish

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Brauzer: `http://127.0.0.1:8000` · Windows uchun `ISHGA_TUSHIRISH.bat` ham bor.
Telegram bot: `python manage.py telegram_bot` (yoki server bilan avtomatik).
