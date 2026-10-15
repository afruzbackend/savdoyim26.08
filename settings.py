import os
from pathlib import Path
import sys
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

TOKENROUTER_API_KEY = os.getenv("TOKENROUTER_API_KEY")
# AI (hisobot yordamchisi) — TokenRouter OpenAI-mos endpoint.
#   AI_MODEL: .env da modelni tanlash. Kimi uchun masalan:
#             AI_MODEL=moonshotai/kimi-k2   (yoki TokenRouter bergan aniq nom)
#   Standart "auto:balance" — router eng mos modelni o'zi tanlaydi.
# Standart: Novita AI (Kimi K3 shu yerda). Boshqa provayderga o'tish uchun .env da o'zgartiring.
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.novita.ai/v3/openai")
AI_MODEL = os.getenv("AI_MODEL", "moonshotai/kimi-k3")
# API uslubi: "chat" — Novita/OpenAI/Moonshot; "responses" — TokenRouter.
AI_API = os.getenv("AI_API", "chat")

def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


# `manage.py test` — test muhiti (production tekshiruvlari o'chadi)
RUNNING_TESTS = len(sys.argv) > 1 and sys.argv[1] == 'test'

# Standart — PRODUCTION (xavfsiz). Lokal ishlab chiqishda .env da DJANGO_DEBUG=True qiling
# (ISHGA_TUSHIRISH.bat buni o'zi qo'yadi).
DEBUG = env_bool('DJANGO_DEBUG', False)
_DEV = DEBUG or RUNNING_TESTS

# Maxfiy kalit FAQAT .env dan. Productionda bo'lmasa — server ishga tushmaydi.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '').strip()
if not SECRET_KEY:
    if not _DEV:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY .env da berilmagan. "
            "Lokal kompyuterda ishlayotgan bo'lsangiz .env fayliga DJANGO_DEBUG=True yozing. "
            "Serverda esa kalit yarating: "
            "python -c \"import secrets; print(secrets.token_urlsafe(50))\""
        )
    SECRET_KEY = 'dev-faqat-lokal-' + 'x' * 40

# Productionda .env da DJANGO_ALLOWED_HOSTS=domen.uz,www.domen.uz,IP ko'rinishida bering.
_hosts = os.environ.get('DJANGO_ALLOWED_HOSTS', '').strip()
ALLOWED_HOSTS = [h.strip() for h in _hosts.split(',') if h.strip()]
if not ALLOWED_HOSTS:
    if not _DEV:
        raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS .env da berilmagan (masalan: savdoyim.uz,www.savdoyim.uz).")
    ALLOWED_HOSTS = ['*']   # faqat lokal/telefon testi uchun

# HTTPS orqali POST ishlashi uchun ishonchli manzillar (.env dan).
CSRF_TRUSTED_ORIGINS = [
    x.strip() for x in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if x.strip()
]


def _mahalliy_iplar():
    import socket
    iplar = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            ip = info[4][0]
            if ':' not in ip and not ip.startswith('127.'):
                iplar.add(ip)
    except Exception:
        pass
    return iplar


# Lokal (DEBUG) rejimda telefon testi uchun kompyuterning LAN IP'lari avtomatik qo'shiladi.
# Productionda qo'shilmaydi.
if DEBUG:
    for _ip in _mahalliy_iplar():
        for _port in ('8000', '8010'):
            CSRF_TRUSTED_ORIGINS.append(f'https://{_ip}:{_port}')
            CSRF_TRUSTED_ORIGINS.append(f'http://{_ip}:{_port}')

# Server nginx/proxy orqasida bo'lsa True: mijoz IP'si X-Forwarded-For'ning OXIRGI
# (proxy qo'shgan) qiymatidan olinadi. Proxy yo'q bo'lsa False — aks holda IP soxtalashtiriladi.
TRUST_X_FORWARDED_FOR = env_bool('TRUST_X_FORWARDED_FOR', False)

