# -*- coding: utf-8 -*-
"""
Hisobot xizmati — savdo ma'lumotlarini yig'ib, PDF va Excel hujjat yasaydi.
Telegram bot ham, veb-sayt ham shu moduldan foydalanadi.
"""
import io
import math
from datetime import datetime, time, timedelta

from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from users.models import CustomUser, DokonEgasiProfil
from .models import SavdoChek, SavdoChekMahsulot, QarzDaftar, Kassa, Qaytarish


# ═══════════════════════════════════════════════════════════
#  YORDAMCHILAR
# ═══════════════════════════════════════════════════════════
def pul(qiymat):
    """Pulni chiroyli formatda: 1 250 000 so'm"""
    try:
        n = int(round(float(qiymat or 0)))
    except (TypeError, ValueError):
        n = 0
    return f"{n:,}".replace(",", " ") + " so'm"


def dokon_aniqla(user: CustomUser):
    """Foydalanuvchidan uning do'konini topadi. Faqat do'kon egasi yoki TASDIQLANGAN
    sotuvchi (Telegram bot ham shu orqali) — yagona manba users.services."""
    from users.services import foydalanuvchi_dokoni
    if not user:
        return None
    return foydalanuvchi_dokoni(user)


def _kun_oralig(sana):
    """Berilgan sana uchun mahalliy vaqt bo'yicha [boshlanish, tugash) oralig'i."""
    tz = timezone.get_current_timezone()
    boshi = timezone.make_aware(datetime.combine(sana, time.min), tz)
    oxiri = boshi + timedelta(days=1)
    return boshi, oxiri


def _oralig(sana_dan, sana_gacha):
    tz = timezone.get_current_timezone()
    boshi = timezone.make_aware(datetime.combine(sana_dan, time.min), tz)
    oxiri = timezone.make_aware(datetime.combine(sana_gacha, time.min), tz) + timedelta(days=1)
    return boshi, oxiri


# ═══════════════════════════════════════════════════════════
#  MA'LUMOT YIG'ISH
# ═══════════════════════════════════════════════════════════
def _yig(dokon, boshi, oxiri, top_limit=10):
    """[boshi, oxiri) oralig'i uchun to'liq statistikani yig'adi."""
    cheklar = SavdoChek.objects.filter(dokon=dokon, yaratilgan__gte=boshi, yaratilgan__lt=oxiri)
    agg = cheklar.aggregate(
        jami_savdo=Sum('jami'),
        soni=Count('id'),
        naqd=Sum('jami', filter=Q(tolash_turi='naqd')),
        karta=Sum('jami', filter=Q(tolash_turi='karta')),
        qarz=Sum('jami', filter=Q(tolash_turi='qarz')),
        chegirma_jami=Sum('chegirma'),
    )
    naqd = agg['naqd'] or 0
    karta = agg['karta'] or 0
    qarz = agg['qarz'] or 0

    # Qaytarishlar (refund) — daromadni va kassani kamaytiradi.
    q_agg = Qaytarish.objects.filter(
        dokon=dokon, yaratilgan__gte=boshi, yaratilgan__lt=oxiri
    ).aggregate(
        jami=Sum('summa'),
        kassadan=Sum('summa', filter=Q(kassadan=True)),
    )
    qaytarilgan = q_agg['jami'] or 0
    qaytarilgan_kassadan = q_agg['kassadan'] or 0

    top = list(
        SavdoChekMahsulot.objects
        .filter(chek__dokon=dokon, chek__yaratilgan__gte=boshi, chek__yaratilgan__lt=oxiri)
        .values('mahsulot_nomi')
        .annotate(jami_soni=Sum('soni'), summa=Sum('jami'))
        .order_by('-summa')[:top_limit]
    )
    yalpi_savdo = agg['jami_savdo'] or 0
    return {
        'dokon_nomi': getattr(dokon, 'dokon_nomi', 'Do\'kon') or 'Do\'kon',
        # jami_savdo = SOF savdo (qaytarishlar ayrilgan)
        'jami_savdo': yalpi_savdo - qaytarilgan,
        'yalpi_savdo': yalpi_savdo,          # qaytarishsiz (yalpi)
        'qaytarilgan': qaytarilgan,          # qaytarilgan jami pul
        'chek_soni': agg['soni'] or 0,
        'naqd': naqd,
        'karta': karta,
        'qarz': qarz,
        'chegirma': agg['chegirma_jami'] or 0,
        # Kassaga real tushgan pul = naqd + karta − kassadan qaytarilgan
        'kassaga_tushgan': (naqd + karta) - qaytarilgan_kassadan,
        'top': top,
    }


