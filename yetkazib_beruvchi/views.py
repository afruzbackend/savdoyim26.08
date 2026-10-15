import json
from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import F

from .models import Jonatma, JonatmaMahsulot, YetkazuvchiSorov
from users.models import YetkazibBeruvchiProfil, ZavodProfil
from mahsulot.models import Mahsulot


def _get_yetkazuvchi(user):
    try:
        return user.yetkazuvchi_profil
    except YetkazibBeruvchiProfil.DoesNotExist:
        return None


def _get_zavod(user):
    try:
        return user.zavod_profil
    except ZavodProfil.DoesNotExist:
        return None


# ─── YETKAZUVCHI ─────────────────────────────────────────────────────────────

@login_required
def yetkazuvchi_dashboard(request):
    profil = _get_yetkazuvchi(request.user)
    if not profil:
        return redirect('login')

    jonatmalar = (Jonatma.objects.filter(yetkazuvchi=profil)
                  .select_related('zavod', 'manzil_dokon')
                  .prefetch_related('mahsulotlar__mahsulot__dokon')
                  .order_by('-yaratilgan'))

    # Kunlik hisobot + reyting
    from django.db.models import Sum, Count, Avg
    from django.utils import timezone
    from users.models import Reyting
    bugun = timezone.localdate()
    bugun_yetkazildi = Jonatma.objects.filter(
        yetkazuvchi=profil, holat='yetkazildi', yangilangan__date=bugun)
    kun_stat = bugun_yetkazildi.aggregate(n=Count('id'), summa=Sum('jami_summa'))
    faol_soni = Jonatma.objects.filter(
        yetkazuvchi=profil, holat__in=['qabul_qilindi', 'yolda']).count()

    reyting_agg = Reyting.objects.filter(baholanuvchi=request.user).aggregate(
        o=Avg('yulduz'), n=Count('id'))

    return render(request, 'yetkazib_beruvchi/dashboard.html', {
        'profil': profil,
        'jonatmalar': jonatmalar,
        'kun_yetkazildi': kun_stat['n'] or 0,
        'kun_daromad': kun_stat['summa'] or 0,
        'faol_soni': faol_soni,
        'reyting': (round(reyting_agg['o'], 1) if reyting_agg['n'] else None),
        'reyting_n': reyting_agg['n'] or 0,
    })


@login_required
def yetkazuvchi_jonatmalar(request):
    """Jo'natmalar ro'yxati — rol bo'yicha:
    yetkazuvchi o'ziga biriktirilganlarni, zavod esa o'z jo'natmalarini ko'radi.
    (Bitta URL /jonatmalar/ ikkala rol uchun ishlaydi.)"""
    yetkazuvchi = _get_yetkazuvchi(request.user)
    zavod = _get_zavod(request.user)
    if yetkazuvchi:
        profil = yetkazuvchi
        jonatmalar = Jonatma.objects.filter(yetkazuvchi=yetkazuvchi)
    elif zavod:
        profil = zavod
        jonatmalar = Jonatma.objects.filter(zavod=zavod)
    else:
        return redirect('login')

    jonatmalar = jonatmalar.prefetch_related('mahsulotlar').order_by('-yaratilgan')

    return render(request, 'yetkazib_beruvchi/jonatmalar_royxat.html', {
        'profil': profil,
        'jonatmalar': jonatmalar,
    })


def _jonatma_push(j):
    """Jo'natma holati o'zgarganda manzil do'koni egasiga Telegram xabar yuboradi."""
    try:
        from kassa.views import _telegramga_yubor
        from users.models import TelegramLink
        dokon = j._manba_dokon()
        if not dokon:
            return
        link = TelegramLink.objects.filter(foydalanuvchi=dokon.foydalanuvchi).first()
        if not link:
            return
        zavod_nomi = j.zavod.zavod_nomi if j.zavod else ''
        if j.holat == 'yolda':
            matn = (f"🚚 <b>Jo'natmangiz yo'lda!</b>\n#{j.id} · {zavod_nomi}\n"
                    f"Yetkazuvchi yo'lga chiqdi — tez orada yetkaziladi.")
        elif j.holat == 'yetkazildi':
            matn = (f"✅ <b>Jo'natma yetkazildi!</b>\n#{j.id} · {zavod_nomi}\n"
                    f"Mahsulotlarni qabul qilib oling.")
        else:
            return
        _telegramga_yubor(link.chat_id, matn)
    except Exception:
        pass


