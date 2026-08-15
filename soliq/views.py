from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum
from .models import SoliqSozlama
from kassa.models import SavdoChek
from users.models import DokonEgasiProfil


def _get_dokon(user):
    if user.rol == 'dokon_egasi':
        try:
            return user.dokon_profil
        except DokonEgasiProfil.DoesNotExist:
            return None
    return None


def _hisob(dokon, stavka, boshlanish):
    savdo = SavdoChek.objects.filter(
        dokon=dokon,
        yaratilgan__date__gte=boshlanish,
    ).aggregate(s=Sum('jami'))['s'] or 0
    return float(savdo), round(float(savdo) * stavka / 100, 2)


@login_required
def soliq_dashboard(request):
    if request.user.rol != 'dokon_egasi':
        return redirect('login')
    dokon = _get_dokon(request.user)
    if not dokon:
        return redirect('login')

    sozlama, _ = SoliqSozlama.objects.get_or_create(dokon=dokon, defaults={'stavka': 12.0})
    bugun = timezone.now().date()

    k_s, k_sol = _hisob(dokon, sozlama.stavka, bugun)
    h_s, h_sol = _hisob(dokon, sozlama.stavka, bugun - timedelta(days=7))
    o_s, o_sol = _hisob(dokon, sozlama.stavka, bugun.replace(day=1))
    y_s, y_sol = _hisob(dokon, sozlama.stavka, bugun.replace(month=1, day=1))

    return render(request, 'soliq/dashboard.html', {
        'sozlama': sozlama,
        'kunlik': {'savdo': k_s, 'soliq': k_sol},
        'haftalik': {'savdo': h_s, 'soliq': h_sol},
        'oylik': {'savdo': o_s, 'soliq': o_sol},
        'yillik': {'savdo': y_s, 'soliq': y_sol},
    })


@login_required
def soliq_api(request):
    if request.user.rol != 'dokon_egasi':
        return JsonResponse({'error': "Ruxsat yo'q"}, status=403)
    dokon = _get_dokon(request.user)
    if not dokon:
        return JsonResponse({'error': 'Profil topilmadi'}, status=404)

    sozlama, _ = SoliqSozlama.objects.get_or_create(dokon=dokon, defaults={'stavka': 12.0})
    bugun = timezone.now().date()

    k_s, k_sol = _hisob(dokon, sozlama.stavka, bugun)
    h_s, h_sol = _hisob(dokon, sozlama.stavka, bugun - timedelta(days=7))
    o_s, o_sol = _hisob(dokon, sozlama.stavka, bugun.replace(day=1))
    y_s, y_sol = _hisob(dokon, sozlama.stavka, bugun.replace(month=1, day=1))

    return JsonResponse({
        'stavka': sozlama.stavka,
        'kunlik': {'savdo': k_s, 'soliq': k_sol},
        'haftalik': {'savdo': h_s, 'soliq': h_sol},
        'oylik': {'savdo': o_s, 'soliq': o_sol},
        'yillik': {'savdo': y_s, 'soliq': y_sol},
    })