def kunlik_hisobot(dokon, sana, top_limit=10):
    """Bitta kun uchun to'liq hisobot (dict)."""
    boshi, oxiri = _kun_oralig(sana)
    data = _yig(dokon, boshi, oxiri, top_limit)
    data['sana'] = sana
    data['subtitle'] = sana.strftime('%d.%m.%Y')
    return data


def davr_hisobot(dokon, boshlanish, tugash, sarlavha='', top_limit=10):
    """Sana oralig'i (davr) uchun to'liq hisobot. Veb eksport uchun."""
    boshi, oxiri = _oralig(boshlanish, tugash)
    data = _yig(dokon, boshi, oxiri, top_limit)
    data['sana'] = tugash  # fayl nomi uchun
    davr_matn = (f"{boshlanish.strftime('%d.%m.%Y')} — {tugash.strftime('%d.%m.%Y')}"
                 if boshlanish != tugash else tugash.strftime('%d.%m.%Y'))
    data['subtitle'] = f"{sarlavha} · {davr_matn}" if sarlavha else davr_matn
    return data


def oraliq_top(dokon, sana_dan, sana_gacha, top_limit=10):
    """Berilgan davr uchun eng ko'p sotilgan mahsulotlar + umumiy savdo."""
    boshi, oxiri = _oralig(sana_dan, sana_gacha)
    cheklar = SavdoChek.objects.filter(dokon=dokon, yaratilgan__gte=boshi, yaratilgan__lt=oxiri)
    agg = cheklar.aggregate(jami_savdo=Sum('jami'), soni=Count('id'))
    top = list(
        SavdoChekMahsulot.objects
        .filter(chek__dokon=dokon, chek__yaratilgan__gte=boshi, chek__yaratilgan__lt=oxiri)
        .values('mahsulot_nomi')
        .annotate(jami_soni=Sum('soni'), summa=Sum('jami'))
        .order_by('-summa')[:top_limit]
    )
    return {
        'sana_dan': sana_dan,
        'sana_gacha': sana_gacha,
        'dokon_nomi': getattr(dokon, 'dokon_nomi', 'Do\'kon'),
        'jami_savdo': agg['jami_savdo'] or 0,
        'chek_soni': agg['soni'] or 0,
        'top': top,
    }


def olik_tovarlar(dokon, kunlar=30, limit=20):
    """O'lik tovar: so'nggi `kunlar` kunda umuman sotilmagan, lekin omborda
    turgan (pul bog'lab qolgan) mahsulotlar. Eng ko'p pul yotgani birinchi.
    Do'kon egasiga qaysi tovar 'yotibdi'ni ko'rsatadi — xaridni to'g'rilaydi."""
    from mahsulot.models import Mahsulot
    from django.db.models import Max
    chegara = timezone.now() - timedelta(days=kunlar)
    mahsulotlar = list(Mahsulot.objects.filter(dokon=dokon, faol=True, soni__gt=0))

    # Har mahsulot uchun oxirgi sotuv sanasi (bitta so'rovda)
    oxirgi = {r['mahsulot_id']: r['oxirgi'] for r in (
        SavdoChekMahsulot.objects
        .filter(chek__dokon=dokon, mahsulot__isnull=False)
        .values('mahsulot_id').annotate(oxirgi=Max('chek__yaratilgan')))}

    natija = []
    for m in mahsulotlar:
        last = oxirgi.get(m.id)
        if last and last >= chegara:
            continue  # yaqinda sotilgan — o'lik emas
        qiymat = (m.sotib_olish_narxi or 0) * m.soni
        natija.append({
            'id': m.id, 'nomi': m.nomi, 'soni': m.soni, 'birlik': m.birlik,
            'oxirgi_sotuv': last, 'hech_sotilmagan': last is None,
            'qiymat': qiymat,
        })
    natija.sort(key=lambda x: x['qiymat'], reverse=True)
    return natija[:limit]


