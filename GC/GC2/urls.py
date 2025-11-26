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
    path('semilleros/eliminar/', views.eliminar_semilleros, name='eliminar_semilleros'),
    path('semillero/<int:id_sem>/miembros/', views.resu_miembros, name='resu-miembros'),
    path('semillero/<int:id_sem>/agregar-miembros/', views.agregar_miembros, name='agregar_miembros'),
    path('resumen/<int:id_sem>/', views.resumen, name='resumen'),
    path('resu-miembros/<int:id_sem>/', views.resu_miembros, name='resu-miembros'),
    path('semillero/<int:id_sem>/asignar-lider/', views.asignar_lider_semillero, name='asignar-lider-semillero'),
    path('agregar-miembros/<int:id_sem>/', views.agregar_miembros, name='agregar_miembros'),
    path('semillero/<int:id_sem>/crear_proyecto/', views.crear_proyecto, name='crear_proyecto'),
    
    path('resu-proyectos/<int:id_sem>/', views.resu_proyectos, name='resu-proyectos'),
    path('resu-proyectos/<int:id_sem>/<int:cod_pro>/', views.resu_proyectos, name='resu-proyectos'),
    path('semilleros/<int:id_sem>/proyectos/<int:cod_pro>/alternar-estado/', views.alternar_estado_miembro, name='alternar-estado-miembro'),
    
    path('semilleros/<int:id_sem>/proyectos/<int:cod_pro>/asignar-lider/', views.asignar_lider_proyecto_ajax, name='asignar-lider-proyecto-ajax'),
    path('recursos/<int:id_sem>/', views.recursos, name='recursos'),
    path('agregar_recurso/<int:id_sem>/', views.agregar_recurso, name='agregar_recurso'),
    path('semillero/<int:id_sem>/proyecto/<int:cod_pro>/entregable/<int:cod_entre>/subir/', views.subir_archivo_entregable, name='subir_archivo_entregable'),
    path('semillero/<int:id_sem>/proyecto/<int:cod_pro>/entregable/<int:cod_entre>/eliminar/', views.eliminar_entregable, name='eliminar_entregable'),
    path('semillero/<int:id_sem>/eliminar-proyecto/<str:cod_pro>/', views.eliminar_proyecto_semillero, name='eliminar_proyecto_sem'),
    path('recursos/<int:id_sem>/eliminar/<int:cod_doc>/', views.eliminar_recurso, name='eliminar_recurso'),

    
    path('proyectos/', views.proyectos, name='proyectos'),

    #MIEMBROS
    path('miembros/', views.miembros, name='miembros'),
    path('registro_aprendiz/', views.registro_aprendiz, name='registro_aprendiz'),
    path(
        'miembros/solicitar-codigo/<str:aprendiz_id>/',
        views.solicitar_codigo_verificacion_form,
        name='solicitar_codigo_verificacion_form'
    ),

    path(
        'miembros/verificar-codigo/',
        views.verificar_codigo_form,
        name='verificar_codigo_form'
    ),

    path(
        'miembros/cancelar-verificacion/',
        views.cancelar_verificacion,
        name='cancelar_verificacion'
    ),
    path('limpiar-numero-revelado/', views.limpiar_numero_revelado, name='limpiar_numero_revelado'),
    #CENTRO DE AYUDA
    path('centroayuda/', views.centroayuda, name='centroayuda'),

    #REPORTES
    path('reportes/', views.reportes, name='reportes'),
    path("reporte-semilleros/", views.reporte_general_semilleros, name="reporte_semilleros"),
    path("reporte-proyectos/", views.reporte_general_proyectos, name="reporte_proyectos"),
    path("reporte-entregables/", views.reporte_entregables, name="reporte_entregables"),
    path("reporte-participantes/", views.reporte_participantes, name="reporte_participantes"),
    path("reporte-dinamico/", views.generar_reporte_dinamico, name="generar_reporte_dinamico"),
    path('reportes/tendencias-crecimiento/', views.reporte_tendencias_crecimiento, name='reporte_tendencias'),
    path('reportes/productividad-semillero/', views.reporte_productividad_semillero, name='reporte_productividad'),
    
    #CONFIGURACIONES ADICIONES 
    path('privacidad/', views.privacidad, name='privacidad'),
    path('logout/', views.logout, name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
