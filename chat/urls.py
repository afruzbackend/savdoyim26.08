from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.chat_royxat, name='chat_royxat'),
    path('chat/qidiruv/', views.chat_qidiruv, name='chat_qidiruv'),
    path('chat/yangi/', views.yangi_chat, name='yangi_chat'),
    path('chat/boshla/<int:foydalanuvchi_id>/', views.chat_boshla, name='chat_boshla'),
    path('chat/<int:xona_id>/', views.chat_xona, name='chat_xona'),
    path('chat/<int:xona_id>/yuborish/', views.xabar_yuborish, name='xabar_yuborish'),
    path('chat/<int:xona_id>/xabarlar/', views.xabarlar_olish, name='xabarlar_olish'),
]
