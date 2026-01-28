# notifications.py - Sistema completo de notificaciones
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta, datetime
from django.db.models import F, Q, Count
from .models import (
    Usuario, Evento, Entregable, Proyecto, Semillero,
    SemilleroUsuario, UsuarioProyecto, Aprendiz, ProyectoAprendiz, Archivo
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
        self._notificar_archivos_entregables()
        
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
                prioridad=1 if minutos < 60 else 2,
                fecha=evento.fecha_eve
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
                prioridad=2,
                fecha=evento.fecha_eve
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
                prioridad=5,
                fecha=evento.fecha_eve
            )
    
    # ==================== PROYECTOS ===================
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
            
            # Usar fecha_creacion si existe, sino fecha actual
            fecha_notif = getattr(proyecto, 'fecha_creacion', self.ahora.date())

            self._agregar_notificacion(
                tipo='proyecto_bajo_progreso',
                icono='fa-exclamation-triangle',
                clase_icono='error',
                titulo='Proyecto con bajo progreso',
                mensaje=f'{proyecto.nom_pro} - {proyecto.progreso}% completado',
                tiempo='Requiere atención',
                url=url,
                prioridad=3,
                fecha=fecha_notif
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
                prioridad=4,
                fecha=proyecto.fecha_creacion
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
            
            fecha_notif = getattr(proyecto, 'fecha_modificacion', self.ahora.date())
            
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
                prioridad=3,
                fecha=fecha_notif
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
                prioridad=2,
                fecha=entregable.fecha_fin
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
                prioridad=1 if dias_restantes <= 2 else 3,
                fecha=entregable.fecha_fin
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
                prioridad=1,
                fecha=entregable.fecha_fin
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
                prioridad=1,
                fecha=entregable.fecha_fin
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
            
            # Usar fecha de inicio o fecha actual
            fecha_notif = getattr(entregable, 'fecha_inicio', self.ahora.date())

            self._agregar_notificacion(
                tipo='entregable_nuevo',
                icono='fa-file-circle-plus',
                clase_icono='info',
                titulo='Nuevo Entregable',
                mensaje=f'{entregable.nom_entre} - {entregable.cod_pro.nom_pro}',
                tiempo=f'Vence: {entregable.fecha_fin.strftime("%d/%m/%Y")}',
                url=url,
                prioridad=4,
                fecha=fecha_notif
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
            
            # Usar fecha de finalización o fecha actual
            fecha_notif = getattr(entregable, 'fecha_fin', self.ahora.date())

            self._agregar_notificacion(
                tipo='entregable_completado',
                icono='fa-check-double',
                clase_icono='success',
                titulo='Entregable Completado',
                mensaje=f'{entregable.nom_entre} - {entregable.cod_pro.nom_pro}',
                tiempo='Completado',
                url=url,
                prioridad=5,
                fecha=fecha_notif
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
            
            # Usar fecha de creación de la relación o fecha actual
            fecha_notif = getattr(miembro, 'fecha_union', self.ahora.date())

            self._agregar_notificacion(
                tipo='nuevo_miembro',
                icono='fa-user-plus',
                clase_icono='success',
                titulo='Nuevo Miembro en Semillero',
                mensaje=f'{miembro.cedula.nom_usu} se unió a {miembro.id_sem.nombre}',
                tiempo='Reciente',
                url=url,
                prioridad=4,
                fecha=fecha_notif
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
            
            fecha_notif = getattr(asignacion, 'fecha_asignacion', self.ahora.date())

            self._agregar_notificacion(
                tipo='nuevo_aprendiz',
                icono='fa-graduation-cap',
                clase_icono='info',
                titulo='Nuevo Aprendiz Asignado',
                mensaje=f'{asignacion.cedula_apre.nombre} en {asignacion.cod_pro.nom_pro}',
                tiempo='Nuevo',
                url=url,
                prioridad=4,
                fecha=fecha_notif
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
            
            fecha_notif = getattr(relacion, 'fecha_liderazgo', self.ahora.date())

            self._agregar_notificacion(
                tipo='nuevo_lider_semillero',
                icono='fa-crown',
                clase_icono='warning',
                titulo='Liderazgo de Semillero',
                mensaje=f'Ahora eres líder de {relacion.id_sem.nombre}',
                tiempo='Actualizado',
                url=url,
                prioridad=3,
                fecha=fecha_notif
            )
    
    def _notificar_semillero_inactivo(self):
        """Semilleros sin actividad reciente"""
        mis_semilleros = SemilleroUsuario.objects.filter(
            cedula=self.usuario,
            es_lider=True
        ).values_list('id_sem', flat=True)

        # Semilleros sin proyectos activos
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
            
            fecha_notif = getattr(semillero, 'fecha_actualizacion', self.ahora.date())

            self._agregar_notificacion(
                tipo='semillero_inactivo',
                icono='fa-exclamation-triangle',
                clase_icono='warning',
                titulo='Semillero sin Proyectos Activos',
                mensaje=f'{semillero.nombre} no tiene proyectos en progreso',
                tiempo='Requiere atención',
                url=url,
                prioridad=5,
                fecha=fecha_notif
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
            
            fecha_notif = getattr(liderazgo, 'fecha_asignacion', self.ahora.date())

            self._agregar_notificacion(
                tipo='lider_proyecto',
                icono='fa-star',
                clase_icono='warning',
                titulo='Líder de Proyecto',
                mensaje=f'Ahora lideras: {liderazgo.cod_pro.nom_pro}',
                tiempo='Nuevo Rol',
                url=url,
                prioridad=3,
                fecha=fecha_notif
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
            
            fecha_notif = getattr(asignacion, 'fecha_asignacion', self.ahora.date())

            self._agregar_notificacion(
                tipo='asignacion_proyecto',
                icono='fa-user-plus',
                clase_icono='info',
                titulo='Asignado a Proyecto',
                mensaje=f'{asignacion.cod_pro.nom_pro}',
                tiempo='Nuevo',
                url=url,
                prioridad=4,
                fecha=fecha_notif
            )
    
    def _notificar_remociones_proyecto(self):
        """Notificar cuando se remueve de un proyecto"""
        remociones = UsuarioProyecto.objects.filter(
            cedula=self.usuario,
            estado='inactivo'
        ).select_related('cod_pro').order_by('-usupro_id')[:1]

        for remocion in remociones:
            fecha_notif = getattr(remocion, 'fecha_remocion', self.ahora.date())
            
            self._agregar_notificacion(
                tipo='remocion_proyecto',
                icono='fa-user-minus',
                clase_icono='error',
                titulo='Removido de Proyecto',
                mensaje=f'Ya no formas parte de: {remocion.cod_pro.nom_pro}',
                tiempo='Actualizado',
                url=reverse('proyectos'),
                prioridad=3,
                fecha=fecha_notif
            )
    
    # ==================== DOCUMENTOS ====================
    def _notificar_documentos_nuevos(self):
        """Documentos nuevos en semilleros del usuario"""
        try:
            from .models import SemilleroDocumento
            
            mis_semilleros = SemilleroUsuario.objects.filter(
                cedula=self.usuario
            ).values_list('id_sem', flat=True)

            documentos = SemilleroDocumento.objects.filter(
                id_sem__in=mis_semilleros
            ).select_related('cod_doc', 'id_sem').order_by('-id_doc')[:2]

            for doc_relacion in documentos:
                url = reverse('resu-miembros', kwargs={'id_sem': doc_relacion.id_sem.id_sem})
                
                # Usar fecha del documento
                fecha_notif = doc_relacion.cod_doc.fecha_doc

                self._agregar_notificacion(
                    tipo='documento_nuevo',
                    icono='fa-file-upload',
                    clase_icono='info',
                    titulo='Nuevo Documento',
                    mensaje=f'{doc_relacion.cod_doc.nom_doc} en {doc_relacion.id_sem.nombre}',
                    tiempo=str(doc_relacion.cod_doc.fecha_doc),
                    url=url,
                    prioridad=5,
                    fecha=fecha_notif
                )
        except ImportError:
            # Si el modelo no existe, simplemente ignorar
            pass

    def _notificar_archivos_entregables(self):
        """Archivos nuevos en entregables de proyectos del usuario"""
        try:
            mis_proyectos = UsuarioProyecto.objects.filter(
                cedula=self.usuario
            ).values_list('cod_pro', flat=True)

            archivos = Archivo.objects.filter(
                entregable__cod_pro__in=mis_proyectos
            ).select_related(
                'entregable',
                'entregable__cod_pro'
            ).order_by('-fecha_subida')[:2]

            for archivo in archivos:
                proyecto = archivo.entregable.cod_pro
                entregable = archivo.entregable

                sempro = proyecto.semilleroproyecto_set.first()
                url = self._get_proyecto_url(proyecto, sempro)

                self._agregar_notificacion(
                    tipo='archivo_entregable',
                    icono='fa-file-upload',
                    clase_icono='success',
                    titulo='Nuevo Archivo',
                    mensaje=f'{archivo.nombre or "Archivo"} en {entregable.nom_entre}',
                    tiempo=archivo.fecha_subida.strftime('%d/%m/%Y %H:%M'),
                    url=url,
                    prioridad=4,
                    fecha=archivo.fecha_subida
                )

        except Exception as e:
            print(f"Error en _notificar_archivos_entregables: {e}")

    # ==================== MÉTODOS AUXILIARES ====================
    def _agregar_notificacion(self, tipo, icono, clase_icono, titulo, mensaje, tiempo, url, prioridad=5, fecha=None):
        """Agrega una notificación a la lista con campo fecha obligatorio"""
        # Si no hay fecha, usar fecha actual
        if fecha is None:
            fecha = self.ahora.date()
        
        # Convertir fecha a ISO string para el frontend
        if isinstance(fecha, datetime):
            fecha_iso = fecha.date().isoformat()
        elif hasattr(fecha, 'isoformat'):
            fecha_iso = fecha.isoformat()
        else:
            # Si es string u otro tipo, intentar convertir
            try:
                fecha_iso = str(fecha)
            except:
                fecha_iso = self.ahora.date().isoformat()
        
        self.notificaciones.append({
            'tipo': tipo,
            'icono': icono,
            'clase_icono': clase_icono,
            'titulo': titulo,
            'mensaje': mensaje,
            'tiempo': tiempo,
            'url': url,
            'leida': False,
            'prioridad': prioridad,
            'fecha': fecha_iso  # Campo obligatorio para el agrupamiento
        })
    
    def _get_proyecto_url(self, proyecto, sempro):
        """Genera URL del proyecto"""
        if sempro:
            try:
                return reverse('detalle-proyecto', kwargs={
                    'id_sem': sempro.id_sem.id_sem,
                    'cod_pro': proyecto.cod_pro
                })
            except:
                return reverse('proyectos')
        return reverse('proyectos')
    
    def _get_entregable_url(self, entregable, sempro):
        """Genera URL del entregable"""
        if sempro:
            try:
                return reverse('detalle-proyecto', kwargs={
                    'id_sem': sempro.id_sem.id_sem,
                    'cod_pro': entregable.cod_pro.cod_pro
                })
            except:
                return reverse('proyectos')
        return reverse('proyectos')
    
    def ordenar_por_prioridad(self):
        """Ordena las notificaciones por prioridad y fecha"""
        self.notificaciones.sort(key=lambda x: (x['prioridad'], x.get('fecha', '')), reverse=False)
        return self.notificaciones
    
    def limitar_notificaciones(self, limite=10):
        """Limita el número de notificaciones"""
        self.notificaciones = self.notificaciones[:limite]
        return self.notificaciones
    
    def agrupar_por_tipo(self):
        """Agrupa notificaciones por tipo"""
        agrupadas = {}
        for notif in self.notificaciones:
            tipo = notif['tipo']
            if tipo not in agrupadas:
                agrupadas[tipo] = []
            agrupadas[tipo].append(notif)
        return agrupadas
    
    def filtrar_por_prioridad(self, prioridad_minima=1):
        """Filtra notificaciones por prioridad mínima"""
        self.notificaciones = [
            n for n in self.notificaciones 
            if n['prioridad'] <= prioridad_minima
        ]
        return self.notificaciones
    
    def marcar_como_leidas(self, tipo=None):
        """Marca notificaciones como leídas"""
        for notif in self.notificaciones:
            if tipo is None or notif['tipo'] == tipo:
                notif['leida'] = True
        return self.notificaciones
    
    def obtener_resumen(self):
        """Obtiene un resumen de notificaciones por categoría"""
        resumen = {
            'eventos': 0,
            'proyectos': 0,
            'entregables': 0,
            'semilleros': 0,
            'usuarios': 0,
            'documentos': 0,
            'total': len(self.notificaciones),
            'urgentes': 0
        }
        
        for notif in self.notificaciones:
            tipo = notif['tipo']
            
            # Contar por categoría
            if 'evento' in tipo:
                resumen['eventos'] += 1
            elif 'proyecto' in tipo:
                resumen['proyectos'] += 1
            elif 'entregable' in tipo:
                resumen['entregables'] += 1
            elif 'semillero' in tipo or 'miembro' in tipo or 'aprendiz' in tipo:
                resumen['semilleros'] += 1
            elif 'lider' in tipo or 'asignacion' in tipo or 'remocion' in tipo:
                resumen['usuarios'] += 1
            elif 'documento' in tipo:
                resumen['documentos'] += 1
            
            # Contar urgentes (prioridad 1-2)
            if notif['prioridad'] <= 2:
                resumen['urgentes'] += 1
        
        return resumen

def obtener_notificaciones_usuario(usuario, limite=20):
    """
    Función principal para obtener notificaciones de un usuario
    
    Args:
        usuario: Instancia del modelo Usuario
        limite: Número máximo de notificaciones a retornar
    
    Returns:
        Lista de notificaciones ordenadas por prioridad
    """
    manager = NotificationManager(usuario)
    notificaciones = manager.obtener_todas()
    manager.ordenar_por_prioridad()
    manager.limitar_notificaciones(limite)
    
    return {
        'notificaciones': manager.notificaciones,
        'resumen': manager.obtener_resumen(),
        'total': len(manager.notificaciones)
    }

def obtener_notificaciones(request, limite=50):
    """
    Función de compatibilidad que obtiene notificaciones desde la sesión/request
    
    Args:
        request: HttpRequest object
        limite: Número máximo de notificaciones
    
    Returns:
        Lista de notificaciones
    """
    try:
        # Verificar que hay sesión activa
        if not hasattr(request, 'session'):
            print("Error: request no tiene sesión")
            return []
        
        cedula = request.session.get('cedula')
        if not cedula:
            print("Error: No hay cédula en sesión")
            return []
        
        # Obtener usuario
        try:
            usuario = Usuario.objects.get(cedula=cedula)
        except Usuario.DoesNotExist:
            print(f"Error: Usuario con cédula {cedula} no existe")
            return []
        
        # Obtener notificaciones
        resultado = obtener_notificaciones_usuario(usuario, limite)
        return resultado['notificaciones']
        
    except Exception as e:
        print(f"Error crítico en obtener_notificaciones: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
    
def obtener_notificaciones_por_categoria(usuario, categoria):
    """
    Obtiene notificaciones filtradas por categoría
    
    Args:
        usuario: Instancia del modelo Usuario
        categoria: 'eventos', 'proyectos', 'entregables', 'semilleros', 'usuarios', 'documentos'
    
    Returns:
        Lista de notificaciones de la categoría especificada
    """
    manager = NotificationManager(usuario)
    notificaciones = manager.obtener_todas()
    
    filtradas = []
    for notif in notificaciones:
        tipo = notif['tipo']
        
        if categoria == 'eventos' and 'evento' in tipo:
            filtradas.append(notif)
        elif categoria == 'proyectos' and 'proyecto' in tipo:
            filtradas.append(notif)
        elif categoria == 'entregables' and 'entregable' in tipo:
            filtradas.append(notif)
        elif categoria == 'semilleros' and ('semillero' in tipo or 'miembro' in tipo or 'aprendiz' in tipo):
            filtradas.append(notif)
        elif categoria == 'usuarios' and ('lider' in tipo or 'asignacion' in tipo or 'remocion' in tipo):
            filtradas.append(notif)
        elif categoria == 'documentos' and 'documento' in tipo:
            filtradas.append(notif)
    
    return filtradas

def obtener_notificaciones(request, limite=50):
    """
    Función de compatibilidad que obtiene notificaciones desde la sesión/request
    
    Args:
        request: HttpRequest object
        limite: Número máximo de notificaciones
    
    Returns:
        Lista de notificaciones
    """
    if not request.session.get('cedula'):
        return []
    
    try:
        usuario = Usuario.objects.get(cedula=request.session['cedula'])
        resultado = obtener_notificaciones_usuario(usuario, limite)
        return resultado['notificaciones']
    except Usuario.DoesNotExist:
        return []
    except Exception as e:
        print(f"Error obteniendo notificaciones: {str(e)}")
        return []

def obtener_notificaciones_con_resumen(request, limite=50):
    """
    Obtiene notificaciones con resumen completo
    """
    resumen_vacio = {
        'eventos': 0,
        'proyectos': 0,
        'entregables': 0,
        'semilleros': 0,
        'usuarios': 0,
        'documentos': 0,
        'total': 0,
        'urgentes': 0
    }
    
    try:
        if not hasattr(request, 'session'):
            return {'notificaciones': [], 'resumen': resumen_vacio, 'total': 0}
        
        cedula = request.session.get('cedula')
        if not cedula:
            return {'notificaciones': [], 'resumen': resumen_vacio, 'total': 0}
        
        try:
            usuario = Usuario.objects.get(cedula=cedula)
        except Usuario.DoesNotExist:
            return {'notificaciones': [], 'resumen': resumen_vacio, 'total': 0}
        
        return obtener_notificaciones_usuario(usuario, limite)
        
    except Exception as e:
        print(f"Error en obtener_notificaciones_con_resumen: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'notificaciones': [], 'resumen': resumen_vacio, 'total': 0}
    """
    Obtiene notificaciones con resumen completo
    
    Args:
        request: HttpRequest object
        limite: Número máximo de notificaciones
    
    Returns:
        Dict con notificaciones, resumen y total
    """
    if not request.session.get('cedula'):
        return {
            'notificaciones': [],
            'resumen': {
                'eventos': 0,
                'proyectos': 0,
                'entregables': 0,
                'semilleros': 0,
                'usuarios': 0,
                'documentos': 0,
                'total': 0,
                'urgentes': 0
            },
            'total': 0
        }
    
    try:
        usuario = Usuario.objects.get(cedula=request.session['cedula'])
        return obtener_notificaciones_usuario(usuario, limite)
    except Usuario.DoesNotExist:
        return {
            'notificaciones': [],
            'resumen': {
                'eventos': 0,
                'proyectos': 0,
                'entregables': 0,
                'semilleros': 0,
                'usuarios': 0,
                'documentos': 0,
                'total': 0,
                'urgentes': 0
            },
            'total': 0
        }
    except Exception as e:
        print(f"Error obteniendo notificaciones: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'notificaciones': [],
            'resumen': {
                'eventos': 0,
                'proyectos': 0,
                'entregables': 0,
                'semilleros': 0,
                'usuarios': 0,
                'documentos': 0,
                'total': 0,
                'urgentes': 0
            },
            'total': 0
        }