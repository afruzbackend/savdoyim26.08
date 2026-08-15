# 🏪 DokonTizim — To'liq Biznes Boshqaruv Tizimi

## 🚀 Ishga tushirish

```powershell
# 1. Papkaga kiring
cd savdo_tizimi

# 2. Virtual muhit
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3. O'rnatish
pip install -r requirements.txt

# 4. Migratsiya
python manage.py makemigrations
python manage.py migrate

# 5. Admin yaratish
python manage.py createsuperuser

# 6. Server
python manage.py runserver
```

**Brauzer:** http://127.0.0.1:8000

---

## 👥 Rollar

| Rol | Imkoniyatlar |
|-----|-------------|
| 🏪 Dokon Egasi | Kassa, Hisobot, Soliq, Qarz daftar, Sotuvchi boshqarish |
| 👨‍💼 Sotuvchi | Kassa (POS), Mahsulot, Qarz, Skanner |
| 🏭 Zavod | Buyurtmalar, Mahsulot, Dokon monitoringi, Chat |
| 🚛 Yetkazib Beruvchi | Buyurtmalar, GPS xarita, Skanner |
| 🛍️ Mijoz | Mahsulot qidirish, GPS orqali yaqin dokon |

---

## 📋 URL Manzillar

| URL | Sahifa |
|-----|--------|
| `/` | Kirish |
| `{% url 'register' %}` | Ro'yxatdan o'tish |
| `{% url 'forgot_password' %}` | Parolni tiklash |
| `% url 'dokon_egasi_dashboard' %}` | Dokon egasi dashboard |
| `/sotuvchi/` | Sotuvchi dashboard |
| `/zavod/` | Zavod dashboard |
| `/yetkazuvchi/` | Yetkazuvchi dashboard |
| `/mijoz/` | Mijoz dashboard |
| `/checkout/kassa/` | Kassa (POS) |
| `/checkout/kassa/qarzlar/` | Qarz daftar |
| `/checkout/kassa/hisobot/` | Hisobotlar |
| `/tax/soliq/` | Soliq hisoblash |
| `/product/mahsulot/` | Mahsulotlar |
| `/product/mahsulot/skanner/` | Barkod skaneri |
| `/order/buyurtma/` | Buyurtmalar |
| ` /chat/chat/` | Chat |
| `/admin/` | Admin panel |
