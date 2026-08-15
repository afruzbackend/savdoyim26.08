# REST API — kelajakdagi React/mobil ilova uchun poydevor

Barcha endpointlar `/api/` ostida. Format: JSON. Auth: **Token** (DRF `authtoken`).

## Autentifikatsiya

```
POST /api/auth/login/
{ "username": "...", "password": "..." }
-> 200 { "token": "abc123...", "user": {id, username, rol, dokon_nomi} }
-> 401 login/parol noto'g'ri
```

Keyingi barcha so'rovlarda sarlavha:
```
Authorization: Token abc123...
```

Boshqa auth endpointlar:
- `POST /api/auth/logout/` — token'ni bekor qiladi
- `GET  /api/me/` — joriy foydalanuvchi

## Ma'lumot endpointlari (o'qish)

Barchasi so'rov yuborgan foydalanuvchining **o'z do'koni** bilan cheklangan
(begona do'kon ma'lumoti KO'RINMAYDI — `api/tests.py` da test qilingan).

| Metod | URL | Tavsif |
|-------|-----|--------|
| GET | `/api/mahsulotlar/` | Do'kon mahsulotlari. `?q=` — nom/barkod qidiruv |
| GET | `/api/mahsulotlar/<id>/` | Bitta mahsulot |
| GET | `/api/qarzlar/` | To'lanmagan qarzlar. `?hammasi=1` — barchasi |
| GET | `/api/cheklar/` | Savdo cheklari (mahsulotlari bilan) |
| GET | `/api/kassa/` | Kassa balansi |

## Misol (React / fetch)

```js
// Login
const r = await fetch('/api/auth/login/', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({username, password}),
});
const {token} = await r.json();

// Himoyalangan so'rov
const mahsulotlar = await fetch('/api/mahsulotlar/?q=non', {
  headers: {'Authorization': `Token ${token}`},
}).then(x => x.json());
```

## Holat (2026-08-09)

- ✅ Token login + do'konga bog'langan **o'qish** endpointlari.
- ⏳ **Yozish** (savdo qilish, qarz to'lash, mahsulot qo'shish) hozircha
  faqat mavjud web view'larda (atomik). API'ga ko'chirish — React ilova
  qurilganda qo'shiladi.
- CORS: dev'da barcha origin ruxsat; production'da `.env` `CORS_ALLOW_ALL=True`
  yoki `CORS_ALLOWED_ORIGINS` bilan cheklanadi.
