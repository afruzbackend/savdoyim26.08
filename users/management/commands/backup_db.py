"""Ma'lumotlar bazasini zaxira (backup) qiladigan buyruq.

Ishlatish:
    python manage.py backup_db              # zaxira yaratadi, oxirgi 14 tasini qoldiradi
    python manage.py backup_db --keep 30    # oxirgi 30 tasini qoldiradi
    python manage.py backup_db --keep 0     # hech qaysini o'chirmaydi

PostgreSQL uchun `pg_dump`, SQLite uchun oddiy fayl nusxasidan foydalanadi.
Zaxiralar `BASE_DIR/backups/` papkasiga sana bilan saqlanadi (masalan
`savdoyim2_2026-08-09_1530.sql`). Bu papka `.gitignore` da (git'ga tushmaydi).
"""
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


# pg_dump.exe odatda PATH da bo'lmaydi (Windows) — quyidagi joylardan qidiramiz.
def _pg_dump_topish():
    # 1) PG_DUMP muhit o'zgaruvchisi (aniq ko'rsatilgan yo'l)
    aniq = os.environ.get('PG_DUMP')
    if aniq and Path(aniq).exists():
        return aniq
    # 2) PATH da bormi
    topilgan = shutil.which('pg_dump')
    if topilgan:
        return topilgan
    # 3) Windows'dagi standart o'rnatish joylari (yangi versiyadan boshlab)
    asos = Path(r'C:\Program Files\PostgreSQL')
    if asos.exists():
        for versiya in sorted(asos.iterdir(), reverse=True):
            nomzod = versiya / 'bin' / 'pg_dump.exe'
            if nomzod.exists():
                return str(nomzod)
    return None


class Command(BaseCommand):
    help = "Ma'lumotlar bazasini backups/ papkasiga zaxira qiladi (PostgreSQL yoki SQLite)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep', type=int, default=14,
            help='Nechta oxirgi zaxirani qoldirish (default 14). 0 = hech qaysi o‘chirilmaydi.',
        )

    def handle(self, *args, **opts):
        keep = opts['keep']
        backup_dir = Path(settings.BASE_DIR) / 'backups'
        backup_dir.mkdir(exist_ok=True)

        db = settings.DATABASES['default']
        engine = db['ENGINE']
        vaqt = datetime.now().strftime('%Y-%m-%d_%H%M%S')

        if 'postgresql' in engine:
            fayl = self._postgres_backup(db, backup_dir, vaqt)
        elif 'sqlite' in engine:
            fayl = self._sqlite_backup(db, backup_dir, vaqt)
        else:
            raise CommandError(f"Qo'llab-quvvatlanmaydigan DB engine: {engine}")

        hajm = fayl.stat().st_size
        self.stdout.write(self.style.SUCCESS(
            f"[OK] Zaxira yaratildi: {fayl.name}  ({hajm/1024:.1f} KB)"
        ))

        if keep > 0:
            self._eskilarini_tozala(backup_dir, keep)

    # ── PostgreSQL ──
    def _postgres_backup(self, db, backup_dir, vaqt):
        pg_dump = _pg_dump_topish()
        if not pg_dump:
            raise CommandError(
                "pg_dump topilmadi. PostgreSQL o'rnatilganini tekshiring yoki "
                "PG_DUMP muhit o'zgaruvchisida to'liq yo'lni ko'rsating."
            )
        nom = db.get('NAME', 'db')
        fayl = backup_dir / f"{nom}_{vaqt}.sql"

        muhit = os.environ.copy()
        if db.get('PASSWORD'):
            muhit['PGPASSWORD'] = db['PASSWORD']

        buyruq = [
            pg_dump,
            '-h', db.get('HOST') or 'localhost',
            '-p', str(db.get('PORT') or '5432'),
            '-U', db.get('USER') or 'postgres',
            '-d', nom,
            '-f', str(fayl),
            '--no-owner', '--no-privileges',
        ]
        self.stdout.write(f"... pg_dump ishga tushirilmoqda ({nom})")
        natija = subprocess.run(buyruq, env=muhit, capture_output=True, text=True)
        if natija.returncode != 0:
            # Xato bo'lsa yarim fayl qolmasin
            if fayl.exists():
                fayl.unlink()
            raise CommandError(f"pg_dump xatolik berdi:\n{natija.stderr.strip()}")
        return fayl

    # ── SQLite ──
    def _sqlite_backup(self, db, backup_dir, vaqt):
        manba = Path(db['NAME'])
        if not manba.exists():
            raise CommandError(f"SQLite fayli topilmadi: {manba}")
        fayl = backup_dir / f"{manba.stem}_{vaqt}.sqlite3"
        # Ishlayotgan bazadan xavfsiz nusxa: SQLite backup API (fayl nusxasi yarim
        # yozilgan tranzaksiyani buzuq holatda olib qolishi mumkin)
        import sqlite3
        src = sqlite3.connect(str(manba))
        dst = sqlite3.connect(str(fayl))
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        return fayl

    # ── Eski zaxiralarni tozalash ──
    def _eskilarini_tozala(self, backup_dir, keep):
        zaxiralar = sorted(
            [p for p in backup_dir.iterdir()
             if p.is_file() and p.suffix in ('.sql', '.sqlite3')],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        ortiqcha = zaxiralar[keep:]
        for p in ortiqcha:
            p.unlink()
        if ortiqcha:
            self.stdout.write(
                f"[TOZALASH] {len(ortiqcha)} ta eski zaxira o'chirildi "
                f"(oxirgi {keep} tasi qoldirildi)."
            )
