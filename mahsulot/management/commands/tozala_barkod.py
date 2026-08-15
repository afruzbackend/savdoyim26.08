# -*- coding: utf-8 -*-
"""Barkod katalogidagi mahsulot nomlarini tozalaydi — uzbek do'konlarida
ishlatiladigan tanish, chiroyli nomlarga keltiradi.

  python manage.py tozala_barkod          # tozalaydi
  python manage.py tozala_barkod --korish # faqat ko'rsatadi (o'zgartirmaydi)

Nima qiladi:
  • "coca-cola classic" -> "Coca Cola Classic"
  • katta/kichik harflarni to'g'rilaydi (title-case)
  • mashhur brendlarni bir xil ko'rinishga keltiradi
  • hajmni (0.5 L, 95 g) tartibga soladi
  • buzuq / bo'sh / bir belgili yozuvlarni o'chiradi
"""
import re
from django.core.management.base import BaseCommand
from mahsulot.models import BarkodKatalog

# Mashhur brendlar: nomda shu kalit uchrasa — kanonik yozuvga o'giramiz
BREND = {
    'coca-cola': 'Coca Cola', 'coca cola': 'Coca Cola', 'cocacola': 'Coca Cola',
    'coca-cola zero': 'Coca Cola Zero', 'coca-cola classic': 'Coca Cola Classic',
    'pepsi': 'Pepsi', 'pepsi-cola': 'Pepsi', 'pepsi cola': 'Pepsi',
    'fanta': 'Fanta', 'sprite': 'Sprite', 'schweppes': 'Schweppes',
    'mirinda': 'Mirinda', '7up': '7UP', '7 up': '7UP',
    'red bull': 'Red Bull', 'redbull': 'Red Bull', 'adrenaline': 'Adrenaline Rush',
    'nescafe': 'Nescafe', 'nescafé': 'Nescafe', 'jacobs': 'Jacobs',
    'lipton': 'Lipton', 'nestle': 'Nestle', 'nestlé': 'Nestle', 'nesquik': 'Nesquik',
    'oreo': 'Oreo', 'milka': 'Milka', 'snickers': 'Snickers', 'mars': 'Mars',
    'twix': 'Twix', 'bounty': 'Bounty', 'kitkat': 'KitKat', 'kit kat': 'KitKat',
    'nutella': 'Nutella', 'kinder': 'Kinder', 'ferrero': 'Ferrero',
    'lay\'s': "Lay's", 'lays': "Lay's", 'pringles': 'Pringles', 'cheetos': 'Cheetos',
    'chupa chups': 'Chupa Chups', 'orbit': 'Orbit', 'dirol': 'Dirol', 'mentos': 'Mentos',
    'danone': 'Danone', 'activia': 'Activia', 'president': 'President',
    'nivea': 'Nivea', 'dove': 'Dove', 'colgate': 'Colgate', 'head & shoulders': 'Head & Shoulders',
    'nabeghlavi': 'Nabeghlavi', 'borjomi': 'Borjomi', 'hrustashka': 'Hrustashka',
}

# Har doim KATTA harf qoladigan qisqartmalar
KATTA = {'uht', 'pet', 'bio', 'led', 'usb', 'pvc', 'uv', '7up', 'kitkat'}
# Kichik qoladigan bog'lovchilar (o'rtada)
KICHIK = {'va', 'and', 'the', 'of', 'ml', 'l', 'g', 'kg', 'gr'}


def hajmni_ajrat(nom):
    """Nomdan hajmni (0.5 l, 1.5l, 95 g, 250ml, 200 мл, 350 г) ajratadi.
    Kirill birliklarini ham tushunadi va lotin (L, ml, g, kg) ga keltiradi."""
    m = re.search(r'(\d+[\.,]?\d*)\s*(мл|кг|гр|мг|л|г|ml|kg|gr|mg|letr|litr|l|g)\b',
                  nom, re.IGNORECASE)
    if not m:
        return nom, ''
    son = m.group(1).replace(',', '.')
    birlik = m.group(2).lower()
    birlik = {
        'gr': 'g', 'gr.': 'g', 'мг': 'mg', 'mg': 'mg',
        'litr': 'L', 'letr': 'L', 'l': 'L', 'л': 'L',
        'ml': 'ml', 'мл': 'ml', 'g': 'g', 'г': 'g', 'кг': 'kg', 'kg': 'kg',
    }.get(birlik, birlik)
    hajm = f"{son} {birlik}"
    toza = (nom[:m.start()] + ' ' + nom[m.end():]).strip()
    return toza, hajm


