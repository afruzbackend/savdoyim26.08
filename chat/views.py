import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import ChatXona, ChatXabar
from users.models import CustomUser


@login_required
def chat_royxat(request):
    xonalar = (request.user.chat_xonalar
               .prefetch_related('ishtirokchilar')
               .order_by('-yaratilgan'))
    return render(request, 'chat/royxat.html', {'xonalar': xonalar})


@login_required
def chat_qidiruv(request):
    """Username bo'yicha foydalanuvchi/kompaniyalarni qidirish (#11)."""
    q = request.GET.get('q', '').strip()
    natijalar = []
    if q:
        from django.db.models import Q
        users = CustomUser.objects.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q)
        ).exclude(id=request.user.id)[:20]
        for u in users:
            # Kompaniya nomini roliga qarab olishga urinamiz
            kompaniya = ''
            dp = getattr(u, 'dokon_profil', None)
            zp = getattr(u, 'zavod_profil', None)
            if dp:
                kompaniya = dp.dokon_nomi
            elif zp:
                kompaniya = zp.mchj_nomi or zp.zavod_nomi
            natijalar.append({
                'id': u.id,
                'username': u.username,
                'ism': u.first_name or u.username,
                'rol': u.get_rol_display() if u.rol else '',
                'kompaniya': kompaniya,
            })
    return JsonResponse({'natijalar': natijalar})


@login_required
def chat_xona(request, xona_id):
    xona = get_object_or_404(ChatXona, id=xona_id)
    if request.user not in xona.ishtirokchilar.all():
        return redirect('chat_royxat')
    xabarlar = xona.xabarlar.all()
    xona.xabarlar.filter(o_qildi=False).exclude(
        yuboruvchi=request.user
    ).update(o_qildi=True)
    boshqa = xona.ishtirokchilar.exclude(id=request.user.id).first()
    return render(request, 'chat/xona.html', {
        'xona': xona,
        'xabarlar': xabarlar,
        'boshqa': boshqa,
    })


@login_required
@require_POST
def xabar_yuborish(request, xona_id):
    xona = get_object_or_404(ChatXona, id=xona_id)
    if request.user not in xona.ishtirokchilar.all():
        return JsonResponse({'error': "Ruxsat yo'q"}, status=403)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'JSON xato'}, status=400)
    matn = data.get('matn', '').strip()
    if not matn:
        return JsonResponse({'error': "Bo'sh xabar"}, status=400)
    x = ChatXabar.objects.create(
        xona=xona, yuboruvchi=request.user, matn=matn
    )
    return JsonResponse({
        'id': x.id,
        'matn': x.matn,
        'yuboruvchi': request.user.first_name or request.user.username,
        'vaqt': x.yaratilgan.strftime('%H:%M'),
    })


@login_required
def xabarlar_olish(request, xona_id):
    xona = get_object_or_404(ChatXona, id=xona_id)
    if request.user not in xona.ishtirokchilar.all():
        return JsonResponse({'error': "Ruxsat yo'q"}, status=403)
    try:
        oxirgi_id = int(request.GET.get('oxirgi_id', 0))
    except (TypeError, ValueError):
        oxirgi_id = 0
    xabarlar = xona.xabarlar.filter(id__gt=oxirgi_id)
    return JsonResponse({
        'xabarlar': [{
            'id': x.id,
            'matn': x.matn,
            'yuboruvchi': x.yuboruvchi.first_name or x.yuboruvchi.username,
            'men': x.yuboruvchi == request.user,
            'vaqt': x.yaratilgan.strftime('%H:%M'),
        } for x in xabarlar]
    })


@login_required
def chat_boshla(request, foydalanuvchi_id):
    """Foydalanuvchi bilan chatni ochish/yaratish va unga o'tish (#21)."""
    boshqa = get_object_or_404(CustomUser, id=foydalanuvchi_id)
    if boshqa == request.user:
        return redirect('chat_royxat')
    umumiy = request.user.chat_xonalar.filter(ishtirokchilar=boshqa)
    if umumiy.exists():
        xona = umumiy.first()
    else:
        xona = ChatXona.objects.create()
        xona.ishtirokchilar.add(request.user, boshqa)
    return redirect('chat_xona', xona_id=xona.id)


@login_required
@require_POST
def yangi_chat(request):
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'JSON xato'}, status=400)
    foydalanuvchi_id = data.get('foydalanuvchi_id')
    try:
        boshqa = CustomUser.objects.get(id=foydalanuvchi_id)
    except CustomUser.DoesNotExist:
        return JsonResponse({'error': 'Foydalanuvchi topilmadi'}, status=404)

    umumiy = request.user.chat_xonalar.filter(ishtirokchilar=boshqa)
    if umumiy.exists():
        xona = umumiy.first()
    else:
        xona = ChatXona.objects.create()
        xona.ishtirokchilar.add(request.user, boshqa)

    return JsonResponse({'xona_id': xona.id})
