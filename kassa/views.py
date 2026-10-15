import json
from decimal import Decimal, InvalidOperation
from datetime import timedelta, date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, IntegrityError
from django.db.models import Sum, F
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from django.conf import settings
from .models import (Kassa, SavdoChek, SavdoChekMahsulot, QarzDaftar,
                     AvtoHisobotSozlama, Smena, Qaytarish, QaytarishItem)
from mahsulot.models import Mahsulot
from users.models import DokonEgasiProfil, TelegramLink

OY_NOMLARI = ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyn', 'Iyl', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek']
KUN_NOMLARI = ['Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh', 'Ya']


def _is_json_request(request):
    return request.content_type == 'application/json'


def _error_response(request, message, status=400):
    if _is_json_request(request):
        return JsonResponse({'error': message}, status=status)
    messages.error(request, message)
    return redirect('kassa')


def _decimal(value, default='0'):
    try:
        return Decimal(str(value if value not in (None, '') else default))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Summa noto'g'ri kiritilgan")


# Kasrli (tarozi) birliklar — kg/litr kabi. Bular 3 xonagacha kasr bo'la oladi.
KASRLI_BIRLIKLAR = ('kg', 'litr', 'gramm', 'metr')


def _miqdor(value, birlik='dona', default='0'):
    """Miqdorni Decimal qilib qaytaradi. dona/quti → butun songa yaxlitlanadi,
    kg/litr → 3 xonagacha (gramm aniqligi). Manfiy bo'lsa 0."""
    from decimal import ROUND_HALF_UP
    try:
        d = Decimal(str(value if value not in (None, '') else default))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Miqdor noto'g'ri kiritilgan")
    if d < 0:
        d = Decimal('0')
    if (birlik or '').lower() in KASRLI_BIRLIKLAR:
        return d.quantize(Decimal('0.001'))
    return d.quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def _son(d):
    """Miqdorni chiroyli matn qiladi: butun→'3', kasrli→'0.75' (ortiqcha 0 kesiladi)."""
    try:
        d = Decimal(str(d))
    except (InvalidOperation, ValueError, TypeError):
        return str(d)
    if d == d.to_integral_value():
        return format(d.quantize(Decimal('1')), 'f')
    return format(d.normalize(), 'f')


def _get_dokon(user):
    """Do'kon egasi yoki TASDIQLANGAN sotuvchining do'koni (yagona manba)."""
    from users.services import foydalanuvchi_dokoni
    return foydalanuvchi_dokoni(user)


def _egasi_dokoni(user):
    """Faqat DO'KON EGASI uchun do'kon (hisobot, eksport, AI, sozlamalar). Kassir -> None."""
    if getattr(user, 'rol', None) != 'dokon_egasi':
        return None
    return _get_dokon(user)


def _ochiq_smena(dokon):
    """Do'konning ochiq smenasini qaytaradi (yoki None)."""
    return Smena.objects.filter(dokon=dokon, holat='ochiq').order_by('-ochilgan').first()


def _telegramga_yubor(chat_id, matn):
    """Do'kon egasiga to'g'ridan-to'g'ri Telegram API orqali xabar yuboradi (bot jarayonisiz)."""
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    if not token or not chat_id:
        return
    try:
        import requests
        requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            data={'chat_id': chat_id, 'text': matn, 'parse_mode': 'HTML'},
            timeout=6,
        )
    except Exception:
        pass


def _cart_key(dokon):
    return f'kassa_savat_{dokon.id}'


def _get_cart(request, dokon):
    return request.session.get(_cart_key(dokon), {})


def _save_cart(request, dokon, cart):
    # Miqdorlar kasrli bo'lishi mumkin (kg/litr) — matn (string) sifatida saqlaymiz.
    cleaned = {}
    for product_id, qty in cart.items():
        try:
            d = Decimal(str(qty))
        except (TypeError, ValueError, InvalidOperation):
            continue
        if d > 0:
            # Ortiqcha nol/kasrsiz ko'rinishda saqlaymiz (masalan '3' yoki '0.75')
            cleaned[str(product_id)] = format(d.normalize(), 'f')
    request.session[_cart_key(dokon)] = cleaned
    request.session.modified = True


def _cart_items(dokon, cart):
    items = []
    total = Decimal('0')
    for product_id, qty in cart.items():
        try:
            product = Mahsulot.objects.get(id=product_id, dokon=dokon, faol=True)
        except Mahsulot.DoesNotExist:
            continue
        try:
            qty = _miqdor(qty, product.birlik)
        except ValueError:
            continue
        qty = min(qty, product.soni)
        if qty <= 0:
            continue
        subtotal = product.narx * qty
        total += subtotal
        items.append({'product': product, 'qty': qty, 'subtotal': subtotal})
    return items, total


HAFTA_KUNLARI = ['Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba',
                 'Juma', 'Shanba', 'Yakshanba']


