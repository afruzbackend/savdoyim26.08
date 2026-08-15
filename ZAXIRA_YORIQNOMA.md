# Ma'lumotlar bazasi zaxirasi (backup) — yo'riqnoma

## Zaxira yaratish

**Qo'lda (buyruq):**
```
python manage.py backup_db
```
- Zaxira `backups/` papkasiga saqlanadi: `savdoyim2_2026-08-09_1530.sql`
- Oxirgi **14 ta** zaxira qoldiriladi, eskilari avtomatik o'chiriladi.
- Boshqacha son: `python manage.py backup_db --keep 30`
- Hech qaysini o'chirmaslik: `python manage.py backup_db --keep 0`

**Oson usul:** `ZAXIRA.bat` faylini ikki marta bosing.

## Har kuni avtomatik (Windows Task Scheduler)

1. Start → **Task Scheduler** (Vazifalar rejalashtiruvchisi) ni oching.
2. **Create Basic Task** → nom: `Savdoyim zaxira`.
3. Trigger: **Daily** (har kuni), vaqt: masalan `23:00`.
4. Action: **Start a program** →
   - Program/script: `C:\Users\ISHONCH\PycharmProject\savdo20\savdo_tizimi\ZAXIRA.bat`
5. Finish. Endi har kuni avtomatik zaxira olinadi.

> Eslatma: bu server o'chiq bo'lsa ham ishlaydi — faqat PostgreSQL xizmati ishlab tursa bo'lgani.

## Zaxirani tiklash (RESTORE) — muhim!

**Diqqat:** tiklash bazadagi hozirgi ma'lumotni almashtiradi. Avval yangi/bo'sh bazaga tiklab sinab ko'rish tavsiya etiladi.

**PostgreSQL:**
```
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d savdoyim2 -f "backups\savdoyim2_2026-08-09_1530.sql"
```
- Parol so'raydi (`.env` dagi `DB_PASSWORD`).
- Butunlay toza tiklash uchun avval bazani qayta yaratish mumkin:
  ```
  dropdb -U postgres savdoyim2
  createdb -U postgres savdoyim2
  psql -U postgres -d savdoyim2 -f "backups\...sql"
  ```

**SQLite** (agar SQLite ishlatilsa): zaxira `.sqlite3` faylni `db.sqlite3` o'rniga nusxalash yetarli.

## Muhim
- `backups/` papkasi `.gitignore` da — git'ga (GitHub'ga) tushmaydi. Bu **to'g'ri**, chunki zaxirada maxfiy savdo ma'lumoti bor.
- Muhim zaxiralarni vaqti-vaqti bilan **boshqa joyga** (tashqi disk / bulut) ham ko'chirib qo'ying — kompyuter buzilsa yagona nusxa yo'qolmasin.
