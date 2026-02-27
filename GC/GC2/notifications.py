import traceback
from django.http import JsonResponse
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta, datetime, date
from django.db.models import Q, Count
from django.views.decorators.http import require_GET

from .models import (
    Usuario, Evento, Entregable, Proyecto, Semillero,
    SemilleroUsuario, UsuarioProyecto, Aprendiz, ProyectoAprendiz, Archivo
)

# ── Constantes de estado (cubren variaciones con/sin tilde, mayús/minús) ──────
ESTADOS_PROYECTO_ACTIVOS    = [
    'pendiente', 'planeacion', 'ejecucion', 'en ejecucion',
    'en_ejecucion', 'activo', 'en curso', 'iniciado', 'Pendiente',
    'Planeacion', 'Ejecucion', 'Activo'
]
ESTADOS_PROYECTO_TERMINADOS = [
    'finalizado', 'completado', 'aprobado', 'terminado',
    'Finalizado', 'Completado', 'Aprobado', 'Terminado'
]
ESTADOS_PROYECTO_CANCELADOS = [
    'cancelado', 'suspendido', 'rechazado',
    'Cancelado', 'Suspendido', 'Rechazado'
]
ESTADOS_EVENTO_ACTIVOS = [
    'Próximo', 'Programado', 'Proximo', 'programado', 'próximo', 'activo', 'Activo'
]
ESTADOS_ENTREGABLE_PENDIENTE  = ['Pendiente', 'pendiente']
ESTADOS_ENTREGABLE_RETRASADO  = ['Retrasado', 'retrasado', 'Vencido', 'vencido']
ESTADOS_ENTREGABLE_COMPLETADO = ['Completado', 'completado', 'Entregado', 'entregado']
ESTADOS_ENTREGABLE_RECHAZADO  = ['Rechazado', 'rechazado']


