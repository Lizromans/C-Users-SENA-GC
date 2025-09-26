from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.bienvenido, name='bienvenido'),
    path('base/', views.base, name='base'),
    path('home/', views.home, name='home'),
    path('registro/', views.registro, name='registro'),
    path('perfil/', views.perfil, name='perfil'),
    path('semilleros/', views.semilleros, name='semilleros'),
    path('base2/', views.base2, name='base2'),
]