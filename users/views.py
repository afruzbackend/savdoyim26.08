import json
import time
import secrets
import hashlib
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.conf import settings
from django.core.mail import send_mail
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Avg
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .services import client_ip, foydalanuvchi_kirishlarini_bekor_qil
from .models import (
    CustomUser, DokonEgasiProfil, SotuvchiProfil,
    ZavodProfil, YetkazibBeruvchiProfil, MijozProfil, Reyting
)

# ── Email tasdiqlash sozlamalari (#ro'yxatdan o'tish) ──
REG_CODE_TTL = 60         # kod 60 soniya amal qiladi
REG_MAX_SEND = 4          # bir email uchun maksimal 4 marta yuborish
REG_BLOCK_TTL = 3600      # 4 martadan keyin 1 soat blok

def _reg_keys(email):
    return (f'reg_code:{email}', f'reg_attempts:{email}', f'reg_block:{email}')


_PAROL_XATO = {
    'password_too_short': "Parol juda qisqa (kamida 6 ta belgi).",
    'password_too_common': "Parol juda oddiy — hamma ishlatadigan parollardan.",
    'password_entirely_numeric': "Parol faqat raqamlardan iborat bo'lmasin.",
    'password_too_similar': "Parol login, ism yoki emailga juda o'xshash.",
}


def _parol_xatolari(e):
    """Django parol validatori xatolarini o'zbekchaga o'giradi."""
    return " ".join(_PAROL_XATO.get(getattr(x, 'code', ''), x.messages[0] if hasattr(x, 'messages') else str(x))
                    for x in e.error_list)


def test_rejimi():
    """Email sozlanmagan LOKAL rejim: kod ekranda ko'rsatiladi. Productionda (DEBUG=False)
    hech qachon True bo'lmaydi — kodni so'ragan odamga ko'rsatish akkauntni egallashga olib keladi."""
    return settings.DEBUG and 'console' in settings.EMAIL_BACKEND


def _kod_yarat():
    return f"{secrets.randbelow(900000) + 100000}"


def _email_sozlanmagan_prod():
    return 'console' in settings.EMAIL_BACKEND and not settings.DEBUG


