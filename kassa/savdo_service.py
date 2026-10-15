# -*- coding: utf-8 -*-
"""Sotuv (savdo) va smena yadrosi — web view ham, REST API ham shu yerdan
foydalanadi (bitta manba). Barcha pul/ombor amallari atomik va poyga-himoyali."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db import transaction, IntegrityError
from django.db.models import F, Sum
from django.utils import timezone

from mahsulot.models import Mahsulot
from .models import SavdoChek, SavdoChekMahsulot, Kassa, QarzDaftar, Smena, Qaytarish

KASRLI_BIRLIKLAR = ('kg', 'litr', 'gramm', 'metr')


class SavdoXato(Exception):
    """Sotuvdagi validatsiya xatosi (xabar + HTTP kod)."""
    def __init__(self, message, code=400):
        self.message = message
        self.code = code
        super().__init__(message)


class _OmborYetarliEmas(Exception):
    """Atomik yozuv paytida qoldiq yetmay qolganda (poyga)."""
    def __init__(self, nomi):
        self.nomi = nomi
        super().__init__(nomi)


def _decimal(value, default='0'):
    try:
        return Decimal(str(value if value not in (None, '') else default))
    except (InvalidOperation, ValueError, TypeError):
        raise SavdoXato("Summa noto'g'ri kiritilgan")


def _miqdor(value, birlik='dona', default='0'):
    """dona/quti → butun; kg/litr → 3 xona; manfiy → 0."""
    try:
        d = Decimal(str(value if value not in (None, '') else default))
    except (InvalidOperation, ValueError, TypeError):
        raise SavdoXato("Miqdor noto'g'ri kiritilgan")
    if d < 0:
        d = Decimal('0')
    if (birlik or '').lower() in KASRLI_BIRLIKLAR:
        return d.quantize(Decimal('0.001'))
    return d.quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def _son(d):
    """Miqdorni chiroyli matn: 3.0→'3', 0.75→'0.75'."""
    try:
        d = Decimal(str(d))
    except (InvalidOperation, ValueError, TypeError):
        return str(d)
    if d == d.to_integral_value():
        return format(d.quantize(Decimal('1')), 'f')
    return format(d.normalize(), 'f')


def ochiq_smena(dokon):
    """Do'konning ochiq smenasi (yoki None)."""
    return Smena.objects.filter(dokon=dokon, holat='ochiq').order_by('-ochilgan').first()


def smena_och(dokon, sotuvchi, boshlangich=Decimal('0')):
    """Smena ochadi. Allaqachon ochiq bo'lsa — o'shani qaytaradi.
    DB constraint tufayli bir vaqtda ikkita ochiq smena bo'lmaydi."""
    mavjud = ochiq_smena(dokon)
    if mavjud:
        return mavjud, False
    if boshlangich is None or boshlangich < 0:
        boshlangich = Decimal('0')
    try:
        with transaction.atomic():
            smena = Smena.objects.create(
                dokon=dokon, sotuvchi=sotuvchi, boshlangich_naqd=boshlangich)
        return smena, True
    except IntegrityError:
        # Poyga — boshqa so'rov ochib ulgurdi
        return ochiq_smena(dokon), False