def soz_titlecase(soz):
    low = soz.lower()
    if low in KATTA:
        return soz.upper()
    if low in KICHIK:
        return low
    # 7up kabi raqam+harf
    if any(c.isdigit() for c in soz) and any(c.isalpha() for c in soz):
        return soz.upper() if len(soz) <= 4 else soz.capitalize()
    return soz[:1].upper() + soz[1:].lower() if soz else soz


def tozala(nom):
    if not nom:
        return None
    nom = nom.strip()
    # ko'p bo'shliq -> bitta
    nom = re.sub(r'\s+', ' ', nom)
    # boshlang'ich junk belgilarni olib tashlaymiz
    nom = nom.strip(' -_.,;|/\\')
    if len(nom) < 2 or not re.search(r'[A-Za-zА-Яа-я]', nom):
        return None  # bo'sh yoki harfsiz -> o'chirish

    # brend borligini tekshiramiz (ichki hajm bilan)
    tan, hajm = hajmni_ajrat(nom)
    past = tan.lower()

    kanonik = None
    for kalit, tozanom in sorted(BREND.items(), key=lambda x: -len(x[0])):
        if kalit in past:
            kanonik = tozanom
            # brenddan keyingi variant so'zlarini ham qo'shishga urinamiz
            qoldiq = re.sub(re.escape(kalit), '', past, flags=re.IGNORECASE).strip(' -_.,')
            qoldiq = re.sub(r'\s+', ' ', qoldiq)
            # brend nomining o'zidagi so'zlarni qoldiqdan olib tashlaymiz
            brend_sozlar = set(tozanom.lower().split())
            qoldiq_sozlar = [w for w in qoldiq.split() if w.lower() not in brend_sozlar]
            variant = ' '.join(soz_titlecase(w) for w in qoldiq_sozlar[:3]).strip()
            natija = (kanonik + (' ' + variant if variant else '')).strip()
            break
    else:
        # brend topilmadi -> oddiy title-case
        natija = ' '.join(soz_titlecase(w) for w in tan.split())

    # hajmni oxiriga qo'shamiz
    if hajm:
        natija = f"{natija} {hajm}"
    natija = re.sub(r'\s+', ' ', natija).strip()
    return natija[:200] if natija else None


class Command(BaseCommand):
    help = "Barkod katalogidagi nomlarni toza, tanish ko'rinishga keltiradi."

    def add_arguments(self, parser):
        parser.add_argument('--korish', action='store_true',
                            help="Faqat ko'rsatadi, o'zgartirmaydi.")

    def handle(self, *args, **opts):
        korish = opts['korish']
        ozgardi = ochirildi = 0
        namuna = []
        for obj in BarkodKatalog.objects.all().iterator():
            yangi = tozala(obj.nomi)
            if yangi is None:
                if len(namuna) < 15:
                    namuna.append(f"  O'CHIR: {obj.nomi!r}")
                if not korish:
                    obj.delete()
                ochirildi += 1
                continue
            if yangi != obj.nomi:
                if len(namuna) < 15:
                    namuna.append(f"  {obj.nomi!r}  ->  {yangi!r}")
                if not korish:
                    obj.nomi = yangi
                    obj.save(update_fields=['nomi'])
                ozgardi += 1

        for s in namuna:
            self.stdout.write(s)
        rejim = "(faqat ko'rish)" if korish else ""
        self.stdout.write(self.style.SUCCESS(
            f"Tugadi {rejim}. O'zgartirildi: {ozgardi}, o'chirildi (buzuq): {ochirildi}, "
            f"katalogda qoldi: {BarkodKatalog.objects.count()} ta."
        ))