def _send_email_code(email, code, maqsad="Tasdiqlash"):
    """Emailga kod yuboradi. Xatoda exception ko'tariladi.
    Qaytaradi: True (lokal test rejimi) yoki False (haqiqiy yuborildi)."""
    if _email_sozlanmagan_prod():
        raise RuntimeError("Email sozlanmagan (EMAIL_HOST_PASSWORD yo'q)")
    send_mail(
        subject=f"Savdoyim — {maqsad} kodi",
        message=(
            f"Assalomu alaykum!\n\n"
            f"Savdoyim uchun {maqsad.lower()} kodingiz: {code}\n\n"
            f"Agar bu so'rovni siz yubormagan bo'lsangiz, ushbu xabarni e'tiborsiz qoldiring.\n\n"
            f"Savdoyim jamoasi"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )
    return test_rejimi()


@require_POST
def send_register_code(request):
    """Ro'yxatdan o'tishda email tasdiqlash kodi (60s amal, 4 marta limit, 1 soat blok)."""
    if request.content_type and 'application/json' in request.content_type:
        try:
            email = json.loads(request.body).get('email', '')
        except Exception:
            email = ''
    else:
        email = request.POST.get('email', '')
    email = (email or '').strip().lower()

    if not email or '@' not in email:
        return JsonResponse({'ok': False, 'error': "To'g'ri email manzil kiriting."}, status=400)
    if CustomUser.objects.filter(email__iexact=email).exists():
        return JsonResponse({'ok': False, 'error': "Bu email allaqachon ro'yxatdan o'tilgan."}, status=400)

    code_key, attempts_key, block_key = _reg_keys(email)

    # 1) Email bloklanganmi?
    block_until = cache.get(block_key)
    if block_until:
        qolgan = max(0, int(block_until - time.time()))
        return JsonResponse({
            'ok': False, 'blocked': True, 'block_seconds': qolgan,
            'error': "Juda ko'p urinish. Bu email vaqtincha bloklandi.",
        }, status=429)

    # 2) Urinishlar limiti (maksimal 4 marta)
    attempts = cache.get(attempts_key, 0)
    if attempts >= REG_MAX_SEND:
        cache.set(block_key, time.time() + REG_BLOCK_TTL, REG_BLOCK_TTL)
        cache.delete(code_key)
        return JsonResponse({
            'ok': False, 'blocked': True, 'block_seconds': REG_BLOCK_TTL,
            'error': "4 marta urinish tugadi. Bu email 1 soatga bloklandi.",
        }, status=429)

    # 3) Yangi kod — eski kod avtomatik bekor bo'ladi (faqat oxirgisi ishlaydi)
    attempts += 1
    cache.set(attempts_key, attempts, REG_BLOCK_TTL)
    # IP bo'yicha ham cheklov (turli emaillar bilan email kvotasini tugatishdan himoya)
    ip_kalit = f"reg_ip:{client_ip(request)}"
    if cache.get(ip_kalit, 0) >= 20:
        return JsonResponse({'ok': False, 'error': "Juda ko'p urinish. Birozdan so'ng qayta urining."}, status=429)
    cache.set(ip_kalit, cache.get(ip_kalit, 0) + 1, 3600)
    code = _kod_yarat()
    cache.set(code_key, code, REG_CODE_TTL)
    try:
        test_rejim = _send_email_code(email, code, "Ro'yxatdan o'tish")
    except Exception:
        return JsonResponse({'ok': False, 'error': "Email yuborilmadi. Birozdan so'ng qayta urinib ko'ring."}, status=500)

    resp = {
        'ok': True,
        'test': test_rejim,
        'ttl': REG_CODE_TTL,
        'attempts_left': REG_MAX_SEND - attempts,
    }
    if test_rejim:
        resp['code'] = code   # faqat lokal (DEBUG) rejimda, email sozlanmagan bo'lsa
    return JsonResponse(resp)


import re as _re

# Username: kichik harf, raqam, nuqta, pastki chiziq (Instagram uslubi)
_USERNAME_RE = _re.compile(r'^[a-z0-9._]{3,30}$')
# Ism: faqat harflar (lotin + kirill + o'zbek apostrofi), bo'sh joy, chiziqcha
_ISM_RE = _re.compile(r"^[A-Za-zÀ-ÿА-Яа-яЎўҚқҒғҲҳʼ'’\- ]+$")


def username_xatosi(username):
    """Username formatini tekshiradi. Xato bo'lsa xabar matni, to'g'ri bo'lsa None."""
    u = (username or '').strip()
    if not u:
        return "Username kiriting"
    if len(u) < 3:
        return "Kamida 3 ta belgi bo'lsin"
    if len(u) > 30:
        return "Ko'pi bilan 30 ta belgi"
    if not _USERNAME_RE.match(u):
        return "Faqat kichik harf, raqam, nuqta va pastki chiziq (a-z, 0-9, . _)"
    if u.startswith('.') or u.endswith('.'):
        return "Nuqta bilan boshlanmasin va tugamasin"
    if '..' in u:
        return "Ketma-ket ikki nuqta bo'lmasin"
    return None


def ism_xatosi(ism):
    """Ism faqat harflardan iboratligini tekshiradi. Xato bo'lsa xabar, aks holda None."""
    i = (ism or '').strip()
    if not i:
        return "Ism kiriting"
    if not _ISM_RE.match(i):
        return "Ismda faqat harflar bo'lishi mumkin (raqam va belgilarsiz)"
    return None


@require_POST
def check_dokon(request):
    """Sotuvchi ro'yxatida egasi username'ini live tekshiradi -> do'kon nomini qaytaradi."""
    try:
        uname = json.loads(request.body).get('username', '')
    except Exception:
        uname = request.POST.get('username', '')
    uname = (uname or '').strip().lower()
    if not uname:
        return JsonResponse({'ok': False, 'reason': "Username kiriting"})
    owner = CustomUser.objects.filter(username__iexact=uname, rol='dokon_egasi').first()
    if not owner:
        return JsonResponse({'ok': False, 'reason': "Bunday do'kon egasi topilmadi"})
    dokon = DokonEgasiProfil.objects.filter(foydalanuvchi=owner).first()
    if not dokon:
        return JsonResponse({'ok': False, 'reason': "Do'kon profili topilmadi"})
    return JsonResponse({'ok': True, 'dokon_nomi': dokon.dokon_nomi or owner.username})


@require_POST
def check_username(request):
    """Live username tekshiruvi (Instagram-dek): format + bandligi. JSON qaytaradi."""
    try:
        username = json.loads(request.body).get('username', '')
    except Exception:
        username = request.POST.get('username', '')
    username = (username or '').strip().lower()
    xato = username_xatosi(username)
    if xato:
        return JsonResponse({'ok': False, 'available': False, 'reason': xato})
    if CustomUser.objects.filter(username__iexact=username).exists():
        return JsonResponse({'ok': False, 'available': False, 'reason': "Bu username band"})
    return JsonResponse({'ok': True, 'available': True, 'reason': "Bo'sh — foydalanish mumkin"})


def _redirect_by_role(user):
    urls = {
        'dokon_egasi': 'dokon_egasi_dashboard',
        'sotuvchi': 'sotuvchi_dashboard',
        'zavod': 'zavod_dashboard',
        'mijoz': 'mijoz_dashboard',
        'yetkazib_beruvchi': 'yetkazuvchi_dashboard',
    }
    return redirect(urls.get(user.rol, 'login'))


# ── Login brute-force himoyasi (parolni cheksiz tanlashni to'sadi) ──
LOGIN_MAX_URINISH = 7          # necha marta xato -> bloklanadi
LOGIN_BLOK_DAQIQA = 15         # necha daqiqaga bloklanadi


def _login_kalit(request, username):
    return f"login_fail:{client_ip(request)}:{(username or '').lower()}"


def _login_hisob_kaliti(username):
    # IP'dan qat'i nazar bitta hisobga urinishlar (IP almashtirib tanlashdan himoya)
    return f"login_fail_user:{(username or '').lower()}"


def login_view(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        kalit = _login_kalit(request, username)
        # Juda ko'p xato urinishdan keyin vaqtincha bloklaymiz
        hisob_kalit = _login_hisob_kaliti(username)
        if cache.get(kalit, 0) >= LOGIN_MAX_URINISH or cache.get(hisob_kalit, 0) >= LOGIN_MAX_URINISH * 4:
            messages.error(request, f"Juda ko'p urinish. {LOGIN_BLOK_DAQIQA} daqiqadan keyin qayta urining.")
            return render(request, 'login.html')
        user = authenticate(request, username=username, password=password)
        if user:
            if not user.tasdiqlangan and user.rol in ['sotuvchi']:
                messages.error(request, "Hisobingiz hali tasdiqlanmagan!")
                return render(request, 'login.html')
            cache.delete(kalit)   # muvaffaqiyatli kirish -> hisoblagichni tozalaymiz
            cache.delete(hisob_kalit)
            login(request, user)
            return _redirect_by_role(user)
        # Xato urinishni qayd qilamiz
        cache.set(kalit, cache.get(kalit, 0) + 1, LOGIN_BLOK_DAQIQA * 60)
        cache.set(hisob_kalit, cache.get(hisob_kalit, 0) + 1, LOGIN_BLOK_DAQIQA * 60)
        messages.error(request, "Login yoki parol noto'g'ri!")
    return render(request, 'login.html')


def register_view(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    if request.method == 'POST':
        data = request.POST
        username = data.get('username', '').strip().lower()
        password = data.get('password', '')
        ism = data.get('ism', '').strip()
        telefon = data.get('telefon', '').strip()
        rol = data.get('rol', '')

        email = data.get('email', '').strip().lower()
        soliq_raqami = data.get('soliq_raqami', '').strip()
        mashina_raqami = data.get('mashina_raqami', '').strip()

        if not username or not password or not rol:
            messages.error(request, "Barcha maydonlarni to'ldiring!")
            return render(request, 'register.html')
        if rol not in ('dokon_egasi', 'sotuvchi', 'zavod', 'yetkazib_beruvchi', 'mijoz'):
            messages.error(request, "Noto'g'ri rol tanlandi!")
            return render(request, 'register.html')

        # Ism — faqat harflar
        _ism_xato = ism_xatosi(ism)
        if _ism_xato:
            messages.error(request, _ism_xato)
            return render(request, 'register.html')

        # Username — Instagram uslubidagi format
        _uname_xato = username_xatosi(username)
        if _uname_xato:
            messages.error(request, f"Username: {_uname_xato}")
            return render(request, 'register.html')

        # Parol kamida 6 ta belgi (#8)
        if len(password) < 6:
            messages.error(request, "Parol kamida 6 ta belgidan iborat bo'lishi kerak!")
            return render(request, 'register.html')
        try:
            validate_password(password, CustomUser(username=username, email=email, first_name=ism))
        except ValidationError as e:
            messages.error(request, _parol_xatolari(e))
            return render(request, 'register.html')

        if CustomUser.objects.filter(username__iexact=username).exists():
            messages.error(request, "Bu username band!")
            return render(request, 'register.html')

        # Email — parolni tiklash uchun kerak (#1)
        if not email:
            messages.error(request, "Email manzilini kiriting!")
            return render(request, 'register.html')
        if CustomUser.objects.filter(email__iexact=email).exists():
            messages.error(request, "Bu email allaqachon ro'yxatdan o'tilgan!")
            return render(request, 'register.html')

        # Takroriy ro'yxatdan o'tishni oldini olish (#9)
        # (Pasport/JSHSHR endi so'ralmaydi — POS uchun kerak emas, shaxsiy ma'lumot xavfi.)
        if soliq_raqami and (
            DokonEgasiProfil.objects.filter(soliq_raqami=soliq_raqami).exists()
            or ZavodProfil.objects.filter(soliq_raqami=soliq_raqami).exists()
        ):
            messages.error(request, "Bu INN (soliq raqami) allaqachon ro'yxatdan o'tilgan!")
            return render(request, 'register.html')
        if rol == 'yetkazib_beruvchi' and mashina_raqami and \
                YetkazibBeruvchiProfil.objects.filter(mashina_raqami__iexact=mashina_raqami).exists():
            messages.error(request, "Bu avtomobil raqami allaqachon ro'yxatdan o'tilgan!")
            return render(request, 'register.html')

        # Do'kon egasi uchun joylashuv majburiy (#7)
        if rol == 'dokon_egasi' and not (data.get('latitude') and data.get('longitude')):
            messages.error(request, "Do'kon joylashuvini belgilash majburiy!")
            return render(request, 'register.html')

        # Email tasdiqlash: kod 60 soniya amal qiladi, faqat oxirgi kod ishlaydi
        tasdiq_kodi = data.get('tasdiq_kodi', '').strip()
        code_key, attempts_key, block_key = _reg_keys(email)
        cached_code = cache.get(code_key)
        if not cached_code:
            messages.error(request, "Tasdiqlash kodi muddati tugagan (60 soniya). Iltimos, qayta kod yuboring.")
            return render(request, 'register.html')
        if not tasdiq_kodi or tasdiq_kodi != cached_code:
            messages.error(request, "Tasdiqlash kodi noto'g'ri!")
            return render(request, 'register.html')
        # Muvaffaqiyatli tasdiqlandi — cache tozalanadi
        cache.delete(code_key)
        cache.delete(attempts_key)
        cache.delete(block_key)

        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=ism,
            telefon=telefon,
            rol=rol,
            tasdiqlangan=False,
        )

        if rol == 'dokon_egasi':
            user.tasdiqlangan = True
            user.save()

            lat = data.get('latitude', '') or None
            lng = data.get('longitude', '') or None

            DokonEgasiProfil.objects.create(
                foydalanuvchi=user,
                dokon_nomi=data.get('dokon_nomi', ''),
                soliq_raqami=data.get('soliq_raqami', ''),
                manzil=data.get('manzil', ''),
                latitude=float(lat) if lat else None,
                longitude=float(lng) if lng else None,
            )
            messages.success(request, "Muvaffaqiyatli ro'yxatdan o'tdingiz!")
            login(request, user)
            return _redirect_by_role(user)

        elif rol == 'sotuvchi':
            # So'rov FAQAT do'kon egasining username'i orqali yuboriladi (#22)
            dokon_username = data.get('dokon_username', '').strip()
            dokon = None
            if dokon_username:
                owner = CustomUser.objects.filter(
                    username__iexact=dokon_username, rol='dokon_egasi'
                ).first()
                if owner:
                    dokon = DokonEgasiProfil.objects.filter(foydalanuvchi=owner).first()
            if not dokon:
                user.delete()
                messages.error(request, "Bunday username bilan do'kon egasi topilmadi! Do'kon egasining username'ini to'g'ri kiriting.")
                return render(request, 'register.html')
            SotuvchiProfil.objects.create(
                foydalanuvchi=user,
                dokon=dokon,
                sorov_holati='kutilmoqda',
            )
            messages.success(request, "So'rov yuborildi! Dokon egasi tasdiqlashini kuting.")

        elif rol == 'zavod':
            user.tasdiqlangan = True
            user.save()
            zp = ZavodProfil.objects.create(
                foydalanuvchi=user,
                zavod_nomi=data.get('zavod_nomi', ''),
                soliq_raqami=data.get('soliq_raqami', ''),
                mchj_nomi=data.get('mchj_nomi', ''),
                mahsulot_turi=data.get('mahsulot_turi', ''),
            )
            if 'hujjat' in request.FILES:
                from .validators import hujjat_kengaytma, hujjat_hajmi
                fayl = request.FILES['hujjat']
                try:
                    hujjat_kengaytma(fayl)
                    hujjat_hajmi(fayl)
                    zp.hujjatlar = fayl
                    zp.save()
                except ValidationError as e:
                    messages.warning(request, "Hujjat qabul qilinmadi: " + " ".join(e.messages))
            messages.success(request, "Muvaffaqiyatli ro'yxatdan o'tdingiz!")
            login(request, user)
            return _redirect_by_role(user)

        elif rol == 'yetkazib_beruvchi':
            mashina_raqami = data.get('mashina_raqami', '').strip()
            if not mashina_raqami:
                user.delete()
                messages.error(request, "Davlat raqamini kiriting!")
                return render(request, 'register.html')
            user.tasdiqlangan = True
            user.save()
            YetkazibBeruvchiProfil.objects.create(
                foydalanuvchi=user,
                mashina_raqami=mashina_raqami,
                mashina_turi=data.get('mashina_turi', ''),
            )
            messages.success(request, "Muvaffaqiyatli ro'yxatdan o'tdingiz!")
            login(request, user)
            return _redirect_by_role(user)

        elif rol == 'mijoz':
            user.tasdiqlangan = True
            user.save()
            MijozProfil.objects.create(foydalanuvchi=user)
            messages.success(request, "Muvaffaqiyatli ro'yxatdan o'tdingiz!")
            login(request, user)
            return _redirect_by_role(user)

    return render(request, 'register.html')


def logout_view(request):
    logout(request)
    return redirect('login')


PW_KOD_TTL = 600          # tiklash kodi 10 daqiqa amal qiladi
PW_MAX_XATO = 5           # 5 ta noto'g'ri urinishdan keyin kod bekor qilinadi
PW_MAX_YUBORISH = 3       # bir hisobga soatiga 3 ta kod
PW_IP_MAX = 10            # bir IP'dan soatiga 10 ta so'rov


def _kod_hash(code):
    return hashlib.sha256(f"{settings.SECRET_KEY}:{code}".encode()).hexdigest()


def forgot_password_view(request):
    """Parolni EMAIL orqali tiklash: kod yuborish -> kod + yangi parol.

    Xavfsizlik: kod serverda (keshda) foydalanuvchi bo'yicha HASH ko'rinishida saqlanadi,
    10 daqiqa amal qiladi va 5 ta xato urinishdan keyin bekor bo'ladi; yuborish soni
    cheklangan; email bor-yo'qligi oshkor qilinmaydi; kod faqat lokal (DEBUG) rejimda
    ekranda ko'rsatiladi."""
    umumiy_xabar = ("Agar bu email ro'yxatdan o'tgan bo'lsa, unga tasdiqlash kodi yuborildi. "
                    "Pochtangizni (va Spam papkasini) tekshiring.")

    if request.method == 'POST':
        action = request.POST.get('action', 'send_code')

        if action == 'send_code':
            email = request.POST.get('email', '').strip().lower()
            ip_kalit = f"pw_ip:{client_ip(request)}"
            if cache.get(ip_kalit, 0) >= PW_IP_MAX:
                messages.error(request, "Juda ko'p urinish. Birozdan so'ng qayta urining.")
                return render(request, 'forgot_password.html', {'step': 'email'})
            cache.set(ip_kalit, cache.get(ip_kalit, 0) + 1, 3600)
            request.session['pw_reset_email'] = email

            user = CustomUser.objects.filter(email__iexact=email).first() if email else None
            if user:
                yub_kalit = f"pw_send:{user.id}"
                if cache.get(yub_kalit, 0) < PW_MAX_YUBORISH:
                    cache.set(yub_kalit, cache.get(yub_kalit, 0) + 1, 3600)
                    code = _kod_yarat()
                    cache.set(f"pw_code:{user.id}", {'h': _kod_hash(code), 'xato': 0}, PW_KOD_TTL)
                    try:
                        if _email_sozlanmagan_prod():
                            raise RuntimeError("Email sozlanmagan")
                        send_mail(
                            subject="Savdoyim — Parolni tiklash kodi",
                            message=(
                                f"Assalomu alaykum!\n\n"
                                f"Sizning login (username): {user.username}\n"
                                f"Parolni tiklash kodi: {code} (10 daqiqa amal qiladi)\n\n"
                                f"Agar bu so'rovni siz yubormagan bo'lsangiz, ushbu xabarni e'tiborsiz qoldiring.\n\n"
                                f"Savdoyim jamoasi"
                            ),
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[user.email],
                            fail_silently=False,
                        )
                        if test_rejimi():
                            messages.info(request, f"LOKAL TEST REJIMI (email sozlanmagan). Kod: {code}")
                    except Exception:
                        cache.delete(f"pw_code:{user.id}")
                        messages.error(request, "Email hozircha yuborilmadi. Iltimos, birozdan so'ng qayta urinib ko'ring.")
                        return render(request, 'forgot_password.html', {'step': 'email'})
            messages.success(request, umumiy_xabar)
            return render(request, 'forgot_password.html', {'step': 'code', 'email': email})

        elif action == 'reset':
            code = request.POST.get('code', '').strip()
            new_password = request.POST.get('new_password', '')
            email = request.session.get('pw_reset_email', '')
            user = CustomUser.objects.filter(email__iexact=email).first() if email else None
            yozuv = cache.get(f"pw_code:{user.id}") if user else None
            if not yozuv:
                messages.error(request, "Kod noto'g'ri yoki muddati tugagan. Qaytadan kod oling.")
                return render(request, 'forgot_password.html', {'step': 'email'})
            if not secrets.compare_digest(yozuv['h'], _kod_hash(code)):
                yozuv['xato'] += 1
                if yozuv['xato'] >= PW_MAX_XATO:
                    cache.delete(f"pw_code:{user.id}")
                    messages.error(request, "Juda ko'p noto'g'ri urinish. Qaytadan kod oling.")
                    return render(request, 'forgot_password.html', {'step': 'email'})
                cache.set(f"pw_code:{user.id}", yozuv, PW_KOD_TTL)
                messages.error(request, "Kod noto'g'ri!")
                return render(request, 'forgot_password.html', {'step': 'code', 'email': email})
            try:
                validate_password(new_password, user)
            except ValidationError as e:
                messages.error(request, "Yangi parol: " + _parol_xatolari(e))
                return render(request, 'forgot_password.html', {'step': 'code', 'email': email})
            cache.delete(f"pw_code:{user.id}")
            user.set_password(new_password)
            user.save()
            # Parol tiklandi -> eski sessiyalar, API token va Telegram bog'lanishi bekor
            foydalanuvchi_kirishlarini_bekor_qil(user)
            request.session.pop('pw_reset_email', None)
            messages.success(request, "Parol muvaffaqiyatli o'zgartirildi! Endi kirishingiz mumkin.")
            return redirect('login')

    return render(request, 'forgot_password.html', {'step': 'email'})


def _onboarding_qur(sarlavha, izoh, qadamlar):
    """Onboarding checklist dict'ini quradi. Progress qadamlarning `bajarildi`
    holatidan hisoblanadi; barcha `majburiy` qadam tugagach `korsat` False bo'ladi
    (karta o'zi yashiriladi). Migratsiya kerak emas — hammasi ma'lumotdan."""
    bajarilgan = sum(1 for q in qadamlar if q['bajarildi'])
    majburiy_tugadi = all(q['bajarildi'] for q in qadamlar if q.get('majburiy'))
    return {
        'sarlavha': sarlavha, 'izoh': izoh, 'qadamlar': qadamlar,
        'bajarilgan': bajarilgan, 'jami': len(qadamlar),
        'foiz': int(bajarilgan / len(qadamlar) * 100) if qadamlar else 0,
        'korsat': not majburiy_tugadi,
    }


@login_required
def dokon_egasi_dashboard(request):
    try:
        profil = request.user.dokon_profil
    except DokonEgasiProfil.DoesNotExist:
        messages.error(request, "Dokon profil topilmadi!")
        return redirect('login')

    from kassa.models import Kassa, QarzDaftar
    from mahsulot.models import Mahsulot

    kassa = Kassa.objects.filter(dokon=profil).first()
    mahsulotlar = list(Mahsulot.objects.filter(dokon=profil))
    # "Tugayotgan" stat kartasi uchun — faqat FAOL (sotiladigan) mahsulotlar
    # (nofaol/yashirilgan mahsulot bejiz sanalmasligi uchun).
    tugayotgan = [m for m in mahsulotlar if m.faol and m.soni <= m.minimum_son]
    qarzlar = QarzDaftar.objects.filter(dokon=profil, to_langan=False)

    kutilmoqda_soni = SotuvchiProfil.objects.filter(
        dokon=profil, sorov_holati='kutilmoqda'
    ).count()

    # Yillik savdo (12 oy) — trading chart uchun. 30 mln = to'la (100%).
    from kassa.models import SavdoChek
    from django.db.models import Sum
    from datetime import date
    import calendar
    _OY = ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyn', 'Iyl', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek']
    bugun = timezone.localdate()
    yillik_data = []
    for oy in range(1, 13):
        bosh = date(bugun.year, oy, 1)
        _, oxir = calendar.monthrange(bugun.year, oy)
        oxir_d = date(bugun.year, oy, oxir)
        if bosh > bugun:
            summa = None  # kelgusi oy
        else:
            summa = float(SavdoChek.objects.filter(
                dokon=profil,
                yaratilgan__date__gte=bosh,
                yaratilgan__date__lte=min(oxir_d, bugun),
            ).aggregate(s=Sum('jami'))['s'] or 0)
        foiz = min(round(summa / 30_000_000 * 100, 1), 100) if summa else 0
        yillik_data.append({'nom': _OY[oy - 1], 'summa': summa, 'foiz': foiz})

    # AI agent (bepul) — anomaliya ogohlantirishlari
    from kassa.anomaliya_service import anomaliyalar
    ogohlantirishlar = anomaliyalar(profil)

    # ── Onboarding checklist (yangi do'kon 5 daqiqada ishga tushsin) ──
    # Progress to'g'ridan-to'g'ri ma'lumotdan hisoblanadi — MIGRATSIYA KERAK EMAS.
    # Majburiy qadamlar (mahsulot + savdo) tugagach checklist o'zi yo'qoladi.
    _mahsulot_bor = len(mahsulotlar) > 0
    _savdo_bor = SavdoChek.objects.filter(dokon=profil).exists()
    _manzil_bor = bool((profil.manzil or '').strip())
    _sotuvchi_bor = SotuvchiProfil.objects.filter(
        dokon=profil, sorov_holati='tasdiqlangan'
    ).exists()
    onboarding = _onboarding_qur(
        "Do'koningizni ishga tushiring",
        "Bir necha qadamda tizimni to'liq faollashtiring",
        [
            {'nomi': "Do'kon ma'lumotlari", 'tavsif': "Manzil va logotip qo'shing",
             'bajarildi': _manzil_bor, 'url': reverse('profil'),
             'icon': 'fa-store', 'majburiy': False},
            {'nomi': "Birinchi mahsulot", 'tavsif': "Omborga mahsulot qo'shing",
             'bajarildi': _mahsulot_bor, 'url': reverse('mahsulot_qoshish'),
             'icon': 'fa-box', 'majburiy': True},
            {'nomi': "Birinchi savdo", 'tavsif': "Kassadan sinov savdosini o'tkazing",
             'bajarildi': _savdo_bor, 'url': reverse('kassa'),
             'icon': 'fa-cash-register', 'majburiy': True},
            {'nomi': "Sotuvchi qo'shish", 'tavsif': "Xodimingizni taklif qiling (ixtiyoriy)",
             'bajarildi': _sotuvchi_bor, 'url': reverse('sotuvchi_ruxsat'),
             'icon': 'fa-user-plus', 'majburiy': False},
        ],
    )

    return render(request, 'dokon_egasi/dashboard.html', {
        'onboarding': onboarding,
        'profil': profil,
        'kassa': kassa,
        'mahsulotlar': mahsulotlar,
        'tugayotgan': tugayotgan,
        'qarzlar': qarzlar,
        'kutilmoqda_soni': kutilmoqda_soni,
        'yillik_data': yillik_data,
        'ogohlantirishlar': ogohlantirishlar,
    })


@login_required
def sotuvchi_dashboard(request):
    try:
        profil = request.user.sotuvchi_profil
    except SotuvchiProfil.DoesNotExist:
        return redirect('login')

    if profil.sorov_holati != 'tasdiqlangan':
        return render(request, 'sotuvchi/kutish.html', {'holat': profil.sorov_holati})

    from mahsulot.models import Mahsulot
    from kassa.models import Kassa, QarzDaftar

    dokon = profil.dokon
    mahsulotlar = list(Mahsulot.objects.filter(dokon=dokon)) if dokon else []
    kassa = Kassa.objects.filter(dokon=dokon).first() if dokon else None
    qarzlar = QarzDaftar.objects.filter(dokon=dokon, to_langan=False) if dokon else []

    return render(request, 'sotuvchi/dashboard.html', {
        'profil': profil,
        'mahsulotlar': mahsulotlar,
        'kassa': kassa,
        'qarzlar': qarzlar,
    })


@login_required
def zavod_dashboard(request):
    try:
        profil = request.user.zavod_profil
    except ZavodProfil.DoesNotExist:
        return redirect('login')

    from mahsulot.models import Mahsulot
    from buyurtma.models import Buyurtma

    mahsulotlar = list(Mahsulot.objects.filter(zavod=profil).select_related('dokon'))
    buyurtmalar = Buyurtma.objects.filter(zavod=profil).select_related('dokon').order_by('-yaratilgan')[:20]
    kam_mahsulotlar = [m for m in mahsulotlar if m.soni <= m.minimum_son]

    from yetkazib_beruvchi.models import Jonatma
    _mahsulot_bor = len(mahsulotlar) > 0
    _jonatma_bor = Jonatma.objects.filter(zavod=profil).exists()
    _malumot_bor = bool((profil.mchj_nomi or '').strip() or (profil.mahsulot_turi or '').strip())
    onboarding = _onboarding_qur(
        "Zavodingizni ishga tushiring",
        "Katalog qo'shing va do'konlarga jo'natmani boshlang",
        [
            {'nomi': "Zavod ma'lumotlari", 'tavsif': "MCHJ va mahsulot turini to'ldiring",
             'bajarildi': _malumot_bor, 'url': reverse('profil'),
             'icon': 'fa-industry', 'majburiy': False},
            {'nomi': "Birinchi mahsulot", 'tavsif': "Katalogga mahsulot qo'shing",
             'bajarildi': _mahsulot_bor, 'url': reverse('mahsulot_qoshish'),
             'icon': 'fa-box', 'majburiy': True},
            {'nomi': "Birinchi jo'natma", 'tavsif': "Do'konga mahsulot jo'nating",
             'bajarildi': _jonatma_bor, 'url': reverse('zavod_jonatma_yaratish'),
             'icon': 'fa-truck', 'majburiy': True},
        ],
    )

    return render(request, 'zavod/dashboard.html', {
        'profil': profil,
        'mahsulotlar': mahsulotlar,
        'buyurtmalar': buyurtmalar,
        'kam_mahsulotlar': kam_mahsulotlar,
        'onboarding': onboarding,
    })


@login_required
def yetkazuvchi_dashboard(request):
    try:
        profil = request.user.yetkazuvchi_profil
    except YetkazibBeruvchiProfil.DoesNotExist:
        return redirect('login')

    from yetkazib_beruvchi.models import Jonatma

    jonatmalar = list(Jonatma.objects.filter(
        yetkazuvchi=profil
    ).prefetch_related('mahsulotlar__mahsulot__dokon').order_by('-yaratilgan'))

    # Aqlli xarita/marshrut uchun — yetkazilishi kerak bo'lgan (yakunlanmagan)
    # jo'natmalarning manzil koordinatalari
    faol_holatlar = ('qabul_kutilmoqda', 'qabul_qilindi', 'yolda')
    manzillar = []
    for j in jonatmalar:
        if j.holat in faol_holatlar and j.xaritada_bormi:
            manzillar.append({
                'id': j.id,
                'nomi': j.manzil_nomi or f"Jo'natma #{j.id}",
                'manzil': j.manzil_matn,
                'lat': j.manzil_lat,
                'lng': j.manzil_lng,
                'holat': j.holat,
            })

    _jonatma_bor = len(jonatmalar) > 0
    _yetkazdi = any(j.holat == 'yetkazildi' for j in jonatmalar)
    _transport_bor = bool((profil.mashina_turi or '').strip())
    onboarding = _onboarding_qur(
        "Ishga tayyorlaning",
        "Transport ma'lumotini to'ldiring va birinchi yetkazishni bajaring",
        [
            {'nomi': "Transport ma'lumotlari", 'tavsif': "Mashina turini ko'rsating",
             'bajarildi': _transport_bor, 'url': reverse('profil'),
             'icon': 'fa-truck', 'majburiy': False},
            {'nomi': "Birinchi jo'natma", 'tavsif': "Sizga biriktirilgan jo'natmani ko'ring",
             'bajarildi': _jonatma_bor, 'url': reverse('yetkazuvchi_jonatmalar'),
             'icon': 'fa-box', 'majburiy': False},
            {'nomi': "Birinchi yetkazish", 'tavsif': "Jo'natmani yetkazib yakunlang",
             'bajarildi': _yetkazdi, 'url': reverse('yetkazuvchi_jonatmalar'),
             'icon': 'fa-flag-checkered', 'majburiy': True},
        ],
    )

    return render(request, 'yetkazib_beruvchi/dashboard.html', {
        'profil': profil,
        'jonatmalar': jonatmalar,
        'manzillar': manzillar,
        'onboarding': onboarding,
    })


def _mahsulot_browse_context(request):
    """Marketplace mahsulot ro'yxati/qidiruv/kategoriya konteksti.
    Ham mijoz (dashboard), ham mehmon (guest) sahifalari uchun umumiy."""
    from mahsulot.models import Mahsulot, Kategoriya

    qidiruv = request.GET.get('q', '').strip()
    kategoriya_nomi = request.GET.get('kategoriya', '').strip()
    kategoriyalar = Kategoriya.objects.all()

    # Faqat DO'KON mahsulotlari marketplace'da ko'rinadi. Zavod o'z katalogiga
    # qo'shgan mahsulot (dokon=None) mijoz/mehmonga chiqmaydi.
    baza = Mahsulot.objects.filter(
        soni__gt=0, faol=True, dokon__isnull=False
    ).select_related('dokon')
    tavsiya = False

    if qidiruv:
        # Nom bo'yicha qidiruv
        mahsulotlar = baza.filter(nomi__icontains=qidiruv)
    elif kategoriya_nomi:
        # Faqat tanlangan kategoriya mahsulotlari (#17)
        mahsulotlar = baza.filter(kategoriya__nomi=kategoriya_nomi).order_by('-yaratilgan')
    else:
        # Tavsiyalar: yangi qo'shilgan mahsulotlar yuqorida (#18)
        mahsulotlar = baza.order_by('-yaratilgan')[:24]
        tavsiya = True

    return {
        'mahsulotlar': mahsulotlar,
        'qidiruv': qidiruv,
        'kategoriyalar': kategoriyalar,
        'tanlangan_kategoriya': kategoriya_nomi,
        'tavsiya': tavsiya,
    }


def home_redirect(request):
    """Bosh sahifa: kirgan foydalanuvchi -> o'z paneliga, mehmon -> ochiq marketplace."""
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)
    return redirect('mehmon_dashboard')


