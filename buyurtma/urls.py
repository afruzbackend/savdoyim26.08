from django.urls import path
from . import views

urlpatterns = [
    path('buyurtma/', views.buyurtmalar_royxat, name='buyurtmalar'),
    path('buyurtma/berish/', views.buyurtma_berish, name='buyurtma_berish'),
    path('buyurtma/yuborish/', views.buyurtma_yuborish, name='buyurtma_yuborish'),
    path('buyurtma/<int:buyurtma_id>/holat/', views.buyurtma_holat, name='buyurtma_holat'),

    # ── Mijoz savati + buyurtma (marketplace) ──
    path('savat/', views.savat_korish, name='savat'),
    path('savat/qoshish/', views.savatga_qoshish, name='savatga_qoshish'),
    path('savat/yangilash/', views.savat_yangilash, name='savat_yangilash'),
    path('savat/checkout/', views.buyurtma_checkout, name='buyurtma_checkout'),
    path('tez-buyurtma/', views.tez_buyurtma, name='tez_buyurtma'),
    path('mening-buyurtmalarim/', views.mijoz_buyurtmalarim, name='mijoz_buyurtmalarim'),
    path('sodiqlik/', views.sodiqlik_sahifa, name='sodiqlik'),
    path('dokon-buyurtmalari/', views.sotuvchi_mijoz_buyurtmalar, name='sotuvchi_mijoz_buyurtmalar'),
    path('mijoz-buyurtma/<int:buyurtma_id>/holat/', views.mijoz_buyurtma_holat, name='mijoz_buyurtma_holat'),
    path('mijoz-buyurtma/<int:buyurtma_id>/qayta/', views.qayta_buyurtma, name='qayta_buyurtma'),
]
