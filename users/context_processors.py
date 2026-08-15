def bildirishnoma_soni(request):
    """Navbar konteksti: o'qilmagan bildirishnomalar soni + mijoz savati soni.
    Barcha shablonlarda mavjud bo'ladi (settings TEMPLATES da ro'yxatdan o'tgan).
    """
    if not request.user.is_authenticated:
        return {}

    ctx = {}
    try:
        ctx['oqilmagan_bildirishnoma'] = request.user.bildirishnomalar.filter(
            oqilgan=False
        ).count()
    except Exception:
        ctx['oqilmagan_bildirishnoma'] = 0

    # Savatdagi mahsulotlar soni (faqat mijoz uchun)
    if getattr(request.user, 'rol', None) == 'mijoz':
        try:
            from django.db.models import Sum
            from buyurtma.models import SavatItem
            agg = SavatItem.objects.filter(
                savat__mijoz=request.user
            ).aggregate(s=Sum('soni'))
            ctx['savat_soni'] = agg['s'] or 0
        except Exception:
            ctx['savat_soni'] = 0

    return ctx