def mehmon_dashboard(request):
    """Guest (mehmon) marketplace — tizimga kirmasdan mahsulotlarni ko'rish/qidirish.
    Kirgan foydalanuvchi bo'lsa o'z paneliga yo'naltiriladi (mijoz -> dashboard)."""
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    ctx = _mahsulot_browse_context(request)
    ctx.update({
        'mehmon': True,                             # base.html guest chrome'ini yoqadi
        'bosh_url': reverse('mehmon_dashboard'),    # "Hammasi" chip / kategoriya bazasi
    })
    return render(request, 'mijoz/dashboard.html', ctx)


@login_required
def mijoz_dashboard(request):
    try:
        profil = request.user.mijoz_profil
    except MijozProfil.DoesNotExist:
        return redirect('login')

    ctx = _mahsulot_browse_context(request)
    ctx.update({
        'profil': profil,
        'bosh_url': reverse('mijoz_dashboard'),
    })
    return render(request, 'mijoz/dashboard.html', ctx)


@login_required
def sotuvchi_ruxsat(request):
    if request.user.rol != 'dokon_egasi':
        return redirect('login')
    try:
        dokon = request.user.dokon_profil
    except DokonEgasiProfil.DoesNotExist:
        return redirect('login')

    if request.method == 'POST':
        sotuvchi_id = request.POST.get('sotuvchi_id')
        harakat = request.POST.get('harakat')
        try:
            s = SotuvchiProfil.objects.get(id=sotuvchi_id, dokon=dokon)
            if harakat == 'tasdiqlash':
                s.sorov_holati = 'tasdiqlangan'
                s.foydalanuvchi.tasdiqlangan = True
                s.foydalanuvchi.save()
                s.save()
                # Sotuvchiga xabar: sayt + email + Telegram
                from .services import NotificationService
                NotificationService.send_sotuvchi_tasdiq(s, True)
                messages.success(request, f"✅ {s.foydalanuvchi.first_name or s.foydalanuvchi.username} tasdiqlandi! Sotuvchiga xabar yuborildi.")
            elif harakat == 'rad':
                s.sorov_holati = 'rad_etilgan'
                s.foydalanuvchi.tasdiqlangan = False
                s.foydalanuvchi.save()
                s.save()
                from .services import NotificationService
                NotificationService.send_sotuvchi_tasdiq(s, False)
                # Rad etilgan sotuvchining barcha kirishlari (sessiya, API token, Telegram) bekor
                foydalanuvchi_kirishlarini_bekor_qil(s.foydalanuvchi)
                messages.success(request, f"❌ {s.foydalanuvchi.first_name or s.foydalanuvchi.username} rad etildi.")
            else:
                s.save()
        except SotuvchiProfil.DoesNotExist:
            messages.error(request, "Sotuvchi topilmadi!")
        return redirect('sotuvchi_ruxsat')

    sotuvchilar = SotuvchiProfil.objects.filter(
        dokon=dokon
    ).select_related('foydalanuvchi').order_by('-yaratilgan')

    kutilmoqda_soni = sotuvchilar.filter(sorov_holati='kutilmoqda').count()

    return render(request, 'dokon_egasi/sotuvchilar.html', {
        'sotuvchilar': sotuvchilar,
        'kutilmoqda_soni': kutilmoqda_soni,
    })


