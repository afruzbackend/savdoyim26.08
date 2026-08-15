from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect
from datetime import date
import calendar

from kassa.models import SavdoChek, QarzDaftar, Kassa
from mahsulot.models import Mahsulot
from users.models import DokonEgasiProfil

OY_NOMLARI = ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyn', 'Iyl', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek']


def _get_dokon(user):
    if user.rol == 'dokon_egasi':
        try:
            return user.dokon_profil
        except DokonEgasiProfil.DoesNotExist:
            return None
    return None


@login_required
def dokon_egasi_dashboard(request):
    if request.user.rol != 'dokon_egasi':
        return redirect('login')

    dokon = _get_dokon(request.user)
    if not dokon:
        return redirect('login')

    profil = dokon
    kassa, _ = Kassa.objects.get_or_create(dokon=dokon)
    mahsulotlar = Mahsulot.objects.filter(dokon=dokon, faol=True)
    tugayotgan = [m for m in mahsulotlar if m.kam_qoldi]
    qarzlar = QarzDaftar.objects.filter(dokon=dokon, to_langan=False).order_by('-yaratilgan')

    bugun = date.today()
    MAX_SUMMA = 30_000_000

    yillik_data = []
    for oy in range(1, 13):
        _, oxir_kun = calendar.monthrange(bugun.year, oy)
        bosh = date(bugun.year, oy, 1)
        oxir = date(bugun.year, oy, oxir_kun)

        if bosh > bugun:
            summa = None
        else:
            summa = float(
                SavdoChek.objects.filter(
                    dokon=dokon,
                    yaratilgan__date__gte=bosh,
                    yaratilgan__date__lte=min(oxir, bugun),
                ).aggregate(s=Sum('jami'))['s'] or 0
            )

        yillik_data.append({
            'nom': OY_NOMLARI[oy - 1],
            'summa': summa,
            'foiz': int(round((summa / MAX_SUMMA) * 100)) if summa is not None else 0,
        })

    return render(request, 'dokon_egasi/dashboard.html', {
        'profil': profil,
        'kassa': kassa,
        'mahsulotlar': mahsulotlar,
        'tugayotgan': tugayotgan,
        'qarzlar': qarzlar,
        'yillik_data': yillik_data,
        'max_summa': MAX_SUMMA,
    })


def dokonlar_api(request):
    dokonlar = list(
        DokonEgasiProfil.objects.filter(
            foydalanuvchi__tasdiqlangan=True
        ).values('id', 'dokon_nomi', 'manzil', 'latitude', 'longitude')
    )
    return JsonResponse({'dokonlar': dokonlar})