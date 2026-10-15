import json
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from .models import (
    Buyurtma, BuyurtmaMahsulot, YetkazishBuyurtma,
    MijozBuyurtma, Savat, SavatItem,
)
from .services import OrderService, sotuvchi_dokoni
from users.models import ZavodProfil, DokonEgasiProfil
from users.services import ServiceError, json_ok, json_err
from mahsulot.models import Mahsulot


def _req_data(request):
    """JSON yoki form POST — bir xil dict qaytaradi."""
    if request.content_type and 'json' in request.content_type:
        try:
            return json.loads(request.body)
        except Exception:
            return {}
    return request.POST


def _decimal(value, default='0'):
    try:
        return Decimal(str(value if value not in (None, '') else default))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Narx noto'g'ri kiritilgan")


def _get_dokon(user):
    if user.rol == 'dokon_egasi':
        try:
            return user.dokon_profil
        except DokonEgasiProfil.DoesNotExist:
            return None
    return None


# ═══════════════════════════════════════════════
#  B2B BUYURTMA (do'kon -> zavod) — mavjud oqim
# ═══════════════════════════════════════════════
@login_required
def buyurtmalar_royxat(request):
    user = request.user
    if user.rol == 'dokon_egasi':
        dokon = _get_dokon(user)
        buyurtmalar = Buyurtma.objects.filter(dokon=dokon).select_related('dokon', 'zavod').order_by('-yaratilgan') if dokon else []
    elif user.rol == 'zavod':
        try:
            buyurtmalar = Buyurtma.objects.filter(zavod=user.zavod_profil).select_related('dokon', 'zavod').order_by('-yaratilgan')
        except Exception:
            buyurtmalar = []
    elif user.rol == 'yetkazib_beruvchi':
        try:
            buyurtmalar = Buyurtma.objects.filter(
                yetkazish__yetkazuvchi=user.yetkazuvchi_profil
            ).select_related('dokon', 'zavod').order_by('-yaratilgan')
        except Exception:
            buyurtmalar = []
    else:
        buyurtmalar = []
    return render(request, 'buyurtma/royxat.html', {'buyurtmalar': buyurtmalar})


@login_required
def buyurtma_berish(request):
    if request.user.rol != 'dokon_egasi':
        return redirect('login')
    zavodlar = ZavodProfil.objects.filter(tasdiqlangan=True)
    return render(request, 'buyurtma/berish.html', {'zavodlar': zavodlar})


@login_required
@require_POST
def buyurtma_yuborish(request):
    if request.user.rol != 'dokon_egasi':
        return JsonResponse({'error': "Ruxsat yo'q"}, status=403)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'JSON xato'}, status=400)
    zavod_id = data.get('zavod_id')
    mahsulotlar = data.get('mahsulotlar', [])
    izoh = data.get('izoh', '')
    if not mahsulotlar:
        return JsonResponse({'error': 'Mahsulot tanlang'}, status=400)
    try:
        zavod = ZavodProfil.objects.get(id=zavod_id)
    except ZavodProfil.DoesNotExist:
        return JsonResponse({'error': 'Zavod topilmadi'}, status=404)
    dokon = _get_dokon(request.user)
    if not dokon:
        return JsonResponse({'error': 'Dokon topilmadi'}, status=404)
    buyurtma = Buyurtma.objects.create(dokon=dokon, zavod=zavod, izoh=izoh)
    jami = Decimal('0')
    for item in mahsulotlar:
        try:
            nomi = item.get('nomi', '').strip()
            soni = _decimal(item.get('soni', 1), default='1')
            narx = _decimal(item.get('narx', 0))
        except (ValueError, AttributeError) as e:
            return JsonResponse({'error': str(e)}, status=400)
        if soni <= 0:
            return JsonResponse({'error': "Mahsulot soni 0 dan katta bo'lishi kerak"}, status=400)
        m = Mahsulot.objects.filter(id=item.get('id')).first() if item.get('id') else None
        if m:
            nomi = m.nomi
            narx = m.narx
        if not nomi:
            return JsonResponse({'error': 'Mahsulot nomi kerak'}, status=400)
        BuyurtmaMahsulot.objects.create(
            buyurtma=buyurtma, mahsulot=m, mahsulot_nomi=nomi, soni=soni, narx=narx,
        )
        jami += narx * soni
    buyurtma.jami = jami
    buyurtma.save(update_fields=['jami'])
    return JsonResponse({'status': 'ok', 'buyurtma_id': buyurtma.id})