@login_required
def profil_view(request):
    """Foydalanuvchi profili — roliga qarab turli maydonlar (#3)."""
    user = request.user
    rol = user.rol
    fields = []

    if rol == 'dokon_egasi':
        p = DokonEgasiProfil.objects.filter(foydalanuvchi=user).first()
        fields = [
            ('Username', user.username),
            ('Kompaniya (MCHJ) nomi', (p.dokon_nomi if p else '') or '—'),
        ]
    elif rol == 'zavod':
        p = ZavodProfil.objects.filter(foydalanuvchi=user).first()
        kompaniya = ''
        if p:
            kompaniya = p.mchj_nomi or p.zavod_nomi
        fields = [
            ('Username', user.username),
            ('Kompaniya (MCHJ) nomi', kompaniya or '—'),
        ]
    elif rol in ('mijoz', 'sotuvchi'):
        fields = [
            ('Ism', user.first_name or '—'),
            ('Telefon raqami', user.telefon or '—'),
        ]
    elif rol == 'yetkazib_beruvchi':
        p = YetkazibBeruvchiProfil.objects.filter(foydalanuvchi=user).first()
        rusum = ''
        if p and p.mashina_turi:
            rusum = p.get_mashina_turi_display()
        fields = [
            ('Mashina rusumi', rusum or '—'),
            ('Avtomobil raqami', (p.mashina_raqami if p else '') or '—'),
        ]
    else:
        fields = [('Username', user.username)]

    return render(request, 'profil.html', {
        'profil_user': user,
        'rol_display': user.get_rol_display(),
        'fields': fields,
    })