def qarz_eslatma(dokon, bugun=None):
    """Muddati o'tgan yoki bugun keladigan to'lanmagan qarzlar (eslatma uchun).
    Qaytadi: {'otgan': [...], 'bugun': [...], 'otgan_jami': .., 'bugun_jami': ..}"""
    from .models import QarzDaftar
    if bugun is None:
        bugun = timezone.localdate()
    qs = (QarzDaftar.objects
          .filter(dokon=dokon, to_langan=False, qaytarish_sana__isnull=False,
                  qaytarish_sana__lte=bugun)
          .order_by('qaytarish_sana'))
    otgan, bugungi = [], []
    for q in qs:
        (bugungi if q.qaytarish_sana == bugun else otgan).append(q)
    return {
        'otgan': otgan,
        'bugun': bugungi,
        'otgan_jami': sum((q.summa or 0) for q in otgan),
        'bugun_jami': sum((q.summa or 0) for q in bugungi),
    }


def qarz_eslatma_matn(dokon, bugun=None):
    """Qarz eslatmasini Telegram uchun HTML matn qilib qaytaradi (yo'q bo'lsa '')."""
    e = qarz_eslatma(dokon, bugun)
    if not e['otgan'] and not e['bugun']:
        return ''
    q = ["💳 <b>Qarz eslatmasi</b>"]
    if e['otgan']:
        q.append(f"\n🔴 Muddati o'tgan: <b>{len(e['otgan'])} ta</b> · {pul(e['otgan_jami'])}")
        for d in e['otgan'][:5]:
            tel = f" ({d.mijoz_telefon})" if d.mijoz_telefon else ""
            q.append(f"  • {d.mijoz_ism}{tel} — {pul(d.summa)} · {d.qaytarish_sana:%d.%m}")
    if e['bugun']:
        q.append(f"\n🟠 Bugun muddati: <b>{len(e['bugun'])} ta</b> · {pul(e['bugun_jami'])}")
        for d in e['bugun'][:5]:
            tel = f" ({d.mijoz_telefon})" if d.mijoz_telefon else ""
            q.append(f"  • {d.mijoz_ism}{tel} — {pul(d.summa)}")
    return "\n".join(q)


def kassa_holati(dokon):
    """Kassa balansi + to'lanmagan qarzlar."""
    kassa = Kassa.objects.filter(dokon=dokon).first()
    qarz = QarzDaftar.objects.filter(dokon=dokon, to_langan=False).aggregate(s=Sum('summa'))['s'] or 0
    return {
        'balans': kassa.balans if kassa else 0,
        'qarz_jami': qarz,
    }


# ═══════════════════════════════════════════════════════════
#  AQLLI OMBOR BASHORATI (recency-weighted talab modeli)
# ═══════════════════════════════════════════════════════════
#  Har bir mahsulot uchun so'nggi kunlardagi sotuvni "yaqin kunlar
#  muhimroq" tamoyili bilan (eksponensial og'irlik / yarim-umr) o'lchaydi.
#  Shu talab tezligiga qarab mahsulot taxminan qachon tugashini
#  (sana bilan) va talab o'sish/pasayish tendensiyasini aniqlaydi.