def smena_yop(dokon, real_naqd=None):
    """Ochiq smenani yopadi va yig'ma natijani (dict) qaytaradi.
    real_naqd berilsa naqd verka (kutilgan/farq) hisoblanadi. Ochiq smena
    bo'lmasa SavdoXato."""
    from .hisobot_service import _yig
    smena = ochiq_smena(dokon)
    if not smena:
        raise SavdoXato("Ochiq smena yo'q.", 400)

    smena.holat = 'yopiq'
    smena.yopilgan = timezone.now()
    smena.save(update_fields=['holat', 'yopilgan'])

    data = _yig(dokon, smena.ochilgan, smena.yopilgan)

    if real_naqd is not None:
        if real_naqd < 0:
            real_naqd = Decimal('0')
        naqd_qaytarilgan = Qaytarish.objects.filter(
            dokon=dokon, chek__tolash_turi='naqd',
            yaratilgan__gte=smena.ochilgan, yaratilgan__lt=smena.yopilgan,
        ).aggregate(s=Sum('summa'))['s'] or Decimal('0')
        # Smena davomida to'langan qarzlar ham kassa yashigiga naqd tushadi deb
        # hisoblanadi (qarz odatda naqd qaytariladi) — aks holda soxta "ortiqcha" chiqadi.
        qarz_naqd = QarzDaftar.objects.filter(
            dokon=dokon, to_langan=True,
            to_langan_sana__gte=smena.ochilgan, to_langan_sana__lt=smena.yopilgan,
        ).aggregate(s=Sum('summa'))['s'] or Decimal('0')
        kutilgan = ((smena.boshlangich_naqd or Decimal('0'))
                    + (data['naqd'] or Decimal('0')) + qarz_naqd - naqd_qaytarilgan)
        smena.real_naqd = real_naqd
        smena.kutilgan_naqd = kutilgan
        smena.naqd_farq = real_naqd - kutilgan
        smena.save(update_fields=['real_naqd', 'kutilgan_naqd', 'naqd_farq'])

    return smena, data


def chek_topish(dokon, q):
    """Chekni raqami (#123 yoki 123) yoki UUID token bo'yicha topadi."""
    import uuid as _uuid
    q = (q or '').lstrip('#').strip()
    if q.isdigit():
        c = SavdoChek.objects.filter(dokon=dokon, id=int(q)).first()
        if c:
            return c
    try:
        return SavdoChek.objects.filter(dokon=dokon, token=_uuid.UUID(q)).first()
    except (ValueError, AttributeError, TypeError):
        return None


def qarz_tolash_yadro(dokon, qarz_id):
    """Qarzni 'to'landi' qiladi va kassaga summani qo'shadi (atomik, idempotent).
    Qaytaradi: True (to'landi) yoki False (topilmadi/allaqachon to'langan)."""
    with transaction.atomic():
        yangilandi = QarzDaftar.objects.filter(
            id=qarz_id, dokon=dokon, to_langan=False
        ).update(to_langan=True, to_langan_sana=timezone.now())
        if not yangilandi:
            return False
        qarz = QarzDaftar.objects.get(id=qarz_id, dokon=dokon)
        Kassa.objects.get_or_create(dokon=dokon)
        Kassa.objects.filter(dokon=dokon).update(balans=F('balans') + qarz.summa)
    return True