# Telegram bot tokeni (.env dan)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()

# Server (runserver) ishga tushganda Telegram bot ham avtomatik fon oqimida ishga tushsin.
# O'chirish uchun .env da: RUN_BOT_WITH_SERVER=False
RUN_BOT_WITH_SERVER = env_bool('RUN_BOT_WITH_SERVER', True)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'users.apps.UsersConfig',
    'dokon.apps.DokonConfig',
    'mahsulot.apps.MahsulotConfig',
    'buyurtma.apps.BuyurtmaConfig',
    'kassa.apps.KassaConfig',
    'soliq.apps.SoliqConfig',
    'chat.apps.ChatConfig',
    'yetkazib_beruvchi',
    'api.apps.ApiConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise — statik fayllarni (logo, i18n.js) DEBUG=False da ham xizmat qiladi
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'users.context_processors.bildirishnoma_soni',
            ],
        },
    },
]

WSGI_APPLICATION = 'wsgi.application'

# DB_ENGINE=postgres bo'lsa PostgreSQL, aks holda SQLite.
if os.environ.get('DB_ENGINE', 'sqlite').strip().lower() in ('postgres', 'postgresql'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'savdoyim1'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_USER_MODEL = 'users.CustomUser'

# Parol xavfsizligi — zaif parolларni (masalan "123", "parol") taqiqlaydi.
# Pul va shaxsiy ma'lumot bo'lgani uchun majburiy.
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 6}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Guest (mehmon) tizimga kirmagan foydalanuvchi cheklangan amal (buyurtma, sharh, ...)
# bajarmoqchi bo'lsa — login sahifasiga yo'naltiriladi (?next=... bilan qaytadi).
LOGIN_URL = 'login'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '120/min',
        'user': '600/min',
        'login': '10/min',
    },
    # Proxy (nginx) orqasida mijoz IP'sini to'g'ri aniqlash uchun
    'NUM_PROXIES': 1 if TRUST_X_FORWARDED_FOR else 0,
}

# CORS: faqat lokal (DEBUG) rejimda hammasiga ochiq; productionda .env CORS_ALLOW_ALL bilan.
CORS_ALLOW_ALL_ORIGINS = DEBUG

# Kesh: login/kod cheklovlari barcha gunicorn worker'larda umumiy bo'lishi uchun.
# REDIS_URL bo'lsa Redis, aks holda fayl kesh (bitta serverda umumiy). Testda — xotira.
if RUNNING_TESTS:
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
elif os.environ.get('REDIS_URL'):
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.redis.RedisCache',
                          'LOCATION': os.environ['REDIS_URL']}}
else:
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
                          'LOCATION': BASE_DIR / '.cache'}}

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise: statik fayllarni siqib xizmat qiladi (manifestsiz — deploy'da xato bermaydi)
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}
# Statik fayllar (i18n.js, CSS) o'zgarganda brauzer tez yangilashi uchun qisqa kesh.
# (Manifest o'rniga — DEBUG=True dev'ni buzmaydi.)
WHITENOISE_MAX_AGE = 60

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ═════════════════════════════════════════════
# PRODUCTION XAVFSIZLIGI — faqat DEBUG=False bo'lganda yoqiladi
# (lokal/telefon testiga xalaqit bermaydi)
# ═════════════════════════════════════════════
if not _DEV:
    # HTTPS orqasidagi proxy (nginx/PaaS) HTTPS'ni to'g'ri aniqlashi uchun
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    # Cookie'lar faqat HTTPS orqali (sniffing'dan himoya)
    SESSION_COOKIE_SECURE = env_bool('SECURE_COOKIES', True)
    CSRF_COOKIE_SECURE = env_bool('SECURE_COOKIES', True)
    # Brauzer himoyasi
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    # HTTP -> HTTPS yo'naltirish (server HTTPS bo'lsa). HTTPS yo'q bo'lsa .env:
    #   SECURE_SSL_REDIRECT=False  qo'ying (aks holda sayt ochilmaydi)
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    # HSTS — brauzerga "doim HTTPS ishlat" deydi (faqat HTTPS ishlaganда yoqing)
    if env_bool('ENABLE_HSTS', False):
        SECURE_HSTS_SECONDS = 31536000
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_HSTS_PRELOAD = True
    # Productionda CORS'ni cheklash (kerak bo'lsa .env orqali kengaytiriladi)
    CORS_ALLOW_ALL_ORIGINS = env_bool('CORS_ALLOW_ALL', False)
    # Sessiya 7 kun (standart 2 hafta o'rniga)
    SESSION_COOKIE_AGE = 7 * 24 * 3600

LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# ═════════════════════════════════════════════
# EMAIL (parolni tiklash kodi uchun) — #1
#
# Gmail "App Password" ko'p hisoblarda ishlamaydi ("Bu sozlama hisobingizda
# ishlamaydi"). Shuning uchun ISTALGAN SMTP provayder bilan ishlaydi.
#
#  ✅ ENG OSON YO'L — Brevo (bepul, kuniga 300 email):
#     1) https://www.brevo.com da ro'yxatdan o'ting
#     2) Chapdagi menyu -> "SMTP & API" -> "SMTP" bo'limi
#     3) U yerdagi ma'lumotlarni pastdagi 4 qatorga qo'ying:
#          SMTP_HOST  = "smtp-relay.brevo.com"
#          SMTP_LOGIN = "...@smtp-brevo.com"   (Brevo bergan login)
#          SMTP_PAROL = "xxxxxxxxxxxxx"         (Brevo "SMTP key")
#          SMTP_FROM  = "sizning@email.com"     (Brevo'da tasdiqlangan yuboruvchi)
#     4) Serverni QAYTA ISHGA TUSHIRING (Ctrl+C -> python manage.py runserver)
#
#  (Gmail app password ishlagan bo'lsa: SMTP_HOST="smtp.gmail.com",
#   SMTP_LOGIN va SMTP_FROM = gmail manzilingiz, SMTP_PAROL = 16 belgili parol.)
#
#  SMTP_PAROL bo'sh bo'lsa -> kod EMAILGA BORMAYDI, faqat terminalga chiqadi (test).
# ═════════════════════════════════════════════

# SMTP ma'lumotlari .env faylidan olinadi (git'ga tushmaydi).
# Diqqat: parol settings nomida saqlanmaydi (DEBUG xato sahifasida ko'rinib qolmasligi uchun).
EMAIL_HOST = os.environ.get('EMAIL_HOST', os.environ.get('SMTP_HOST', 'smtp-relay.brevo.com'))
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', os.environ.get('SMTP_LOGIN', ''))
EMAIL_HOST_PASSWORD = (os.environ.get('EMAIL_HOST_PASSWORD', '') or os.environ.get('SMTP_PAROL', '')).replace(' ', '')
_email_from = os.environ.get('EMAIL_FROM', os.environ.get('SMTP_FROM', 'phytonbackend@gmail.com'))

# Parol bor -> haqiqiy SMTP; yo'q -> konsol (faqat lokal test rejimi).
# Productionda konsol rejimi kodlarni hech qachon ekranga chiqarmaydi (users/views.py: test_rejimi()).
if EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Yuboruvchi "Savdoyim" nomi bilan ko'rinadi
DEFAULT_FROM_EMAIL = 'Savdoyim <{}>'.format(_email_from)
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Admin panel manzili (.env ADMIN_URL bilan o'zgartiring — taxmin qilinmasin)
ADMIN_URL = os.environ.get('ADMIN_URL', 'admin/').strip('/') + '/'

# Loglar konsolga (gunicorn/systemd jurnaliga) yoziladi
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': os.environ.get('LOG_LEVEL', 'WARNING')},
}