@login_required
@require_POST
def buyurtma_holat(request, buyurtma_id):
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'JSON xato'}, status=400)
    holat = data.get('holat')
    user = request.user
    if holat not in dict(Buyurtma.HOLAT):
        return JsonResponse({'error': "Noto'g'ri holat"}, status=400)
    try:
        if user.rol == 'zavod':
            b = Buyurtma.objects.get(id=buyurtma_id, zavod=user.zavod_profil)
        elif user.rol == 'yetkazib_beruvchi':
            b = Buyurtma.objects.get(id=buyurtma_id, yetkazish__yetkazuvchi=user.yetkazuvchi_profil)
        elif user.rol == 'dokon_egasi':
            b = Buyurtma.objects.get(id=buyurtma_id, dokon=_get_dokon(user))
        else:
            return JsonResponse({'error': "Ruxsat yo'q"}, status=403)

        # Holat faqat ketma-ket oldinga siljisin; 'bekor' esa yakunlanmagan
        # buyurtma uchun istalgan paytda mumkin. Orqaga/sakrash taqiqlanadi.
        OQIM = ['yangi', 'qabul_qilindi', 'tayyorlanmoqda', 'yolda', 'yetkazildi']
        if holat == 'bekor':
            if b.holat in ('yetkazildi', 'bekor'):
                return JsonResponse({'error': "Buyurtma yakuniy holatda."}, status=400)
        elif (b.holat not in OQIM or holat not in OQIM
              or OQIM.index(holat) != OQIM.index(b.holat) + 1):
            return JsonResponse(
                {'error': "Holatni faqat ketma-ket oldinga o'tkazish mumkin."}, status=400)

        b.holat = holat
        b.save(update_fields=['holat'])
        return JsonResponse({'status': 'ok'})
    except Buyurtma.DoesNotExist:
        return JsonResponse({'error': 'Topilmadi'}, status=404)


# ═══════════════════════════════════════════════
#  MIJOZ SAVATI + BUYURTMA (thin views -> OrderService)
# ═══════════════════════════════════════════════
def _savat(user):
    savat, _ = Savat.objects.get_or_create(mijoz=user)
    return savat


@login_required
@require_POST
def savatga_qoshish(request):
    data = _req_data(request)
    mahsulot = get_object_or_404(Mahsulot, id=data.get('mahsulot_id'), faol=True)
    if mahsulot.soni <= 0:
        return json_err("Bu mahsulot hozir mavjud emas.", status=400)
    # Kasrli (kg/litr) mahsulot uchun kasrli miqdor, dona uchun butun son
    qoldiq = mahsulot.soni if mahsulot.kasrli else int(mahsulot.soni)
    try:
        soni = _decimal(data.get('soni', 1), default='1')
        if not mahsulot.kasrli:
            soni = Decimal(int(soni))
        if soni <= 0:
            soni = Decimal('1')
    except (ValueError, InvalidOperation):
        soni = Decimal('1')
    savat = _savat(request.user)
    item, created = SavatItem.objects.get_or_create(
        savat=savat, mahsulot=mahsulot, defaults={'soni': min(soni, qoldiq)})
    if not created:
        item.soni += soni
        item.save(update_fields=['soni'])
    # Savatdagi soni ombordagidan oshmasin (ortiqcha buyurtmani oldini oladi)
    if item.soni > qoldiq:
        item.soni = qoldiq
        item.save(update_fields=['soni'])
        birlik_txt = mahsulot.birlik if mahsulot.kasrli else 'dona'
        return json_ok(
            f"Omborda faqat {qoldiq} {birlik_txt} bor — shuncha qo'shildi.",
            {'savat_soni': str(savat.soni)})
    return json_ok("Savatga qo'shildi.", {'savat_soni': str(savat.soni)})


@login_required
@require_POST
def savat_yangilash(request):
    savat = _savat(request.user)
    item = get_object_or_404(SavatItem, id=request.POST.get('item_id'), savat=savat)
    try:
        soni = _decimal(request.POST.get('soni', 1), default='1')
        if item.mahsulot and not item.mahsulot.kasrli:
            soni = Decimal(int(soni))
    except (ValueError, InvalidOperation):
        soni = Decimal('1')
    # Savatdagi soni ombordan oshmasin (ortiqcha buyurtmani oldini oladi)
    if item.mahsulot and soni > item.mahsulot.soni:
        soni = item.mahsulot.soni
    if soni <= 0:
        item.delete()
    else:
        item.soni = soni
        item.save(update_fields=['soni'])
    return redirect('savat')


@login_required
def savat_korish(request):
    savat = _savat(request.user)
    itemlar = savat.itemlar.select_related('mahsulot', 'mahsulot__dokon')
    return render(request, 'buyurtma/savat.html', {'savat': savat, 'itemlar': itemlar})


@login_required
@require_POST
def buyurtma_checkout(request):
    try:
        buyurtmalar = OrderService.create_from_cart(request.user, request)
    except ServiceError as e:
        return json_err(e.message, e.errors, e.code)
    return json_ok("Buyurtma qabul qilindi.", {'buyurtma_ids': [b.id for b in buyurtmalar]}, status=201)


