from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.bienvenido, name='bienvenido'),
    path('home/', views.home, name='home'),
    path('registro/', views.registro, name='registro'),
    path('iniciarsesion/', views.iniciarsesion, name='iniciarsesion'),
    path('verificar_email/<str:token>/', views.verificar_email, name='verificar_email'),
    path('recuperar-contrasena/', views.mostrar_recuperar_contrasena, name='mostrar_recuperar_contrasena'),
    path('procesar-recuperacion/', views.recuperar_contrasena, name='recuperar_contrasena'),
    path('reset-password/<str:uidb64>/<str:token>/', views.reset_password, name='reset_password'),
    path('reset-password-confirm/', views.reset_password_confirm, name='reset_password_confirm'),
    path('perfil/', views.perfil, name='perfil'),
    path('semilleros/', views.semilleros, name='semilleros'),
    path('resumen/', views.resumen, name='resumen'),
    path('resu-miembros/', views.resu_miembros, name='resu-miembros'),
    path('resu-proyectos/', views.resu_proyectos, name='resu-proyectos'),
    path('recursos/', views.recursos, name='recursos'),
    path('proyectos/', views.proyectos, name='proyectos'),
    path('miembros/', views.miembros, name='miembros'),
    path('centroayuda/', views.centroayuda, name='centroayuda'),
    path('reportes/', views.reportes, name='reportes'),
]