# ═══════════════════════════════════════════════
#  SOZLAMALAR (Settings) — theme, bildirishnoma, profil tahrirlash
# ═══════════════════════════════════════════════
ACCENT_KOMBOLAR = [
    ('blue',    'Ko\'k',      '#4f8cff'),
    ('emerald', 'Zumrad',    '#10c98b'),
    ('violet',  'Siyohrang', '#8b5cf6'),
    ('rose',    'Marjon',    '#f43f6e'),
    ('amber',   'Kahrabo',   '#f5920b'),
    ('cyan',    'Moviy',     '#0ea5e9'),
]


def _bot_ulangan(user):
    from .models import TelegramLink
    return TelegramLink.objects.filter(foydalanuvchi=user).exists()


@login_required
def settings_view(request):
    """Sozlamalar sahifasi — theme, bildirishnoma, profil."""
    user = request.user
    bot_yoq = None
    if user.rol == 'dokon_egasi':
        from kassa.models import AvtoHisobotSozlama
        p = DokonEgasiProfil.objects.filter(foydalanuvchi=user).first()
        if p:
            avto, _ = AvtoHisobotSozlama.objects.get_or_create(dokon=p)
            bot_yoq = avto.kunlik_yoq
    return render(request, 'settings.html', {
        'accent_kombolar': ACCENT_KOMBOLAR,
        'sayt_bildirishnoma': user.sayt_bildirishnoma,
        'bot_yoq': bot_yoq,
        'bot_ulangan': _bot_ulangan(user),
    })