def _bashorat_yadro(dokon, mahsulot_ids=None, kunlar=30, yarim_umr=14.0):
    """So'nggi `kunlar` kundagi kunlik sotuvni recency-weighted hisoblaydi.

    Yaqin kunlar ko'proq og'irlik oladi (yarim_umr kunlik half-life).
    Qaytadi: {mahsulot_id: {'rate': og'irlikli kunlik sotuv,
                            'sotuv_kunlari': nechta kun sotilgan,
                            'trend': 'osish'|'pasayish'|'barqaror'}}"""
    tugash = timezone.localdate()
    boshi, oxiri = _oralig(tugash - timedelta(days=kunlar - 1), tugash)

    qs = (SavdoChekMahsulot.objects
          .filter(chek__dokon=dokon, mahsulot__isnull=False,
                  chek__yaratilgan__gte=boshi, chek__yaratilgan__lt=oxiri)
          .annotate(kun=TruncDate('chek__yaratilgan'))
          .values('mahsulot_id', 'kun')
          .annotate(s=Sum('soni')))
    if mahsulot_ids is not None:
        qs = qs.filter(mahsulot_id__in=list(mahsulot_ids))

    def _ogirlik(kun_avval):
        # yarim-umr: har `yarim_umr` kunda og'irlik yarmiga tushadi
        return 0.5 ** (kun_avval / yarim_umr)

    umumiy_ogirlik = sum(_ogirlik(d) for d in range(kunlar)) or 1.0

    xom = {}  # mid -> {'numer':.., 'kunlar':int, 'oxirgi7':.., 'oldingi7':..}
    for row in qs:
        mid, kun, s = row['mahsulot_id'], row['kun'], float(row['s'] or 0)
        kun_avval = (tugash - kun).days
        if kun_avval < 0 or kun_avval >= kunlar:
            continue
        d = xom.setdefault(mid, {'numer': 0.0, 'kunlar': 0, 'oxirgi7': 0.0, 'oldingi7': 0.0})
        d['numer'] += s * _ogirlik(kun_avval)
        d['kunlar'] += 1
        if kun_avval < 7:
            d['oxirgi7'] += s
        elif kun_avval < 14:
            d['oldingi7'] += s

    natija = {}
    for mid, d in xom.items():
        rate = d['numer'] / umumiy_ogirlik
        r7, o7 = d['oxirgi7'] / 7.0, d['oldingi7'] / 7.0
        if (o7 > 0 and r7 > o7 * 1.2) or (o7 == 0 and r7 > 0):
            trend = 'osish'
        elif o7 > 0 and r7 < o7 * 0.8:
            trend = 'pasayish'
        else:
            trend = 'barqaror'
        natija[mid] = {'rate': rate, 'sotuv_kunlari': d['kunlar'], 'trend': trend}
    return natija


def _bashorat_tafsil(mahsulot, yadro_entry):
    """Yadro natijasini bitta mahsulot uchun ko'rsatiladigan bashoratga aylantiradi."""
    bugun = timezone.localdate()
    rate = yadro_entry['rate'] if yadro_entry else 0.0
    sotuv_kunlari = yadro_entry['sotuv_kunlari'] if yadro_entry else 0
    trend = yadro_entry['trend'] if yadro_entry else 'barqaror'

    if rate > 0 and mahsulot.soni > 0:
        qolgan_kun = int(math.ceil(float(mahsulot.soni) / rate))
        tugash_sana = bugun + timedelta(days=qolgan_kun)
    else:
        qolgan_kun = None
        tugash_sana = None

    # Ishonch: nechta kun sotuv bo'lgani (ko'proq kun = ishonchliroq bashorat)
    if sotuv_kunlari >= 8:
        ishonch = 'yuqori'
    elif sotuv_kunlari >= 3:
        ishonch = 'orta'
    else:
        ishonch = 'past'

    return {
        'kunlik_sotuv': round(rate, 1),
        'qolgan_kun': qolgan_kun,
        'tugash_sana': tugash_sana,
        'trend': trend,
        'ishonch': ishonch,
    }


