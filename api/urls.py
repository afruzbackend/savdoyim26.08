"""REST API URL'lari — barchasi `/api/` ostida.

Endpointlar:
  POST  /api/auth/login/    -> {token, user}
  POST  /api/auth/logout/   -> token bekor qilinadi
  GET   /api/me/            -> joriy foydalanuvchi
  GET   /api/mahsulotlar/   -> do'kon mahsulotlari (?q= qidiruv)
  GET   /api/qarzlar/       -> qarzlar (?hammasi=1)
  GET   /api/cheklar/       -> savdo cheklari
  GET   /api/kassa/         -> kassa balansi
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('mahsulotlar', views.MahsulotViewSet, basename='api-mahsulot')
router.register('qarzlar', views.QarzViewSet, basename='api-qarz')
router.register('cheklar', views.SavdoChekViewSet, basename='api-chek')

urlpatterns = [
    path('auth/login/', views.LoginView.as_view(), name='api-login'),
    path('auth/logout/', views.logout_view, name='api-logout'),
    path('me/', views.me_view, name='api-me'),
    path('kassa/', views.kassa_view, name='api-kassa'),
    # Mijoz uchun ommaviy (login talab qilmaydigan) mahsulot ro'yxati
    path('ommaviy/mahsulotlar/', views.ommaviy_mahsulotlar, name='api-ommaviy-mahsulot'),
    # Sotuvchi: smena + savdo (yozish)
    path('smena/', views.smena_holati, name='api-smena'),
    path('smena/ochish/', views.smena_ochish_api, name='api-smena-ochish'),
    path('smena/yopish/', views.smena_yopish_api, name='api-smena-yopish'),
    path('savdo/', views.savdo_api, name='api-savdo'),
    # Sotuvchi: qarz to'lash, barkod, qaytarish (refund)
    path('qarz/<int:qarz_id>/tolash/', views.qarz_tolash_api, name='api-qarz-tolash'),
    path('mahsulot/barkod/<str:barkod>/', views.mahsulot_barkod, name='api-mahsulot-barkod'),
    path('chek/topish/', views.chek_topish_api, name='api-chek-topish'),
    path('qaytarish/', views.qaytarish_api, name='api-qaytarish'),
    # Mijoz: buyurtma (Click & Collect)
    path('mijoz/buyurtmalar/', views.mijoz_buyurtmalar, name='api-mijoz-buyurtmalar'),
    path('mijoz/buyurtma/', views.mijoz_buyurtma_yarat, name='api-mijoz-buyurtma'),
    path('mijoz/buyurtma/<int:buyurtma_id>/bekor/', views.mijoz_buyurtma_bekor, name='api-mijoz-buyurtma-bekor'),
    # Mijoz: sodiqlik ballari, mahsulot sharhi
    path('mijoz/sodiqlik/', views.mijoz_sodiqlik, name='api-mijoz-sodiqlik'),
    path('mahsulot/<int:mahsulot_id>/sharh/', views.mahsulot_sharh, name='api-mahsulot-sharh'),
]
urlpatterns += router.urls