@login_required
@require_POST
def jonatma_qabul(request, jonatma_id):
    """Yetkazuvchi jo'natmani qabul qiladi"""
    profil = _get_yetkazuvchi(request.user)
    if not profil:
        return JsonResponse({'error': "Ruxsat yo'q"}, status=403)

    try:
        j = Jonatma.objects.get(id=jonatma_id, yetkazuvchi=profil, holat='qabul_kutilmoqda')
    except Jonatma.DoesNotExist:
        return JsonResponse({'error': "Jo'natma topilmadi"}, status=404)

    j.holat = 'qabul_qilindi'
    j.save(update_fields=['holat'])
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def jonatma_holat(request, jonatma_id):
    """Holat o'zgartirish: yolda / yetkazildi"""
    profil = _get_yetkazuvchi(request.user)
    if not profil:
        return JsonResponse({'error': "Ruxsat yo'q"}, status=403)

    try:
        data = json.loads(request.body)
        holat = data.get('holat')
    except Exception:
        return JsonResponse({'error': 'JSON xato'}, status=400)

    ruxsat = ['yolda', 'yetkazildi']
    if holat not in ruxsat:
        return JsonResponse({'error': "Noto'g'ri holat"}, status=400)

    try:
        j = Jonatma.objects.get(id=jonatma_id, yetkazuvchi=profil)
    except Jonatma.DoesNotExist:
        return JsonResponse({'error': "Jo'natma topilmadi"}, status=404)

    # Holat faqat ketma-ket oldinga siljisin (orqaga yoki sakrash yo'q):
    #   qabul_qilindi -> yolda -> yetkazildi
    OQIM = ['qabul_kutilmoqda', 'qabul_qilindi', 'yolda', 'yetkazildi']
    if j.holat not in OQIM or OQIM.index(holat) != OQIM.index(j.holat) + 1:
        return JsonResponse(
            {'error': "Holatni faqat ketma-ket oldinga o'tkazish mumkin."}, status=400)

    j.holat = holat
    j.save(update_fields=['holat'])
    _jonatma_push(j)   # manzil do'koni egasiga Telegram xabar (yolda/yetkazildi)

    resp = {'status': 'ok'}
    if holat == 'yetkazildi':
        # Do'kon skaner qilishi uchun QR kod (jo'natma barkodini kodlaydi)
        from kassa.views import _qr_data_uri
        resp['qr'] = _qr_data_uri(j.barkod)
        resp['barkod'] = j.barkod
    return JsonResponse(resp)


@login_required
def jonatma_qr(request, jonatma_id):
    """Yetkazilgan jo'natma QR kodini qaytaradi (do'kon skaner qilishi uchun)."""
    profil = _get_yetkazuvchi(request.user)
    if not profil:
        return JsonResponse({'error': "Ruxsat yo'q"}, status=403)
    j = Jonatma.objects.filter(id=jonatma_id, yetkazuvchi=profil).first()
    if not j:
        return JsonResponse({'error': "Jo'natma topilmadi"}, status=404)
    from kassa.views import _qr_data_uri
    return JsonResponse({'status': 'ok', 'qr': _qr_data_uri(j.barkod), 'barkod': j.barkod})


