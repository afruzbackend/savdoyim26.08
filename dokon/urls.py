from django.urls import path
from . import views

urlpatterns = [
    path('api/dokonlar/', views.dokonlar_api, name='dokonlar_api'),
]