def _hisobot_grafik(dokon, davr, bugun):
    """Hisobot sahifasidagi rangli grafik ma'lumotlarini tayyorlaydi.
    Qaytadi: (soat_data, kun_data, oy_data).

    Har bir davr uchun BITTA guruhlangan (GROUP BY) so'rov ishlatiladi —
    ilgari har soat/kun/oy uchun alohida so'rov ketardi (N+1)."""
    import calendar
    from django.db.models.functions import ExtractHour, TruncDate, ExtractMonth

    soat_data = []
    kun_data = []
    oy_data = []

    # Grafik SOF savdoni ko'rsatadi: har bo'lakdan o'sha bo'lakdagi
    # qaytarishlar (refund) ayriladi (0 dan pastga tushmaydi).
    def _sof(sotuv, qaytgan):
        return max(0.0, float(sotuv or 0) - float(qaytgan or 0))

    if davr == 'kunlik':
        # Bugungi savdo — soatlar bo'yicha bitta so'rovda guruhlab olamiz.
        xom = (
            SavdoChek.objects
            .filter(dokon=dokon, yaratilgan__date=bugun)
            .annotate(soat=ExtractHour('yaratilgan'))
            .values('soat')
            .annotate(s=Sum('jami'))
        )
        summa_by_soat = {r['soat']: float(r['s'] or 0) for r in xom}
        q_xom = (
            Qaytarish.objects
            .filter(dokon=dokon, yaratilgan__date=bugun)
            .annotate(soat=ExtractHour('yaratilgan'))
            .values('soat').annotate(s=Sum('summa'))
        )
        qaytgan_by_soat = {r['soat']: float(r['s'] or 0) for r in q_xom}
        for soat in range(24):
            soat_data.append({'soat': soat,
                              'summa': _sof(summa_by_soat.get(soat), qaytgan_by_soat.get(soat))})

    elif davr == 'haftalik':
        boshi = bugun - timedelta(days=6)
        xom = (
            SavdoChek.objects
            .filter(dokon=dokon, yaratilgan__date__gte=boshi,
                    yaratilgan__date__lte=bugun)
            .annotate(kun=TruncDate('yaratilgan'))
            .values('kun')
            .annotate(s=Sum('jami'))
        )
        summa_by_kun = {r['kun']: float(r['s'] or 0) for r in xom}
        q_xom = (
            Qaytarish.objects
            .filter(dokon=dokon, yaratilgan__date__gte=boshi, yaratilgan__date__lte=bugun)
            .annotate(kun=TruncDate('yaratilgan'))
            .values('kun').annotate(s=Sum('summa'))
        )
        qaytgan_by_kun = {r['kun']: float(r['s'] or 0) for r in q_xom}
        for i in range(6, -1, -1):
            kun = bugun - timedelta(days=i)
            kun_data.append({
                'nom': HAFTA_KUNLARI[kun.weekday()],
                'sana': kun.strftime('%d.%m'),
                'summa': _sof(summa_by_kun.get(kun), qaytgan_by_kun.get(kun)),
            })

    elif davr == 'oylik':
        _, kunlar_soni = calendar.monthrange(bugun.year, bugun.month)
        oy_boshi = date(bugun.year, bugun.month, 1)
        xom = (
            SavdoChek.objects
            .filter(dokon=dokon, yaratilgan__date__gte=oy_boshi,
                    yaratilgan__date__lte=bugun)
            .annotate(kun=TruncDate('yaratilgan'))
            .values('kun')
            .annotate(s=Sum('jami'))
        )
        summa_by_kun = {r['kun']: float(r['s'] or 0) for r in xom}
        q_xom = (
            Qaytarish.objects
            .filter(dokon=dokon, yaratilgan__date__gte=oy_boshi, yaratilgan__date__lte=bugun)
            .annotate(kun=TruncDate('yaratilgan'))
            .values('kun').annotate(s=Sum('summa'))
        )
        qaytgan_by_kun = {r['kun']: float(r['s'] or 0) for r in q_xom}
        for kun_raqam in range(1, kunlar_soni + 1):
            kun = date(bugun.year, bugun.month, kun_raqam)
            summa = _sof(summa_by_kun.get(kun), qaytgan_by_kun.get(kun)) if kun <= bugun else 0
            kun_data.append({
                'kun': kun_raqam,
                'sana': kun.strftime('%d.%m'),
                'summa': summa,
            })

    elif davr == 'yillik':
        yil_boshi = date(bugun.year, 1, 1)
        xom = (
            SavdoChek.objects
            .filter(dokon=dokon, yaratilgan__date__gte=yil_boshi,
                    yaratilgan__date__lte=bugun)
            .annotate(oy=ExtractMonth('yaratilgan'))
            .values('oy')
            .annotate(s=Sum('jami'))
        )
        summa_by_oy = {r['oy']: float(r['s'] or 0) for r in xom}
        q_xom = (
            Qaytarish.objects
            .filter(dokon=dokon, yaratilgan__date__gte=yil_boshi, yaratilgan__date__lte=bugun)
            .annotate(oy=ExtractMonth('yaratilgan'))
            .values('oy').annotate(s=Sum('summa'))
        )
        qaytgan_by_oy = {r['oy']: float(r['s'] or 0) for r in q_xom}
        summa_by_oy = {oy: _sof(summa_by_oy.get(oy), qaytgan_by_oy.get(oy))
                       for oy in set(summa_by_oy) | set(qaytgan_by_oy)}
        for oy in range(1, 13):
            bosh = date(bugun.year, oy, 1)
            summa = summa_by_oy.get(oy, 0.0) if bosh <= bugun else 0
            # Ustun balandligi: 30 mln = to'la (100%), 15 mln = yarim (50%)
            foiz = min(round(summa / 30_000_000 * 100, 1), 100)
            mln = round(summa / 1_000_000, 1)  # yorliq uchun (masalan 15.0 mln)
            oy_data.append({'nom': OY_NOMLARI[oy - 1], 'summa': summa,
                            'foiz': foiz, 'mln': mln})

    return soat_data, kun_data, oy_data


