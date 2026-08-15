# -*- coding: utf-8 -*-
"""Open Food Facts'dan O'zbekistonda sotiladigan mahsulotlarni (haqiqiy barkodlar)
umumiy barkod katalogiga import qiladi. Bepul, ochiq ma'lumot.

Ishlatish:
    python manage.py import_barkod            # 20 sahifa (~2000 mahsulot)
    python manage.py import_barkod --sahifa 5 # kamroq
"""
import time
from django.core.management.base import BaseCommand
from mahsulot.models import BarkodKatalog
from mahsulot.views import _off_kategoriya  # OFF kategoriyasini bizning slugga o'giradi

OFF_URL = 'https://world.openfoodfacts.org/cgi/search.pl'
HEADERS = {'User-Agent': 'Savdoyim/1.0 (savdo tizimi; uz)'}


class Command(BaseCommand):
    help = "Open Food Facts'dan O'zbekiston mahsulotlarini barkod katalogiga import qiladi."

    def add_arguments(self, parser):
        parser.add_argument('--sahifa', type=int, default=20,
                            help="Nechta sahifa import qilinsin (har sahifa ~100 ta).")
        parser.add_argument('--davlat', type=str, default='Uzbekistan',
                            help="Davlat (OFF countries tegi). Standart: Uzbekistan.")

    def handle(self, *args, **opts):
        import requests
        qoshildi = yangilandi = otkazildi = 0
        for page in range(1, opts['sahifa'] + 1):
            try:
                r = requests.get(OFF_URL, headers=HEADERS, timeout=30, params={
                    'action': 'process',
                    'tagtype_0': 'countries', 'tag_contains_0': 'contains',
                    'tag_0': opts['davlat'],
                    'fields': 'code,product_name,product_name_en,brands,categories_tags,categories,quantity',
                    'json': 1, 'page_size': 100, 'page': page,
                })
                if r.status_code != 200:
                    self.stdout.write(f"  sahifa {page}: HTTP {r.status_code} — o'tkazildi")
                    time.sleep(4)
                    continue
                prods = r.json().get('products', [])
            except Exception as e:
                self.stdout.write(f"  sahifa {page}: xato ({type(e).__name__}) — o'tkazildi")
                time.sleep(4)
                continue

            if not prods:
                break

            for p in prods:
                code = (p.get('code') or '').strip()
                nomi = (p.get('product_name') or p.get('product_name_en')
                        or p.get('brands') or '').strip()
                # Yaroqli barkod (8-14 raqam) va nomi bo'lishi shart
                if not code or not nomi or not code.isdigit() or not (8 <= len(code) <= 14):
                    otkazildi += 1
                    continue
                kat = _off_kategoriya(p)
                hajm = (p.get('quantity') or '').strip()

                def bilan_hajm(nom):
                    # Hajmni (0.5 l, 200 gr...) nomga qo'shadi, agar hali yo'q bo'lsa
                    if hajm and hajm.lower() not in nom.lower():
                        return f"{nom} {hajm}"[:200]
                    return nom[:200]

                obj, created = BarkodKatalog.objects.get_or_create(
                    barkod=code, defaults={'nomi': bilan_hajm(nomi), 'kategoriya': kat}
                )
                if created:
                    qoshildi += 1
                else:
                    ozgardi = False
                    yangi_nom = bilan_hajm(obj.nomi)
                    if yangi_nom != obj.nomi:
                        obj.nomi = yangi_nom
                        ozgardi = True
                    if kat and not obj.kategoriya:
                        obj.kategoriya = kat
                        ozgardi = True
                    if ozgardi:
                        obj.save()
                    yangilandi += 1

            self.stdout.write(f"  sahifa {page}: {len(prods)} ta o'qildi (jami yangi: {qoshildi})")
            time.sleep(1)  # OFF serverini bosmaslik uchun

        self.stdout.write(self.style.SUCCESS(
            f"Tugadi. Yangi qo'shilgan: {qoshildi}, mavjud: {yangilandi}, "
            f"o'tkazilgan (yaroqsiz): {otkazildi}. "
            f"Katalogda jami: {BarkodKatalog.objects.count()} ta barkod."
        ))