@login_required
@require_POST
def settings_action(request):
    """Sozlamalarni saqlash — 'action' bo'yicha yo'naltiradi (AJAX/JSON)."""
    user = request.user
    action = request.POST.get('action', '')

    # ── Sayt/bot bildirishnoma toggle ──
    if action == 'notif':
        user.sayt_bildirishnoma = request.POST.get('sayt') == '1'
        user.save(update_fields=['sayt_bildirishnoma'])
        if user.rol == 'dokon_egasi' and 'bot' in request.POST:
            from kassa.models import AvtoHisobotSozlama
            p = DokonEgasiProfil.objects.filter(foydalanuvchi=user).first()
            if p:
                avto, _ = AvtoHisobotSozlama.objects.get_or_create(dokon=p)
                avto.kunlik_yoq = request.POST.get('bot') == '1'
                avto.ombor_yoq = avto.kunlik_yoq
                avto.save(update_fields=['kunlik_yoq', 'ombor_yoq'])
        return JsonResponse({'ok': True, 'message': 'Bildirishnoma sozlamalari saqlandi.'})

    # ── Ism o'zgartirish ──
    if action == 'name':
        yangi = request.POST.get('first_name', '').strip()
        if not yangi:
            return JsonResponse({'ok': False, 'message': 'Ism bo\'sh bo\'lishi mumkin emas.'}, status=400)
        user.first_name = yangi[:150]
        user.save(update_fields=['first_name'])
        return JsonResponse({'ok': True, 'message': 'Ism yangilandi.', 'value': user.first_name})

    # ── Parol o'zgartirish (eski + yangi x2) ──
    if action == 'password':
        eski = request.POST.get('eski', '')
        yangi = request.POST.get('yangi', '')
        yangi2 = request.POST.get('yangi2', '')
        if not user.check_password(eski):
            return JsonResponse({'ok': False, 'message': 'Eski parol noto\'g\'ri.'}, status=400)
        if len(yangi) < 6:
            return JsonResponse({'ok': False, 'message': 'Yangi parol kamida 6 belgidan iborat bo\'lsin.'}, status=400)
        if yangi != yangi2:
            return JsonResponse({'ok': False, 'message': 'Yangi parollar mos kelmadi.'}, status=400)
        try:
            validate_password(yangi, user)
        except ValidationError as e:
            return JsonResponse({'ok': False, 'message': _parol_xatolari(e)}, status=400)
        user.set_password(yangi)
        user.save(update_fields=['password'])
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, user)
        # Boshqa qurilmalardagi sessiyalar, API token va Telegram bog'lanishi bekor qilinadi
        foydalanuvchi_kirishlarini_bekor_qil(user, joriy_sessiya=request.session.session_key)
        return JsonResponse({'ok': True, 'message': 'Parol muvaffaqiyatli o\'zgartirildi.'})

    # ── Email o'zgartirish: 1) kod yuborish ──
    if action == 'email_code':
        yangi = request.POST.get('email', '').strip().lower()
        if '@' not in yangi:
            return JsonResponse({'ok': False, 'message': 'To\'g\'ri email kiriting.'}, status=400)
        if CustomUser.objects.filter(email__iexact=yangi).exclude(id=user.id).exists():
            return JsonResponse({'ok': False, 'message': 'Bu email allaqachon ro\'yxatdan o\'tgan.'}, status=400)
        kod = _kod_yarat()
        cache.set(f'email_change:{user.id}', {'email': yangi, 'kod': kod}, 600)
        try:
            send_mail('Savdoyim — email tasdiqlash',
                      f'Yangi email tasdiqlash kodi: {kod}',
                      settings.DEFAULT_FROM_EMAIL, [yangi], fail_silently=False)
        except Exception:
            return JsonResponse({'ok': False, 'message': 'Kod yuborilmadi. Keyinroq urinib ko\'ring.'}, status=500)
        return JsonResponse({'ok': True, 'message': f'Tasdiqlash kodi {yangi} ga yuborildi.'})

    # ── Email o'zgartirish: 2) kodni tasdiqlash ──
    if action == 'email_verify':
        kiritilgan = request.POST.get('kod', '').strip()
        data = cache.get(f'email_change:{user.id}')
        if not data:
            return JsonResponse({'ok': False, 'message': 'Kod muddati tugagan. Qaytadan yuboring.'}, status=400)
        if kiritilgan != data['kod']:
            return JsonResponse({'ok': False, 'message': 'Kod noto\'g\'ri.'}, status=400)
        if CustomUser.objects.filter(email__iexact=data['email']).exclude(id=user.id).exists():
            return JsonResponse({'ok': False, 'message': 'Bu email band qilingan.'}, status=400)
        user.email = data['email']
        user.save(update_fields=['email'])
        cache.delete(f'email_change:{user.id}')
        return JsonResponse({'ok': True, 'message': 'Email yangilandi.', 'value': user.email})

    return JsonResponse({'ok': False, 'message': 'Noma\'lum amal.'}, status=400)


