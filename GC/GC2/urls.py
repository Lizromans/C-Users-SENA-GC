from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.bienvenido, name='bienvenido'),
    path('base/', views.base, name='base'),
    path('home/', views.home, name='home'),
    path('registro/', views.registro, name='registro'),
]