# ─── Vista API ────────────────────────────────────────────────────────────────
@require_GET
def api_notificaciones(request):
    try:
        cedula = request.session.get('cedula')
        if not cedula:
            return JsonResponse({
                'success': False, 'notificaciones': [],
                'count': 0, 'resumen': _resumen_vacio()
            })

        usuario = Usuario.objects.filter(cedula=cedula).first()
        if not usuario:
            return JsonResponse({
                'success': False, 'notificaciones': [],
                'count': 0, 'resumen': _resumen_vacio()
            })

        resultado = obtener_notificaciones_usuario(usuario, limite=50)
        return JsonResponse({
            'success': True,
            'notificaciones': resultado['notificaciones'],
            'count': resultado['total'],
            'resumen': resultado['resumen'],
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({
            'success': False, 'error': str(e),
            'notificaciones': [], 'count': 0
        }, status=500)


def _resumen_vacio():
    return {
        'eventos': 0, 'proyectos': 0, 'entregables': 0,
        'semilleros': 0, 'usuarios': 0, 'documentos': 0,
        'total': 0, 'urgentes': 0
    }


def _to_date(valor):
    if valor is None:
        return date.today()
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return datetime.fromisoformat(str(valor)).date()
    except Exception:
        return date.today()


# ─── Manager ──────────────────────────────────────────────────────────────────
class NotificationManager:

    def __init__(self, usuario):
        self.usuario = usuario
        self.ahora   = timezone.now()
        self.hoy     = self.ahora.date()
        self.notificaciones = []

    def obtener_todas(self):
        for metodo in [
            self._notif_eventos_proximos,
            self._notif_eventos_hoy,
            self._notif_eventos_sin_cerrar,
            self._notif_proyectos_asignados,
            self._notif_proyectos_lider,
            self._notif_proyectos_bajo_progreso,
            self._notif_proyectos_terminados,
            self._notif_proyectos_cancelados,
            self._notif_proyectos_cerca_vencimiento,
            self._notif_entregables_vencen_hoy,
            self._notif_entregables_retrasados,
            self._notif_entregables_pendientes_proximos,
            self._notif_entregables_completados,
            self._notif_entregables_rechazados,
            self._notif_liderazgo_semillero,
            self._notif_nuevos_miembros,
            self._notif_semillero_inactivo,
            self._notif_archivos_recientes,
            self._notif_documentos_nuevos,
        ]:
            try:
                metodo()
            except Exception as e:
                print(f"[notifications] ⚠️  {metodo.__name__}: {e}")
        return self.notificaciones

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _pids(self, solo_lider=False):
        qs = UsuarioProyecto.objects.filter(cedula=self.usuario)
        if solo_lider:
            qs = qs.filter(es_lider_pro=True)
        return list(qs.values_list('cod_pro', flat=True))

    def _sids(self, solo_lider=False):
        qs = SemilleroUsuario.objects.filter(cedula=self.usuario)
        if solo_lider:
            qs = qs.filter(es_lider=True)
        return list(qs.values_list('id_sem', flat=True))

    def _url_pro(self, proyecto):
        try:
            sp = proyecto.semilleroproyecto_set.first()
            if sp:
                return reverse('detalle-proyecto', kwargs={
                    'id_sem': sp.id_sem.id_sem,
                    'cod_pro': proyecto.cod_pro
                })
        except Exception:
            pass
        return reverse('proyectos')

    def _add(self, tipo, icono, clase, titulo, mensaje, tiempo, url,
             prioridad=5, fecha=None):
        self.notificaciones.append({
            'tipo': tipo,
            'icono': icono,
            'clase_icono': clase,
            'titulo': titulo,
            'mensaje': mensaje,
            'tiempo': tiempo,
            'url': url,
            'leida': False,
            'prioridad': prioridad,
            'fecha': _to_date(fecha).isoformat() if fecha else self.hoy.isoformat(),
        })

    # ── EVENTOS ───────────────────────────────────────────────────────────────
    def _notif_eventos_proximos(self):
        for ev in Evento.objects.filter(
            fecha_eve__gte=self.hoy,
            fecha_eve__lte=(self.ahora + timedelta(days=1)).date(),
            estado_eve__in=ESTADOS_EVENTO_ACTIVOS
        ).order_by('fecha_eve', 'hora_inicio')[:5]:
            dt = datetime.combine(ev.fecha_eve, ev.hora_inicio)
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
            mins = (dt - self.ahora).total_seconds() / 60
            if mins < 0:
                continue
            h   = int(mins // 60)
            msg = f'Comienza en {int(mins)} min' if mins < 60 else f'Comienza en {h}h'
            self._add('evento_proximo', 'fa-calendar-check',
                      'error' if mins < 180 else 'warning',
                      f'Evento Próximo: {ev.nom_eve}', msg,
                      ev.fecha_eve.strftime('%d/%m/%Y'),
                      reverse('eventos'),
                      prioridad=1 if mins < 60 else 2, fecha=ev.fecha_eve)

    def _notif_eventos_hoy(self):
        for ev in Evento.objects.filter(
            fecha_eve=self.hoy,
            estado_eve__in=ESTADOS_EVENTO_ACTIVOS
        ).order_by('hora_inicio')[:5]:
            self._add('evento_hoy', 'fa-calendar-day', 'warning',
                      f'Evento Hoy: {ev.nom_eve}',
                      f'A las {ev.hora_inicio.strftime("%H:%M")}',
                      'Hoy', reverse('eventos'), prioridad=2, fecha=ev.fecha_eve)

    def _notif_eventos_sin_cerrar(self):
        for ev in Evento.objects.filter(
            fecha_eve__lt=self.hoy,
            estado_eve__in=ESTADOS_EVENTO_ACTIVOS
        ).order_by('-fecha_eve')[:3]:
            self._add('evento_sin_cerrar', 'fa-calendar-xmark', 'warning',
                      'Evento sin cerrar',
                      f'{ev.nom_eve} — pasó el {ev.fecha_eve.strftime("%d/%m/%Y")}',
                      'Requiere cierre', reverse('eventos'),
                      prioridad=4, fecha=ev.fecha_eve)

    # ── PROYECTOS ─────────────────────────────────────────────────────────────
    def _notif_proyectos_asignados(self):
        """Todos los proyectos del usuario que NO estén terminados/cancelados."""
        for up in UsuarioProyecto.objects.filter(
            cedula=self.usuario
        ).select_related('cod_pro').order_by('-usupro_id')[:5]:
            p = up.cod_pro
            if p.estado_pro in ESTADOS_PROYECTO_TERMINADOS + ESTADOS_PROYECTO_CANCELADOS:
                continue
            self._add('asignacion_proyecto', 'fa-diagram-project', 'info',
                      'Proyecto Activo',
                      f'{p.nom_pro} — {p.estado_pro}',
                      f'Progreso: {p.progreso}%',
                      self._url_pro(p),
                      prioridad=4, fecha=p.fecha_creacion)

    def _notif_proyectos_lider(self):
        for up in UsuarioProyecto.objects.filter(
            cedula=self.usuario, es_lider_pro=True
        ).select_related('cod_pro').order_by('-usupro_id')[:3]:
            p = up.cod_pro
            self._add('lider_proyecto', 'fa-star', 'warning',
                      'Eres Líder de Proyecto',
                      f'{p.nom_pro}',
                      'Rol activo', self._url_pro(p),
                      prioridad=3, fecha=p.fecha_creacion)

    def _notif_proyectos_bajo_progreso(self):
        pids = self._pids()
        for p in Proyecto.objects.filter(
            cod_pro__in=pids,
            progreso__lt=30,
            estado_pro__in=ESTADOS_PROYECTO_ACTIVOS
        ).order_by('progreso')[:3]:
            self._add('proyecto_bajo_progreso', 'fa-exclamation-triangle', 'error',
                      'Proyecto con bajo progreso',
                      f'{p.nom_pro} — {p.progreso}%',
                      'Requiere atención', self._url_pro(p),
                      prioridad=3, fecha=p.fecha_creacion)

    def _notif_proyectos_terminados(self):
        pids = self._pids()
        for p in Proyecto.objects.filter(
            cod_pro__in=pids,
            estado_pro__in=ESTADOS_PROYECTO_TERMINADOS
        ).order_by('-cod_pro')[:3]:
            # ✅ Proyecto SÍ tiene fecha_completado
            fecha = p.fecha_completado or p.fecha_creacion or self.hoy
            self._add('proyecto_completado', 'fa-circle-check', 'success',
                      'Proyecto Completado',
                      f'{p.nom_pro} ha sido finalizado',
                      _to_date(fecha).strftime('%d/%m/%Y'),
                      self._url_pro(p),
                      prioridad=4, fecha=fecha)

    def _notif_proyectos_cancelados(self):
        pids = self._pids()
        for p in Proyecto.objects.filter(
            cod_pro__in=pids,
            estado_pro__in=ESTADOS_PROYECTO_CANCELADOS
        ).order_by('-cod_pro')[:2]:
            self._add('proyecto_cancelado', 'fa-ban', 'error',
                      'Proyecto Cancelado',
                      f'{p.nom_pro} — "{p.estado_pro}"',
                      'Actualizado', self._url_pro(p),
                      prioridad=2, fecha=p.fecha_creacion)

    def _notif_proyectos_cerca_vencimiento(self):
        pids  = self._pids()
        limite = self.hoy + timedelta(days=7)
        vistos = set()
        for e in Entregable.objects.filter(
            cod_pro__in=pids,
            estado__in=ESTADOS_ENTREGABLE_PENDIENTE,
            fecha_fin__gte=self.hoy,
            fecha_fin__lte=limite
        ).select_related('cod_pro').order_by('fecha_fin')[:6]:
            pk = e.cod_pro.cod_pro
            if pk in vistos:
                continue
            vistos.add(pk)
            dias = (e.fecha_fin - self.hoy).days
            self._add('proyecto_vencimiento', 'fa-hourglass-half', 'warning',
                      'Entregable próximo en proyecto',
                      f'{e.cod_pro.nom_pro} — vence en {dias} día(s)',
                      e.fecha_fin.strftime('%d/%m/%Y'),
                      self._url_pro(e.cod_pro),
                      prioridad=2 if dias <= 3 else 3, fecha=e.fecha_fin)

    # ── ENTREGABLES ───────────────────────────────────────────────────────────
    def _notif_entregables_vencen_hoy(self):
        pids = self._pids()
        for e in Entregable.objects.filter(
            cod_pro__in=pids,
            estado__in=ESTADOS_ENTREGABLE_PENDIENTE,
            fecha_fin=self.hoy
        ).select_related('cod_pro'):
            self._add('entregable_hoy', 'fa-exclamation-circle', 'error',
                      '¡Entregable Vence Hoy!',
                      f'{e.nom_entre} — {e.cod_pro.nom_pro}',
                      'Vence Hoy', self._url_pro(e.cod_pro),
                      prioridad=1, fecha=e.fecha_fin)

    def _notif_entregables_retrasados(self):
        pids = self._pids()
        # Con estado explícito 'Retrasado'
        for e in Entregable.objects.filter(
            cod_pro__in=pids,
            estado__in=ESTADOS_ENTREGABLE_RETRASADO
        ).select_related('cod_pro')[:5]:
            dias = max(0, (self.hoy - e.fecha_fin).days)
            self._add('entregable_retrasado', 'fa-clock', 'error',
                      'Entregable Retrasado',
                      f'{e.nom_entre} — {dias} día(s) de retraso',
                      f'Venció el {e.fecha_fin.strftime("%d/%m/%Y")}',
                      self._url_pro(e.cod_pro),
                      prioridad=1, fecha=e.fecha_fin)
        # Pendientes con fecha ya vencida (aunque no estén marcados 'Retrasado')
        for e in Entregable.objects.filter(
            cod_pro__in=pids,
            estado__in=ESTADOS_ENTREGABLE_PENDIENTE,
            fecha_fin__lt=self.hoy
        ).select_related('cod_pro')[:3]:
            dias = (self.hoy - e.fecha_fin).days
            self._add('entregable_retrasado', 'fa-clock', 'error',
                      'Entregable Vencido',
                      f'{e.nom_entre} — {dias} día(s) sin entregar',
                      f'Venció el {e.fecha_fin.strftime("%d/%m/%Y")}',
                      self._url_pro(e.cod_pro),
                      prioridad=1, fecha=e.fecha_fin)

    def _notif_entregables_pendientes_proximos(self):
        pids = self._pids()
        for e in Entregable.objects.filter(
            cod_pro__in=pids,
            estado__in=ESTADOS_ENTREGABLE_PENDIENTE,
            fecha_fin__gte=self.hoy,
            fecha_fin__lte=(self.hoy + timedelta(days=7))
        ).select_related('cod_pro').order_by('fecha_fin')[:5]:
            dias = (e.fecha_fin - self.hoy).days
            self._add('entregable_pendiente', 'fa-file-alt',
                      'warning' if dias <= 2 else 'info',
                      f'Entregable: {e.nom_entre}',
                      f'Vence en {dias} día(s) — {e.cod_pro.nom_pro}',
                      e.fecha_fin.strftime('%d/%m/%Y'),
                      self._url_pro(e.cod_pro),
                      prioridad=1 if dias <= 2 else 3, fecha=e.fecha_fin)

    def _notif_entregables_completados(self):
        pids = self._pids()
        for e in Entregable.objects.filter(
            cod_pro__in=pids,
            estado__in=ESTADOS_ENTREGABLE_COMPLETADO
        ).select_related('cod_pro').order_by('-cod_entre')[:3]:
            self._add('entregable_completado', 'fa-check-double', 'success',
                      'Entregable Completado',
                      f'{e.nom_entre} — {e.cod_pro.nom_pro}',
                      'Completado', self._url_pro(e.cod_pro),
                      prioridad=5, fecha=e.fecha_fin)

    def _notif_entregables_rechazados(self):
        pids = self._pids()
        for e in Entregable.objects.filter(
            cod_pro__in=pids,
            estado__in=ESTADOS_ENTREGABLE_RECHAZADO
        ).select_related('cod_pro').order_by('-cod_entre')[:3]:
            self._add('entregable_rechazado', 'fa-file-circle-xmark', 'error',
                      'Entregable Rechazado',
                      f'{e.nom_entre} necesita corrección',
                      'Requiere corrección', self._url_pro(e.cod_pro),
                      prioridad=2, fecha=e.fecha_fin)

    # ── SEMILLEROS ────────────────────────────────────────────────────────────
    def _notif_liderazgo_semillero(self):
        for su in SemilleroUsuario.objects.filter(
            cedula=self.usuario, es_lider=True
        ).select_related('id_sem')[:3]:
            url = reverse('resu-miembros', kwargs={'id_sem': su.id_sem.id_sem})
            # ✅ Semillero tiene fecha_creacion (auto_now_add)
            self._add('nuevo_lider_semillero', 'fa-crown', 'warning',
                      'Líder de Semillero',
                      f'Eres líder de {su.id_sem.nombre}',
                      'Rol activo', url,
                      prioridad=3, fecha=su.id_sem.fecha_creacion)

    def _notif_nuevos_miembros(self):
        sids = self._sids(solo_lider=True)
        for m in SemilleroUsuario.objects.filter(
            id_sem__in=sids
        ).select_related('cedula', 'id_sem').order_by('-semusu_id')[:5]:
            if m.cedula.cedula == self.usuario.cedula:
                continue
            url = reverse('resu-miembros', kwargs={'id_sem': m.id_sem.id_sem})
            # ✅ SemilleroUsuario NO tiene fecha_union → usa fecha_creacion del semillero
            self._add('nuevo_miembro', 'fa-user-plus', 'success',
                      'Miembro en Semillero',
                      f'{m.cedula.nom_usu} en {m.id_sem.nombre}',
                      'Activo', url,
                      prioridad=4, fecha=m.id_sem.fecha_creacion)

    def _notif_semillero_inactivo(self):
        sids = self._sids(solo_lider=True)
        # ✅ Semillero tiene M2M 'proyectos' via SemilleroProyecto → Count('proyectos') es correcto
        for s in Semillero.objects.filter(id_sem__in=sids).annotate(
            activos=Count(
                'proyectos',
                filter=Q(proyectos__estado_pro__in=ESTADOS_PROYECTO_ACTIVOS)
            )
        ).filter(activos=0)[:2]:
            url = reverse('resu-miembros', kwargs={'id_sem': s.id_sem})
            self._add('semillero_inactivo', 'fa-leaf', 'warning',
                      'Semillero sin proyectos activos',
                      f'{s.nombre} no tiene proyectos en progreso',
                      'Requiere atención', url,
                      prioridad=5, fecha=s.fecha_creacion)

    # ── ARCHIVOS / DOCUMENTOS ─────────────────────────────────────────────────
    def _notif_archivos_recientes(self):
        pids = self._pids()
        # ✅ Archivo NO tiene campo 'eliminado' → sin ese filtro
        for arch in Archivo.objects.filter(
            entregable__cod_pro__in=pids
        ).select_related(
            'entregable', 'entregable__cod_pro'
        ).order_by('-fecha_subida')[:3]:
            self._add('archivo_entregable', 'fa-file-arrow-up', 'success',
                      'Archivo en Entregable',
                      f'{arch.nombre or "Archivo"} → {arch.entregable.nom_entre}',
                      arch.fecha_subida.strftime('%d/%m/%Y %H:%M'),
                      self._url_pro(arch.entregable.cod_pro),
                      prioridad=4, fecha=arch.fecha_subida)

    def _notif_documentos_nuevos(self):
        try:
            from .models import SemilleroDocumento
            sids = self._sids()
            for d in SemilleroDocumento.objects.filter(
                id_sem__in=sids
            ).select_related('cod_doc', 'id_sem').order_by('-id_doc')[:3]:
                url = reverse('resu-miembros', kwargs={'id_sem': d.id_sem.id_sem})
                self._add('documento_nuevo', 'fa-file-upload', 'info',
                          'Documento en Semillero',
                          f'{d.cod_doc.nom_doc} — {d.id_sem.nombre}',
                          str(d.cod_doc.fecha_doc), url,
                          prioridad=5, fecha=d.id_sem.fecha_creacion)
        except Exception:
            pass

    # ── Utilidades ────────────────────────────────────────────────────────────
    def ordenar_por_prioridad(self):
        self.notificaciones.sort(
            key=lambda x: (x['prioridad'], x.get('fecha', ''))
        )
        return self.notificaciones

    def limitar_notificaciones(self, limite=50):
        self.notificaciones = self.notificaciones[:limite]
        return self.notificaciones

    def obtener_resumen(self):
        r = {
            'eventos': 0, 'proyectos': 0, 'entregables': 0,
            'semilleros': 0, 'usuarios': 0, 'documentos': 0,
            'total': len(self.notificaciones), 'urgentes': 0
        }
        for n in self.notificaciones:
            t = n['tipo']
            if   'evento'     in t: r['eventos']    += 1
            elif 'proyecto'   in t: r['proyectos']   += 1
            elif 'entregable' in t: r['entregables'] += 1
            elif any(k in t for k in ('semillero', 'miembro')): r['semilleros'] += 1
            elif any(k in t for k in ('lider', 'asignacion')): r['usuarios']   += 1
            elif 'documento'  in t: r['documentos']  += 1
            if n['prioridad'] <= 2: r['urgentes'] += 1
        return r

    # Legacy aliases
    _agregar_notificacion = _add
    _get_proyecto_url     = lambda self, p, *_: self._url_pro(p)
    _get_entregable_url   = lambda self, e, *_: self._url_pro(e.cod_pro)


# ─── Funciones de conveniencia ────────────────────────────────────────────────
def obtener_notificaciones_usuario(usuario, limite=50):
    m = NotificationManager(usuario)
    m.obtener_todas()
    m.ordenar_por_prioridad()
    m.limitar_notificaciones(limite)
    return {
        'notificaciones': m.notificaciones,
        'resumen': m.obtener_resumen(),
        'total': len(m.notificaciones)
    }


def obtener_notificaciones(request, limite=50):
    try:
        cedula = request.session.get('cedula')
        if not cedula:
            return []
        usuario = Usuario.objects.filter(cedula=cedula).first()
        if not usuario:
            return []
        return obtener_notificaciones_usuario(usuario, limite)['notificaciones']
    except Exception:
        traceback.print_exc()
        return []


def obtener_notificaciones_con_resumen(request, limite=50):
    vacio = {'notificaciones': [], 'resumen': _resumen_vacio(), 'total': 0}
    try:
        cedula = request.session.get('cedula')
        if not cedula:
            return vacio
        usuario = Usuario.objects.filter(cedula=cedula).first()
        if not usuario:
            return vacio
        return obtener_notificaciones_usuario(usuario, limite)
    except Exception:
        traceback.print_exc()
        return vacio


def obtener_notificaciones_por_categoria(usuario, categoria):
    m = NotificationManager(usuario)
    m.obtener_todas()
    mapa = {
        'eventos':     lambda t: 'evento' in t,
        'proyectos':   lambda t: 'proyecto' in t,
        'entregables': lambda t: 'entregable' in t,
        'semilleros':  lambda t: any(k in t for k in ('semillero', 'miembro')),
        'usuarios':    lambda t: any(k in t for k in ('lider', 'asignacion')),
        'documentos':  lambda t: 'documento' in t,
    }
    f = mapa.get(categoria)
    return [n for n in m.notificaciones if f and f(n['tipo'])]