@login_required
def kassa_view(request):
    dokon = _get_dokon(request.user)
    if not dokon:
        return redirect('login')
    kassa, _ = Kassa.objects.get_or_create(dokon=dokon)
    mahsulotlar = Mahsulot.objects.filter(dokon=dokon, faol=True, soni__gt=0)
    cart = _get_cart(request, dokon)
    cart_items, cart_total = _cart_items(dokon, cart)
    return render(request, 'kassa/kassa.html', {
        'kassa': kassa,
        'mahsulotlar': mahsulotlar,
        'cart_items': cart_items,
        'cart_total': cart_total,
        'smena': _ochiq_smena(dokon),
    })


@login_required
@require_POST
def smena_ochish(request):
    dokon = _get_dokon(request.user)
    if not dokon:
        return redirect('login')
    if not _ochiq_smena(dokon):
        try:
            boshlangich = _decimal(request.POST.get('boshlangich_naqd', 0))
            if boshlangich < 0:
                boshlangich = Decimal('0')
        except ValueError:
            boshlangich = Decimal('0')
        try:
            with transaction.atomic():
                Smena.objects.create(dokon=dokon, sotuvchi=request.user,
                                     boshlangich_naqd=boshlangich)
        except IntegrityError:
            # Ikki so'rov bir vaqtda kelgan (tez ketma-ket bosish) —
            # DB constraint ikkinchisini rad etdi, allaqachon ochiq smena bor.
            messages.info(request, "Smena allaqachon ochiq.")
            return redirect('kassa')
        if boshlangich:
            messages.success(request, f"✅ Smena ochildi. Boshlang'ich naqd: {boshlangich:,.0f} UZS.")
        else:
            messages.success(request, "✅ Smena ochildi. Endi sotishingiz mumkin.")
    return redirect('kassa')


