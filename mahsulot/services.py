"""Sharh (review) biznes logikasi + reyting statistikasi (keshli).
View'lar faqat shu servisni chaqiradi (thin views)."""
from django.db import transaction, IntegrityError
from django.db.models import Avg, Count
from django.core.cache import cache
from .models import MahsulotSharh, SharhRasm
from users.services import ServiceError, AuditService


class ReviewStats:
    """Mahsulot reyting statistikasi — aggregatsiya + keshlash."""
    TIMEOUT = 300

    @staticmethod
    def _key(mahsulot_id):
        return f'mahsulot_stats_{mahsulot_id}'

    @classmethod
    def get(cls, mahsulot):
        key = cls._key(mahsulot.id)
        cached = cache.get(key)
        if cached is not None:
            return cached
        qs = MahsulotSharh.objects.filter(mahsulot=mahsulot, holat='faol')
        agg = qs.aggregate(ortacha=Avg('yulduz'), jami=Count('id'))
        jami = agg['jami'] or 0
        ortacha = round(agg['ortacha'], 1) if agg['ortacha'] else 0
        taqsimot = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        for row in qs.values('yulduz').annotate(n=Count('id')):
            taqsimot[row['yulduz']] = row['n']
        foizlar = {s: (round(taqsimot[s] / jami * 100) if jami else 0) for s in range(1, 6)}
        stats = {'ortacha': ortacha, 'jami': jami, 'taqsimot': taqsimot, 'foizlar': foizlar}
        cache.set(key, stats, cls.TIMEOUT)
        return stats

    @classmethod
    def invalidate(cls, mahsulot_id):
        cache.delete(cls._key(mahsulot_id))


class ReviewService:
    """Sharh yaratish/tahrirlash/yashirish — barcha tekshiruvlar server tomonida."""

    @staticmethod
    def _validate_yulduz(yulduz):
        try:
            yulduz = int(yulduz)
        except (TypeError, ValueError):
            yulduz = 0
        if yulduz < 1 or yulduz > 5:
            raise ServiceError("Yulduzni 1 dan 5 gacha tanlang.", 400, {'yulduz': 'invalid'})
        return yulduz

    @staticmethod
    def _verify_purchase(user, mahsulot):
        """Foydalanuvchining shu mahsulot uchun 'olib_ketildi' buyurtmasi (yoki None)."""
        from buyurtma.models import MijozBuyurtma
        return (MijozBuyurtma.objects
                .filter(mijoz=user, holat='olib_ketildi', itemlar__mahsulot=mahsulot)
                .order_by('-yaratilgan').first())

    @staticmethod
    @transaction.atomic
    def create(user, mahsulot, yulduz, izoh, rasmlar, request=None):
        yulduz = ReviewService._validate_yulduz(yulduz)
        rasmlar = rasmlar or []
        if len(rasmlar) > 3:
            raise ServiceError("Ko'pi bilan 3 ta rasm qo'shish mumkin.", 400, {'rasmlar': 'max_3'})
        buyurtma = ReviewService._verify_purchase(user, mahsulot)
        if not buyurtma:
            raise ServiceError("Faqat sotib olib, olib ketilgan mahsulotga sharh yozish mumkin.", 403)
        if MahsulotSharh.objects.filter(mahsulot=mahsulot, foydalanuvchi=user).exists():
            raise ServiceError("Siz bu mahsulotga allaqachon sharh yozgansiz.", 409)
        try:
            sharh = MahsulotSharh.objects.create(
                mahsulot=mahsulot, foydalanuvchi=user, buyurtma=buyurtma,
                yulduz=yulduz, izoh=(izoh or '').strip(), xaridor_tasdiqlangan=True,
            )
        except IntegrityError:
            raise ServiceError("Siz bu mahsulotga allaqachon sharh yozgansiz.", 409)
        from users.image_utils import rasm_haqiqiymi
        for r in rasmlar[:3]:
            if rasm_haqiqiymi(r):
                SharhRasm.objects.create(sharh=sharh, rasm=r)
        ReviewStats.invalidate(mahsulot.id)
        AuditService.log(user, 'review_created', sharh, f"{yulduz}*", request)
        return sharh

    @staticmethod
    @transaction.atomic
    def update(user, sharh, yulduz, izoh, yangi_rasmlar, request=None):
        if sharh.foydalanuvchi_id != user.id:
            raise ServiceError("Bu sharh sizga tegishli emas.", 403)
        yulduz = ReviewService._validate_yulduz(yulduz)
        yangi_rasmlar = yangi_rasmlar or []
        joriy = sharh.rasmlar.count()
        if joriy + len(yangi_rasmlar) > 3:
            raise ServiceError("Jami 3 tadan ortiq rasm bo'lishi mumkin emas.", 400, {'rasmlar': 'max_3'})
        sharh.yulduz = yulduz
        if izoh is not None:
            sharh.izoh = izoh.strip()
        # xaridor_tasdiqlangan hech qachon o'zgartirilmaydi
        sharh.save(update_fields=['yulduz', 'izoh', 'yangilangan'])
        from users.image_utils import rasm_haqiqiymi
        for r in yangi_rasmlar[:max(0, 3 - joriy)]:
            if rasm_haqiqiymi(r):
                SharhRasm.objects.create(sharh=sharh, rasm=r)
        ReviewStats.invalidate(sharh.mahsulot_id)
        AuditService.log(user, 'review_updated', sharh, '', request)
        return sharh

    @staticmethod
    def _moderatsiya(admin, sharh, holat, amal, request=None):
        if not (admin.is_staff or admin.is_superuser):
            raise ServiceError("Ruxsat yo'q. Bu amal faqat administrator uchun.", 403)
        sharh.holat = holat
        sharh.save(update_fields=['holat'])
        ReviewStats.invalidate(sharh.mahsulot_id)
        AuditService.log(admin, amal, sharh, '', request)
        return sharh

    @staticmethod
    def hide(admin, sharh, request=None):
        return ReviewService._moderatsiya(admin, sharh, 'yashirin', 'review_hidden', request)

    @staticmethod
    def restore(admin, sharh, request=None):
        return ReviewService._moderatsiya(admin, sharh, 'faol', 'review_restored', request)