@login_required
@require_POST
def barkod_qabul(request):
    """Barkod orqali jo'natmani topib qabul qilish"""
    profil = _get_yetkazuvchi(request.user)
    if not profil:
        return JsonResponse({'error': "Ruxsat yo'q"}, status=403)

    try:
        data = json.loads(request.body)
        barkod = data.get('barkod', '').strip().upper()
    except Exception:
        return JsonResponse({'error': 'JSON xato'}, status=400)

    if not barkod:
        return JsonResponse({'error': 'Barkod kiritilmadi'}, status=400)

    try:
        j = Jonatma.objects.get(barkod=barkod)
    except Jonatma.DoesNotExist:
        return JsonResponse({'error': 'Barkod topilmadi'}, status=404)

    if j.holat not in ['qabul_kutilmoqda']:
        return JsonResponse({'error': f"Holat: {j.get_holat_display()}"}, status=400)

    # Jo'natma allaqachon boshqa yetkazuvchiga tayinlangan bo'lsa — egallab bo'lmaydi.
    if j.yetkazuvchi_id and j.yetkazuvchi_id != profil.id:
        return JsonResponse(
            {'error': "Bu jo'natma boshqa yetkazuvchiga tayinlangan."}, status=403)

    j.yetkazuvchi = profil
    j.holat = 'qabul_qilindi'
    j.save(update_fields=['yetkazuvchi', 'holat'])

    return JsonResponse({
        'status': 'ok',
        'xabar': f"Jo'natma #{j.id} qabul qilindi!"
    })


@login_required
def zavod_sorov_yuborish(request):
    """Yetkazuvchi zavodga so'rov yuboradi"""
    profil = _get_yetkazuvchi(request.user)
    if not profil:
        return redirect('login')

    zavodlar = ZavodProfil.objects.filter(tasdiqlangan=True)
    mening_sorovlarim = YetkazuvchiSorov.objects.filter(
        yetkazuvchi=profil
    ).select_related('zavod')

    if request.method == 'POST':
        zavod_id = request.POST.get('zavod_id')
        try:
            zavod = ZavodProfil.objects.get(id=zavod_id, tasdiqlangan=True)
        except ZavodProfil.DoesNotExist:
            from django.contrib import messages
            messages.error(request, "Zavod topilmadi!")
            return redirect('zavod_sorov_yuborish')

        sorov, created = YetkazuvchiSorov.objects.get_or_create(
            yetkazuvchi=profil,
            zavod=zavod,
            defaults={'holat': 'kutilmoqda'}
        )
        from django.contrib import messages
        if created:
            messages.success(request, f"{zavod.zavod_nomi}ga so'rov yuborildi!")
        else:
            messages.warning(request, "Bu zavodga so'rov allaqachon yuborilgan!")
        return redirect('zavod_sorov_yuborish')

    return render(request, 'yetkazib_beruvchi/sorov.html', {
        'profil': profil,
        'zavodlar': zavodlar,
        'mening_sorovlarim': mening_sorovlarim,
    })


# ─── ZAVOD (yetkazuvchilarni boshqarish) ─────────────────────────────────────

@login_required
def zavod_yetkazuvchilar(request):
    """Zavod o'ziga biriktirilgan yetkazuvchilarni ko'radi"""
    profil = _get_zavod(request.user)
    if not profil:
        return redirect('login')

    sorovlar = YetkazuvchiSorov.objects.filter(
        zavod=profil
    ).select_related('yetkazuvchi__foydalanuvchi')

    return render(request, 'zavod/yetkazuvchilar.html', {
        'profil': profil,
        'sorovlar': sorovlar,
    })


@login_required
@require_POST
def zavod_sorov_javob(request, sorov_id):
    """Zavod so'rovni qabul yoki rad etadi"""
    profil = _get_zavod(request.user)
    if not profil:
        return JsonResponse({'error': "Ruxsat yo'q"}, status=403)

    try:
        sorov = YetkazuvchiSorov.objects.get(id=sorov_id, zavod=profil)
    except YetkazuvchiSorov.DoesNotExist:
        return JsonResponse({'error': "So'rov topilmadi"}, status=404)

    try:
        data = json.loads(request.body)
        harakat = data.get('harakat')
    except Exception:
        harakat = request.POST.get('harakat')

    if harakat == 'qabul':
        sorov.holat = 'qabul_qilindi'
        sorov.yetkazuvchi.zavod = profil
        sorov.yetkazuvchi.save(update_fields=['zavod'])
        sorov.save(update_fields=['holat'])
        return JsonResponse({'status': 'ok', 'xabar': 'Qabul qilindi'})
    elif harakat == 'rad':
        sorov.holat = 'rad_etildi'
        sorov.save(update_fields=['holat'])
        return JsonResponse({'status': 'ok', 'xabar': "Rad etildi"})
    else:
        return JsonResponse({'error': "Noto'g'ri harakat"}, status=400)