# Kim kimni baholay oladi (#5)
#   Mijoz -> do'kon egasi, sotuvchi
#   Do'kon egasi -> zavod, yetkazib beruvchi
REYTING_RUXSAT = {
    'mijoz': ['dokon_egasi', 'sotuvchi'],
    'dokon_egasi': ['zavod', 'yetkazib_beruvchi'],
}


def _reyting_nomi(user):
    """Baholanuvchining ko'rinadigan nomi (kompaniya bo'lsa kompaniya)."""
    dp = DokonEgasiProfil.objects.filter(foydalanuvchi=user).first()
    if dp:
        return dp.dokon_nomi
    zp = ZavodProfil.objects.filter(foydalanuvchi=user).first()
    if zp:
        return zp.mchj_nomi or zp.zavod_nomi
    return user.first_name or user.username


def _baholanuvchi_dokoni(baholanuvchi):
    """Baholanuvchi (do'kon egasi yoki sotuvchi) tegishli bo'lgan DokonEgasiProfil."""
    if baholanuvchi.rol == 'dokon_egasi':
        return DokonEgasiProfil.objects.filter(foydalanuvchi=baholanuvchi).first()
    if baholanuvchi.rol == 'sotuvchi':
        sp = SotuvchiProfil.objects.filter(foydalanuvchi=baholanuvchi).first()
        return sp.dokon if sp else None
    return None