@login_required
@require_POST
def smena_yopish(request):
    dokon = _get_dokon(request.user)
    if not dokon:
        return redirect('login')
    smena = _ochiq_smena(dokon)
    if not smena:
        messages.error(request, "Ochiq smena yo'q.")
        return redirect('kassa')

    # Kassir real sanagan naqd (ixtiyoriy) — verka uchun
    real_naqd = None
    real_naqd_raw = str(request.POST.get('real_naqd', '') or '').strip()
    if real_naqd_raw != '':
        try:
            real_naqd = _decimal(real_naqd_raw)
        except ValueError:
            real_naqd = None

    # Yopish + verka — YAGONA manba (savdo_service.smena_yop): API bilan bir xil hisob,
    # smena davomida naqd to'langan qarzlar ham kutilgan naqdga qo'shiladi.
    from .savdo_service import smena_yop, SavdoXato
    try:
        smena, data = smena_yop(dokon, real_naqd=real_naqd)
    except SavdoXato as e:
        messages.error(request, e.message)
        return redirect('kassa')

    from .hisobot_service import pul
    from django.utils.html import escape as _esc
    sotuvchi = smena.sotuvchi.first_name if smena.sotuvchi and smena.sotuvchi.first_name         else (smena.sotuvchi.username if smena.sotuvchi else '—')
    davomiylik = smena.yopilgan - smena.ochilgan
    soat = int(davomiylik.total_seconds() // 3600)
    daqiqa = int((davomiylik.total_seconds() % 3600) // 60)

    # Sotuvchining o'rtacha reytingi (mijozlar bahosi)
    reyting_qatori = None
    if smena.sotuvchi:
        from users.models import Reyting
        from django.db.models import Avg, Count
        agg = Reyting.objects.filter(baholanuvchi=smena.sotuvchi).aggregate(
            o=Avg('yulduz'), n=Count('id'))
        if agg['n']:
            ort = round(agg['o'], 1)
            reyting_qatori = f"⭐ Reyting: <b>{ort}/5</b> ({agg['n']} ta baho)"

    matn = [
        "🔒 <b>Smena yopildi</b>",
        f"🏪 {_esc(dokon.dokon_nomi)}",
        f"👤 Sotuvchi: <b>{_esc(sotuvchi)}</b>",
    ]
    if reyting_qatori:
        matn.append(reyting_qatori)
    matn += [
        f"🕐 {timezone.localtime(smena.ochilgan):%d.%m %H:%M} — "
        f"{timezone.localtime(smena.yopilgan):%H:%M} ({soat}s {daqiqa}d)",
        "",
        f"💰 Sof savdo: <b>{pul(data['jami_savdo'])}</b>",
        f"🏦 Kassaga tushgan: <b>{pul(data['kassaga_tushgan'])}</b>",
        f"🧾 Cheklar: <b>{data['chek_soni']} ta</b>",
        f"💵 Naqd: {pul(data['naqd'])} · 💳 Karta: {pul(data['karta'])} · 📋 Qarz: {pul(data['qarz'])}",
    ]
    if data.get('qaytarilgan'):
        matn.append(f"↩️ Qaytarilgan: <b>{pul(data['qaytarilgan'])}</b>")

    # ── Pul verkasi (Z-hisobot) ──
    if smena.real_naqd is not None and smena.naqd_farq is not None:
        matn += [
            "",
            "🧮 <b>Naqd verka:</b>",
            f"  Kutilgan: {pul(smena.kutilgan_naqd)} · Sanaldi: {pul(smena.real_naqd)}",
        ]
        if smena.naqd_farq == 0:
            matn.append("  ✅ Farq yo'q — kassa to'g'ri")
        elif smena.naqd_farq < 0:
            matn.append(f"  ⛔ Kamomad: <b>{pul(abs(smena.naqd_farq))}</b>")
        else:
            matn.append(f"  ⚠️ Ortiqcha: <b>{pul(smena.naqd_farq)}</b>")

    if data['top']:
        matn.append("\n🏆 <b>Eng ko'p sotilgan:</b>")
        for i, mm in enumerate(data['top'][:5], 1):
            matn.append(f"  {i}. {_esc(mm['nomi'])} — {mm['jami_soni']} dona · {pul(mm['summa'])}")

    # Do'kon egasiga Telegramга yuboramiz
    link = TelegramLink.objects.filter(foydalanuvchi=dokon.foydalanuvchi).first()
    if link:
        _telegramga_yubor(link.chat_id, "\n".join(matn))

    # Sotuvchining o'ziga ham natijani ko'rsatamiz (shaxsiy smena hisoboti)
    natija = {
        'sotuvchi': sotuvchi,
        'dokon_nomi': dokon.dokon_nomi,
        'ochilgan': smena.ochilgan,
        'yopilgan': smena.yopilgan,
        'davomiylik': f"{soat}s {daqiqa}d",
        'jami_savdo': data['jami_savdo'],
        'kassaga_tushgan': data['kassaga_tushgan'],
        'qaytarilgan': data.get('qaytarilgan') or 0,
        'chek_soni': data['chek_soni'],
        'naqd': data['naqd'],
        'karta': data['karta'],
        'qarz': data['qarz'],
        'top': data['top'][:5],
        'reyting': (round(agg['o'], 1) if smena.sotuvchi and agg['n'] else None),
        'reyting_n': (agg['n'] if smena.sotuvchi else 0),
        # Pul verkasi
        'boshlangich_naqd': smena.boshlangich_naqd,
        'real_naqd': smena.real_naqd,
        'kutilgan_naqd': smena.kutilgan_naqd,
        'naqd_farq': smena.naqd_farq,
        'verka_holati': smena.verka_holati,
    }
    return render(request, 'kassa/smena_natija.html', {'natija': natija})


@login_required
@require_POST
def savat_action(request):
    dokon = _get_dokon(request.user)
    if not dokon:
        return redirect('login')
    cart = _get_cart(request, dokon)
    action = request.POST.get('action')
    product_id = request.POST.get('product_id')
    if action == 'clear':
        _save_cart(request, dokon, {})
        return redirect('kassa')
    if not product_id:
        return redirect('kassa')
    try:
        product = Mahsulot.objects.get(id=product_id, dokon=dokon, faol=True)
    except Mahsulot.DoesNotExist:
        return redirect('kassa')
    # Smena ochiq bo'lmasa — sotib bo'lmaydi
    if action in ['add', 'inc'] and not _ochiq_smena(dokon):
        messages.error(request, "Smena yopiq. Sotishni boshlash uchun avval smenani oching.")
        return redirect('kassa')

    # Yaroqlilik muddati o'tgan mahsulotni savatga qo'shib bo'lmaydi
    if action in ['add', 'inc'] and product.muddati_otgan:
        messages.error(request, f"{product.nomi}: yaroqlilik muddati tugagan — sotib bo'lmaydi!")
        return redirect('kassa')

    current = _miqdor(cart.get(str(product.id), '0'), product.birlik)
    # Bosishda qo'shiladigan qadam: dona uchun 1, kg/litr uchun ham 1 (aniq
    # og'irlikни "son yozish" (set) orqali kiritiladi, masalan 0.75).
    qadam = Decimal('1')
    if action in ['add', 'inc']:
        if current < product.soni:
            cart[str(product.id)] = min(current + qadam, product.soni)
        else:
            # Ombordagi soni tugagan — ko'proq qo'shib bo'lmaydi (#6)
            if product.soni <= 0:
                messages.warning(request, f"⚠️ {product.nomi}: omborda qolmagan!")
            else:
                messages.warning(
                    request,
                    f"⚠️ {product.nomi}: omborda faqat {_son(product.soni)} {product.birlik} bor — "
                    f"hammasi savatда, ko'proq qo'shib bo'lmaydi."
                )
    elif action == 'dec':
        yangi = current - qadam
        if yangi <= 0:
            cart.pop(str(product.id), None)
        else:
            cart[str(product.id)] = yangi
    elif action == 'del':
        cart.pop(str(product.id), None)
    elif action == 'set':
        # Karobka/tarozi: bir yo'la N dona yoki N.NN kg qo'yish
        if not _ochiq_smena(dokon):
            messages.error(request, "Smena yopiq. Avval smenani oching.")
            return redirect('kassa')
        if product.muddati_otgan:
            messages.error(request, f"{product.nomi}: yaroqlilik muddati tugagan!")
            return redirect('kassa')
        try:
            yangi = _miqdor(request.POST.get('soni', '1'), product.birlik, default='1')
        except ValueError:
            yangi = Decimal('1')
        if yangi <= 0:
            cart.pop(str(product.id), None)
        elif yangi > product.soni:
            cart[str(product.id)] = product.soni
            messages.warning(
                request,
                f"⚠️ {product.nomi}: omborda faqat {_son(product.soni)} {product.birlik} bor — "
                f"shuncha qo'shildi."
            )
        else:
            cart[str(product.id)] = yangi
    _save_cart(request, dokon, cart)
    return redirect('kassa')


@login_required
@require_POST
def kassa_skan(request):
    """Kameradan kelgan barkod bo'yicha mahsulotni topib, savatga qo'shadi.
    JSON qaytaradi (kassa sahifasi kamera-skaneri uchun)."""
    dokon = _get_dokon(request.user)
    if not dokon:
        return JsonResponse({'error': "Ruxsat yo'q"}, status=403)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'JSON xato'}, status=400)

    if not _ochiq_smena(dokon):
        return JsonResponse({'error': "Smena yopiq. Avval smenani oching.", 'smena_yopiq': True}, status=400)

    barkod = (data.get('barkod') or '').strip()
    if not barkod:
        return JsonResponse({'error': "Barkod bo'sh"}, status=400)

    try:
        m = Mahsulot.objects.get(barkod=barkod, dokon=dokon, faol=True)
    except Mahsulot.DoesNotExist:
        return JsonResponse({'error': f"Barkod topilmadi: {barkod}", 'topilmadi': True}, status=404)

    # Yaroqlilik muddati o'tgan bo'lsa — sotib bo'lmaydi, savatga qo'shilmaydi
    if m.muddati_otgan:
        return JsonResponse({
            'error': f"{m.nomi}: yaroqlilik muddati tugagan ({m.yaroqlilik_muddati:%d.%m.%Y}) — sotib bo'lmaydi!",
            'muddati_otgan': True,
        }, status=400)

    cart = _get_cart(request, dokon)
    current = _miqdor(cart.get(str(m.id), '0'), m.birlik)
    qoshildi = False
    if current < m.soni:
        cart[str(m.id)] = min(current + Decimal('1'), m.soni)
        qoshildi = True
    _save_cart(request, dokon, cart)
    _, total = _cart_items(dokon, cart)
    cart = _get_cart(request, dokon)  # normallashtirilgan holatni qayta o'qiymiz

    return JsonResponse({
        'ok': True,
        'id': m.id,
        'nomi': m.nomi,
        'narx': float(m.narx),
        'birlik': m.birlik,
        'soni_qoldi': float(m.soni),
        'savatda': cart.get(str(m.id), '0'),
        'qoshildi': qoshildi,           # False -> ombordagi soni tugagan
        'cart_total': float(total),
        'cart_count': len(cart),
    })


