from django.urls import path
from . import views, api_views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('register/send-code/', views.send_register_code, name='send_register_code'),
    path('register/check-username/', views.check_username, name='check_username'),
    path('register/check-dokon/', views.check_dokon, name='check_dokon'),
    path('about/', views.about_view, name='about'),
    path('profil/', views.profil_view, name='profil'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/save/', views.settings_action, name='settings_action'),
    path('bildirishnomalar/', views.bildirishnomalar, name='bildirishnomalar'),
    path('reyting/<int:user_id>/', views.reytinglar, name='reytinglar'),
    path('reyting/berish/', views.reyting_berish, name='reyting_berish'),

    path('dokon-egasi/', views.dokon_egasi_dashboard, name='dokon_egasi_dashboard'),
    path('dokon-egasi/sotuvchilar/', views.sotuvchi_ruxsat, name='sotuvchi_ruxsat'),
    path('sotuvchi/', views.sotuvchi_dashboard, name='sotuvchi_dashboard'),
    path('zavod/', views.zavod_dashboard, name='zavod_dashboard'),
    path('yetkazib-beruvchi/', views.yetkazuvchi_dashboard, name='yetkazuvchi_dashboard'),
    path('mijoz/', views.mijoz_dashboard, name='mijoz_dashboard'),
    path('mehmon/', views.mehmon_dashboard, name='mehmon_dashboard'),

    path('api/users/me/', api_views.me_view, name='api_me'),
    path('api/users/location/', api_views.update_location, name='update_location'),
]