from django.urls import path
from . import views

urlpatterns = [
    path('mahsulot/', views.mahsulot_royxat, name='mahsulot_royxat'),
    path('mahsulot/qoshish/', views.mahsulot_qoshish, name='mahsulot_qoshish'),
    path('mahsulot/<int:mahsulot_id>/tahrir/', views.mahsulot_tahrir, name='mahsulot_tahrir'),
    path('mahsulot/import/', views.mahsulot_import, name='mahsulot_import'),
    path('mahsulot/skanner/', views.skanner_view, name='skanner'),
    path('mahsulot/skanner/action/', views.skanner_action, name='skanner_action'),
    path('mahsulot/jonatma-qabul/', views.jonatma_qabul_dokon, name='jonatma_qabul_dokon'),
    path('mahsulot/jonatma-qabul/action/', views.jonatma_qabul_dokon_action, name='jonatma_qabul_dokon_action'),
    path('mahsulot/qidirish/', views.api_mahsulot_qidirish, name='mahsulot_qidirish'),
    path('mahsulot/barkod-info/', views.mahsulot_barkod_info, name='mahsulot_barkod_info'),

    # Inventarizatsiya (ombor sanog'i)
    path('inventarizatsiya/', views.inventarizatsiya_royxat, name='inventarizatsiya_royxat'),
    path('inventarizatsiya/boshlash/', views.inventarizatsiya_boshlash, name='inventarizatsiya_boshlash'),
    path('inventarizatsiya/<int:inv_id>/', views.inventarizatsiya_detail, name='inventarizatsiya_detail'),
    path('inventarizatsiya/<int:inv_id>/saqlash/', views.inventarizatsiya_saqlash, name='inventarizatsiya_saqlash'),

    # Sharh (review) endpointlari
    path('sharh/qoldirish/', views.sharh_qoldirish, name='sharh_qoldirish'),
    path('sharh/<int:sharh_id>/tahrirlash/', views.sharh_tahrirlash, name='sharh_tahrirlash'),
    path('sharh/<int:sharh_id>/moderatsiya/', views.sharh_moderatsiya, name='sharh_moderatsiya'),

    # Ochiq mahsulot sahifasi (int — oxirida, boshqa yo'llar bilan to'qnashmaydi)
    path('mahsulot/<int:mahsulot_id>/', views.mahsulot_detail, name='mahsulot_detail'),
]