def mahsulot_bashorat(mahsulot, kunlar=30):
    """Bitta mahsulot uchun 'taxminan qachon tugaydi' bashorati (web sahifa uchun)."""
    yadro = _bashorat_yadro(mahsulot.dokon, [mahsulot.id], kunlar)
    return _bashorat_tafsil(mahsulot, yadro.get(mahsulot.id))


def mahsulotlar_bashorati(dokon, mahsulotlar, kunlar=30):
    """Bir nechta mahsulot uchun bashorat lug'ati: {mahsulot_id: tafsil}.
    Mahsulot ro'yxati sahifasi uchun (bitta so'rovda hammasi)."""
    yadro = _bashorat_yadro(dokon, [m.id for m in mahsulotlar], kunlar)
    return {m.id: _bashorat_tafsil(m, yadro.get(m.id)) for m in mahsulotlar}


def ombor_prognoz(dokon, kunlar=30, ogohlantirish_kun=7, limit=40):
    """Aqlli ombor prognozi (recency-weighted talab modeli).
    Har bir mahsulot taxminan qachon tugashini (sana bilan) hisoblaydi va
    ogohlantirish kerak bo'lganlarni qaytaradi (eng shoshilinch birinchi)."""
    from mahsulot.models import Mahsulot
    mahsulotlar = list(Mahsulot.objects.filter(dokon=dokon, faol=True))
    yadro = _bashorat_yadro(dokon, [m.id for m in mahsulotlar], kunlar)

    natija = []
    for m in mahsulotlar:
        t = _bashorat_tafsil(m, yadro.get(m.id))
        shoshilinch = (t['qolgan_kun'] is not None and t['qolgan_kun'] <= ogohlantirish_kun)
        minimumdan_past = m.soni <= (m.minimum_son or 0)
        if not (shoshilinch or minimumdan_past):
            continue
        natija.append({
            'nomi': m.nomi,
            'soni': m.soni,
            'birlik': m.birlik,
            'minimum_son': m.minimum_son,
            'kunlik_sotuv': t['kunlik_sotuv'],
            'qolgan_kun': t['qolgan_kun'],
            'tugash_sana': t['tugash_sana'],
            'trend': t['trend'],
            'ishonch': t['ishonch'],
            'minimumdan_past': minimumdan_past,
        })

    # Eng shoshilinch (kam kun qolgan) birinchi; sotilmayotganlar (None) oxirida
    natija.sort(key=lambda x: (x['qolgan_kun'] is None, x['qolgan_kun'] if x['qolgan_kun'] is not None else 9999))
    return natija[:limit]


# ═══════════════════════════════════════════════════════════
#  PDF YASASH (reportlab + Arial — unicode/kirill uchun)
# ═══════════════════════════════════════════════════════════
_FONT_OK = False


def _shrift_royxatga():
    """Windows Arial shriftini reportlab'ga ulaymiz (bir marta)."""
    global _FONT_OK
    if _FONT_OK:
        return True
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import os
    yollar = [
        (r'C:\Windows\Fonts\arial.ttf', r'C:\Windows\Fonts\arialbd.ttf'),
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
    ]
    for oddiy, qalin in yollar:
        if os.path.exists(oddiy):
            pdfmetrics.registerFont(TTFont('AppFont', oddiy))
            pdfmetrics.registerFont(TTFont('AppFont-Bold', qalin if os.path.exists(qalin) else oddiy))
            _FONT_OK = True
            return True
    return False


