from django.urls import path
from . import views

urlpatterns = [
    path('kassa/', views.kassa_view, name='kassa'),
    path('kassa/savat/', views.savat_action, name='kassa_savat'),
    path('kassa/savdo/', views.savdo_qilish, name='savdo_qilish'),
    path('kassa/skan/', views.kassa_skan, name='kassa_skan'),
    path('kassa/smena/ochish/', views.smena_ochish, name='smena_ochish'),
    path('kassa/smena/yopish/', views.smena_yopish, name='smena_yopish'),
    path('kassa/qarzlar/', views.qarz_royxat, name='qarz_royxat'),
    path('kassa/qaytarish/', views.qaytarish_view, name='qaytarish'),
    path('kassa/qaytarish/qil/', views.qaytarish_qil, name='qaytarish_qil'),
    path('kassa/sotuvchilar/', views.sotuvchilar_kpi, name='sotuvchilar_kpi'),
    path('kassa/qarz/<int:qarz_id>/tolash/', views.qarz_tolash, name='qarz_tolash'),
    path('kassa/hisobot/', views.hisobot_view, name='hisobot'),
    path('kassa/hisobot/export/<str:fmt>/', views.hisobot_export, name='hisobot_export'),
    path('kassa/hisobot/avto/', views.avto_hisobot_saqlash, name='avto_hisobot_saqlash'),
    path('kassa/hisobot/ai/tahlil/', views.ai_tahlil, name='ai_tahlil'),
    path('kassa/hisobot/ai/chat/', views.ai_chat, name='ai_chat'),
    path('chek/<uuid:token>/', views.chek_korish, name='chek_korish'),
]