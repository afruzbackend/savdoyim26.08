# -*- coding: utf-8 -*-
"""Bepul "AI agent" — qoidalar asosidagi anomaliya aniqlash.
LLM/pul kerak emas: mavjud ma'lumotni tekshirib, muammolarni topadi.
Dashboardда ko'rsatiladi va Telegram botга yuboriladi.
"""
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum


def anomaliyalar(dokon):
    """Do'kon uchun ogohlantirishlar ro'yxatini qaytaradi.
    Har biri: {'daraja': 'red|orange|blue', 'ikon': emoji, 'matn': str}."""
    from mahsulot.models import Mahsulot
    from kassa.models import QarzDaftar, SavdoChekMahsulot

    natija = []
    hozir = timezone.now()
    bugun = timezone.localdate()
    mahsulotlar = list(Mahsulot.objects.filter(dokon=dokon))

    # 1) Tugagan (0 dona)
    tugagan = [m for m in mahsulotlar if m.soni <= 0 and m.faol]
    if tugagan:
        nomlar = ', '.join(m.nomi for m in tugagan[:3])
        qoshimcha = f" va yana {len(tugagan) - 3} ta" if len(tugagan) > 3 else ""
        natija.append({'daraja': 'red', 'ikon': '🔴',
                       'matn': f"{len(tugagan)} ta mahsulot tugagan: {nomlar}{qoshimcha}"})

    # 2) Kam qolgan (minimumdan past, lekin 0 emas)
    kam = [m for m in mahsulotlar if 0 < m.soni <= m.minimum_son]
    if kam:
        nomlar = ', '.join(f"{m.nomi} ({m.soni})" for m in kam[:3])
        qoshimcha = f" va yana {len(kam) - 3} ta" if len(kam) > 3 else ""
        natija.append({'daraja': 'orange', 'ikon': '🟠',
                       'matn': f"{len(kam)} ta mahsulot kam qoldi: {nomlar}{qoshimcha}"})

    # 3) Muddati o'tgan
    otgan = [m for m in mahsulotlar if m.muddati_otgan]
    if otgan:
        nomlar = ', '.join(m.nomi for m in otgan[:3])
        natija.append({'daraja': 'red', 'ikon': '⛔',
                       'matn': f"{len(otgan)} ta mahsulotning muddati o'tgan — sotib bo'lmaydi: {nomlar}"})

    # 4) Muddati tez tugayapti (7 kun)
    tugayapti = [m for m in mahsulotlar if m.muddati_tugayapti]
    if tugayapti:
        nomlar = ', '.join(m.nomi for m in tugayapti[:3])
        natija.append({'daraja': 'orange', 'ikon': '⏳',
                       'matn': f"{len(tugayapti)} ta mahsulot muddati 7 kunda tugaydi: {nomlar}"})

    # 5) To'lanmagan qarz (jami katta bo'lsa)
    qarz = QarzDaftar.objects.filter(dokon=dokon, to_langan=False).aggregate(
        s=Sum('summa'))['s'] or 0
    qarz_soni = QarzDaftar.objects.filter(dokon=dokon, to_langan=False).count()
    if qarz and qarz >= 500000:  # 500 ming so'mdan oshsa
        natija.append({'daraja': 'orange', 'ikon': '📋',
                       'matn': f"To'lanmagan qarz: {int(qarz):,} so'm ({qarz_soni} ta mijoz)".replace(',', ' ')})

    # 6) O'lik mahsulot — 30 kunda umuman sotilmagan (zaxira bor)
    oy_oldin = hozir - timedelta(days=30)
    sotilgan_ids = set(SavdoChekMahsulot.objects.filter(
        chek__dokon=dokon, chek__yaratilgan__gte=oy_oldin, mahsulot__isnull=False
    ).values_list('mahsulot_id', flat=True))
    olik = [m for m in mahsulotlar if m.soni > 0 and m.faol and m.id not in sotilgan_ids]
    if len(olik) >= 3:  # kamida 3 ta bo'lsa xabar beramiz
        natija.append({'daraja': 'blue', 'ikon': '💤',
                       'matn': f"{len(olik)} ta mahsulot 30 kunda umuman sotilmadi (o'lik zaxira)"})

    return natija


def anomaliya_matn(dokon):
    """Telegram bot uchun matnli hisobot (yoki None — muammo yo'q)."""
    lst = anomaliyalar(dokon)
    if not lst:
        return None
    q = [f"🤖 <b>Ogohlantirish — {dokon.dokon_nomi}</b>", ""]
    for a in lst:
        q.append(f"{a['ikon']} {a['matn']}")
    q.append("\n💡 Tavsiya: 🔴/⛔ belgililariga zudlik bilan e'tibor bering.")
    return "\n".join(q)
