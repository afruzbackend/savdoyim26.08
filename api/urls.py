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
]
urlpatterns += router.urls