@login_required
@require_POST
def savdo_qilish(request):
    dokon = _get_dokon(request.user)
    if not dokon:
        return _error_response(request, "Ruxsat yo'q", 403)

    if not _ochiq_smena(dokon):
        return _error_response(request, "Smena yopiq. Sotishni yakunlash uchun smena ochiq bo'lishi kerak.", 400)

    if _is_json_request(request):
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({'error': 'JSON xato'}, status=400)
        mahsulotlar_data = data.get('mahsulotlar', [])
    else:
        data = request.POST
        cart = _get_cart(request, dokon)
        mahsulotlar_data = [{'id': pid, 'soni': qty} for pid, qty in cart.items()]

    tolash_turi = data.get('tolash_turi', 'naqd')

    try:
        chegirma = _decimal(data.get('chegirma', 0))
        berilgan = _decimal(data.get('berilgan', 0))
    except ValueError as e:
        return _error_response(request, str(e), 400)

    # Naqd va karta uchun mijoz ma'lumotlari saqlanmaydi
    if tolash_turi == 'qarz':
        mijoz_ism = data.get('mijoz_ism', '')
        mijoz_telefon = data.get('mijoz_telefon', '')
        qaytarish_sana = (data.get('qaytarish_sana', '') or '').strip() or None
    else:
        mijoz_ism = ''
        mijoz_telefon = ''
        qaytarish_sana = None

    # Naqd va karta uchun chegirma yo'q
    if tolash_turi != 'qarz':
        chegirma = Decimal('0')

    if not mahsulotlar_data:
        return _error_response(request, 'Mahsulot tanlang', 400)

    # ── Sotuv yadrosi savdo_service'da (web + API bitta manbadan) ──
    from .savdo_service import savdo_yarat, SavdoXato
    try:
        chek = savdo_yarat(
            dokon, request.user, mahsulotlar_data, tolash_turi=tolash_turi,
            chegirma=chegirma, berilgan=berilgan, mijoz_ism=mijoz_ism,
            mijoz_telefon=mijoz_telefon, qaytarish_sana=qaytarish_sana,
        )
    except SavdoXato as e:
        return _error_response(request, e.message, e.code)

    qaytim = chek.qaytim

    if _is_json_request(request):
        return JsonResponse({
            'status': 'ok', 'chek_id': chek.id,
            'jami': float(chek.jami), 'qaytim': float(qaytim),
            'chek_url': request.build_absolute_uri(
                reverse('chek_korish', args=[chek.token])),
        })

    _save_cart(request, dokon, {})
    messages.success(request, f"Savdo yakunlandi. Qaytim: {qaytim:,.0f} UZS")
    return redirect('chek_korish', token=chek.token)


def _qr_data_uri(matn):
    """Matnni QR kod PNG (data URI) qilib qaytaradi.
    qrcode/PIL o'rnatilmagan bo'lsa — chek sahifasi 500 bermasin, QR'siz ochilsin."""
    try:
        import io, base64
        import qrcode
        img = qrcode.make(matn)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def chek_korish(request, token):
    """Ochiq (login talab qilmaydigan) raqamli chek sahifasi. QR shu sahifaga ishora qiladi."""
    chek = get_object_or_404(SavdoChek, token=token)
    items = chek.mahsulotlar.all()
    chek_url = request.build_absolute_uri(reverse('chek_korish', args=[chek.token]))
    qr = _qr_data_uri(chek_url)
    return render(request, 'kassa/chek.html', {
        'chek': chek,
        'items': items,
        'qr': qr,
        'chek_url': chek_url,
    })


