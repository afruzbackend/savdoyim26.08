import os
from pathlib import Path
from dotenv import load_dotenv

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


# Maxfiy kalit .env dan olinadi (bo'lmasa — eski qiymat, faqat lokal uchun)
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-savdo-tizimi-2024-xavfsiz-kalit-ozgartiring'
)

# Lokal ishlab chiqishda True. Productionda .env da DJANGO_DEBUG=False qiling.
DEBUG = env_bool('DJANGO_DEBUG', True)

# Productionda .env da DJANGO_ALLOWED_HOSTS=domen.uz,www.domen.uz,IP ko'rinishida bering.
# Bo'sh bo'lsa: DEBUG=True da hammasi (*), aks holda ham * (lekin domen berish tavsiya etiladi).
_hosts = os.environ.get('DJANGO_ALLOWED_HOSTS', '').strip()
ALLOWED_HOSTS = [h.strip() for h in _hosts.split(',') if h.strip()] or ['*']

# HTTPS orqali (telefonda kamera testi) POST ishlashi uchun ishonchli manzillar.
# .env dagi qiymatlar + kompyuterning joriy LAN IP manzillari avtomatik qo'shiladi
# (IP o'zgarsa ham telefonda ishlashi uchun).
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


for _ip in _mahalliy_iplar():
    for _port in ('8000', '8010'):
        CSRF_TRUSTED_ORIGINS.append(f'https://{_ip}:{_port}')
        CSRF_TRUSTED_ORIGINS.append(f'http://{_ip}:{_port}')

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
}

CORS_ALLOW_ALL_ORIGINS = True

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
if not DEBUG:
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

# SMTP ma'lumotlari endi .env faylidan olinadi (git'ga tushmaydi).
SMTP_HOST  = os.environ.get('SMTP_HOST', 'smtp-relay.brevo.com')
SMTP_LOGIN = os.environ.get('SMTP_LOGIN', '')
SMTP_PAROL = os.environ.get('SMTP_PAROL', '')
SMTP_FROM  = os.environ.get('SMTP_FROM', 'phytonbackend@gmail.com')

# Env o'zgaruvchilar ustun turadi (ishlab chiqarish uchun xavfsizroq)
EMAIL_HOST = os.environ.get('EMAIL_HOST', SMTP_HOST)
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', SMTP_LOGIN)
EMAIL_HOST_PASSWORD = (os.environ.get('EMAIL_HOST_PASSWORD', '') or SMTP_PAROL).replace(' ', '')
_email_from = os.environ.get('EMAIL_FROM', SMTP_FROM)

# Parol bor -> haqiqiy SMTP; yo'q -> konsol (test rejimi)
if EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Yuboruvchi "Savdoyim" nomi bilan ko'rinadi
DEFAULT_FROM_EMAIL = 'Savdoyim <{}>'.format(_email_from)
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# ─────────────────────────────────────────────
# BREVO API (ENG OSON YO'L) — Login KERAK EMAS, faqat 1 ta API kalit!
#   1) Brevo -> "SMTP & API" -> "API Keys" bo'limi
#   2) "Generate a new API key" -> nusxa oling (xkeysib-... bilan boshlanadi)
#   3) Uni pastdagi BREVO_API_KEY ga qo'ying
#   4) Brevo -> "Senders" da yuboruvchi emailni TASDIQLANG va uni
#      BREVO_SENDER_EMAIL ga yozing
#   5) Serverni qayta ishga tushiring
#   BREVO_API_KEY bo'lsa -> email API orqali yuboriladi (SMTP'dan ustun).
# ─────────────────────────────────────────────
BREVO_API_KEY = os.environ.get('BREVO_API_KEY', "")          # ← xkeysib-... shu yerga
BREVO_SENDER_EMAIL = os.environ.get('BREVO_SENDER_EMAIL', "phytonbackend@gmail.com")  # tasdiqlangan yuboruvchi
BREVO_SENDER_NAME = "Savdoyim"