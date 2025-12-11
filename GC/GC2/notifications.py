# notifications.py - Sistema completo de notificaciones
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta, datetime
from django.db.models import F, Q, Count, Avg  # ✅ IMPORTAR F AQUÍ
from .models import (
    Usuario, Evento, Entregable, Proyecto, Semillero,
    SemilleroUsuario, UsuarioProyecto, Aprendiz, ProyectoAprendiz
)

class NotificationManager:
    """Gestor centralizado de notificaciones"""
    
    def __init__(self, usuario):
        self.usuario = usuario
        self.ahora = timezone.now()
        self.notificaciones = []
    
    def obtener_todas(self):
        """Obtiene todas las notificaciones del usuario"""
        # 1. Eventos
        self._notificar_eventos_proximos()
        self._notificar_eventos_hoy()
        self._notificar_eventos_nuevos()
        
        # 2. Proyectos
        self._notificar_proyectos_bajo_progreso()
        self._notificar_proyectos_nuevos()
        self._notificar_cambios_estado_proyecto()
        self._notificar_proyectos_cerca_vencimiento()
        
        # 3. Entregables
        self._notificar_entregables_pendientes()
        self._notificar_entregables_retrasados()
        self._notificar_entregables_vencen_hoy()
        self._notificar_entregables_nuevos()
        self._notificar_entregables_completados()
        
        # 4. Semilleros
        self._notificar_nuevos_miembros()
        self._notificar_nuevos_aprendices()
        self._notificar_cambios_liderazgo()
        self._notificar_semillero_inactivo()
        
        # 5. Usuarios y Roles
        self._notificar_nuevos_lideres_proyecto()
        self._notificar_asignaciones_proyecto()
        self._notificar_remociones_proyecto()
        
        # 6. Documentos
        self._notificar_documentos_nuevos()
        
        return self.notificaciones
    
    # ==================== EVENTOS ====================
    
    def _notificar_eventos_proximos(self):
        """Eventos en las próximas 24 horas"""
        eventos = Evento.objects.filter(
            fecha_eve__gte=self.ahora.date(),
            fecha_eve__lte=(self.ahora + timedelta(days=1)).date(),
            estado_eve__in=['Próximo', 'Programado']
        ).order_by('fecha_eve', 'hora_inicio')[:3]

        for evento in eventos:
            dt_evento = datetime.combine(evento.fecha_eve, evento.hora_inicio)
            if timezone.is_naive(dt_evento):
                dt_evento = timezone.make_aware(dt_evento)

            minutos = (dt_evento - self.ahora).total_seconds() / 60
            if minutos < 0:
                continue

            horas = int(minutos // 60)
            
            if minutos < 60:
                tiempo_msg = f'Comienza en {int(minutos)} minuto(s)'
                clase = 'error'
            elif horas < 3:
                tiempo_msg = f'Comienza en {horas} hora(s)'
                clase = 'error'
            else:
                tiempo_msg = f'Comienza en {horas} hora(s)'
                clase = 'warning'

            self._agregar_notificacion(
                tipo='evento_proximo',
                icono='fa-calendar-check',
                clase_icono=clase,
                titulo=f'Evento Próximo: {evento.nom_eve}',
                mensaje=tiempo_msg,
                tiempo=evento.fecha_eve.strftime('%d/%m/%Y %H:%M'),
                url=reverse('eventos'),
                prioridad=1 if minutos < 60 else 2
            )
    
    def _notificar_eventos_hoy(self):
        """Eventos que ocurren hoy"""
        eventos = Evento.objects.filter(
            fecha_eve=self.ahora.date(),
            estado_eve__in=['Próximo', 'Programado']
        ).order_by('hora_inicio')

        for evento in eventos:
            self._agregar_notificacion(
                tipo='evento_hoy',
                icono='fa-calendar-day',
                clase_icono='warning',
                titulo=f'Evento Hoy: {evento.nom_eve}',
                mensaje=f'A las {evento.hora_inicio.strftime("%H:%M")}',
                tiempo='Hoy',
                url=reverse('eventos'),
                prioridad=2
            )
    
    def _notificar_eventos_nuevos(self):
        """Eventos creados en las últimas 48 horas"""
        if not hasattr(Evento, 'fecha_creacion'):
            return
            
        eventos = Evento.objects.filter(
            fecha_eve__gte=self.ahora.date(),
            estado_eve__in=['Próximo', 'Programado']
        ).exclude(cedula=self.usuario).order_by('-fecha_eve')[:2]

        for evento in eventos:
            self._agregar_notificacion(
                tipo='evento_nuevo',
                icono='fa-calendar-plus',
                clase_icono='info',
                titulo=f'Nuevo Evento: {evento.nom_eve}',
                mensaje=f'Programado para {evento.fecha_eve.strftime("%d/%m/%Y")}',
                tiempo='Nuevo',
                url=reverse('eventos'),
                prioridad=5
            )
    
    # ==================== PROYECTOS ====================
    
    def _notificar_proyectos_bajo_progreso(self):
        """Proyectos con progreso menor al 30%"""
        proyectos_usuario = UsuarioProyecto.objects.filter(
            cedula=self.usuario
        ).values_list('cod_pro', flat=True)
        
        proyectos = Proyecto.objects.filter(
            cod_pro__in=proyectos_usuario,
            progreso__lt=30,
            estado_pro__in=['planeacion', 'ejecucion']
        ).order_by('progreso')[:2]

        for proyecto in proyectos:
            sempro = proyecto.semilleroproyecto_set.first()
            url = self._get_proyecto_url(proyecto, sempro)

            self._agregar_notificacion(
                tipo='proyecto_bajo_progreso',
                icono='fa-exclamation-triangle',
                clase_icono='error',
                titulo='Proyecto con bajo progreso',
                mensaje=f'{proyecto.nom_pro} - {proyecto.progreso}% completado',
                tiempo='Requiere atención',
                url=url,
                prioridad=3
            )
    
    def _notificar_proyectos_nuevos(self):
        """Proyectos asignados recientemente"""
        if not hasattr(Proyecto, 'fecha_creacion'):
            return
            
        fecha_limite = self.ahora - timedelta(days=7)
        
        proyectos_usuario = UsuarioProyecto.objects.filter(
            cedula=self.usuario
        ).values_list('cod_pro', flat=True)
        
        proyectos = Proyecto.objects.filter(
            cod_pro__in=proyectos_usuario,
            fecha_creacion__gte=fecha_limite
        ).order_by('-fecha_creacion')[:2]

        for proyecto in proyectos:
            sempro = proyecto.semilleroproyecto_set.first()
            url = self._get_proyecto_url(proyecto, sempro)

            self._agregar_notificacion(
                tipo='proyecto_nuevo',
                icono='fa-project-diagram',
                clase_icono='success',
                titulo='Nuevo Proyecto Asignado',
                mensaje=f'{proyecto.nom_pro}',
                tiempo=proyecto.fecha_creacion.strftime('%d/%m/%Y'),
                url=url,
                prioridad=4
            )
    
    def _notificar_cambios_estado_proyecto(self):
        """Proyectos que cambiaron de estado recientemente"""
        if not hasattr(Proyecto, 'estado_original'):
            return
            
        proyectos_usuario = UsuarioProyecto.objects.filter(
            cedula=self.usuario
        ).values_list('cod_pro', flat=True)
        
        proyectos = Proyecto.objects.filter(
            cod_pro__in=proyectos_usuario
        ).exclude(estado_pro=F('estado_original'))[:2]

        estados_positivos = ['finalizado', 'completado', 'aprobado']
        
        for proyecto in proyectos:
            sempro = proyecto.semilleroproyecto_set.first()
            url = self._get_proyecto_url(proyecto, sempro)
            
            if proyecto.estado_pro in estados_positivos:
                clase = 'success'
                icono = 'fa-check-circle'
            else:
                clase = 'warning'
                icono = 'fa-sync'

            self._agregar_notificacion(
                tipo='proyecto_cambio_estado',
                icono=icono,
                clase_icono=clase,
                titulo='Cambio de Estado en Proyecto',
                mensaje=f'{proyecto.nom_pro} ahora está en "{proyecto.estado_pro}"',
                tiempo='Actualizado',
                url=url,
                prioridad=3
            )
    
    def _notificar_proyectos_cerca_vencimiento(self):
        """Proyectos que están por vencer (basado en entregables)"""
        proyectos_usuario = UsuarioProyecto.objects.filter(
            cedula=self.usuario
        ).values_list('cod_pro', flat=True)
        
        fecha_limite = self.ahora.date() + timedelta(days=7)
        
        entregables = Entregable.objects.filter(
            cod_pro__in=proyectos_usuario,
            estado='Pendiente',
            fecha_fin__lte=fecha_limite,
            fecha_fin__gte=self.ahora.date()
        ).select_related('cod_pro').order_by('fecha_fin')[:3]

        proyectos_notificados = set()
        
        for entregable in entregables:
            if entregable.cod_pro.cod_pro in proyectos_notificados:
                continue
                
            proyectos_notificados.add(entregable.cod_pro.cod_pro)
            dias = (entregable.fecha_fin - self.ahora.date()).days
            
            sempro = entregable.cod_pro.semilleroproyecto_set.first()
            url = self._get_proyecto_url(entregable.cod_pro, sempro)

            self._agregar_notificacion(
                tipo='proyecto_vencimiento',
                icono='fa-hourglass-half',
                clase_icono='warning',
                titulo='Proyecto con entregables próximos',
                mensaje=f'{entregable.cod_pro.nom_pro} - Vence en {dias} día(s)',
                tiempo=entregable.fecha_fin.strftime('%d/%m/%Y'),
                url=url,
                prioridad=2
            )
    
    # ==================== ENTREGABLES ====================
    
    def _notificar_entregables_pendientes(self):
        """Entregables pendientes próximos a vencer (7 días)"""
        proyectos_usuario = UsuarioProyecto.objects.filter(
            cedula=self.usuario
        ).values_list('cod_pro', flat=True)

        entregables = Entregable.objects.filter(
            cod_pro__in=proyectos_usuario,
            estado='Pendiente',
            fecha_fin__gte=self.ahora.date(),
            fecha_fin__lte=(self.ahora + timedelta(days=7)).date()
        ).select_related('cod_pro').order_by('fecha_fin')[:3]

        for entregable in entregables:
            dias_restantes = (entregable.fecha_fin - self.ahora.date()).days
            
            sempro = entregable.cod_pro.semilleroproyecto_set.first()
            url = self._get_entregable_url(entregable, sempro)

            self._agregar_notificacion(
                tipo='entregable_pendiente',
                icono='fa-file-alt',
                clase_icono='warning' if dias_restantes <= 2 else 'success',
                titulo=f'Entregable: {entregable.nom_entre}',
                mensaje=f'Vence en {dias_restantes} día(s) - {entregable.cod_pro.nom_pro}',
                tiempo=entregable.fecha_fin.strftime('%d/%m/%Y'),
                url=url,
                prioridad=1 if dias_restantes <= 2 else 3
            )
    
    def _notificar_entregables_retrasados(self):
        """Entregables que ya pasaron su fecha de vencimiento"""
        proyectos_usuario = UsuarioProyecto.objects.filter(
            cedula=self.usuario
        ).values_list('cod_pro', flat=True)

        entregables = Entregable.objects.filter(
            cod_pro__in=proyectos_usuario,
            estado='Retrasado'
        ).select_related('cod_pro')[:3]

        for entregable in entregables:
            dias_retraso = (self.ahora.date() - entregable.fecha_fin).days
            
            sempro = entregable.cod_pro.semilleroproyecto_set.first()
            url = self._get_entregable_url(entregable, sempro)

            self._agregar_notificacion(
                tipo='entregable_retrasado',
                icono='fa-clock',
                clase_icono='error',
                titulo='Entregable Retrasado',
                mensaje=f'{entregable.nom_entre} - Retraso de {dias_retraso} día(s)',
                tiempo=f'Venció el {entregable.fecha_fin.strftime("%d/%m/%Y")}',
                url=url,
                prioridad=1
            )
    
    def _notificar_entregables_vencen_hoy(self):
        """Entregables que vencen hoy"""
        proyectos_usuario = UsuarioProyecto.objects.filter(
            cedula=self.usuario
        ).values_list('cod_pro', flat=True)

        entregables = Entregable.objects.filter(
            cod_pro__in=proyectos_usuario,
            estado='Pendiente',
            fecha_fin=self.ahora.date()
        ).select_related('cod_pro')

        for entregable in entregables:
            sempro = entregable.cod_pro.semilleroproyecto_set.first()
            url = self._get_entregable_url(entregable, sempro)

            self._agregar_notificacion(
                tipo='entregable_hoy',
                icono='fa-exclamation-circle',
                clase_icono='error',
                titulo='¡Entregable Vence Hoy!',
                mensaje=f'{entregable.nom_entre} - {entregable.cod_pro.nom_pro}',
                tiempo='Vence Hoy',
                url=url,
                prioridad=1
            )
    
    def _notificar_entregables_nuevos(self):
        """Entregables creados recientemente"""
        proyectos_usuario = UsuarioProyecto.objects.filter(
            cedula=self.usuario
        ).values_list('cod_pro', flat=True)

        # Asumiendo que los entregables recientes tienen cod_entre alto
        entregables = Entregable.objects.filter(
            cod_pro__in=proyectos_usuario,
            estado='Pendiente'
        ).select_related('cod_pro').order_by('-cod_entre')[:2]

        for entregable in entregables:
            sempro = entregable.cod_pro.semilleroproyecto_set.first()
            url = self._get_entregable_url(entregable, sempro)

            self._agregar_notificacion(
                tipo='entregable_nuevo',
                icono='fa-file-circle-plus',
                clase_icono='info',
                titulo='Nuevo Entregable',
                mensaje=f'{entregable.nom_entre} - {entregable.cod_pro.nom_pro}',
                tiempo=f'Vence: {entregable.fecha_fin.strftime("%d/%m/%Y")}',
                url=url,
                prioridad=4
            )
    
    def _notificar_entregables_completados(self):
        """Entregables completados recientemente"""
        proyectos_usuario = UsuarioProyecto.objects.filter(
            cedula=self.usuario
        ).values_list('cod_pro', flat=True)

        entregables = Entregable.objects.filter(
            cod_pro__in=proyectos_usuario,
            estado='Completado'
        ).select_related('cod_pro').order_by('-cod_entre')[:2]

        for entregable in entregables:
            sempro = entregable.cod_pro.semilleroproyecto_set.first()
            url = self._get_entregable_url(entregable, sempro)

            self._agregar_notificacion(
                tipo='entregable_completado',
                icono='fa-check-double',
                clase_icono='success',
                titulo='Entregable Completado',
                mensaje=f'{entregable.nom_entre} - {entregable.cod_pro.nom_pro}',
                tiempo='Completado',
                url=url,
                prioridad=5
            )
    
    # ==================== SEMILLEROS ====================
    
    def _notificar_nuevos_miembros(self):
        """Nuevos miembros en semilleros donde el usuario es líder"""
        mis_semilleros = SemilleroUsuario.objects.filter(
            cedula=self.usuario,
            es_lider=True
        ).values_list('id_sem', flat=True)

        nuevos_miembros = SemilleroUsuario.objects.filter(
            id_sem__in=mis_semilleros
        ).select_related('cedula', 'id_sem').order_by('-semusu_id')[:3]

        for miembro in nuevos_miembros:
            if miembro.cedula.cedula == self.usuario.cedula:
                continue

            url = reverse('resu-miembros', kwargs={'id_sem': miembro.id_sem.id_sem})

            self._agregar_notificacion(
                tipo='nuevo_miembro',
                icono='fa-user-plus',
                clase_icono='success',
                titulo='Nuevo Miembro en Semillero',
                mensaje=f'{miembro.cedula.nom_usu} se unió a {miembro.id_sem.nombre}',
                tiempo='Reciente',
                url=url,
                prioridad=4
            )
    
    def _notificar_nuevos_aprendices(self):
        """Nuevos aprendices en proyectos del usuario"""
        proyectos_usuario = UsuarioProyecto.objects.filter(
            cedula=self.usuario,
            es_lider_pro=True
        ).values_list('cod_pro', flat=True)

        nuevos_aprendices = ProyectoAprendiz.objects.filter(
            cod_pro__in=proyectos_usuario
        ).select_related('cedula_apre', 'cod_pro').order_by('-proapre_id')[:2]

        for asignacion in nuevos_aprendices:
            sempro = asignacion.cod_pro.semilleroproyecto_set.first()
            url = self._get_proyecto_url(asignacion.cod_pro, sempro)

            self._agregar_notificacion(
                tipo='nuevo_aprendiz',
                icono='fa-graduation-cap',
                clase_icono='info',
                titulo='Nuevo Aprendiz Asignado',
                mensaje=f'{asignacion.cedula_apre.nombre} en {asignacion.cod_pro.nom_pro}',
                tiempo='Nuevo',
                url=url,
                prioridad=4
            )
    
    def _notificar_cambios_liderazgo(self):
        """Cambios en liderazgo de semilleros"""
        # Semilleros donde ahora eres líder
        nuevos_liderazgos = SemilleroUsuario.objects.filter(
            cedula=self.usuario,
            es_lider=True
        ).select_related('id_sem')[:2]

        for relacion in nuevos_liderazgos:
            url = reverse('resu-miembros', kwargs={'id_sem': relacion.id_sem.id_sem})

            self._agregar_notificacion(
                tipo='nuevo_lider_semillero',
                icono='fa-crown',
                clase_icono='warning',
                titulo='Liderazgo de Semillero',
                mensaje=f'Ahora eres líder de {relacion.id_sem.nombre}',
                tiempo='Actualizado',
                url=url,
                prioridad=3
            )
    
    def _notificar_semillero_inactivo(self):
        """Semilleros sin actividad reciente"""
        mis_semilleros = SemilleroUsuario.objects.filter(
            cedula=self.usuario,
            es_lider=True
        ).values_list('id_sem', flat=True)

        # Semilleros sin proyectos activos
        from django.db.models import Count, Q
        
        semilleros_inactivos = Semillero.objects.filter(
            id_sem__in=mis_semilleros
        ).annotate(
            proyectos_activos=Count(
                'proyectos',
                filter=Q(proyectos__estado_pro__in=['planeacion', 'ejecucion'])
            )
        ).filter(proyectos_activos=0)[:2]

        for semillero in semilleros_inactivos:
            url = reverse('resu-miembros', kwargs={'id_sem': semillero.id_sem})

            self._agregar_notificacion(
                tipo='semillero_inactivo',
                icono='fa-exclamation-triangle',
                clase_icono='warning',
                titulo='Semillero sin Proyectos Activos',
                mensaje=f'{semillero.nombre} no tiene proyectos en progreso',
                tiempo='Requiere atención',
                url=url,
                prioridad=5
            )
    
    # ==================== USUARIOS Y ROLES ====================
    
    def _notificar_nuevos_lideres_proyecto(self):
        """Notificar cuando se convierte en líder de proyecto"""
        liderazgos = UsuarioProyecto.objects.filter(
            cedula=self.usuario,
            es_lider_pro=True
        ).select_related('cod_pro').order_by('-usupro_id')[:2]

        for liderazgo in liderazgos:
            sempro = liderazgo.cod_pro.semilleroproyecto_set.first()
            url = self._get_proyecto_url(liderazgo.cod_pro, sempro)

            self._agregar_notificacion(
                tipo='lider_proyecto',
                icono='fa-star',
                clase_icono='warning',
                titulo='Líder de Proyecto',
                mensaje=f'Ahora lideras: {liderazgo.cod_pro.nom_pro}',
                tiempo='Nuevo Rol',
                url=url,
                prioridad=3
            )
    
    def _notificar_asignaciones_proyecto(self):
        """Notificar asignaciones recientes a proyectos"""
        asignaciones = UsuarioProyecto.objects.filter(
            cedula=self.usuario,
            estado='activo'
        ).select_related('cod_pro').order_by('-usupro_id')[:2]

        for asignacion in asignaciones:
            sempro = asignacion.cod_pro.semilleroproyecto_set.first()
            url = self._get_proyecto_url(asignacion.cod_pro, sempro)

            self._agregar_notificacion(
                tipo='asignacion_proyecto',
                icono='fa-user-plus',
                clase_icono='info',
                titulo='Asignado a Proyecto',
                mensaje=f'{asignacion.cod_pro.nom_pro}',
                tiempo='Nuevo',
                url=url,
                prioridad=4
            )
    
    def _notificar_remociones_proyecto(self):
        """Notificar cuando se remueve de un proyecto"""
        remociones = UsuarioProyecto.objects.filter(
            cedula=self.usuario,
            estado='inactivo'
        ).select_related('cod_pro').order_by('-usupro_id')[:1]

        for remocion in remociones:
            self._agregar_notificacion(
                tipo='remocion_proyecto',
                icono='fa-user-minus',
                clase_icono='error',
                titulo='Removido de Proyecto',
                mensaje=f'Ya no formas parte de: {remocion.cod_pro.nom_pro}',
                tiempo='Actualizado',
                url=reverse('proyectos'),
                prioridad=3
            )
    
    # ==================== DOCUMENTOS ====================
    
    def _notificar_documentos_nuevos(self):
        """Documentos nuevos en semilleros del usuario"""
        from .models import SemilleroDocumento
        
        mis_semilleros = SemilleroUsuario.objects.filter(
            cedula=self.usuario
        ).values_list('id_sem', flat=True)

        documentos = SemilleroDocumento.objects.filter(
            id_sem__in=mis_semilleros
        ).select_related('cod_doc', 'id_sem').order_by('-id_doc')[:2]

        for doc_relacion in documentos:
            url = reverse('resu-miembros', kwargs={'id_sem': doc_relacion.id_sem.id_sem})

            self._agregar_notificacion(
                tipo='documento_nuevo',
                icono='fa-file-upload',
                clase_icono='info',
                titulo='Nuevo Documento',
                mensaje=f'{doc_relacion.cod_doc.nom_doc} en {doc_relacion.id_sem.nombre}',
                tiempo=doc_relacion.cod_doc.fecha_doc,
                url=url,
                prioridad=5
            )
    
    # ==================== MÉTODOS AUXILIARES ====================
    
    def _agregar_notificacion(self, tipo, icono, clase_icono, titulo, mensaje, tiempo, url, prioridad=5):
        """Agrega una notificación a la lista"""
        self.notificaciones.append({
            'tipo': tipo,
            'icono': icono,
            'clase_icono': clase_icono,
            'titulo': titulo,
            'mensaje': mensaje,
            'tiempo': tiempo,
            'url': url,
            'leida': False,
            'prioridad': prioridad
        })
    
    def _get_proyecto_url(self, proyecto, sempro):
        """Genera URL del proyecto"""
        if sempro:
            return reverse('detalle-proyecto', kwargs={
                'id_sem': sempro.id_sem.id_sem,
                'cod_pro': proyecto.cod_pro
            })
        return reverse('proyectos')
    
    def _get_entregable_url(self, entregable, sempro):
        """Genera URL del entregable"""
        if sempro:
            return (
                reverse('detalle-proyecto', kwargs={
                    'id_sem': sempro.id_sem.id_sem,
                    'cod_pro': entregable.cod_pro.cod_pro
                }) + '?tab=entregables'
            )
        return reverse('proyectos')


# ==================== FUNCIÓN PRINCIPAL ====================

def obtener_notificaciones(request):
    """
    Función principal para obtener todas las notificaciones del usuario.
    Compatible con el sistema existente.
    """
    # 1. Validar sesión
    usuario_id = request.session.get('cedula')
    if not usuario_id:
        return []

    try:
        usuario = Usuario.objects.get(cedula=usuario_id)
    except Usuario.DoesNotExist:
        return []

    # 2. Obtener notificaciones usando el gestor
    manager = NotificationManager(usuario)
    notificaciones = manager.obtener_todas()
    
    # 3. Ordenar por prioridad y limitar
    notificaciones.sort(key=lambda x: x['prioridad'])
    
    return notificaciones

# ==================== SIGNALS PARA NOTIFICACIONES EN TIEMPO REAL ====================

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

@receiver(post_save, sender=Entregable)
def notificar_entregable_creado(sender, instance, created, **kwargs):
    """Notifica cuando se crea un nuevo entregable"""
    if created:
        # Aquí puedes agregar lógica para websockets o notificaciones push
        pass

@receiver(post_save, sender=SemilleroUsuario)
def notificar_nuevo_miembro(sender, instance, created, **kwargs):
    """Notifica a líderes cuando hay un nuevo miembro"""
    if created:
        # Aquí puedes agregar lógica para websockets o notificaciones push
        pass

@receiver(pre_save, sender=Proyecto)
def notificar_cambio_estado_proyecto(sender, instance, **kwargs):
    """Notifica cuando cambia el estado de un proyecto"""
    if instance.pk:
        try:
            old_instance = Proyecto.objects.get(pk=instance.pk)
            if old_instance.estado_pro != instance.estado_pro:
                # Aquí puedes agregar lógica para websockets o notificaciones push
                pass
        except Proyecto.DoesNotExist:
            pass