@login_required
@require_POST
def tez_buyurtma(request):
    data = _req_data(request)
    mahsulot = get_object_or_404(Mahsulot, id=data.get('mahsulot_id'), faol=True)
    if not mahsulot.dokon:
        return json_err("Mahsulot do'koni topilmadi.", status=400)
    try:
        soni = _decimal(data.get('soni', 1), default='1')
        if not mahsulot.kasrli:
            soni = Decimal(int(soni))
        if soni <= 0:
            soni = Decimal('1')
    except (ValueError, InvalidOperation):
        soni = Decimal('1')
    try:
        b = OrderService.create(request.user, mahsulot.dokon, [(mahsulot, soni)], request)
    except ServiceError as e:
        return json_err(e.message, e.errors, e.code)
    return json_ok("Buyurtma qabul qilindi.", {'buyurtma_id': b.id}, status=201)


@login_required
def mijoz_buyurtmalarim(request):
    from mahsulot.models import MahsulotSharh
    qs = (MijozBuyurtma.objects
          .filter(mijoz=request.user)
          .prefetch_related('itemlar', 'itemlar__mahsulot', 'tarix'))
    page = Paginator(qs, 10).get_page(request.GET.get('page'))
    sharh_yozilgan = set(
        MahsulotSharh.objects.filter(foydalanuvchi=request.user)
        .values_list('mahsulot_id', flat=True))
    return render(request, 'buyurtma/mening_buyurtmalarim.html', {
        'page_obj': page, 'buyurtmalar': page.object_list, 'sharh_yozilgan': sharh_yozilgan,
    })


@login_required
def sotuvchi_mijoz_buyurtmalar(request):
    dokon = sotuvchi_dokoni(request.user)
    if not dokon:
        return redirect('login')
    qs = (MijozBuyurtma.objects.filter(dokon=dokon)
          .select_related('mijoz').prefetch_related('itemlar'))
    holat = request.GET.get('holat')
    if holat in dict(MijozBuyurtma.HOLAT):
        qs = qs.filter(holat=holat)
    page = Paginator(qs, 12).get_page(request.GET.get('page'))
    return render(request, 'buyurtma/dokon_buyurtmalari.html', {
        'page_obj': page, 'buyurtmalar': page.object_list,
        'tanlangan_holat': holat or '', 'filtr_holatlar': MijozBuyurtma.HOLAT,
    })


@login_required
def sodiqlik_sahifa(request):
    """Mijozning sodiqlik ballari — balans, daraja, tarix, qoidalar."""
    from users.models import MijozProfil
    from .models import SodiqlikTarix
    from .services import BALL_QIYMATI, BALL_TOPISH_NARXI
    profil = MijozProfil.objects.filter(foydalanuvchi=request.user).first()
    ball = profil.sodiqlik_ball if profil else 0
    return render(request, 'buyurtma/sodiqlik.html', {
        'ball': ball,
        'ball_qiymati': ball * BALL_QIYMATI,
        'daraja': profil.daraja if profil else None,
        'tarix': SodiqlikTarix.objects.filter(mijoz=request.user)[:50],
        'ball_qiymati_birlik': BALL_QIYMATI,
        'ball_topish_narxi': BALL_TOPISH_NARXI,
    })


@login_required
@require_POST
def qayta_buyurtma(request, buyurtma_id):
    """Oldingi buyurtmadagi mahsulotlarni qayta savatga qo'shadi (reorder)."""
    buyurtma = get_object_or_404(MijozBuyurtma, id=buyurtma_id, mijoz=request.user)
    savat = _savat(request.user)
    qoshildi, mavjud_emas = 0, 0
    for it in buyurtma.itemlar.all():
        m = it.mahsulot
        if not m or not m.faol or m.soni <= 0:
            mavjud_emas += 1
            continue
        item, created = SavatItem.objects.get_or_create(
            savat=savat, mahsulot=m, defaults={'soni': min(it.soni, m.soni)})
        if not created:
            item.soni += it.soni
            item.save(update_fields=['soni'])
        # Savatdagi soni ombordan oshmasin
        if item.soni > m.soni:
            item.soni = m.soni
            item.save(update_fields=['soni'])
        qoshildi += 1
    if qoshildi == 0:
        return json_err("Bu buyurtmadagi mahsulotlar hozir mavjud emas.", status=400)
    msg = f"{qoshildi} ta mahsulot savatga qo'shildi."
    if mavjud_emas:
        msg += f" ({mavjud_emas} tasi hozir yo'q)"
    return json_ok(msg, {'savat_soni': savat.soni})


@login_required
@require_POST
def mijoz_buyurtma_holat(request, buyurtma_id):
    buyurtma = get_object_or_404(MijozBuyurtma, id=buyurtma_id)
    target = _req_data(request).get('holat')
    try:
        if target == 'bekor':
            OrderService.cancel(buyurtma, request.user, request)
        else:
            OrderService.advance_status(buyurtma, request.user, target, request)
    except ServiceError as e:
        return json_err(e.message, e.errors, e.code)
    return json_ok("Status yangilandi.", {
        'holat': buyurtma.holat,
        'holat_nomi': buyurtma.get_holat_display(),
        'keyingi': buyurtma.keyingi_holat(),
    })
