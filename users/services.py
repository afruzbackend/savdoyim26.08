"""Umumiy servislar: xatolik turi, audit log, bildirishnoma.
Biznes logika view'lardan ajratilgan (qayta ishlatiladigan, testlanadigan)."""
from django.http import JsonResponse
from .models import Bildirishnoma, AuditLog


def json_ok(message='', data=None, status=200):
    """Bir xil JSON javob (muvaffaqiyat)."""
    return JsonResponse({'success': True, 'message': message, 'data': data or {}}, status=status)


def json_err(message='', errors=None, status=400):
    """Bir xil JSON javob (xatolik)."""
    return JsonResponse({'success': False, 'message': message, 'errors': errors or {}}, status=status)


class ServiceError(Exception):
    """Servis darajasidagi xatolik. View uni JSON envelope'ga aylantiradi."""
    def __init__(self, message, code=400, errors=None):
        self.message = message
        self.code = code
        self.errors = errors or {}
        super().__init__(message)


def foydalanuvchi_dokoni(user):
    """YAGONA manba: foydalanuvchining do'koni yoki None.

    Do'kon egasi -> o'z do'koni. Sotuvchi -> faqat TASDIQLANGAN bo'lsa (sorov_holati
    'tasdiqlangan', user.tasdiqlangan va is_active) biriktirilgan do'kon. Kutilayotgan yoki
    rad etilgan sotuvchi hech qayerda (web, API, Telegram bot) do'kon ma'lumotini ko'rmaydi."""
    if not user or not getattr(user, 'is_authenticated', False) or not getattr(user, 'is_active', False):
        return None
    rol = getattr(user, 'rol', None)
    if rol == 'dokon_egasi':
        try:
            return user.dokon_profil
        except Exception:
            return None
    if rol == 'sotuvchi':
        if not getattr(user, 'tasdiqlangan', False):
            return None
        try:
            sp = user.sotuvchi_profil
        except Exception:
            return None
        if sp.sorov_holati == 'tasdiqlangan':
            return sp.dokon
    return None


def client_ip(request):
    """Mijoz IP manzili. X-Forwarded-For faqat TRUST_X_FORWARDED_FOR=True (nginx orqasida)
    bo'lganda ishlatiladi va uning OXIRGI qiymati olinadi (uni proxy qo'shadi; boshidagi
    qiymatlarni mijoz o'zi yozib yuborishi mumkin)."""
    if not request:
        return None
    from django.conf import settings
    if getattr(settings, 'TRUST_X_FORWARDED_FOR', False):
        xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
        oxirgi = xff.split(',')[-1].strip() if xff else ''
        if oxirgi:
            return oxirgi
    return request.META.get('REMOTE_ADDR')


def foydalanuvchi_kirishlarini_bekor_qil(user, joriy_sessiya=None):
    """Foydalanuvchining barcha kirishlarini bekor qiladi: web sessiyalar, API token
    va Telegram bog'lanishi. Sotuvchi rad etilganda / parol tiklanganda chaqiriladi.
    `joriy_sessiya` — saqlab qolinadigan sessiya kaliti (parol o'zgartirgan o'zi)."""
    from django.contrib.sessions.models import Session
    from django.utils import timezone
    from .models import TelegramLink
    try:
        from rest_framework.authtoken.models import Token
        Token.objects.filter(user=user).delete()
    except Exception:
        pass
    TelegramLink.objects.filter(foydalanuvchi=user).delete()
    uid = str(user.pk)
    for sess in Session.objects.filter(expire_date__gt=timezone.now()).iterator():
        if sess.session_key == joriy_sessiya:
            continue
        try:
            if sess.get_decoded().get('_auth_user_id') == uid:
                sess.delete()
        except Exception:
            continue


class AuditService:
    """Muhim amallarni qayd etadi. Audit hech qachon asosiy oqimni buzmaydi."""
    @staticmethod
    def log(user, amal, obj=None, tafsilot='', request=None):
        try:
            AuditLog.objects.create(
                foydalanuvchi=user if (user and getattr(user, 'is_authenticated', False)) else None,
                amal=amal,
                obyekt_turi=obj.__class__.__name__ if obj is not None else '',
                obyekt_id=getattr(obj, 'id', None),
                tafsilot=(tafsilot or '')[:255],
                ip=client_ip(request),
            )
        except Exception:
            pass


