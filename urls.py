from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from users.views import home_redirect, pwa_manifest, pwa_service_worker

urlpatterns = [
    path('', home_redirect, name='home'),
    # PWA — root scope'да bo'lishi shart (offline + ilova o'rnatish)
    path('sw.js', pwa_service_worker, name='pwa_sw'),
    path('manifest.webmanifest', pwa_manifest, name='pwa_manifest'),
    path('admin/', admin.site.urls),
    path('delivery_person/', include('yetkazib_beruvchi.urls')),
    path('zavod/', include('yetkazib_beruvchi.urls')),
    path('user/', include('users.urls')),
    path('dokon/', include('dokon.urls')),
    path('product/', include('mahsulot.urls')),
    path('checkout/', include('kassa.urls')),
    path('tax/', include('soliq.urls')),
    path('order/', include('buyurtma.urls')),
    path('chat/', include('chat.urls')),
    path('api/', include('api.urls')),
]

# Yuklangan media (mahsulot rasmlari) — DEBUG=False (production) da ham ko'rinishi uchun.
# Statik fayllarni WhiteNoise xizmat qiladi, media'ni esa Django (oddiy deploy uchun).
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Xato sahifalari uchun handler'lar (templates/404.html, 500.html, 403.html, 400.html)
handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'
handler403 = 'django.views.defaults.permission_denied'
handler400 = 'django.views.defaults.bad_request'