# ══════════════════════════════════════════════════════════════
#  MAHSULOT QAYTARISH (REFUND)
# ══════════════════════════════════════════════════════════════
@login_required
def qaytarish_view(request):
    """Qaytarish sahifasi: chekni raqami bo'yicha topib, tovarlarni qaytarish.
    ?q= bilan chek qidiriladi; qidiruvsiz — so'nggi qaytarishlar ro'yxati."""
    dokon = _get_dokon(request.user)
    if not dokon:
        return redirect('login')

    q = (request.GET.get('q') or '').strip()
    chek = None
    qatorlar = []
    xato = None
    if q:
        # Chek raqami (#123) yoki token bo'yicha qidiramiz
        chek = _chek_topish(dokon, q)
        if not chek:
            xato = f"“{q}” bo'yicha chek topilmadi. Chek raqamini tekshiring."
        else:
            for cm in chek.mahsulotlar.all():
                qatorlar.append({'cm': cm, 'qolgan': cm.qolgan_qaytarish})

    oxirgi = (Qaytarish.objects
              .filter(dokon=dokon)
              .select_related('chek', 'sotuvchi')
              .prefetch_related('mahsulotlar')[:20])

    return render(request, 'kassa/qaytarish.html', {
        'q': q,
        'chek': chek,
        'qatorlar': qatorlar,
        'xato': xato,
        'oxirgi': oxirgi,
        'sabablar': Qaytarish.SABAB,
    })


def _chek_topish(dokon, q):
    """Chekni raqami (#123 yoki 123) yoki UUID token bo'yicha topadi."""
    q = q.lstrip('#').strip()
    # Avval ID sifatida
    if q.isdigit():
        chek = SavdoChek.objects.filter(dokon=dokon, id=int(q)).first()
        if chek:
            return chek
    # So'ng token (UUID) sifatida
    try:
        import uuid as _uuid
        return SavdoChek.objects.filter(dokon=dokon, token=_uuid.UUID(q)).first()
    except (ValueError, AttributeError, TypeError):
        return None


@login_required
@require_POST
def qaytarish_qil(request):
    """Tanlangan tovarlarni qaytaradi: ombor +, kassa −, audit yozuvi."""
    dokon = _get_dokon(request.user)
    if not dokon:
        return _error_response(request, "Ruxsat yo'q", 403)

    chek_id = request.POST.get('chek_id')
    chek = SavdoChek.objects.filter(dokon=dokon, id=chek_id).first()
    if not chek:
        messages.error(request, "Chek topilmadi.")
        return redirect('qaytarish')

    sabab = request.POST.get('sabab', 'boshqa')
    izoh = (request.POST.get('izoh') or '').strip()

    # Har qator uchun POST'dagi qty_<cm.id> ni yig'ib, servisga beramiz
    qatorlar = [{'cm_id': cm.id, 'soni': request.POST.get(f'qty_{cm.id}', '0')}
                for cm in chek.mahsulotlar.all()]

    from .savdo_service import qaytarish_yarat, SavdoXato
    try:
        _, jami_summa, kassadan = qaytarish_yarat(
            dokon, request.user, chek, qatorlar, sabab=sabab, izoh=izoh)
    except SavdoXato as e:
        messages.error(request, e.message)
        return redirect(f"{reverse('qaytarish')}?q={chek.id}")

    manba = "kassadan" if kassadan else "qarzdan"
    from users.services import AuditService
    AuditService.log(request.user, 'qaytarish', chek, f"{jami_summa} UZS {manba}", request)
    messages.success(
        request,
        f"✅ {jami_summa:,.0f} UZS qaytarildi ({manba}). Tovar omborga qaytdi.")
    return redirect(f"{reverse('qaytarish')}?q={chek.id}")


@login_required
def qarz_royxat(request):
    dokon = _get_dokon(request.user)
    if not dokon:
        return redirect('login')
    qarzlar = QarzDaftar.objects.filter(dokon=dokon).order_by('-yaratilgan')
    from .hisobot_service import qarz_eslatma
    eslatma = qarz_eslatma(dokon)
    return render(request, 'kassa/qarzlar.html', {
        'qarzlar': qarzlar,
        'bugun': timezone.localdate(),
        'dokon_nomi': dokon.dokon_nomi,
        'eslatma': eslatma,
    })


