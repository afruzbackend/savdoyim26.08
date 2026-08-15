from django.urls import path
from . import views

urlpatterns = [
    path('soliq/', views.soliq_dashboard, name='soliq_dashboard'),
    path('soliq/api/', views.soliq_api, name='soliq_api'),
]
