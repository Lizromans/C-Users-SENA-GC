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
    path('actualizar_foto/', views.actualizar_foto, name='actualizar_foto'),

    #SEMILERO
    path('semilleros/', views.semilleros, name='semilleros'),
    path('crear_semillero/', views.crear_semillero, name='crear_semillero'),
    path('semillero/<int:id_sem>/miembros/', views.resu_miembros, name='resu-miembros'),
    path('semillero/<int:id_sem>/agregar-miembros/', views.agregar_miembros, name='agregar_miembros'),
    path('resumen/<int:id_sem>/', views.resumen, name='resumen'),
    path('resu-miembros/<int:id_sem>/', views.resu_miembros, name='resu-miembros'),
    path('semillero/<int:id_sem>/asignar-lider/', views.asignar_lider_semillero, name='asignar-lider-semillero'),
    path('agregar-miembros/<int:id_sem>/', views.agregar_miembros, name='agregar_miembros'),
    path('resu-proyectos/', views.resu_proyectos, name='resu-proyectos'),
    path('recursos/', views.recursos, name='recursos'),

    #PROYECTOS
    path('proyectos/', views.proyectos, name='proyectos'),

    #MIEMBROS
    path('miembros/', views.miembros, name='miembros'),

    #CENTRO DE AYUDA
    path('centroayuda/', views.centroayuda, name='centroayuda'),

    #REPORTES
    path('reportes/', views.reportes, name='reportes'),

    #CONFIGURACIONES ADICIONES 
    path('privacidad/', views.privacidad, name='privacidad'),
    path('logout/', views.logout, name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