@login_required
def sotuvchilar_kpi(request):
    """Do'kon sotuvchilarining KPI reytingi — bugungi va oylik savdo, cheklar, baho."""
    dokon = _egasi_dokoni(request.user)
    if not dokon:
        return redirect('login')
    from django.db.models import Sum, Count, Avg
    from users.models import Reyting, CustomUser
    bugun = timezone.localdate()
    oy_boshi = bugun.replace(day=1)

    def _agg(dan):
        return {r['sotuvchi']: r for r in (
            SavdoChek.objects
            .filter(dokon=dokon, sotuvchi__isnull=False, yaratilgan__date__gte=dan)
            .values('sotuvchi').annotate(savdo=Sum('jami'), cheklar=Count('id')))}

    kun = _agg(bugun)
    oy = _agg(oy_boshi)
    ids = set(kun) | set(oy)
    userlar = {u.id: u for u in CustomUser.objects.filter(id__in=ids)}
    reyting = {r['baholanuvchi']: r for r in (
        Reyting.objects.filter(baholanuvchi_id__in=ids)
        .values('baholanuvchi').annotate(o=Avg('yulduz'), n=Count('id')))}

    qatorlar = []
    for uid in ids:
        u = userlar.get(uid)
        if not u:
            continue
        k, o = kun.get(uid, {}), oy.get(uid, {})
        rt = reyting.get(uid)
        qatorlar.append({
            'ism': u.first_name or u.username,
            'kun_savdo': k.get('savdo') or 0, 'kun_cheklar': k.get('cheklar') or 0,
            'oy_savdo': o.get('savdo') or 0, 'oy_cheklar': o.get('cheklar') or 0,
            'reyting': (round(rt['o'], 1) if rt and rt['n'] else None),
            'reyting_n': (rt['n'] if rt else 0),
        })
    qatorlar.sort(key=lambda x: x['oy_savdo'], reverse=True)
    return render(request, 'kassa/sotuvchilar_kpi.html', {
        'qatorlar': qatorlar, 'bugun': bugun,
    })


@login_required
@require_POST
def qarz_tolash(request, qarz_id):
    dokon = _get_dokon(request.user)
    if not dokon:
        return JsonResponse({'error': "Ruxsat yo'q"}, status=403)
    from .savdo_service import qarz_tolash_yadro
    if qarz_tolash_yadro(dokon, qarz_id):
        from users.services import AuditService
        AuditService.log(request.user, 'qarz_tolandi', None, f"qarz #{qarz_id}", request)
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': "Topilmadi yoki allaqachon to'langan"}, status=404)


@login_required
def hisobot_view(request):
    dokon = _egasi_dokoni(request.user)
    if not dokon:
        return redirect('login')

    davr = request.GET.get('davr', 'kunlik')
    bugun = timezone.localdate()

    # Boshlanish sanasi
    if davr == 'kunlik':
        boshlanish = bugun
    elif davr == 'haftalik':
        boshlanish = bugun - timedelta(days=6)
    elif davr == 'oylik':
        boshlanish = bugun.replace(day=1)
    elif davr == 'yillik':
        boshlanish = bugun.replace(month=1, day=1)
    else:
        boshlanish = bugun

    cheklar = SavdoChek.objects.filter(
        dokon=dokon, yaratilgan__date__gte=boshlanish
    ).select_related('sotuvchi').order_by('-yaratilgan')

    jami_savdo = cheklar.aggregate(s=Sum('jami'))['s'] or 0
    jami_son = cheklar.count()

    eng_sotilgan = (
        SavdoChekMahsulot.objects
        .filter(chek__dokon=dokon, chek__yaratilgan__date__gte=boshlanish)
        .values('mahsulot_nomi')
        .annotate(jami_soni=Sum('soni'), jami_summa=Sum('jami'))
        .order_by('-jami_soni')[:10]
    )

    kassa, _ = Kassa.objects.get_or_create(dokon=dokon)

    # ── Rangli statistika ma'lumotlari (soat/kun/oy grafiklari) ──
    soat_data, kun_data, oy_data = _hisobot_grafik(dokon, davr, bugun)

    # ── O'lik tovar tahlili (30 kunda sotilmagan, pul bog'lab turgan) ──
    from .hisobot_service import olik_tovarlar
    olik = olik_tovarlar(dokon, kunlar=30)
    olik_jami_qiymat = sum(x['qiymat'] for x in olik)

    avto, _ = AvtoHisobotSozlama.objects.get_or_create(dokon=dokon)

    from ai.services import mavjud as _ai_mavjud

    return render(request, 'kassa/hisobot.html', {
        'davr': davr,
        'ai_yoqmi': _ai_mavjud(),
        'jami_savdo': jami_savdo,
        'jami_son': jami_son,
        'eng_sotilgan': eng_sotilgan,
        'kassa': kassa,
        'cheklar': cheklar[:20],
        'soat_data': soat_data,
        'kun_data': kun_data,
        'oy_data': oy_data,
        'avto': avto,
        'olik': olik,
        'olik_jami_qiymat': olik_jami_qiymat,
    })


@login_required
@require_POST
def avto_hisobot_saqlash(request):
    """Hisobot sahifasidagi 'avtomatik yuborish vaqti' sozlamasini saqlaydi."""
    dokon = _egasi_dokoni(request.user)
    if not dokon:
        return redirect('login')
    from datetime import datetime as _dt

    def _vaqt(qiymat, default):
        try:
            return _dt.strptime((qiymat or '').strip(), '%H:%M').time()
        except (ValueError, TypeError):
            return default

    s, _ = AvtoHisobotSozlama.objects.get_or_create(dokon=dokon)

    eski_kunlik_vaqt = s.kunlik_vaqt
    eski_ombor_vaqt = s.ombor_vaqt

    s.kunlik_yoq = request.POST.get('kunlik_yoq') == 'on'
    s.ombor_yoq = request.POST.get('ombor_yoq') == 'on'
    s.kunlik_vaqt = _vaqt(request.POST.get('kunlik_vaqt'), s.kunlik_vaqt)
    s.ombor_vaqt = _vaqt(request.POST.get('ombor_vaqt'), s.ombor_vaqt)

    # Vaqt o'zgargan bo'lsa — "bugun yuborilgan" belgisini tozalaymiz,
    # aks holda yangi vaqtga qo'yilsa ham bugun qayta kelmaydi.
    if s.kunlik_vaqt != eski_kunlik_vaqt:
        s.oxirgi_kunlik = None
    if s.ombor_vaqt != eski_ombor_vaqt:
        s.oxirgi_ombor = None

    s.save()
    messages.success(request, "✅ Avtomatik hisobot sozlamalari saqlandi.")
    return redirect('hisobot')


