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
    path(settings.ADMIN_URL, admin.site.urls),
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

# Yuklangan media — faqat RASMLAR ochiq beriladi (mahsulot, logo, avatar, sharh).
# Boshqa fayllar (HTML, skript, zavod hujjatlari) ochiq berilmaydi: XSS va maxfiylik himoyasi.
_OCHIQ_RASM = ('.jpg', '.jpeg', '.png', '.webp', '.gif')


def media_serve(request, path):
    import os
    from django.http import Http404
    ext = os.path.splitext(path)[1].lower()
    if path.startswith('zavod_hujjatlar/'):
        if not (request.user.is_authenticated and request.user.is_staff):
            raise Http404()
    elif ext not in _OCHIQ_RASM:
        raise Http404()
    resp = serve(request, path, document_root=settings.MEDIA_ROOT)
    resp['X-Content-Type-Options'] = 'nosniff'
    if ext not in _OCHIQ_RASM:
        resp['Content-Disposition'] = 'attachment'
    return resp


urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', media_serve),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Xato sahifalari uchun handler'lar (templates/404.html, 500.html, 403.html, 400.html)
handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'
handler403 = 'django.views.defaults.permission_denied'
handler400 = 'django.views.defaults.bad_request'