# ─── ZAVOD — Jo'natma yaratish ────────────────────────────────────────────────

@login_required
def zavod_analitika(request):
    """Zavod analitikasi — qaysi do'kon ko'p oladi + oylik buyurtma hajmi (grafik)."""
    profil = _get_zavod(request.user)
    if not profil:
        return redirect('login')
    from buyurtma.models import Buyurtma
    from django.db.models import Sum, Count
    from django.utils import timezone
    from datetime import date
    import calendar

    hammasi = Buyurtma.objects.filter(zavod=profil)

    # Do'konlar reytingi (ko'p oluvchi birinchi)
    dokonlar = list(hammasi.exclude(holat='bekor')
                    .values('dokon__dokon_nomi')
                    .annotate(summa=Sum('jami'), soni=Count('id'))
                    .order_by('-summa')[:20])

    # Oylik buyurtma hajmi (grafik uchun)
    _OY = ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyn', 'Iyl', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek']
    bugun = timezone.localdate()
    yillik_data = []
    for oy in range(1, 13):
        bosh = date(bugun.year, oy, 1)
        _, oxir = calendar.monthrange(bugun.year, oy)
        oxir_d = date(bugun.year, oy, oxir)
        if bosh > bugun:
            summa = None
        else:
            summa = float(hammasi.exclude(holat='bekor').filter(
                yaratilgan__date__gte=bosh, yaratilgan__date__lte=min(oxir_d, bugun)
            ).aggregate(s=Sum('jami'))['s'] or 0)
        yillik_data.append({'nom': _OY[oy - 1], 'summa': summa})

    jami_summa = hammasi.exclude(holat='bekor').aggregate(s=Sum('jami'))['s'] or 0
    return render(request, 'zavod/analitika.html', {
        'profil': profil,
        'dokonlar': dokonlar,
        'yillik_data': yillik_data,
        'jami_summa': jami_summa,
        'buyurtma_soni': hammasi.count(),
    })


@login_required
def zavod_jonatma_yaratish(request):
    profil = _get_zavod(request.user)
    if not profil:
        return redirect('login')

    from users.models import DokonEgasiProfil
    from buyurtma.models import Buyurtma

    mahsulotlar = Mahsulot.objects.filter(zavod=profil, faol=True, soni__gt=0)
    # Bu zavod so'rovini QABUL QILGAN yetkazuvchilar (bittasi bir nechta zavodga
    # xizmat qila oladi — so'rov jadvali orqali, bitta FK bilan cheklanmasdan).
    yetkazuvchilar = YetkazibBeruvchiProfil.objects.filter(
        sorovlar__zavod=profil, sorovlar__holat='qabul_qilindi')
    dokonlar = DokonEgasiProfil.objects.all().order_by('dokon_nomi')

    # Do'kon so'rovidan (Buyurtma) kelgan bo'lsa — manzilni avtomatik tanlaymiz
    tanlangan_dokon_id = request.GET.get('dokon') or ''
    buyurtma_id = request.GET.get('buyurtma') or ''
    if buyurtma_id:
        b = Buyurtma.objects.filter(id=buyurtma_id, zavod=profil).select_related('dokon').first()
        if b and b.dokon_id:
            tanlangan_dokon_id = str(b.dokon_id)

    return render(request, 'yetkazib_beruvchi/jonatma_yaratish.html', {
        'profil': profil,
        'mahsulotlar': mahsulotlar,
        'yetkazuvchilar': yetkazuvchilar,
        'dokonlar': dokonlar,
        'tanlangan_dokon_id': str(tanlangan_dokon_id),
    })


