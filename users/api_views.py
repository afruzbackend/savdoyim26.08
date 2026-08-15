from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import json


@login_required
def me_view(request):
    user = request.user
    return JsonResponse({
        'id': user.id,
        'username': user.username,
        'ism': user.first_name,
        'rol': user.rol,
        'telefon': user.telefon,
        'tasdiqlangan': user.tasdiqlangan,
    })


@login_required
def update_location(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST kerak'}, status=405)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'JSON xato'}, status=400)

    lat = data.get('latitude')
    lng = data.get('longitude')
    if lat is not None and lng is not None:
        try:
            lat = float(lat)
            lng = float(lng)
        except (TypeError, ValueError):
            return JsonResponse({'error': 'latitude va longitude son bo\'lishi kerak'}, status=400)
        request.user.latitude = lat
        request.user.longitude = lng
        request.user.save(update_fields=['latitude', 'longitude'])
        if request.user.rol == 'mijoz':
            try:
                p = request.user.mijoz_profil
                p.latitude = lat
                p.longitude = lng
                p.save(update_fields=['latitude', 'longitude'])
            except Exception:
                pass
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': 'latitude va longitude kerak'}, status=400)