# ═══════════════════════════════════════════════════════════
#  HISOBOT EKSPORT — PDF / Excel
# ═══════════════════════════════════════════════════════════
def _davr_oraligi(davr, bugun):
    """Tanlangan davr uchun (boshlanish, tugash, sarlavha)."""
    if davr == 'haftalik':
        return bugun - timedelta(days=6), bugun, 'Haftalik'
    if davr == 'oylik':
        return bugun.replace(day=1), bugun, 'Oylik'
    if davr == 'yillik':
        return bugun.replace(month=1, day=1), bugun, 'Yillik'
    return bugun, bugun, 'Kunlik'


@login_required
def hisobot_export(request, fmt):
    """Hisobotni PDF yoki Excel qilib yuklab beradi.
    ?davr=kunlik|haftalik|oylik|yillik  yoki  ?sana=YYYY-MM-DD"""
    from django.http import HttpResponse, Http404
    from .hisobot_service import davr_hisobot, kunlik_hisobot, hisobot_pdf, hisobot_excel

    dokon = _egasi_dokoni(request.user)
    if not dokon:
        return redirect('login')

    bugun = timezone.localdate()
    sana_param = request.GET.get('sana')
    if sana_param:
        try:
            kun = date.fromisoformat(sana_param)
        except ValueError:
            kun = bugun
        data = kunlik_hisobot(dokon, kun)
        nom_sana = kun.isoformat()
    else:
        davr = request.GET.get('davr', 'kunlik')
        boshi, tugash, sarlavha = _davr_oraligi(davr, bugun)
        data = davr_hisobot(dokon, boshi, tugash, sarlavha)
        nom_sana = f"{davr}_{tugash.isoformat()}"

    if fmt == 'pdf':
        buf = hisobot_pdf(data)
        resp = HttpResponse(buf.getvalue(), content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="hisobot_{nom_sana}.pdf"'
        return resp
    elif fmt in ('excel', 'xlsx'):
        buf = hisobot_excel(data)
        resp = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp['Content-Disposition'] = f'attachment; filename="hisobot_{nom_sana}.xlsx"'
        return resp
    raise Http404("Noma'lum format")


# ═══════════════════════════════════════════════════════════
#  AI HISOBOT YORDAMCHISI
#  - ai_tahlil: hisobotni avtomatik tahlil (nega shunday + nima qilish)
#  - ai_chat:   cheklangan chat (faqat hisobot bo'yicha savol)
# ═══════════════════════════════════════════════════════════
_DAVRLAR = ('kunlik', 'haftalik', 'oylik', 'yillik')


AI_KUNLIK_LIMIT = 30   # bir do'kon uchun kuniga AI so'rovlari (pullik API xarajatini cheklaydi)


def _ai_limit_ok(dokon):
    from django.core.cache import cache
    kalit = f"ai_limit:{dokon.pk}:{timezone.localdate().isoformat()}"
    soni = cache.get(kalit, 0)
    if soni >= AI_KUNLIK_LIMIT:
        return False
    cache.set(kalit, soni + 1, 24 * 3600)
    return True


def _davr_tozala(qiymat):
    return qiymat if qiymat in _DAVRLAR else 'oylik'


@login_required
@require_POST
def ai_tahlil(request):
    """Joriy davr hisobotini AI orqali tahlil qiladi (JSON)."""
    dokon = _egasi_dokoni(request.user)
    if not dokon:
        return JsonResponse({'ok': False, 'xato': 'Do\'kon topilmadi.'}, status=403)

    if not _ai_limit_ok(dokon):
        return JsonResponse({'ok': False, 'xato': "Bugungi AI so'rovlar limiti tugadi. Ertaga qayta urinib ko'ring."}, status=429)
    from ai.services import hisobot_tahlil
    davr = _davr_tozala(request.GET.get('davr') or request.POST.get('davr'))
    natija = hisobot_tahlil(dokon, davr)
    return JsonResponse(natija, status=200 if natija['ok'] else 400)


@login_required
@require_POST
def ai_chat(request):
    """Cheklangan chat: do'kon egasi faqat hisoboti bo'yicha savol beradi (JSON)."""
    dokon = _egasi_dokoni(request.user)
    if not dokon:
        return JsonResponse({'ok': False, 'xato': 'Do\'kon topilmadi.'}, status=403)

    if not _ai_limit_ok(dokon):
        return JsonResponse({'ok': False, 'xato': "Bugungi AI so'rovlar limiti tugadi. Ertaga qayta urinib ko'ring."}, status=429)

    if _is_json_request(request):
        try:
            data = json.loads(request.body or '{}')
        except (ValueError, TypeError):
            data = {}
        savol = (data.get('savol') or '').strip()
        davr = _davr_tozala(data.get('davr'))
    else:
        savol = (request.POST.get('savol') or '').strip()
        davr = _davr_tozala(request.POST.get('davr'))

    if not savol:
        return JsonResponse({'ok': False, 'xato': 'Savol bo\'sh.'}, status=400)
    if len(savol) > 500:
        savol = savol[:500]

    from ai.services import savol_javob
    natija = savol_javob(dokon, savol, davr)
    return JsonResponse(natija, status=200 if natija['ok'] else 400)