@login_required
@require_POST
def zavod_jonatma_yuborish(request):
    """Jo'natma yaratish API"""
    profil = _get_zavod(request.user)
    if not profil:
        return JsonResponse({'error': "Ruxsat yo'q"}, status=403)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'JSON xato'}, status=400)

    mahsulotlar_data = data.get('mahsulotlar', [])
    yetkazuvchi_id = data.get('yetkazuvchi_id')
    izoh = data.get('izoh', '')
    dokon_id = data.get('dokon_id')
    manzil_txt = (data.get('manzil') or '').strip()

    def _f(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None
    lat = _f(data.get('lat'))
    lng = _f(data.get('lng'))

    def _sana(s):
        """'14.07.2026' yoki '14072026' -> date; bo'lmasa None."""
        s = (s or '').strip().replace('.', '').replace('/', '').replace('-', '')
        if len(s) != 8 or not s.isdigit():
            return None
        from datetime import date
        try:
            return date(int(s[4:8]), int(s[2:4]), int(s[0:2]))
        except ValueError:
            return None

    chiqish_sana = _sana(data.get('chiqish_sana'))

    if not mahsulotlar_data:
        return JsonResponse({'error': 'Mahsulot tanlang'}, status=400)

    yetkazuvchi = None
    if yetkazuvchi_id:
        # Faqat shu zavod so'rovini qabul qilgan yetkazuvchi tanlanishi mumkin.
        yetkazuvchi = YetkazibBeruvchiProfil.objects.filter(
            id=yetkazuvchi_id, sorovlar__zavod=profil,
            sorovlar__holat='qabul_qilindi').first()
        if not yetkazuvchi:
            return JsonResponse({'error': 'Yetkazuvchi topilmadi'}, status=404)

    # Manzil do'koni (ixtiyoriy) — belgilanmasa mahsulotdan aniqlanadi
    manzil_dokon = None
    if dokon_id:
        from users.models import DokonEgasiProfil
        manzil_dokon = DokonEgasiProfil.objects.filter(id=dokon_id).first()

    try:
        with transaction.atomic():
            jonatma = Jonatma.objects.create(
                zavod=profil,
                yetkazuvchi=yetkazuvchi,
                izoh=izoh,
                holat='qabul_kutilmoqda',
                manzil_dokon=manzil_dokon,
                lat=lat,
                lng=lng,
                manzil_txt=manzil_txt,
                chiqish_sana=chiqish_sana,
            )
            jami = Decimal('0')
            for item in mahsulotlar_data:
                m = Mahsulot.objects.get(id=item['id'], zavod=profil)
                try:
                    soni = Decimal(str(item['soni']))
                except (InvalidOperation, TypeError, KeyError):
                    raise ValueError("Mahsulot soni noto'g'ri kiritilgan")
                if soni <= 0:
                    continue
                # Ombordan faqat qoldiq yetsagina (atomik F()) kamaytiramiz —
                # bir vaqtda bir necha jo'natma bo'lsa ham minusga tushmaydi.
                kamaydi = Mahsulot.objects.filter(
                    id=m.id, soni__gte=soni
                ).update(soni=F('soni') - soni)
                if not kamaydi:
                    m.refresh_from_db(fields=['soni'])
                    raise ValueError(f"{m.nomi} yetarli emas (qoldi: {m.soni})")
                JonatmaMahsulot.objects.create(
                    jonatma=jonatma,
                    mahsulot=m,
                    mahsulot_nomi=m.nomi,
                    barkod=m.barkod or '',
                    soni=soni,
                    birlik=(item.get('birlik') or m.birlik or 'dona'),
                    narx=m.narx,
                    tugash_sana=_sana(item.get('tugash')),
                )
                jami += m.narx * soni

            jonatma.jami_summa = jami
            jonatma.save(update_fields=['jami_summa'])

    except Mahsulot.DoesNotExist:
        return JsonResponse({'error': 'Mahsulot topilmadi'}, status=404)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({
        'status': 'ok',
        'jonatma_id': jonatma.id,
        'barkod': jonatma.barkod,
    })