def _mijoz_xarid_qilganmi(mijoz, baholanuvchi):
    """Mijoz shu do'kondan (baholanuvchi do'koni) buyurtma qilib, OLIB KETGANmi.
    Mahsulot sharhi bilan bir xil tamoyil: faqat yakunlangan xariddan keyin baho.
    """
    dokon = _baholanuvchi_dokoni(baholanuvchi)
    if not dokon:
        return False
    from buyurtma.models import MijozBuyurtma
    return MijozBuyurtma.objects.filter(
        mijoz=mijoz, dokon=dokon, holat='olib_ketildi'
    ).exists()


@login_required
def reytinglar(request, user_id):
    """Foydalanuvchining reytinglari — hamma ko'ra oladi (#5)."""
    baholanuvchi = get_object_or_404(CustomUser, id=user_id)
    qs = Reyting.objects.filter(baholanuvchi=baholanuvchi).select_related('baholovchi')
    agg = qs.aggregate(o=Avg('yulduz'))
    ortacha = round(agg['o'], 1) if agg['o'] else 0
    mening = qs.filter(baholovchi=request.user).first()
    can_rate = (
        request.user.id != baholanuvchi.id
        and baholanuvchi.rol in REYTING_RUXSAT.get(request.user.rol, [])
    )
    # Mijoz faqat XARID QILGAN (olib ketgan) do'kon/sotuvchini baholay oladi
    xarid_kerak = False
    if can_rate and request.user.rol == 'mijoz' and not mening:
        if not _mijoz_xarid_qilganmi(request.user, baholanuvchi):
            can_rate = False
            xarid_kerak = True
    return render(request, 'reyting/reytinglar.html', {
        'baholanuvchi': baholanuvchi,
        'baholanuvchi_nomi': _reyting_nomi(baholanuvchi),
        'baholanuvchi_rol': baholanuvchi.get_rol_display() if baholanuvchi.rol else '',
        'reytinglar': qs,
        'ortacha': ortacha,
        'soni': qs.count(),
        'mening': mening,
        'can_rate': can_rate,
        'xarid_kerak': xarid_kerak,
        'yulduzlar': [5, 4, 3, 2, 1],
    })


@login_required
@require_POST
def reyting_berish(request):
    """Baho qo'yish/yangilash (#5)."""
    baholanuvchi = get_object_or_404(CustomUser, id=request.POST.get('baholanuvchi_id'))
    try:
        yulduz = int(request.POST.get('yulduz', 0))
    except (TypeError, ValueError):
        yulduz = 0
    izoh = request.POST.get('izoh', '').strip()

    if request.user.id == baholanuvchi.id or \
            baholanuvchi.rol not in REYTING_RUXSAT.get(request.user.rol, []):
        messages.error(request, "Siz bu foydalanuvchini baholay olmaysiz.")
        return redirect('reytinglar', user_id=baholanuvchi.id)
    if yulduz < 1 or yulduz > 5:
        messages.error(request, "Iltimos, 1 dan 5 gacha yulduz tanlang.")
        return redirect('reytinglar', user_id=baholanuvchi.id)

    # Mijoz faqat xarid qilgan (olib ketgan) do'konini baholay oladi.
    # Mavjud bahoni tahrirlashga ruxsat (eski ma'lumotlar buzilmasin).
    mavjud = Reyting.objects.filter(
        baholovchi=request.user, baholanuvchi=baholanuvchi
    ).first()
    if request.user.rol == 'mijoz' and not mavjud and \
            not _mijoz_xarid_qilganmi(request.user, baholanuvchi):
        messages.error(
            request,
            "Faqat xarid qilib, buyurtmangizni olib ketgan do'koningizni baholay olasiz."
        )
        return redirect('reytinglar', user_id=baholanuvchi.id)

    Reyting.objects.update_or_create(
        baholovchi=request.user,
        baholanuvchi=baholanuvchi,
        defaults={'yulduz': yulduz, 'izoh': izoh},
    )
    messages.success(request, "Bahoyingiz saqlandi. Rahmat!")
    return redirect('reytinglar', user_id=baholanuvchi.id)


def about_view(request):
    """Biz haqimizda — ochiq sahifa (login shart emas)."""
    return render(request, 'about.html')


# ═══════════════════════════════════════════════
#  PWA — telefonga o'rnatiladigan ilova + offline
# ═══════════════════════════════════════════════
_PWA_MANIFEST = {
    "name": "Savdoyim", "short_name": "Savdoyim",
    "description": "Do'kon boshqaruv tizimi",
    "start_url": "/", "scope": "/", "display": "standalone",
    "orientation": "portrait", "background_color": "#070b14", "theme_color": "#4f8cff",
    "icons": [
        {"src": "/static/logo2.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
        {"src": "/static/logo3.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
    ],
}

_PWA_SW = """
// v2: shaxsiy sahifalar (hisobot, qarzlar, kassa) KESHLANMAYDI — boshqa odam shu
// qurilmada offline ochsa ko'rmasin. Faqat statik fayllar va rasmlar keshlanadi.
const CACHE='savdoyim-v2';
const CORE=['/static/i18n.js','/static/logod.png','/static/logol.png'];
const OFFLINE='<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Internet yo\'q</title><body style="font-family:sans-serif;text-align:center;padding:60px 20px"><h2>Internet aloqasi yo\'q</h2><p>Aloqa tiklangach sahifani yangilang.</p></body>';
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE)).catch(()=>{}));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));self.clients.claim();});
self.addEventListener('fetch',e=>{
  const req=e.request; if(req.method!=='GET')return;
  const url=new URL(req.url); if(url.origin!==location.origin)return;
  if(url.pathname.startsWith('/static/')||url.pathname.startsWith('/media/')){
    e.respondWith(caches.match(req).then(r=>r||fetch(req).then(res=>{if(res.ok){const cl=res.clone();caches.open(CACHE).then(c=>c.put(req,cl));}return res;})));
    return;
  }
  if(req.mode==='navigate'){
    e.respondWith(fetch(req).catch(()=>new Response(OFFLINE,{headers:{'Content-Type':'text/html; charset=utf-8'}})));
  }
});
"""


def pwa_manifest(request):
    return JsonResponse(_PWA_MANIFEST, content_type='application/manifest+json')


def pwa_service_worker(request):
    from django.http import HttpResponse
    resp = HttpResponse(_PWA_SW, content_type='application/javascript')
    resp['Service-Worker-Allowed'] = '/'
    return resp


@login_required
def bildirishnomalar(request):
    """Ilova ichidagi bildirishnomalar — ochilganda o'qilgan deb belgilanadi."""
    royxat = list(request.user.bildirishnomalar.all()[:100])
    request.user.bildirishnomalar.filter(oqilgan=False).update(oqilgan=True)
    return render(request, 'bildirishnoma/royxat.html', {'bildirishnomalar': royxat})