def qaytarish_yarat(dokon, sotuvchi, chek, qatorlar, sabab='boshqa', izoh=''):
    """Chek bo'yicha tanlangan tovarlarni qaytaradi (refund).
    qatorlar: [{'cm_id':.., 'soni':..}, ...]. Tovar omborga qaytadi, pul kassadan
    (yoki to'lanmagan qarzdan) kamayadi. Qaytaradi: (qaytarish, jami_summa, kassadan)."""
    from .models import Qaytarish, QaytarishItem
    if sabab not in dict(Qaytarish.SABAB):
        sabab = 'boshqa'

    cm_map = {cm.id: cm for cm in chek.mahsulotlar.all()}

    # Avval cm_id bo'yicha sonlarni YIG'AMIZ — bitta so'rovda bir xil qator
    # ikki marta kelsa ham (takror), umumiy son bo'yicha tekshiriladi (over-refund yo'q).
    sonlar = {}
    for q in (qatorlar or []):
        try:
            cid = int(q.get('cm_id'))
        except (TypeError, ValueError):
            continue
        cm = cm_map.get(cid)
        if not cm:
            continue
        birlik = cm.mahsulot.birlik if cm.mahsulot_id else 'dona'
        soni = _miqdor(q.get('soni', 0), birlik)
        if soni > 0:
            sonlar[cid] = sonlar.get(cid, Decimal('0')) + soni

    tanlangan = []
    jami_summa = Decimal('0')
    for cid, soni in sonlar.items():
        cm = cm_map[cid]
        birlik = cm.mahsulot.birlik if cm.mahsulot_id else 'dona'
        qolgan = cm.qolgan_qaytarish
        if soni > qolgan:
            raise SavdoXato(
                f"{cm.mahsulot_nomi}: {_son(soni)} {birlik} qaytarib bo'lmaydi "
                f"(mumkin: {_son(qolgan)} {birlik}).", 400)
        satr_jami = cm.narx * soni
        tanlangan.append((cm, soni, satr_jami))
        jami_summa += satr_jami

    if not tanlangan:
        raise SavdoXato("Kamida bitta mahsulot va sonini tanlang.", 400)

    qarz = None
    kassadan = True
    if chek.tolash_turi == 'qarz':
        qarz = QarzDaftar.objects.filter(dokon=dokon, chek=chek).first()
        if qarz and not qarz.to_langan:
            kassadan = False

    with transaction.atomic():
        qaytarish = Qaytarish.objects.create(
            dokon=dokon, chek=chek, sotuvchi=sotuvchi,
            summa=jami_summa, sabab=sabab, izoh=izoh, kassadan=kassadan)
        for cm, soni, satr_jami in tanlangan:
            QaytarishItem.objects.create(
                qaytarish=qaytarish, chek_mahsulot=cm, mahsulot=cm.mahsulot,
                mahsulot_nomi=cm.mahsulot_nomi, soni=soni, narx=cm.narx, jami=satr_jami)
            if cm.mahsulot_id:
                Mahsulot.objects.filter(id=cm.mahsulot_id).update(soni=F('soni') + soni)
        if kassadan:
            Kassa.objects.get_or_create(dokon=dokon)
            Kassa.objects.filter(dokon=dokon).update(balans=F('balans') - jami_summa)
        elif qarz is not None:
            yangi = max(Decimal('0'), (qarz.summa or Decimal('0')) - jami_summa)
            qarz.summa = yangi
            if yangi == 0:
                qarz.to_langan = True
                qarz.to_langan_sana = timezone.now()
                qarz.save(update_fields=['summa', 'to_langan', 'to_langan_sana'])
            else:
                qarz.save(update_fields=['summa'])
    return qaytarish, jami_summa, kassadan


def chek_buyurtmadan(buyurtma, sotuvchi=None, tolash_turi='naqd'):
    """Olib ketilgan mijoz buyurtmasi uchun SAVDO CHEKI yaratadi (daromad + kassa).

    MUHIM: ombor buyurtma yaratilganda ALLAQACHON rezervlangan (kamaytirilgan) —
    shu yerda QAYTA kamaytirilmaydi (ikki marta kamayib ketmasligi uchun).
    Shu tufayli onlayn buyurtma ham hisobot/kassaга tushadi."""
    dokon = buyurtma.dokon
    jami = buyurtma.jami or Decimal('0')
    if tolash_turi not in ('naqd', 'karta', 'qarz'):
        tolash_turi = 'naqd'
    to_langan = jami if tolash_turi != 'qarz' else Decimal('0')
    with transaction.atomic():
        chek = SavdoChek.objects.create(
            dokon=dokon, sotuvchi=sotuvchi, jami=jami,
            to_langan=to_langan, tolash_turi=tolash_turi,
        )
        for it in buyurtma.itemlar.all():
            SavdoChekMahsulot.objects.create(
                chek=chek, mahsulot=it.mahsulot, mahsulot_nomi=it.mahsulot_nomi,
                soni=it.soni, narx=it.narx, jami=it.narx * it.soni,
            )
        if tolash_turi != 'qarz':
            Kassa.objects.get_or_create(dokon=dokon)
            Kassa.objects.filter(dokon=dokon).update(balans=F('balans') + to_langan)
    return chek