class NotificationService:
    """Bildirishnomalarni markazlashgan yaratish. View'lar to'g'ridan-to'g'ri
    Bildirishnoma yaratmaydi — shu servisdan foydalanadi."""
    HAVOLA = '/order/mening-buyurtmalarim/'

    @staticmethod
    def _send(user, matn, havola=''):
        return Bildirishnoma.yubor(user, matn, havola)

    @classmethod
    def send_order_created(cls, buyurtma):
        return cls._send(buyurtma.mijoz, "Buyurtmangiz qabul qilindi.", cls.HAVOLA)

    @classmethod
    def send_order_preparing(cls, buyurtma):
        return cls._send(buyurtma.mijoz, "Buyurtmangiz tayyorlanmoqda.", cls.HAVOLA)

    @classmethod
    def send_order_ready(cls, buyurtma):
        return cls._send(buyurtma.mijoz, "Buyurtmangiz tayyor. Kelib olib ketishingiz mumkin.", cls.HAVOLA)

    @classmethod
    def send_order_completed(cls, buyurtma):
        return cls._send(buyurtma.mijoz, "Buyurtmangiz olib ketildi. Mahsulotni baholashni unutmang.", cls.HAVOLA)

    @classmethod
    def send_order_cancelled(cls, buyurtma):
        return cls._send(buyurtma.mijoz, "Buyurtmangiz bekor qilindi.", cls.HAVOLA)

    @classmethod
    def send_review_reply(cls, sharh, matn=''):
        return cls._send(sharh.foydalanuvchi, matn or "Sharhingizga javob berildi.", '')

    @classmethod
    def send_sotuvchi_tasdiq(cls, sotuvchi_profil, tasdiqlandi):
        """Sotuvchiga so'rovi natijasini yetkazadi: sayt bildirishnomasi + email +
        Telegram (bog'langan bo'lsa). Sotuvchi tasdiqgacha login qilolmaydi —
        shu sabab email eng muhim ("qaytib kiring" signali)."""
        user = sotuvchi_profil.foydalanuvchi
        dokon = getattr(sotuvchi_profil, 'dokon', None)
        nomi = getattr(dokon, 'dokon_nomi', '') or "do'kon"
        if tasdiqlandi:
            matn = (f"Tabriklaymiz! \"{nomi}\" do'koniga sotuvchi sifatida "
                    f"tasdiqlandingiz. Endi tizimga kirishingiz mumkin.")
            havola = '/user/sotuvchi/'
            mavzu = "Sotuvchi so'rovingiz tasdiqlandi"
        else:
            matn = f"\"{nomi}\" do'koniga qo'shilish so'rovingiz rad etildi."
            havola = ''
            mavzu = "Sotuvchi so'rovingiz rad etildi"
        cls._send(user, matn, havola)          # 1) sayt (keyingi loginda ko'rinadi)
        cls._email_xabar(user, mavzu, matn)    # 2) email (qaytib kirishga chorlaydi)
        cls._telegram_xabar(user, matn)        # 3) Telegram (bog'langan bo'lsa)

    @staticmethod
    def _email_xabar(user, mavzu, matn):
        if not getattr(user, 'email', ''):
            return
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            send_mail(mavzu, matn, settings.DEFAULT_FROM_EMAIL, [user.email],
                      fail_silently=True)
        except Exception:
            pass

    @staticmethod
    def _telegram_xabar(user, matn):
        try:
            from .models import TelegramLink
            link = TelegramLink.objects.filter(foydalanuvchi=user).first()
            if link:
                from kassa.views import _telegramga_yubor   # lazy — sikldan qochish
                _telegramga_yubor(link.chat_id, matn)
        except Exception:
            pass

    @classmethod
    def send_order_status(cls, buyurtma, holat):
        mapping = {
            'yangi': cls.send_order_created,
            'tayyorlanmoqda': cls.send_order_preparing,
            'tayyor': cls.send_order_ready,
            'olib_ketildi': cls.send_order_completed,
            'bekor': cls.send_order_cancelled,
        }
        fn = mapping.get(holat)
        return fn(buyurtma) if fn else None