def hisobot_pdf(data):
    """Kunlik hisobotni chiroyli PDF qilib bytes qaytaradi."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    bor = _shrift_royxatga()
    asosiy = 'AppFont' if bor else 'Helvetica'
    qalin = 'AppFont-Bold' if bor else 'Helvetica-Bold'

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=18 * mm, bottomMargin=16 * mm,
        leftMargin=16 * mm, rightMargin=16 * mm,
        title="Savdo hisoboti",
    )
    styles = getSampleStyleSheet()
    ACCENT = colors.HexColor('#3b6ef0')
    DARK = colors.HexColor('#0f172a')
    GREY = colors.HexColor('#64748b')

    h1 = ParagraphStyle('h1', parent=styles['Title'], fontName=qalin,
                        fontSize=20, textColor=DARK, spaceAfter=2)
    sub = ParagraphStyle('sub', parent=styles['Normal'], fontName=asosiy,
                         fontSize=10, textColor=GREY, spaceAfter=2)
    h2 = ParagraphStyle('h2', parent=styles['Heading2'], fontName=qalin,
                        fontSize=13, textColor=ACCENT, spaceBefore=10, spaceAfter=6)
    cell = ParagraphStyle('cell', parent=styles['Normal'], fontName=asosiy, fontSize=10)

    elems = []
    subtitle = data.get('subtitle') or data['sana'].strftime('%d.%m.%Y')
    elems.append(Paragraph("🧾 SAVDO HISOBOTI", h1))
    elems.append(Paragraph(f"{data['dokon_nomi']} · {subtitle}", sub))
    elems.append(Spacer(1, 8))

    # Asosiy ko'rsatkichlar — 2x2 karta
    kartalar = [
        ["Sof savdo", pul(data['jami_savdo']), "Kassaga tushgan", pul(data['kassaga_tushgan'])],
        ["Cheklar soni", str(data['chek_soni']), "Chegirma", pul(data['chegirma'])],
    ]
    if data.get('qaytarilgan'):
        kartalar.append(["Qaytarilgan", pul(data['qaytarilgan']),
                         "Yalpi savdo", pul(data.get('yalpi_savdo', 0))])
    t = Table(kartalar, colWidths=[38 * mm, 48 * mm, 38 * mm, 48 * mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), asosiy, 10),
        ('FONT', (0, 0), (0, -1), qalin, 10),
        ('FONT', (2, 0), (2, -1), qalin, 10),
        ('TEXTCOLOR', (0, 0), (0, -1), GREY),
        ('TEXTCOLOR', (2, 0), (2, -1), GREY),
        ('TEXTCOLOR', (1, 0), (1, -1), DARK),
        ('TEXTCOLOR', (3, 0), (3, -1), DARK),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5fb')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dbe3f0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dbe3f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elems.append(t)

    # To'lov turlari
    elems.append(Paragraph("To'lov turlari bo'yicha", h2))
    tolov = [
        ["💵 Naqd", pul(data['naqd'])],
        ["💳 Karta", pul(data['karta'])],
        ["📋 Qarz (nasiya)", pul(data['qarz'])],
    ]
    t2 = Table([["Tur", "Summa"]] + tolov, colWidths=[110 * mm, 62 * mm])
    t2.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), asosiy, 10),
        ('FONT', (0, 0), (-1, 0), qalin, 10),
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f6f8fc')]),
        ('LINEBELOW', (0, 0), (-1, -1), 0.4, colors.HexColor('#e2e8f0')),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elems.append(t2)

    # Top mahsulotlar
    elems.append(Paragraph("🏆 Eng ko'p sotilgan mahsulotlar", h2))
    if data['top']:
        satrlar = [["#", "Mahsulot", "Soni", "Summa"]]
        for i, m in enumerate(data['top'], 1):
            satrlar.append([
                str(i),
                Paragraph(str(m['mahsulot_nomi']), cell),
                str(m['jami_soni'] or 0),
                pul(m['summa']),
            ])
        t3 = Table(satrlar, colWidths=[10 * mm, 92 * mm, 24 * mm, 46 * mm])
        t3.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), asosiy, 9.5),
            ('FONT', (0, 0), (-1, 0), qalin, 10),
            ('BACKGROUND', (0, 0), (-1, 0), DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f6f8fc')]),
            ('LINEBELOW', (0, 0), (-1, -1), 0.4, colors.HexColor('#e2e8f0')),
            ('ALIGN', (2, 0), (3, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elems.append(t3)
    else:
        elems.append(Paragraph("Bu kunda savdo bo'lmagan.", cell))

    elems.append(Spacer(1, 16))
    izoh = ParagraphStyle('izoh', parent=styles['Normal'], fontName=asosiy,
                          fontSize=8.5, textColor=GREY, alignment=1)
    elems.append(Paragraph(
        f"Savdoyim tizimi tomonidan yaratildi · {timezone.localtime().strftime('%d.%m.%Y %H:%M')}",
        izoh))

    doc.build(elems)
    buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════════════
#  EXCEL YASASH (openpyxl)
# ═══════════════════════════════════════════════════════════
def hisobot_excel(data):
    """Kunlik hisobotni Excel (.xlsx) qilib bytes qaytaradi."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = Workbook()
    ws = wb.active
    ws.title = "Hisobot"

    ACCENT = "3B6EF0"
    DARK = "0F172A"
    oq = Font(color="FFFFFF", bold=True, size=11)
    qalin = Font(bold=True, size=11)
    markaz = Alignment(horizontal="center", vertical="center")
    ong = Alignment(horizontal="right")
    chegara = Border(bottom=Side(style="thin", color="E2E8F0"))

    subtitle = data.get('subtitle') or data['sana'].strftime('%d.%m.%Y')
    ws.merge_cells("A1:D1")
    ws["A1"] = f"SAVDO HISOBOTI — {data['dokon_nomi']} ({subtitle})"
    ws["A1"].font = Font(bold=True, size=14, color=DARK)
    ws.row_dimensions[1].height = 24

    # Asosiy ko'rsatkichlar
    korsatkich = [
        ("Sof savdo (qaytarish ayrilgan)", int(data['jami_savdo'] or 0)),
        ("Kassaga tushgan (naqd+karta)", int(data['kassaga_tushgan'] or 0)),
        ("Cheklar soni", int(data['chek_soni'] or 0)),
        ("Chegirma", int(data['chegirma'] or 0)),
        ("Qaytarilgan (refund)", int(data.get('qaytarilgan') or 0)),
        ("Naqd", int(data['naqd'] or 0)),
        ("Karta", int(data['karta'] or 0)),
        ("Qarz (nasiya)", int(data['qarz'] or 0)),
    ]
    r = 3
    ws[f"A{r}"] = "Ko'rsatkich"; ws[f"B{r}"] = "Qiymat"
    for c in ("A", "B"):
        ws[f"{c}{r}"].font = oq
        ws[f"{c}{r}"].fill = PatternFill("solid", fgColor=ACCENT)
    r += 1
    for nom, qiy in korsatkich:
        ws[f"A{r}"] = nom
        ws[f"B{r}"] = qiy
        ws[f"B{r}"].number_format = '# ##0'
        ws[f"A{r}"].border = chegara
        ws[f"B{r}"].border = chegara
        r += 1

    # Top mahsulotlar
    r += 1
    ws[f"A{r}"] = "Eng ko'p sotilgan mahsulotlar"
    ws[f"A{r}"].font = Font(bold=True, size=12, color=ACCENT)
    r += 1
    bosh = ["#", "Mahsulot", "Soni", "Summa"]
    for i, h in enumerate(bosh):
        c = ws.cell(row=r, column=1 + i, value=h)
        c.font = oq
        c.fill = PatternFill("solid", fgColor=DARK)
        c.alignment = markaz if i != 1 else Alignment(horizontal="left")
    r += 1
    for i, m in enumerate(data['top'], 1):
        ws.cell(row=r, column=1, value=i).alignment = markaz
        ws.cell(row=r, column=2, value=str(m['mahsulot_nomi']))
        ws.cell(row=r, column=3, value=int(m['jami_soni'] or 0)).alignment = markaz
        cc = ws.cell(row=r, column=4, value=int(m['summa'] or 0))
        cc.number_format = '# ##0'
        cc.alignment = ong
        r += 1

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 34
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 18

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