def savdo_yarat(dokon, sotuvchi, mahsulotlar_data, tolash_turi='naqd',
                chegirma=Decimal('0'), berilgan=Decimal('0'),
                mijoz_ism='', mijoz_telefon='', qaytarish_sana=None):
    """Bitta sotuvni ATOMIK yaratadi. mahsulotlar_data: [{'id':.., 'soni':..}, ...].

    Muvaffaqiyatda SavdoChek qaytaradi; xatoda SavdoXato ko'taradi.
    DIQQAT: ochiq smena borligini chaqiruvchi tekshirishi kerak."""
    if tolash_turi not in ('naqd', 'karta', 'qarz'):
        tolash_turi = 'naqd'
    if not mahsulotlar_data:
        raise SavdoXato('Mahsulot tanlang', 400)

    # Naqd va karta uchun chegirma yo'q (faqat qarzda)
    if tolash_turi != 'qarz':
        chegirma = Decimal('0')

    jami = Decimal('0')
    chek_items = []
    for item in mahsulotlar_data:
        try:
            mahsulot = Mahsulot.objects.get(id=item['id'], dokon=dokon)
            soni = _miqdor(item['soni'], mahsulot.birlik)
        except Mahsulot.DoesNotExist:
            raise SavdoXato(f"Mahsulot topilmadi: {item.get('id')}", 404)
        except (KeyError, TypeError):
            raise SavdoXato("Mahsulot ma'lumoti noto'g'ri", 400)
        if soni <= 0:
            raise SavdoXato("Mahsulot soni 0 dan katta bo'lishi kerak", 400)
        if mahsulot.muddati_otgan:
            raise SavdoXato(f"{mahsulot.nomi}: yaroqlilik muddati tugagan — sotib bo'lmaydi!", 400)
        if mahsulot.soni < soni:
            raise SavdoXato(f"{mahsulot.nomi} yetarli emas (qoldi: {_son(mahsulot.soni)})", 400)
        narx = mahsulot.narx
        jami += narx * soni
        chek_items.append((mahsulot, soni, narx))

    jami_chegirmali = max(Decimal('0'), jami - chegirma)
    to_langan = jami_chegirmali if tolash_turi != 'qarz' else Decimal('0')
    qaytim = (max(Decimal('0'), berilgan - jami_chegirmali)
              if tolash_turi == 'naqd' and berilgan > jami_chegirmali else Decimal('0'))

    try:
        with transaction.atomic():
            chek = SavdoChek.objects.create(
                dokon=dokon, sotuvchi=sotuvchi, jami=jami_chegirmali,
                chegirma=chegirma, to_langan=to_langan, qaytim=qaytim,
                tolash_turi=tolash_turi,
            )
            for mahsulot, soni, narx in chek_items:
                kamaydi = Mahsulot.objects.filter(
                    id=mahsulot.id, soni__gte=soni
                ).update(soni=F('soni') - soni)
                if not kamaydi:
                    raise _OmborYetarliEmas(mahsulot.nomi)
                SavdoChekMahsulot.objects.create(
                    chek=chek, mahsulot=mahsulot, mahsulot_nomi=mahsulot.nomi,
                    soni=soni, narx=narx, jami=soni * narx,
                )
            if tolash_turi != 'qarz':
                Kassa.objects.get_or_create(dokon=dokon)
                Kassa.objects.filter(dokon=dokon).update(balans=F('balans') + to_langan)
            else:
                QarzDaftar.objects.create(
                    dokon=dokon, mijoz_ism=mijoz_ism or "Noma'lum",
                    mijoz_telefon=mijoz_telefon, qaytarish_sana=qaytarish_sana,
                    chek=chek, summa=jami_chegirmali,
                )
    except _OmborYetarliEmas as e:
        raise SavdoXato(
            f"{e.nomi} yetarli emas — tovar boshqa mijozga sotilgan bo'lishi mumkin. "
            f"Savatni yangilang.", 409)
    return chek
