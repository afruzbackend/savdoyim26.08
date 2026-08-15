from django.urls import path
from . import views

urlpatterns = [
    # ── Yetkazuvchi ──────────────────────────────────────────────
    path('', views.yetkazuvchi_dashboard, name='yetkazuvchi_dashboard'),
    path('jonatmalar/', views.yetkazuvchi_jonatmalar, name='yetkazuvchi_jonatmalar'),
    path('qabul/<int:jonatma_id>/', views.jonatma_qabul, name='jonatma_qabul'),
    path('holat/<int:jonatma_id>/', views.jonatma_holat, name='jonatma_holat'),
    path('qr/<int:jonatma_id>/', views.jonatma_qr, name='jonatma_qr'),
    path('barkod-qabul/', views.barkod_qabul, name='barkod_qabul'),
    path('sorov/', views.zavod_sorov_yuborish, name='zavod_sorov_yuborish'),

    # ── Zavod (yetkazuvchi boshqaruvi) ───────────────────────────
    path('yetkazuvchilar/', views.zavod_yetkazuvchilar, name='zavod_yetkazuvchilar'),
    path('sorov/<int:sorov_id>/javob/', views.zavod_sorov_javob, name='zavod_sorov_javob'),
    path('analitika/', views.zavod_analitika, name='zavod_analitika'),
    path('jonatish/', views.zavod_jonatma_yaratish, name='zavod_jonatma_yaratish'),
    path('jonatish/yuborish/', views.zavod_jonatma_yuborish, name='zavod_jonatma_yuborish'),
    # Eslatma: /jonatmalar/ yuqorida (yetkazuvchi_jonatmalar) rol bo'yicha
    # ishlaydi — zavod ham, yetkazuvchi ham o'z jo'natmalarini shu URL'dan ko'radi.
]