from urllib import request
from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from .forms import UsuarioRegistroForm
from .models import Documento, Usuario, Semillero,SemilleroUsuario, Archivo, Aprendiz, ProyectoAprendiz, Proyecto, UsuarioProyecto, SemilleroProyecto, Entregable, SemilleroDocumento
from django.utils import timezone 
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_str, force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.auth.decorators import permission_required
from django.views.decorators.cache import never_cache
from functools import wraps
from django.utils import timezone
from django.utils.timezone import now
from datetime import timedelta
from django.http import Http404
from django.db.models import Q, Avg
from datetime import datetime
from django.db.models import Case, When, Value, IntegerField
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
import os
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
import openpyxl
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from datetime import date
from openpyxl.styles import Border, Side, Font
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO


# Create your views here.
def bienvenido(request):
    return render(request, 'paginas/bienvenido.html')

# VISTAS DE LOGIN
def registro(request):
    if request.method == 'POST':
        form = UsuarioRegistroForm(request.POST)
        if form.is_valid():
            try:
                usuario = form.save(commit=False)
                usuario.email_verificado = False
                usuario.save()

                # Si tu modelo tiene métodos personalizados:
                if hasattr(usuario, 'generar_token_verificacion'):
                    usuario.generar_token_verificacion()
                if hasattr(usuario, 'enviar_email_verificacion'):
                    usuario.enviar_email_verificacion(request)

                messages.success(request, "¡Registro exitoso! Verifica tu correo electrónico.")
                return redirect('iniciarsesion')
            except Exception as e:
                messages.error(request, f"Error al registrar usuario: {e}")
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = UsuarioRegistroForm()

    # CAMBIO: Ya no enviamos show_login, la página inicia siempre en login
    return render(request, 'paginas/registro.html', {
        'form': form,
        'current_page_name': 'registro',
        'show_register': True  # Nueva variable para indicar que queremos mostrar registro
    })

# Vista para verificar el correo electrónico
def verificar_email(request, token):
    try:
        # Buscar el administrador con este token
        usuario = Usuario.objects.get(token_verificacion=token)
        
        # Verificar si el token ha expirado
        if usuario.token_expira and usuario.token_expira < timezone.now():
            messages.error(request, "El enlace de verificación ha expirado. Por favor, solicita uno nuevo.")
            return redirect('iniciarsesion')
        
        # Marcar como verificado
        usuario.email_verificado = True
        usuario.token_verificacion = None
        usuario.token_expira = None
        usuario.save()
        
        messages.success(request, "¡Tu correo electrónico ha sido verificado correctamente! Ahora puedes iniciar sesión.")
        return redirect('iniciarsesion')
        
    except Usuario.DoesNotExist:
        messages.error(request, "El enlace de verificación no es válido.")
        return redirect('iniciarsesion') 

# VISTA DE INICIAR SESION
def iniciarsesion(request):
    if request.method == 'POST':

        cedula = request.POST.get('cedula')
        password = request.POST.get('password')
        rol = request.POST.get('rol')

        errores = {}

        # --- Validaciones ---
        if not rol:
            errores['error_rol'] = "Debe seleccionar un rol."
        if not cedula:
            errores['error_user'] = "La cédula es obligatoria."
        if not password:
            errores['error_password'] = "La contraseña es obligatoria."

        if errores:
            # CAMBIO: Ya no necesitamos show_login, siempre inicia en login
            return render(request, 'paginas/registro.html', {
                **errores,
                'cedula': cedula,
                'rol': rol,
                'current_page_name': 'Iniciar Sesión'
            })

        # --- Autenticación oficial Django ---
        usuario = authenticate(request, cedula=cedula, password=password)

        if usuario is None:
            # Si no pasa autenticación, puede ser que el rol no coincida
            try:
                u = Usuario.objects.get(cedula=cedula)
                if not u.check_password(password):
                    errores['error_password'] = "Contraseña incorrecta."
                elif u.rol != rol:
                    errores['error_rol'] = "El rol seleccionado no coincide con tu usuario."
                else:
                    errores['error_user'] = "Usuario no encontrado o inactivo."
            except Usuario.DoesNotExist:
                errores['error_user'] = "Usuario no registrado."

            # CAMBIO: Ya no necesitamos show_login
            return render(request, 'paginas/registro.html', {
                **errores,
                'cedula': cedula,
                'rol': rol,
                'current_page_name': 'Iniciar Sesión'
            })

        # --- Verificación de correo electrónico ---
        if not usuario.email_verificado:
            return render(request, 'paginas/registro.html', {
                'error_user': 'Debes verificar tu correo antes de iniciar sesión.',
                'cedula': cedula,
                'rol': rol,
                'current_page_name': 'Iniciar Sesión'
            })

        # --- Iniciar sesión ---
        login(request, usuario)

        # --- Guardar información adicional en sesión ---
        request.session['cedula'] = usuario.cedula
        request.session['nom_usu'] = usuario.nom_usu
        request.session['ape_usu'] = usuario.ape_usu
        request.session['rol'] = usuario.rol
        request.session['grupos'] = [usuario.rol]

        # --- Actualizar último acceso ---
        usuario.last_login = now()
        usuario.save(update_fields=['last_login'])

        messages.success(request, f"¡Bienvenido, {usuario.nom_usu}!")
        return redirect('home')

    # --- Si es GET ---
    # CAMBIO: Ya no enviamos show_login, la página siempre inicia en login por defecto
    return render(request, 'paginas/registro.html', {
        'current_page_name': 'Iniciar Sesión'
    })

def mostrar_recuperar_contrasena(request):

    return render(request, 'paginas/registro.html', {
        'mostrar_modal': True,
        'show_login': True,  # <- para que cargue login directamente
        'current_page_name': 'Recuperar Contraseña'
    })

def recuperar_contrasena(request):
    """
    Esta vista procesa el formulario de recuperación de contraseña
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        
        if not email:
            return render(request, 'iniciarsesion', {
                'mostrar_modal': True,
                'email_error': 'El correo electrónico es obligatorio',
                'current_page_name': 'Recuperar Contraseña'
            })
        
        try:
            # Verificar si existe un administrador con ese correo
            admin = Usuario.objects.filter(correo_ins=email).first()
            
            if admin:
                # Generar el token y el uid codificado para el enlace de restablecimiento
                uid = urlsafe_base64_encode(force_bytes(admin.pk))
                token = default_token_generator.make_token(admin)
                
                # Construir el enlace de restablecimiento
                reset_link = f"{request.scheme}://{request.get_host()}/reset-password/{uid}/{token}/"
                
                try:
                    # Preparar y enviar el correo
                    subject = "Restablecimiento de contraseña"
                    message = render_to_string('paginas/reset_password_email.html', {
                        'user': admin,
                        'reset_link': reset_link,
                        'site_name': 'GC'
                    })
                    
                    # Cambiado fail_silently a False para que muestre errores
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [admin.correo_ins],
                        html_message=message,
                        fail_silently=False
                    )
                    print(f"Correo enviado exitosamente a {admin.correo_ins}")
                except Exception as email_error:
                    print(f"Error al enviar correo: {email_error}")
                    # Ahora mostramos el error al usuario para facilitar la depuración
                    messages.error(request, f"Problema al enviar el correo: {email_error}")
                    return redirect('iniciarsesion')
                
            # Por seguridad, mostramos un mensaje genérico independientemente de si el correo existe o no
            messages.success(request, "Si el correo está asociado a una cuenta, recibirás instrucciones para restablecer tu contraseña.")
            return redirect('iniciarsesion')
            
        except Exception as e:
            print(f"Error durante recuperación de contraseña: {e}")
            messages.error(request, f"{str(e)}")
            return redirect('iniciarsesion')
    
    # Si no es POST, redirigir a la página de inicio de sesión
    return redirect('iniciarsesion')

def reset_password(request, uidb64, token):
    """
    Vista que muestra el formulario de restablecimiento de contraseña
    cuando el usuario hace clic en el enlace del correo.
    """
    try:
        # 1️⃣ Decodificar el UID
        uid = force_str(urlsafe_base64_decode(uidb64))
        usuario = Usuario.objects.get(pk=uid)

        # 2️⃣ Validar el token
        if default_token_generator.check_token(usuario, token):
            print(f"✅ Token válido para el usuario: {usuario.nom_usu}")
            return render(request, 'paginas/reset_password.html', {
                'valid': True,
                'uidb64': uidb64,
                'token': token,
                'current_page_name': 'Restablecer Contraseña'
            })
        else:
            print("❌ Token inválido o expirado")
            messages.error(request, "El enlace de restablecimiento no es válido o ha expirado.")
            return redirect('iniciarsesion')

    except Exception as e:
        print(f"⚠️ Error en reset_password: {e}")
        messages.error(request, "Error al procesar el enlace de restablecimiento.")
        return redirect('iniciarsesion')

def reset_password_confirm(request):
    """
    Vista que procesa el formulario de restablecimiento de contraseña.
    """
    if request.method == 'POST':
        uidb64 = request.POST.get('uidb64')
        token = request.POST.get('token')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # 1️⃣ Validar coincidencia de contraseñas
        if password1 != password2:
            return render(request, 'paginas/reset_password.html', {
                'valid': True,
                'uidb64': uidb64,
                'token': token,
                'error': 'Las contraseñas no coinciden.',
                'current_page_name': 'Restablecer Contraseña'
            })

        try:
            # 2️⃣ Decodificar el UID y obtener el usuario
            uid = force_str(urlsafe_base64_decode(uidb64))
            usuario = Usuario.objects.get(pk=uid)

            # 3️⃣ Verificar token válido
            if default_token_generator.check_token(usuario, token):

                # ✅ Guardar contraseña de forma segura
                usuario.set_password(password1)
                usuario.save()

                messages.success(request, "Tu contraseña ha sido restablecida con éxito. Ahora puedes iniciar sesión.")
                return redirect('iniciarsesion')
            else:
                messages.error(request, "El enlace de restablecimiento no es válido o ha expirado.")
                return redirect('iniciarsesion')

        except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist) as e:
            print(f"⚠️ Error al restablecer contraseña: {e}")
            messages.error(request, "El enlace de restablecimiento no es válido.")
            return redirect('iniciarsesion')
    
    # Si no es POST, redirigir a la página de inicio de sesión
    return redirect('iniciarsesion')

# VISTA DE PRIVACIDAD
def privacidad(request):
    usuario_id = request.session.get('cedula')
    
    try:
        usuario = Usuario.objects.get(pk=usuario_id)
        
        if request.method == 'POST':
            contraseña_actual = request.POST.get('contraseña_actual')
            nueva_contraseña = request.POST.get('nueva_contraseña')
            confirmar_contraseña = request.POST.get('confirmar_contraseña')
            
            # ✅ Verificar la contraseña actual usando el campo correcto
            if not check_password(contraseña_actual, usuario.password):
                messages.error(request, "La contraseña actual es incorrecta.")
                return redirect('privacidad')
            
            # ✅ Verificar coincidencia
            if nueva_contraseña != confirmar_contraseña:
                messages.error(request, "Las contraseñas nuevas no coinciden.")
                return redirect('privacidad')
            
            # ✅ Validar longitud mínima
            if len(nueva_contraseña) < 8:
                messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
                return redirect('privacidad')
            
            # ✅ Guardar correctamente usando set_password()
            usuario.set_password(nueva_contraseña)
            usuario.save()

            messages.success(request, "Contraseña actualizada correctamente.")
            return redirect('home')
            
    except Usuario.DoesNotExist:
        messages.error(request, "Usuario no encontrado. Por favor, inicie sesión nuevamente.")
        return redirect('iniciarsesion')
    except Exception as e:
        messages.error(request, f"Error al actualizar la contraseña: {str(e)}")
        return redirect('privacidad')
    
    return render(request, 'paginas/home.html', {
        'current_page': 'privacidad',
        'current_page_name': 'Privacidad'
    })

# VISTAS DE HOME 
def home(request):
    usuario_id = request.session.get('cedula')
    if not usuario_id:
        messages.error(request, "Debes iniciar sesión para ver tu perfil.")
        return redirect('iniciarsesion')

    # Obtener usuario
    try:
        usuario = Usuario.objects.get(cedula=usuario_id)
    except Usuario.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect('iniciarsesion')

    return render(request, 'paginas/home.html',{
        'current_page': 'home',
        'current_page_name': 'Inicio',
        'usuario': usuario
    })
    
# VISTAS PERFIL
def perfil(request):
    # Verificar sesión activa
    usuario_id = request.session.get('cedula')
    if not usuario_id:
        messages.error(request, "Debes iniciar sesión para ver tu perfil.")
        return redirect('iniciarsesion')

    # Obtener usuario
    try:
        usuario = Usuario.objects.get(cedula=usuario_id)
    except Usuario.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect('iniciarsesion')

    # Calcular último acceso
    ultimo_acceso = "Sin registro"
    if usuario.last_login:
        tiempo = now() - usuario.last_login
        dias, segundos = tiempo.days, tiempo.seconds
        if dias == 0:
            if segundos < 60:
                ultimo_acceso = "Hace unos segundos"
            elif segundos < 3600:
                minutos = segundos // 60
                ultimo_acceso = f"Hace {minutos} minuto{'s' if minutos != 1 else ''}"
            else:
                horas = segundos // 3600
                ultimo_acceso = f"Hace {horas} hora{'s' if horas != 1 else ''}"
        elif dias == 1:
            ultimo_acceso = "Ayer"
        elif dias < 7:
            ultimo_acceso = f"Hace {dias} día{'s' if dias != 1 else ''}"
        elif dias < 30:
            semanas = dias // 7
            ultimo_acceso = f"Hace {semanas} semana{'s' if semanas != 1 else ''}"
        elif dias < 365:
            meses = dias // 30
            ultimo_acceso = f"Hace {meses} mes{'es' if meses != 1 else ''}"
        else:
            años = dias // 365
            ultimo_acceso = f"Hace {años} año{'s' if años != 1 else ''}"

    # Actualización de datos del perfil
    if request.method == 'POST':
        usuario.nom_usu = request.POST.get('nombre1')
        usuario.ape_usu = request.POST.get('nombre2')
        usuario.correo_per = request.POST.get('correo1')
        usuario.telefono = request.POST.get('celular')
        usuario.fecha_nacimiento = request.POST.get('fecha')
        usuario.genero = request.POST.get('genero')
        usuario.correo_ins = request.POST.get('correo2')
        usuario.vinculacion_laboral = request.POST.get('vinculacion')
        usuario.dependencia = request.POST.get('dependencia')
        usuario.rol = request.POST.get('rol')
        usuario.save()
        messages.success(request, "Cambios guardados correctamente.")
        return redirect('perfil')

    semilleros = usuario.semilleros.all()
    total_semilleros = semilleros.count()

    proyectos = usuario.proyectos.all()
    total_proyectos = proyectos.count()

    # Enviar datos al template
    context = {
        'usuario': usuario,
        'ultimo_acceso': ultimo_acceso,
        'semilleros': semilleros,
        'total_semilleros': total_semilleros,
        'proyectos': proyectos,
        'total_proyectos': total_proyectos,
    }

    return render(request, 'paginas/perfil.html', context)

# VISTA ACTUALIZAR FOTO PERFIL
def actualizar_foto(request):
    if request.method == 'POST':
        usuario_id = request.session.get('cedula')
        usuario = Usuario.objects.get(cedula=usuario_id)

        if 'imagen_perfil' in request.FILES:
            # Eliminar la imagen anterior (opcional pero recomendado)
            if usuario.imagen_perfil:
                usuario.imagen_perfil.delete(save=False)
            
            # Guardar la nueva
            usuario.imagen_perfil = request.FILES['imagen_perfil']
            usuario.save()
            messages.success(request, "Imagen actualizada correctamente.")
        else:
            messages.error(request, "No se seleccionó ninguna imagen.")
        
        return redirect('perfil')  # o a la vista donde se muestra el perfil

# VISTAS SEMILLEROS
def semilleros(request):
    usuario_id = request.session.get('cedula')
    if not usuario_id:
        messages.error(request, "Debes iniciar sesión para ver tu perfil.")
        return redirect('iniciarsesion')

    try:
        usuario = Usuario.objects.get(cedula=usuario_id)
    except Usuario.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect('iniciarsesion')
    
    semilleros = Semillero.objects.all()
    
    for semillero in semilleros:
        # Calcular y actualizar progreso
        actualizar_progreso_semillero(semillero)
        
        # Resto del código existente...
        cedulas = SemilleroUsuario.objects.filter(
            id_sem=semillero
        ).values_list('cedula', flat=True)
        
        total_usuarios = Usuario.objects.filter(cedula__in=cedulas).count()
        total_aprendices = Aprendiz.objects.filter(id_sem=semillero).count()
        semillero.total_miembros = total_usuarios + total_aprendices

        proyectos = SemilleroProyecto.objects.filter(id_sem=semillero)
        total_proyectos = proyectos.count()
        semillero.total_proyectos = total_proyectos

        total_entregables = Entregable.objects.filter(
            cod_pro__in=proyectos.values('cod_pro')
        ).count()
        semillero.total_entregables = total_entregables
        
    return render(request, 'paginas/semilleros.html', {
        'semilleros': semilleros,
        'usuario': usuario
    })

def crear_semillero(request):
    if request.method == 'POST':
        # Obtener los datos del formulario
        cod_sem = request.POST.get('cod_sem')  
        sigla = request.POST.get('sigla')
        nombre = request.POST.get('nombre')
        desc_sem = request.POST.get('desc_sem')
        objetivo = request.POST.getlist('objetivo')  # varios textareas

        # Combinar los objetivos en una sola cadena (separados por saltos de línea)
        objetivo_texto = "\n".join(objetivo)

        # Validar campos requeridos
        if not all([cod_sem, sigla, nombre, desc_sem, objetivo_texto]):
            messages.error(request, 'Todos los campos son obligatorios')
            return redirect('semilleros')

        try:
            semillero = Semillero(
                cod_sem=cod_sem,
                sigla=sigla,
                nombre=nombre,
                desc_sem=desc_sem,
                objetivo=objetivo_texto,
                estado='Activo',
                progreso_sem=0
            )
            semillero.save()
            messages.success(request, f'Semillero "{sigla}" creado exitosamente')
            return redirect('semilleros')

        except Exception as e:
            messages.error(request, f'Error al crear semillero: {str(e)}')
            return redirect('semilleros')

    return redirect('semilleros')

def eliminar_semilleros(request):
    if request.method == 'POST':
        semilleros_ids = request.POST.getlist('semilleros_eliminar')
        
        if not semilleros_ids:
            messages.warning(request, 'No se seleccionó ningún semillero para eliminar')
            return redirect('semilleros')
        
        try:
            eliminados = 0
            errores = []
            
            for id_sem in semilleros_ids:
                try:
                    semillero = Semillero.objects.get(id_sem=id_sem)
                    
                    # 1. Restaurar roles de líderes de semillero
                    lideres_sem = SemilleroUsuario.objects.filter(
                        id_sem=semillero, 
                        es_lider=True
                    ).select_related('cedula')
                    
                    for relacion_lider in lideres_sem:
                        usuario_lider = relacion_lider.cedula
                        if usuario_lider.rol == 'Líder de Semillero':
                            # Verificar si es líder en otros semilleros
                            otros_semilleros_lider = SemilleroUsuario.objects.filter(
                                cedula=usuario_lider, 
                                es_lider=True
                            ).exclude(id_sem=semillero).exists()
                            
                            if not otros_semilleros_lider:
                                # Restaurar rol original
                                if hasattr(usuario_lider, 'rol_original') and usuario_lider.rol_original:
                                    usuario_lider.rol = usuario_lider.rol_original
                                elif usuario_lider.vinculacion_laboral and 'instructor' in usuario_lider.vinculacion_laboral.lower():
                                    usuario_lider.rol = 'Instructor'
                                else:
                                    usuario_lider.rol = 'Investigador'
                                usuario_lider.save()
                    
                    # 2. Obtener todos los proyectos del semillero
                    proyectos = Proyecto.objects.filter(
                        semilleroproyecto__id_sem=semillero
                    )
                    
                    for proyecto in proyectos:
                        # Restaurar roles de líderes de proyecto
                        lideres_proyecto = UsuarioProyecto.objects.filter(
                            cod_pro=proyecto, 
                            es_lider_pro=True
                        ).select_related('cedula')
                        
                        for relacion_lider in lideres_proyecto:
                            usuario_lider = relacion_lider.cedula
                            if usuario_lider.rol == 'Líder de Proyecto':
                                # Verificar si es líder en otros proyectos
                                otros_proyectos_lider = UsuarioProyecto.objects.filter(
                                    cedula=usuario_lider, 
                                    es_lider_pro=True
                                ).exclude(cod_pro=proyecto).exists()
                                
                                if not otros_proyectos_lider:
                                    # Restaurar rol
                                    if hasattr(usuario_lider, 'rol_original') and usuario_lider.rol_original:
                                        usuario_lider.rol = usuario_lider.rol_original
                                    else:
                                        es_lider_sem = SemilleroUsuario.objects.filter(
                                            cedula=usuario_lider, 
                                            es_lider=True
                                        ).exists()
                                        if es_lider_sem:
                                            usuario_lider.rol = 'Líder de Semillero'
                                        elif usuario_lider.vinculacion_laboral and 'instructor' in usuario_lider.vinculacion_laboral.lower():
                                            usuario_lider.rol = 'Instructor'
                                        else:
                                            usuario_lider.rol = 'Investigador'
                                    usuario_lider.save()
                        
                        # Eliminar entregables y archivos
                        entregables = Entregable.objects.filter(cod_pro=proyecto)
                        for entregable in entregables:
                            archivos = Archivo.objects.filter(entregable=entregable)
                            for archivo in archivos:
                                if archivo.archivo:
                                    archivo.archivo.delete(save=False)
                            archivos.delete()
                        entregables.delete()
                        
                        # Eliminar relaciones con usuarios y aprendices
                        UsuarioProyecto.objects.filter(cod_pro=proyecto).delete()
                        ProyectoAprendiz.objects.filter(cod_pro=proyecto).delete()
                        
                        # Eliminar relación proyecto-semillero
                        SemilleroProyecto.objects.filter(cod_pro=proyecto).delete()
                        
                        # Eliminar el proyecto
                        proyecto.delete()
                    
                    # 3. Eliminar documentos del semillero
                    documentos_semillero = SemilleroDocumento.objects.filter(id_sem=semillero)
                    for rel_doc in documentos_semillero:
                        documento = rel_doc.cod_doc
                        if documento.archivo:
                            documento.archivo.delete(save=False)
                        documento.delete()
                    documentos_semillero.delete()
                    
                    # 4. Eliminar relaciones con usuarios
                    SemilleroUsuario.objects.filter(id_sem=semillero).delete()
                    
                    # 5. Actualizar aprendices (quitar referencia al semillero)
                    Aprendiz.objects.filter(id_sem=semillero).delete()
                    
                    # 6. Eliminar el semillero
                    semillero.delete()
                    
                    eliminados += 1
                    
                except Semillero.DoesNotExist:
                    errores.append(f'Semillero con ID {id_sem} no encontrado')
                except Exception as e:
                    errores.append(f'Error al eliminar semillero {id_sem}: {str(e)}')
            
            # Mostrar mensajes
            if eliminados > 0:
                messages.success(
                    request, 
                    f'✅ {eliminados} semillero(s) eliminado(s) correctamente y roles restaurados.'
                )
            
            if errores:
                for error in errores:
                    messages.error(request, f'⚠️ {error}')
            
            return redirect('semilleros')
            
        except Exception as e:
            messages.error(request, f'⚠️ Error general al eliminar semilleros: {str(e)}')
            return redirect('semilleros')
    
    # Si no es POST, redirigir
    return redirect('semilleros')

def actualizar_progreso_semillero(semillero):
    # Obtener todos los proyectos del semillero
    proyectos = Proyecto.objects.filter(semilleroproyecto__id_sem=semillero)
    total_proyectos = proyectos.count()
    
    if total_proyectos == 0:
        semillero.progreso_sem = 0
    else:
        # Calcular promedio de progreso
        promedio = proyectos.aggregate(Avg('progreso'))['progreso__avg']
        semillero.progreso_sem = round(promedio) if promedio else 0
    
    semillero.save(update_fields=['progreso_sem'])
    return semillero.progreso_sem

def resumen(request, id_sem):
    usuario_id = request.session.get('cedula')
    if not usuario_id:
        messages.error(request, "Debes iniciar sesión para ver tu perfil.")
        return redirect('iniciarsesion')

    try:
        usuario = Usuario.objects.get(cedula=usuario_id)
    except Usuario.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect('iniciarsesion')
    
    semillero = get_object_or_404(Semillero, id_sem=id_sem)
    
    # Convertir los objetivos a lista
    objetivos_lista = []
    if semillero.objetivo:  
        objetivos_lista = semillero.objetivo.split('\n')
        objetivos_lista = [obj.strip() for obj in objetivos_lista if obj.strip()]
    
    # Calcular total de miembros
    cedulas = SemilleroUsuario.objects.filter(
        id_sem=semillero
    ).values_list('cedula', flat=True)
    
    total_usuarios = Usuario.objects.filter(cedula__in=cedulas).count()
    total_aprendices = Aprendiz.objects.filter(id_sem=semillero).count()
    total_miembros = total_usuarios + total_aprendices

    # Proyectos del semillero
    proyectos = SemilleroProyecto.objects.filter(id_sem=semillero)
    total_proyectos = proyectos.count()

    # Entregables asociados a esos proyectos
    total_entregables = Entregable.objects.filter(
        cod_pro__in=proyectos.values('cod_pro')
    ).count()

    semillero = get_object_or_404(Semillero, id_sem=id_sem)
    
    # Actualizar progreso del semillero
    actualizar_progreso_semillero(semillero)

    return render(request, 'paginas/resumen.html', {
        'current_page': 'resumen',
        'current_page_name': 'Semilleros',
        'semillero': semillero,
        'objetivos_lista': objetivos_lista,
        'total_miembros': total_miembros,
        'total_proyectos': total_proyectos,
        'total_entregables': total_entregables,
        'usuario' : usuario
    })

def resu_miembros(request, id_sem):
    usuario_id = request.session.get('cedula')
    if not usuario_id:
        messages.error(request, "Debes iniciar sesión para ver tu perfil.")
        return redirect('iniciarsesion')

    try:
        usuario = Usuario.objects.get(cedula=usuario_id)
    except Usuario.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect('iniciarsesion') 
    
    semillero = get_object_or_404(Semillero, id_sem=id_sem)

    cedulas_en_semillero = SemilleroUsuario.objects.filter(
        id_sem=semillero
    ).values_list('cedula', flat=True)
    
    # Instructores
    usuarios = Usuario.objects.filter(cedula__in=cedulas_en_semillero)
    usuarios_disponibles = Usuario.objects.exclude(cedula__in=cedulas_en_semillero)
    
    # Aprendices
    aprendices = Aprendiz.objects.filter(id_sem=semillero)

    total_miembros = usuarios.count() + aprendices.count()

    # Ordenar miembros: primero el líder de semillero, luego líderes de proyecto, luego los demás
    miembros = SemilleroUsuario.objects.filter(
        id_sem=semillero
    ).select_related('cedula').order_by('-es_lider', 'cedula__nom_usu')

    # Obtener proyectos del semillero
    proyectos = Proyecto.objects.filter(semilleroproyecto__id_sem=semillero)
    codigos_proyectos = proyectos.values_list('cod_pro', flat=True)

    # CRÍTICO: Agregar verificación de liderazgo de proyecto a TODOS los miembros
    for miembro in miembros:
        # Verificar si este usuario es líder de algún proyecto del semillero
        miembro.es_lider_proyecto = UsuarioProyecto.objects.filter(
            cedula=miembro.cedula,
            cod_pro__in=codigos_proyectos,
            es_lider_pro=True
        ).exists()
        
        # Obtener nombres de los proyectos que lidera (para mostrar tooltip)
        if miembro.es_lider_proyecto:
            proyectos_liderados = UsuarioProyecto.objects.filter(
                cedula=miembro.cedula,
                cod_pro__in=codigos_proyectos,
                es_lider_pro=True
            ).select_related('cod_pro').values_list('cod_pro__nom_pro', flat=True)
            miembro.proyectos_liderados = list(proyectos_liderados)

    # 🎯 NUEVO: Crear lista de instructores filtrada Y con la misma lógica de liderazgo
    instructores = SemilleroUsuario.objects.filter(
        id_sem=semillero
    ).filter(
        Q(cedula__rol__icontains='instructor') |
        Q(cedula__rol__icontains='investigador') |
        Q(cedula__rol__icontains='líder') |
        Q(cedula__rol__icontains='lider')
    ).select_related('cedula').order_by('-es_lider', 'cedula__nom_usu')

    # CRÍTICO: Agregar la misma verificación a la lista de instructores
    for instructor in instructores:
        instructor.es_lider_proyecto = UsuarioProyecto.objects.filter(
            cedula=instructor.cedula,
            cod_pro__in=codigos_proyectos,
            es_lider_pro=True
        ).exists()
        
        if instructor.es_lider_proyecto:
            proyectos_liderados = UsuarioProyecto.objects.filter(
                cedula=instructor.cedula,
                cod_pro__in=codigos_proyectos,
                es_lider_pro=True
            ).select_related('cod_pro').values_list('cod_pro__nom_pro', flat=True)
            instructor.proyectos_liderados = list(proyectos_liderados)

    # Verificar si hay instructores
    tiene_instructores = any(
        m.cedula.rol.lower() in ['instructor', 'investigador', 'líder', 'lider'] 
        for m in miembros
    )

    total_proyectos = proyectos.count()

    # Entregables asociados a esos proyectos
    total_entregables = Entregable.objects.filter(
        cod_pro__in=proyectos.values('cod_pro')
    ).count()

    context = {
        'current_page': 'resu_miembros',
        'current_page_name': 'Semilleros',
        'semillero': semillero,
        'usuarios': usuarios,
        'aprendices': aprendices,
        'miembros': miembros, 
        'Usuarios': usuarios_disponibles,
        'total_miembros': total_miembros,
        'proyectos': proyectos,
        'tiene_instructores': tiene_instructores,
        'total_proyectos': total_proyectos,
        'total_entregables': total_entregables,
        'instructores': instructores, 
        'usuario' : usuario,
    }

    return render(request, 'paginas/resu-miembros.html', context)

def agregar_miembros(request, id_sem):
    if request.method == 'POST':
        semillero = get_object_or_404(Semillero, id_sem=id_sem)
        miembros_seleccionados = request.POST.getlist('miembros_seleccionados')
        
        if not miembros_seleccionados:
            messages.warning(request, 'No se seleccionó ningún miembro')
            return redirect('resu-miembros', id_sem=id_sem)
        
        try:
            agregados = 0
            ya_existentes = 0
            
            for cedula in miembros_seleccionados:
                usuario = get_object_or_404(Usuario, cedula=cedula)
                
                existe = SemilleroUsuario.objects.filter(
                    id_sem=semillero, 
                    cedula=usuario
                ).exists()
                
                if not existe:
                    SemilleroUsuario.objects.create(
                        id_sem=semillero, 
                        cedula=usuario
                    )
                    agregados += 1
                else:
                    ya_existentes += 1
            
            if agregados > 0:
                messages.success(request, f'{agregados} miembro(s) agregado(s) exitosamente')
            if ya_existentes > 0:
                messages.info(request, f'{ya_existentes} miembro(s) ya estaban en el semillero')
            
            return redirect('resu-miembros', id_sem=id_sem)
            
        except Exception as e:
            messages.error(request, f'Error al agregar miembros: {str(e)}')
            return redirect('resu-miembros', id_sem=id_sem)
    
    return redirect('resu-miembros', id_sem=id_sem)
    
def asignar_lider_semillero(request, id_sem):
    if request.method == "POST":
        semillero = get_object_or_404(Semillero, id_sem=id_sem)
        id_relacion = request.POST.get("lider_semillero")

        # Verificar existencia segura
        try:
            nueva_relacion_lider = SemilleroUsuario.objects.get(semusu_id=id_relacion, id_sem=semillero)
        except SemilleroUsuario.DoesNotExist:
            messages.error(request, "El usuario seleccionado no pertenece a este semillero.")
            return redirect("resu-miembros", semillero.id_sem)

        # Paso 1: Obtener el líder anterior (si existe)
        try:
            relacion_lider_anterior = SemilleroUsuario.objects.get(id_sem=semillero, es_lider=True)
            usuario_anterior = relacion_lider_anterior.cedula
            
            # Cambiar rol del antiguo líder a "Miembro" o "Instructor"
            if usuario_anterior.rol == 'Líder de Semillero':
                usuario_anterior.rol = 'Instructor'  # o 'Miembro', según tu necesidad
                usuario_anterior.save()
            
            # Quitar liderazgo en la tabla intermedia
            relacion_lider_anterior.es_lider = False
            relacion_lider_anterior.save()
            
        except SemilleroUsuario.DoesNotExist:
            # No había líder anterior, continuar normalmente
            pass

        # Paso 2: Asignar nuevo líder en la tabla intermedia
        nueva_relacion_lider.es_lider = True
        nueva_relacion_lider.save()

        # Paso 3: Cambiar el rol del nuevo líder en la tabla Usuario
        nuevo_usuario_lider = nueva_relacion_lider.cedula
        nuevo_usuario_lider.rol = 'Líder de Semillero'
        nuevo_usuario_lider.save()

        messages.success(
            request, 
            f"{nuevo_usuario_lider.nom_usu} {nuevo_usuario_lider.ape_usu} ha sido asignado como líder del semillero."
        )
        return redirect("resu-miembros", semillero.id_sem)
    
    semillero = get_object_or_404(Semillero, id_sem=id_sem)
    
    if request.method == "POST":
        cedula_instructor = request.POST.get("instructor_seleccionado")
        cod_proyecto = request.POST.get("proyecto_seleccionado")

        # Validar que se seleccionaron ambos
        if not cedula_instructor or not cod_proyecto:
            messages.error(request, "Debes seleccionar un instructor y un proyecto.")
            return redirect("resu-miembros", id_sem=id_sem)

        try:
            # Obtener el instructor y el proyecto
            instructor = Usuario.objects.get(cedula=cedula_instructor)
            proyecto = Proyecto.objects.get(cod_pro=cod_proyecto)

            # Verificar que el proyecto pertenece al semillero
            if not SemilleroProyecto.objects.filter(id_sem=semillero, cod_pro=proyecto).exists():
                messages.error(request, "El proyecto seleccionado no pertenece a este semillero.")
                return redirect("resu-miembros", id_sem=id_sem)

            # Verificar que el instructor pertenece al semillero
            if not SemilleroUsuario.objects.filter(id_sem=semillero, cedula=instructor).exists():
                messages.error(request, "El instructor seleccionado no pertenece a este semillero.")
                return redirect("resu-miembros", id_sem=id_sem)

            # Paso 1: Obtener y actualizar el líder anterior del proyecto
            try:
                relacion_anterior = UsuarioProyecto.objects.get(cod_pro=proyecto, es_lider=True)
                usuario_anterior = relacion_anterior.cedula
                
                # Cambiar rol si era "Líder de Proyecto"
                if usuario_anterior.rol == 'Líder de Proyecto':
                    usuario_anterior.rol = 'Instructor'  
                    usuario_anterior.save()
                
                # Quitar liderazgo
                relacion_anterior.es_lider_pro = False
                relacion_anterior.save()
                
            except UsuarioProyecto.DoesNotExist:
                # No había líder anterior
                pass

            # Paso 2: Buscar si ya existe la relación usuario-proyecto
            try:
                relacion = UsuarioProyecto.objects.get(
                    cedula=instructor,
                    cod_pro=proyecto
                )
                # Si existe, actualizar el liderazgo
                relacion.es_lider_pro = True
                relacion.save()
                creada = False
            except UsuarioProyecto.DoesNotExist:
                # Si no existe, crear nueva relación
                relacion = UsuarioProyecto.objects.create(
                    cedula=instructor,
                    cod_pro=proyecto,
                    es_lider=True
                )
                creada = True

            # Paso 3: Actualizar el rol del nuevo líder
            instructor.rol = 'Líder de Proyecto'  
            instructor.save()

            mensaje = "asignado" if creada else "actualizado como"
            messages.success(
                request, 
                f"{instructor.nom_usu} {instructor.ape_usu} ha sido {mensaje} líder del proyecto '{proyecto.nom_pro}'."
            )
            return redirect("resu-miembros", id_sem=id_sem)

        except Usuario.DoesNotExist:
            messages.error(request, "El instructor seleccionado no existe.")
            return redirect("resu-miembros", id_sem=id_sem)
        
        except Proyecto.DoesNotExist:
            messages.error(request, "El proyecto seleccionado no existe.")
            return redirect("resu-miembros", id_sem=id_sem)
        
        except Exception as e:
            messages.error(request, f"Error al asignar líder: {e}")
            return redirect("resu-miembros", id_sem=id_sem)

    # Si es GET, redirigir a resu-miembros (el modal se abre desde allí)
    return redirect("resu-miembros", id_sem=id_sem)

def resu_proyectos(request, id_sem, cod_pro=None):
    usuario_id = request.session.get('cedula')
    if not usuario_id:
        messages.error(request, "Debes iniciar sesión para ver tu perfil.")
        return redirect('iniciarsesion')

    try:
        usuario = Usuario.objects.get(cedula=usuario_id)
    except Usuario.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect('iniciarsesion') 
    
    semillero = get_object_or_404(Semillero, id_sem=id_sem)

    proyecto_editar = None
    mostrar_modal_editar = False
    mostrar_modal_gestionar = False
    lineas_tec_lista = []
    lineas_inv_lista = []
    lineas_sem_lista = []
    miembros_proyecto_actual = []

    mostrar_gestionar = request.GET.get('gestionar_equipo')

    # GUARDAR CAMBIOS DEL PROYECTO
    if request.method == 'POST' and cod_pro:
        proyecto_editar = get_object_or_404(Proyecto, cod_pro=cod_pro)

        try:
            proyecto_editar.nom_pro = request.POST.get('nom_pro', '').strip()
            proyecto_editar.tipo = request.POST.get('tipo', '').strip().lower()
            proyecto_editar.desc_pro = request.POST.get('desc_pro', '').strip()

            # LÍNEAS DESDE EL FORMULARIO
            lineas_tec = request.POST.getlist('lineastec[]')
            lineas_inv = request.POST.getlist('lineasinv[]')
            lineas_sem = request.POST.getlist('lineassem[]')

            # ACTUALIZAR SOLO SI EL FORMULARIO ENVÍA LÍNEAS
            if lineas_tec:
                proyecto_editar.linea_tec = "\n".join([l.strip() for l in lineas_tec if l.strip()])

            if lineas_inv:
                proyecto_editar.linea_inv = "\n".join([l.strip() for l in lineas_inv if l.strip()])

            if lineas_sem:
                proyecto_editar.linea_sem = "\n".join([l.strip() for l in lineas_sem if l.strip()])

            nueva_nota = request.POST.get('notas', '').strip()
            if nueva_nota:
                if proyecto_editar.notas:
                    proyecto_editar.notas += f"\n{nueva_nota}"
                else:
                    proyecto_editar.notas = nueva_nota

            proyecto_editar.save()

            miembros_seleccionados = request.POST.getlist('miembros_proyecto[]')

            for cedula in miembros_seleccionados:

                # Primero verificar si es usuario
                usuario = Usuario.objects.filter(cedula=cedula).first()
                if usuario:
                    ya_existe = UsuarioProyecto.objects.filter(
                        cedula=usuario, 
                        cod_pro=proyecto_editar
                    ).exists()
                    if not ya_existe:
                        UsuarioProyecto.objects.create(
                            cedula=usuario, 
                            cod_pro=proyecto_editar, 
                            estado="activo"
                        )
                    continue
                
                # Sino, intentar como aprendiz
                aprendiz = Aprendiz.objects.filter(cedula_apre=cedula).first()
                if aprendiz:
                    ya_existe = ProyectoAprendiz.objects.filter(
                        cedula_apre=aprendiz, 
                        cod_pro=proyecto_editar
                    ).exists()
                    if not ya_existe:
                        ProyectoAprendiz.objects.create(
                            cedula_apre=aprendiz, 
                            cod_pro=proyecto_editar, 
                            estado="activo"
                        )

            messages.success(request, f'Proyecto "{proyecto_editar.nom_pro}" actualizado correctamente.')
            return redirect('resu-proyectos', id_sem=id_sem)

        except Exception as e:
            messages.error(request, f'Error al actualizar proyecto: {str(e)}')
            return redirect('resu-proyectos', id_sem=id_sem, cod_pro=cod_pro)

    # MODAL GESTIONAR EQUIPO
    if mostrar_gestionar and cod_pro and request.method == 'GET':
        proyecto_editar = get_object_or_404(Proyecto, cod_pro=cod_pro)
        mostrar_modal_gestionar = True

        usuarios_proyecto = UsuarioProyecto.objects.filter(cod_pro=proyecto_editar).select_related('cedula')
        aprendices_proyecto = ProyectoAprendiz.objects.filter(cod_pro=proyecto_editar).select_related('cedula_apre')

        miembros_equipo = []

        for up in usuarios_proyecto:
            # Traer si este usuario es líder de semillero
            su = SemilleroUsuario.objects.filter(cedula=up.cedula, id_sem=semillero).first()
            es_lider_sem = su.es_lider if su else False

            miembros_equipo.append({
                'cedula': up.cedula.cedula,
                'nombre_completo': f"{up.cedula.nom_usu} {up.cedula.ape_usu}",
                'nom_usu': up.cedula.nom_usu,
                'ape_usu': up.cedula.ape_usu,
                'email': up.cedula.correo_ins if up.cedula.correo_ins else up.cedula.correo_per,
                'iniciales': up.cedula.get_iniciales,
                'tipo': 'Usuario',
                'rol': up.cedula.rol,
                'estado': up.estado,
                'es_lider': up.es_lider_pro,
                'es_lider_sem': es_lider_sem
            })

        for ap in aprendices_proyecto:
            miembros_equipo.append({
                'cedula': ap.cedula_apre.cedula_apre,
                'nombre_completo': f"{ap.cedula_apre.nombre} {ap.cedula_apre.apellido}",
                'nom_usu': ap.cedula_apre.nombre,
                'ape_usu': ap.cedula_apre.apellido,
                'email': ap.cedula_apre.correo_ins if hasattr(ap.cedula_apre, 'correo_ins') and ap.cedula_apre.correo_ins else (ap.cedula_apre.correo_per if hasattr(ap.cedula_apre, 'correo_per') else ''),
                'iniciales': ap.cedula_apre.get_iniciales,
                'tipo': 'Aprendiz',
                'rol': 'Aprendiz',
                'estado': ap.estado,
                'es_lider': False,
            })

        # FILTROS
        busqueda = request.GET.get('busqueda_usuario', '').strip().lower()
        filtro_rol = request.GET.get('filtro_rol', '').strip().lower()
        filtro_estado = request.GET.get('filtro_estado', '').strip().lower()

        if busqueda:
            miembros_equipo = [
                m for m in miembros_equipo
                if busqueda in m['nombre_completo'].lower() or busqueda in m['email'].lower()
            ]

        if filtro_rol:
            if filtro_rol == 'es_lider':
                miembros_equipo = [m for m in miembros_equipo if m.get('es_lider', False)]
            else:
                miembros_equipo = [m for m in miembros_equipo if m['rol'].lower() == filtro_rol]

        if filtro_estado:
            miembros_equipo = [m for m in miembros_equipo if m['estado'].lower() == filtro_estado]

        miembros_proyecto_actual = miembros_equipo

    # MODAL EDITAR
    elif cod_pro and request.method == 'GET' and not mostrar_gestionar:
        proyecto_editar = get_object_or_404(Proyecto, cod_pro=cod_pro)
        mostrar_modal_editar = True

        lineas_tec_lista = []
        lineas_inv_lista = []
        lineas_sem_lista = []

        if proyecto_editar.linea_tec:
            lineas_tec_lista = [l.strip() for l in proyecto_editar.linea_tec.split('\n') if l.strip()]

        if proyecto_editar.linea_inv:
            lineas_inv_lista = [l.strip() for l in proyecto_editar.linea_inv.split('\n') if l.strip()]

        if proyecto_editar.linea_sem:
            lineas_sem_lista = [l.strip() for l in proyecto_editar.linea_sem.split('\n') if l.strip()]

        usuarios_proyecto = UsuarioProyecto.objects.filter(cod_pro=proyecto_editar).select_related('cedula')
        aprendices_proyecto = ProyectoAprendiz.objects.filter(cod_pro=proyecto_editar).select_related('cedula_apre')

        for up in usuarios_proyecto:
            miembros_proyecto_actual.append({
                'cedula': up.cedula.cedula,
                'nombre_completo': f"{up.cedula.nom_usu} {up.cedula.ape_usu}",
                'iniciales': up.cedula.get_iniciales,
                'tipo': 'Usuario',
                'rol': up.cedula.rol,
                'estado': up.estado
            })

        for ap in aprendices_proyecto:
            miembros_proyecto_actual.append({
                'cedula': ap.cedula_apre.cedula_apre,
                'nombre_completo': f"{ap.cedula_apre.nombre} {ap.cedula_apre.apellido}",
                'iniciales': ap.cedula_apre.get_iniciales,
                'tipo': 'Aprendiz',
                'rol': 'Aprendiz',
                'estado': ap.estado
            })

    proyectos = Proyecto.objects.filter(semilleroproyecto__id_sem=semillero)

    for proyecto in proyectos:
        verificar_y_actualizar_estados_entregables(proyecto)

    tipo_seleccionado = None
    if cod_pro:
        proyectos = proyectos.order_by(
            Case(
                When(cod_pro=cod_pro, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )

        proyecto_sel = proyectos.filter(cod_pro=cod_pro).first()
        if proyecto_sel:
            tipo_seleccionado = proyecto_sel.tipo.lower()

    proyectos_sennova = list(proyectos.filter(tipo__iexact="sennova"))
    proyectos_capacidad = list(proyectos.filter(tipo__iexact="capacidadinstalada"))
    proyectos_formativos = list(proyectos.filter(tipo__iexact="formativo"))

    for proyecto in proyectos_sennova + proyectos_capacidad + proyectos_formativos:
        usuarios_proyecto = UsuarioProyecto.objects.filter(cod_pro=proyecto).select_related('cedula')
        aprendices_proyecto = ProyectoAprendiz.objects.filter(cod_pro=proyecto).select_related('cedula_apre')

        proyecto.lineas_tec_lista = [l.strip() for l in proyecto.linea_tec.split('\n') if l.strip()] if proyecto.linea_tec else []
        proyecto.lineas_inv_lista = [l.strip() for l in proyecto.linea_inv.split('\n') if l.strip()] if proyecto.linea_inv else []
        proyecto.lineas_sem_lista = [l.strip() for l in proyecto.linea_sem.split('\n') if l.strip()] if proyecto.linea_sem else []
        
        miembros_lista = []

        for up in usuarios_proyecto:
            miembros_lista.append({
                'cedula': up.cedula.cedula,
                'nombre_completo': f"{up.cedula.nom_usu} {up.cedula.ape_usu}",
                'iniciales': up.cedula.get_iniciales,
                'tipo': 'Usuario',
                'rol': up.cedula.rol,
                'estado': up.estado
            })

        for ap in aprendices_proyecto:
            miembros_lista.append({
                'cedula': ap.cedula_apre.cedula_apre,
                'nombre_completo': f"{ap.cedula_apre.nombre} {ap.cedula_apre.apellido}",
                'iniciales': ap.cedula_apre.get_iniciales,
                'tipo': 'Aprendiz',
                'rol': 'Aprendiz',
                'estado': ap.estado
            })

        proyecto.miembros_lista = miembros_lista
        proyecto.miembros_activos = [m for m in miembros_lista if m['estado'] == 'activo']
        
        proyecto.lineas_tec_lista = [l.strip() for l in proyecto.linea_tec.split('\n') if l.strip()] if proyecto.linea_tec else []
        proyecto.lineas_inv_lista = [l.strip() for l in proyecto.linea_inv.split('\n') if l.strip()] if proyecto.linea_inv else []
        proyecto.lineas_sem_lista = [l.strip() for l in proyecto.linea_sem.split('\n') if l.strip()] if proyecto.linea_sem else []

    proyectos_count = SemilleroProyecto.objects.filter(id_sem=semillero)
    total_proyectos = proyectos_count.count()

    usuarios = SemilleroUsuario.objects.filter(id_sem=semillero)
    aprendices = Aprendiz.objects.filter(id_sem=semillero)
    total_miembros = usuarios.count() + aprendices.count()
    miembros = usuarios.select_related('cedula')

    total_entregables = Entregable.objects.filter(
        cod_pro__in=proyectos_count.values('cod_pro')
    ).count()

    proyectos_semillero = proyectos_count.values_list('cod_pro', flat=True)
    usuarios_asignados = UsuarioProyecto.objects.filter(
        cod_pro__in=proyectos_semillero
    ).values_list('cedula__cedula', flat=True)
    aprendices_asignados = ProyectoAprendiz.objects.filter(
        cod_pro__in=proyectos_semillero
    ).values_list('cedula_apre__cedula_apre', flat=True)

    cedulas_asignadas = set(str(c) for c in usuarios_asignados) | set(str(c) for c in aprendices_asignados)

    usuarios_semillero = SemilleroUsuario.objects.filter(id_sem=semillero).select_related('cedula')
    usuarios_disponibles = [u for u in usuarios_semillero if str(u.cedula.cedula) not in cedulas_asignadas]

    aprendices_semillero = Aprendiz.objects.filter(id_sem=semillero)
    aprendices_disponibles = [a for a in aprendices_semillero if str(a.cedula_apre) not in cedulas_asignadas]

    miembros_semillero = []
    for u in usuarios_disponibles:
        miembros_semillero.append({
            'cedula': u.cedula.cedula,
            'nombre_completo': f"{u.cedula.nom_usu} {u.cedula.ape_usu}",
            'iniciales': u.cedula.get_iniciales,
            'tipo': 'Usuario',
            'rol': u.cedula.rol
        })

    for a in aprendices_disponibles:
        miembros_semillero.append({
            'cedula': a.cedula_apre,
            'nombre_completo': f"{a.nombre} {a.apellido}",
            'iniciales': a.get_iniciales,
            'tipo': 'Aprendiz',
            'rol': 'Aprendiz'
        })

    context = {
        'current_page': 'resu_proyectos',
        'current_page_name': 'Semilleros',
        'semillero': semillero,
        'proyectos_sennova': proyectos_sennova,
        'proyectos_capacidad': proyectos_capacidad,
        'proyectos_formativos': proyectos_formativos,
        'total_proyectos': total_proyectos,
        'total_miembros': total_miembros,
        'miembros': miembros,
        'total_entregables': total_entregables,
        'miembros_semillero': miembros_semillero,
        'proyecto_seleccionado': cod_pro,
        'tipo_seleccionado': tipo_seleccionado,
        'miembros_proyecto_actual': miembros_proyecto_actual,
        'mostrar_modal_editar': mostrar_modal_editar,
        'mostrar_modal_gestionar': mostrar_modal_gestionar,
        'proyecto_editar': proyecto_editar,
        'lineas_tec_lista': lineas_tec_lista,
        'lineas_inv_lista': lineas_inv_lista,
        'lineas_sem_lista': lineas_sem_lista,
        'busqueda_usuario': request.GET.get('busqueda_usuario', ''),
        'filtro_rol': request.GET.get('filtro_rol', ''),
        'filtro_estado': request.GET.get('filtro_estado', ''),
        'usuario' : usuario
    }

    return render(request, 'paginas/resu-proyectos.html', context)

def asignar_lider_proyecto_ajax(request, id_sem, cod_pro):
    """
    Asigna o quita el rol de líder de proyecto mediante AJAX
    """
    semillero = get_object_or_404(Semillero, id_sem=id_sem)
    proyecto = get_object_or_404(Proyecto, cod_pro=cod_pro)
    cedula_miembro = request.POST.get('cedula_miembro')
    
    if not cedula_miembro:
        return JsonResponse({'success': False, 'error': 'No se especificó el miembro'})
    
    try:
        # Verificar que el proyecto pertenece al semillero
        if not SemilleroProyecto.objects.filter(id_sem=semillero, cod_pro=proyecto).exists():
            return JsonResponse({'success': False, 'error': 'El proyecto no pertenece a este semillero'})
        
        # Intentar obtener el miembro (solo usuarios pueden ser líderes)
        try:
            miembro = Usuario.objects.get(cedula=cedula_miembro)
        except Usuario.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Solo los usuarios pueden ser líderes de proyecto'})
        
        # Verificar que el usuario pertenece al semillero
        if not SemilleroUsuario.objects.filter(id_sem=semillero, cedula=miembro).exists():
            return JsonResponse({'success': False, 'error': 'El usuario no pertenece a este semillero'})
        
        # Verificar si el usuario ya está en el proyecto
        try:
            relacion_actual = UsuarioProyecto.objects.get(cedula=miembro, cod_pro=proyecto)
            es_lider_actual = relacion_actual.es_lider_pro
        except UsuarioProyecto.DoesNotExist:
            # Si no existe la relación, crearla
            relacion_actual = UsuarioProyecto.objects.create(
                cedula=miembro,
                cod_pro=proyecto,
                es_lider_pro=False,
                estado='activo'
            )
            es_lider_actual = False
        
        # Si ya es líder, informar
        if es_lider_actual:
            return JsonResponse({
                'success': True,
                'es_lider_pro': True,
                'mensaje': f'{miembro.nom_usu} {miembro.ape_usu} ya es líder de este proyecto'
            })
        
        # Quitar liderazgo al líder anterior y restaurar su rol
        try:
            relacion_anterior = UsuarioProyecto.objects.get(cod_pro=proyecto, es_lider_pro=True)
            usuario_anterior = relacion_anterior.cedula
            
            # Guardar el rol original ANTES de cambiar a líder (si no está guardado)
            if not hasattr(usuario_anterior, 'rol_original') or not usuario_anterior.rol_original:
                # Si no existe el campo, buscar el rol en el perfil base
                rol_original = usuario_anterior.rol
                if rol_original == 'Líder de Proyecto':
                    # Si ya era líder, buscar en otros proyectos o usar Instructor/Investigador
                    rol_original = 'Instructor'  # valor temporal
            
            # Verificar si el rol actual es "Líder de Proyecto" antes de cambiarlo
            if usuario_anterior.rol == 'Líder de Proyecto':
                # Buscar otros proyectos donde también sea líder
                otros_proyectos_lider = UsuarioProyecto.objects.filter(
                    cedula=usuario_anterior,
                    es_lider_pro=True
                ).exclude(cod_pro=proyecto).exists()
                
                # Solo cambiar rol si NO es líder en otros proyectos
                if not otros_proyectos_lider:
                    # Buscar el rol original guardado o determinarlo
                    if hasattr(usuario_anterior, 'rol_original') and usuario_anterior.rol_original:
                        usuario_anterior.rol = usuario_anterior.rol_original
                    else:
                        # Determinar basado en el contexto del usuario
                        # Verificar si tiene vinculación laboral como instructor
                        if usuario_anterior.vinculacion_laboral and 'instructor' in usuario_anterior.vinculacion_laboral.lower():
                            usuario_anterior.rol = 'Instructor'
                        else:
                            usuario_anterior.rol = 'Investigador'
                    
                    usuario_anterior.save()
            
            # Quitar liderazgo del proyecto
            relacion_anterior.es_lider_pro = False
            relacion_anterior.save()
            
        except UsuarioProyecto.DoesNotExist:
            pass
        
        # Guardar el rol original del nuevo líder ANTES de cambiarlo
        if miembro.rol != 'Líder de Proyecto':
            if hasattr(miembro, 'rol_original'):
                miembro.rol_original = miembro.rol
        
        # Asignar nuevo líder
        relacion_actual.es_lider_pro = True
        relacion_actual.save()
        
        # Actualizar rol del nuevo líder
        if miembro.rol != 'Líder de Proyecto':
            miembro.rol = 'Líder de Proyecto'
            miembro.save()
        
        return JsonResponse({
            'success': True,
            'es_lider_pro': True,
            'mensaje': f'{miembro.nom_usu} {miembro.ape_usu} ha sido asignado como líder del proyecto'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def alternar_estado_miembro(request, id_sem, cod_pro):
    semillero = get_object_or_404(Semillero, id_sem=id_sem)
    proyecto = get_object_or_404(Proyecto, cod_pro=cod_pro)
    cedula_miembro = request.POST.get('cedula_miembro')

    if not cedula_miembro:
        return JsonResponse({'success': False, 'error': 'No se especificÃ³ el miembro'})

    try:
        # Verificar si es usuario o aprendiz
        try:
            relacion = UsuarioProyecto.objects.get(cedula__cedula=cedula_miembro, cod_pro=proyecto)
            
            # ðŸ‘‡ AGREGAR ESTA VALIDACIÃ“N
            # Verificar si es lÃ­der antes de cambiar a inactivo
            if relacion.estado == "activo" and relacion.es_lider_pro:
                return JsonResponse({
                    'success': False, 
                    'error': 'No se puede desactivar al lÃ­der del proyecto. Primero asigne otro lÃ­der.'
                })
            
        except UsuarioProyecto.DoesNotExist:
            relacion = ProyectoAprendiz.objects.get(cedula_apre__cedula_apre=cedula_miembro, cod_pro=proyecto)

        # Cambiar estado
        relacion.estado = "inactivo" if relacion.estado == "activo" else "activo"
        relacion.save()

        return JsonResponse({
            'success': True,
            'nuevo_estado': relacion.estado,
            'mensaje': f'Estado actualizado a {relacion.estado}'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
def crear_proyecto(request, id_sem):
    semillero = get_object_or_404(Semillero, id_sem=id_sem)

    # Obtener todos los proyectos del semillero
    proyectos_semillero = SemilleroProyecto.objects.filter(
        id_sem=semillero
    ).values_list('cod_pro', flat=True)

    # Obtener cédulas de usuarios asignados a esos proyectos
    usuarios_asignados = UsuarioProyecto.objects.filter(
        cod_pro__in=proyectos_semillero
    ).values_list('cedula__cedula', flat=True)

    # Obtener cédulas de aprendices asignados a esos proyectos
    aprendices_asignados = ProyectoAprendiz.objects.filter(
        cod_pro__in=proyectos_semillero
    ).values_list('cedula_apre__cedula_apre', flat=True)

    cedulas_asignadas = set(str(c) for c in usuarios_asignados) | set(str(c) for c in aprendices_asignados)

    # Filtrar usuarios del semillero que NO están asignados a ningún proyecto
    usuarios_semillero = SemilleroUsuario.objects.filter(id_sem=semillero).select_related('cedula')

    usuarios_disponibles = [u for u in usuarios_semillero if str(u.cedula.cedula) not in cedulas_asignadas]

    # Filtrar aprendices del semillero que NO están asignados a ningún proyecto
    aprendices_semillero = Aprendiz.objects.filter(id_sem=semillero)

    aprendices_disponibles = [a for a in aprendices_semillero if str(a.cedula_apre) not in cedulas_asignadas]

    # Combinar los miembros disponibles para pasar al template
    miembros_semillero = []

    for u in usuarios_disponibles:
        miembros_semillero.append({
            'cedula': u.cedula.cedula,
            'nombre_completo': f"{u.cedula.nom_usu} {u.cedula.ape_usu}",
            'iniciales': u.cedula.get_iniciales,
            'tipo': 'Usuario',
            'rol': u.cedula.rol
        })

    for a in aprendices_disponibles:
        miembros_semillero.append({
            'cedula': a.cedula_apre,
            'nombre_completo': f"{a.nombre} {a.apellido}",
            'iniciales': a.get_iniciales,
            'tipo': 'Aprendiz',
            'rol': 'Aprendiz'
        })

    # --- Crear proyecto ---
    if request.method == 'POST':
        try:
            cedula_usuario = request.session.get('cedula')
            if not cedula_usuario:
                messages.error(request, 'Debes iniciar sesión para crear un proyecto.')
                return redirect('iniciarsesion')

            usuario_actual = Usuario.objects.get(cedula=cedula_usuario)

            nom_pro = request.POST.get('nom_pro', '').strip()
            tipo = request.POST.get('tipo', '').strip().lower()
            programa_formacion = request.POST.get('programa_formacion', '').strip()

            desc_pro = request.POST.get('desc_pro', '').strip()
            lineas_tec = [l.strip() for l in request.POST.getlist('lineastec[]') if l.strip()]
            lineas_inv = [l.strip() for l in request.POST.getlist('lineasinv[]') if l.strip()]
            lineas_sem = [l.strip() for l in request.POST.getlist('lineassem[]') if l.strip()]
            miembros_seleccionados = request.POST.getlist('miembros_proyecto[]')

            if not all([nom_pro, tipo, desc_pro]):
                messages.error(request, 'Todos los campos son obligatorios.')
                return redirect('resu-proyectos', id_sem=id_sem)
            # Validación específica
            if tipo == "formativo" and not programa_formacion:
                messages.error(request, 'Debe ingresar el programa de formación para un proyecto formativo.')
                return redirect('resu-proyectos', id_sem=id_sem)


            # Crear proyecto
            ultimo_proyecto = Proyecto.objects.order_by('-cod_pro').first()
            nuevo_cod_pro = ultimo_proyecto.cod_pro + 1 if ultimo_proyecto else 1

            proyecto = Proyecto.objects.create(
                cod_pro=nuevo_cod_pro,
                nom_pro=nom_pro,
                tipo=tipo,
                desc_pro=desc_pro,
                linea_tec="\n".join(lineas_tec),
                linea_inv="\n".join(lineas_inv),
                linea_sem="\n".join(lineas_sem),
                estado_pro="Activo",
                programa_formacion=programa_formacion if tipo == "formativo" else None
            )


            # Asociar proyecto al semillero
            SemilleroProyecto.objects.create(id_sem=semillero, cod_pro=proyecto)

            # Asociar usuario creador
            UsuarioProyecto.objects.create(cedula=usuario_actual, cod_pro=proyecto)

            # Asociar miembros seleccionados
            for cedula in miembros_seleccionados:
                if str(cedula) != str(cedula_usuario):
                    try:
                        usuario = Usuario.objects.get(cedula=cedula)
                        UsuarioProyecto.objects.create(cedula=usuario, cod_pro=proyecto)
                    except Usuario.DoesNotExist:
                        try:
                            aprendiz = Aprendiz.objects.get(cedula_apre=cedula)
                            ProyectoAprendiz.objects.create(cedula_apre=aprendiz, cod_pro=proyecto)
                        except Aprendiz.DoesNotExist:
                            pass

            # Crear entregables por defecto con fechas
            entregables_default = [
                {"nombre": "Formalización de Proyecto", "descripcion": "Documento formal del proyecto."},
                {"nombre": "Diagnóstico", "descripcion": "Análisis de la situación actual."},
                {"nombre": "Planeación", "descripcion": "Cronograma y metodología del proyecto."},
                {"nombre": "Ejecución", "descripcion": "Evidencias y resultados del proyecto."},
                {"nombre": "Evaluación", "descripcion": "Cumplimiento e impacto del proyecto."},
                {"nombre": "Conclusiones", "descripcion": "Reflexiones finales y recomendaciones."},
            ]

            ultimo_entregable = Entregable.objects.order_by('-cod_entre').first()
            base_cod = ultimo_entregable.cod_entre if ultimo_entregable else 0

            for i, entregable_data in enumerate(entregables_default, start=1):
                #  Leer fecha_inicio y fecha_fin
                fecha_inicio_str = request.POST.get(f'fecha_inicio_{i}')
                fecha_fin_str = request.POST.get(f'fecha_fin_{i}')

                # Convertir formato de fecha
                fecha_inicio = None
                fecha_fin = None
                
                try:
                    if fecha_inicio_str:
                        fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
                    if fecha_fin_str:
                        fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
                except ValueError:
                    # Si el formato es distinto, intenta dd/mm/yyyy
                    try:
                        if fecha_inicio_str:
                            fecha_inicio = datetime.strptime(fecha_inicio_str, '%d/%m/%Y').date()
                        if fecha_fin_str:
                            fecha_fin = datetime.strptime(fecha_fin_str, '%d/%m/%Y').date()
                    except Exception as e:
                        print(f"Error al convertir fechas del entregable {i}: {e}")

                Entregable.objects.create(
                    cod_entre=base_cod + i,
                    nom_entre=entregable_data["nombre"],
                    desc_entre=entregable_data["descripcion"],
                    estado="Pendiente",
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,  
                    cod_pro=proyecto
                )

            messages.success(request, f'Proyecto "{nom_pro}" creado correctamente.')
            return redirect('resu-proyectos', id_sem=id_sem)

        except Exception as e:
            messages.error(request, f'Error al crear proyecto: {str(e)}')
            return redirect('resu-proyectos', id_sem=id_sem)

    # Renderizar formulario
    return render(request, 'crear_proyecto.html', {
        'semillero': semillero,
        'miembros_semillero': miembros_semillero
    })

def subir_archivo_entregable(request, id_sem, cod_pro, cod_entre):
    semillero = get_object_or_404(Semillero, id_sem=id_sem)
    entregable = get_object_or_404(Entregable, cod_pro=cod_pro, cod_entre=cod_entre)

    if request.method == 'POST':

        # PERMITIMOS VARIOS ARCHIVOS
        archivos = request.FILES.getlist('archivo')

        if not archivos:
            messages.error(request, '⚠️ Debes seleccionar uno o más archivos para subir.')
            return redirect('resu-proyectos', id_sem=id_sem)

        # Guardamos todos los archivos
        for archivo in archivos:
            Archivo.objects.create(
                entregable=entregable,
                archivo=archivo,
                nombre=archivo.name
            )

        fecha_actual = date.today()

        if entregable.fecha_fin:
            if fecha_actual > entregable.fecha_fin:
                entregable.estado = 'Entrega Tardía'
            else:
                entregable.estado = 'Completado'
        else:
            entregable.estado = 'Completado'

        entregable.save()

        # Actualizar progreso del proyecto
        actualizar_progreso_proyecto(entregable.cod_pro)

        # Mostrar mensaje con cantidad de archivos
        messages.success(
            request,
            f'✅ {len(archivos)} archivo(s) subido(s) correctamente al entregable "{entregable.nom_entre}".'
        )

        return redirect('resu-proyectos', id_sem=id_sem)

    messages.error(request, 'Método no permitido.')
    return redirect('resu-proyectos', id_sem=id_sem)

def actualizar_progreso_proyecto(proyecto):
    entregables = Entregable.objects.filter(cod_pro=proyecto)
    total_entregables = entregables.count()

    if total_entregables == 0:
        proyecto.progreso = 0
        proyecto.estado_pro = "diagnostico"
    else:
        # Contar entregables completados (incluye entregas tardías)
        entregables_completados = entregables.filter(
            estado__in=['Completado', 'Entrega Tardía']
        ).count()

        # Calcular porcentaje de progreso
        progreso = round((entregables_completados / total_entregables) * 100)
        proyecto.progreso = progreso

        # ===== ASIGNAR ESTADO SEGÚN ENTREGABLES COMPLETADOS =====
        if entregables_completados <= 2:
            proyecto.estado_pro = "diagnostico"
        elif entregables_completados == 3:
            proyecto.estado_pro = "planeacion"
        elif 4 <= entregables_completados <= 5:
            proyecto.estado_pro = "ejecucion"
        elif entregables_completados >= 6:
            proyecto.estado_pro = "completado"

    proyecto.save(update_fields=['progreso', 'estado_pro'])
    
    # Actualizar progreso del semillero asociado
    semilleros = Semillero.objects.filter(semilleroproyecto__cod_pro=proyecto)
    for semillero in semilleros:
        actualizar_progreso_semillero(semillero)

def verificar_y_actualizar_estados_entregables(proyecto):
    from datetime import date
    
    fecha_actual = date.today()
    entregables = Entregable.objects.filter(cod_pro=proyecto)
    
    for entregable in entregables:
        # Verificar si tiene archivos
        tiene_archivos = Archivo.objects.filter(entregable=entregable).exists()
        
        if tiene_archivos:
            # Si tiene archivos, verificar si fue entrega tardía
            if entregable.fecha_fin and fecha_actual > entregable.fecha_fin:
                if entregable.estado not in ['Completado', 'Entrega Tardía']:
                    entregable.estado = 'Entrega Tardía'
                    entregable.save()
            else:
                if entregable.estado != 'Completado':
                    entregable.estado = 'Completado'
                    entregable.save()
        else:
            # No tiene archivos
            if entregable.fecha_fin and fecha_actual > entregable.fecha_fin:
                # Pasó la fecha y no tiene archivos
                if entregable.estado != 'Retrasado':
                    entregable.estado = 'Retrasado'
                    entregable.save()
            else:
                # Aún está en fecha o no hay fecha_fin
                if entregable.estado not in ['Completado', 'Entrega Tardía']:
                    entregable.estado = 'Pendiente'
                    entregable.save()

def eliminar_entregable(request, id_sem, cod_pro, cod_entre):
    """
    Vista para eliminar un archivo de un entregable (opcional)
    """
    if request.method == 'POST':
        semillero = get_object_or_404(Semillero, id_sem=id_sem)
        proyecto = get_object_or_404(Proyecto, cod_pro=cod_pro)
        entregable = get_object_or_404(Entregable, cod_entre=cod_entre, cod_pro=proyecto)
        
        # Verificar que el proyecto pertenece al semillero
        if not SemilleroProyecto.objects.filter(id_sem=semillero, cod_pro=proyecto).exists():
            messages.error(request, 'El proyecto no pertenece a este semillero')
            return redirect('resu-proyectos', id_sem=id_sem, cod_pro=cod_pro)
        
        try:
            # Eliminar el archivo
            if entregable.archivo:
                entregable.archivo.delete(save=False)
                entregable.archivo = None
                entregable.estado = 'Pendiente'
                entregable.save()
                
                # Actualizar progreso del proyecto
                actualizar_progreso_proyecto(proyecto)
                
                messages.success(request, f'Archivo eliminado de "{entregable.nom_entre}"')
            else:
                messages.info(request, 'No hay archivo para eliminar')
            
            return redirect('resu-proyectos', id_sem=id_sem, cod_pro=cod_pro)
            
        except Exception as e:
            messages.error(request, f'Error al eliminar el archivo: {str(e)}')
            return redirect('resu-proyectos', id_sem=id_sem, cod_pro=cod_pro)
    return redirect('resu-proyectos', id_sem=id_sem)

def eliminar_proyecto_semillero(request, id_sem, cod_pro):
    try:
        semillero = get_object_or_404(Semillero, id_sem=id_sem)
        proyecto = get_object_or_404(Proyecto, cod_pro=cod_pro)

        # Restaurar roles de los líderes de proyecto
        lideres_proyecto = UsuarioProyecto.objects.filter(
            cod_pro=proyecto, es_lider_pro=True
        ).select_related('cedula')

        for relacion_lider in lideres_proyecto:
            usuario_lider = relacion_lider.cedula
            if usuario_lider.rol == 'Líder de Proyecto':
                otros_proyectos_lider = UsuarioProyecto.objects.filter(
                    cedula=usuario_lider, es_lider_pro=True
                ).exclude(cod_pro=proyecto).exists()

                if not otros_proyectos_lider:
                    if hasattr(usuario_lider, 'rol_original') and usuario_lider.rol_original:
                        usuario_lider.rol = usuario_lider.rol_original
                    else:
                        es_lider_semillero = SemilleroUsuario.objects.filter(
                            cedula=usuario_lider, es_lider=True
                        ).exists()
                        if es_lider_semillero:
                            usuario_lider.rol = 'Líder de Semillero'
                        elif usuario_lider.vinculacion_laboral and 'instructor' in usuario_lider.vinculacion_laboral.lower():
                            usuario_lider.rol = 'Instructor'
                        else:
                            usuario_lider.rol = 'Investigador'
                    usuario_lider.save()

        # Eliminar entregables y sus archivos asociados
        entregables = Entregable.objects.filter(cod_pro=proyecto)
        for entregable in entregables:
            archivos = Archivo.objects.filter(entregable=entregable)
            for archivo in archivos:
                archivo.archivo.delete(save=False)  # eliminar físicamente
            archivos.delete()
        entregables.delete()

        # Eliminar relaciones con usuarios y aprendices
        UsuarioProyecto.objects.filter(cod_pro=proyecto).delete()
        ProyectoAprendiz.objects.filter(cod_pro=proyecto).delete()

        # Eliminar relación con semillero
        SemilleroProyecto.objects.filter(id_sem=semillero, cod_pro=proyecto).delete()

        # Eliminar proyecto
        nombre_proyecto = proyecto.nom_pro
        proyecto.delete()

        messages.success(request, f'✅ Proyecto "{nombre_proyecto}" eliminado correctamente y roles restaurados.')

    except Exception as e:
        messages.error(request, f'⚠️ Error al eliminar el proyecto: {e}')

    return redirect('resu-proyectos', id_sem=id_sem)

def recursos(request, id_sem):
    usuario_id = request.session.get('cedula')
    if not usuario_id:
        messages.error(request, "Debes iniciar sesión para ver tu perfil.")
        return redirect('iniciarsesion')

    try:
        usuario = Usuario.objects.get(cedula=usuario_id)
    except Usuario.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect('iniciarsesion') 
    
    semillero = get_object_or_404(Semillero, id_sem=id_sem)
    
    # Obtener todos los documentos del semillero
    relaciones = SemilleroDocumento.objects.filter(id_sem=semillero)
    todos_documentos = Documento.objects.filter(
        cod_doc__in=relaciones.values_list('cod_doc', flat=True)
    )
    
    # Separar por categorías
    documentos = todos_documentos.filter(tipo__in=['Documento', 'Guía'])
    fichas = todos_documentos.filter(tipo__in=['Ficha', 'Acta'])

    # Calcular total de miembros
    cedulas = SemilleroUsuario.objects.filter(
        id_sem=semillero
    ).values_list('cedula', flat=True)
    
    total_usuarios = Usuario.objects.filter(cedula__in=cedulas).count()
    total_aprendices = Aprendiz.objects.filter(id_sem=semillero).count()
    total_miembros = total_usuarios + total_aprendices

    # Proyectos del semillero
    proyectos = SemilleroProyecto.objects.filter(id_sem=semillero)
    total_proyectos = proyectos.count()

    # Entregables asociados a esos proyectos
    total_entregables = Entregable.objects.filter(
        cod_pro__in=proyectos.values('cod_pro')
    ).count()

    
    return render(request, 'paginas/recursos.html', {
        'current_page': 'recursos', 
        'semillero': semillero,
        'current_page_name': 'Semilleros',
        'documentos': documentos,
        'fichas': fichas,
        'total_miembros': total_miembros,
        'total_proyectos': total_proyectos,
        'total_entregables': total_entregables,
        'usuario' : usuario,
    })

def agregar_recurso(request, id_sem):
    semillero = get_object_or_404(Semillero, id_sem=id_sem)
    
    if request.method == 'POST':
        # Obtener los datos del formulario
        nom_doc = request.POST.get('nom_doc')
        tipo = request.POST.get('tipo')
        archivo = request.FILES.get('archivo')
        
        # Validar que todos los campos requeridos estén presentes
        if not all([nom_doc, tipo, archivo]):
            messages.error(request, 'Todos los campos son obligatorios')
            return redirect('recursos', id_sem=id_sem)
                
        # Validar que el archivo sea PDF
        if archivo and not archivo.name.lower().endswith('.pdf'):
            messages.error(request, 'Solo se permiten archivos PDF')
            return redirect('recursos', id_sem=id_sem)
        
        try:
            # Generar el próximo cod_doc
            ultimo_doc = Documento.objects.order_by('-cod_doc').first()
            nuevo_cod_doc = (ultimo_doc.cod_doc + 1) if ultimo_doc else 1
            
            # Obtener fecha actual
            fecha_actual = datetime.now().strftime('%Y-%m-%d')
            
            # Crear el nuevo documento
            documento = Documento(
                cod_doc=nuevo_cod_doc,
                nom_doc=nom_doc,
                tipo=tipo,
                fecha_doc=fecha_actual,
                archivo=archivo
            )
            
            # Guardar el documento en la base de datos
            documento.save()
            
            # Crear la relación con el semillero 
            SemilleroDocumento.objects.create(
                id_sem=semillero,
                cod_doc=documento
            )
            
            messages.success(request, 'Documento guardado exitosamente')
            return redirect('recursos', id_sem=id_sem)
            
        except Exception as e:
            messages.error(request, f'Error al guardar el documento: {str(e)}')
            return redirect('recursos', id_sem=id_sem)
    
    # Si la solicitud no es POST, redirigir a la página de recursos
    return redirect('recursos', id_sem=id_sem)

def eliminar_recurso(request, id_sem, cod_doc):
    semillero = get_object_or_404(Semillero, id_sem=id_sem)
    documento = get_object_or_404(Documento, cod_doc=cod_doc)

    try:
        # Borrar el archivo físico si existe
        if hasattr(documento, 'archivo') and documento.archivo:
            documento.archivo.delete(save=False)

        # Eliminar la relación con el semillero
        SemilleroDocumento.objects.filter(
            id_sem=semillero, cod_doc=documento
        ).delete()

        # Eliminar el documento en sí
        documento.delete()

        messages.success(request, f'✅ Recurso "{documento.nom_doc}" eliminado correctamente.')
    except Exception as e:
        messages.error(request, f'⚠️ Error al eliminar el recurso: {e}')

    return redirect('recursos', id_sem=id_sem)

# VISTAS DE PROYECTOS
def proyectos(request):
    usuario_id = request.session.get('cedula')
    if not usuario_id:
        messages.error(request, "Debes iniciar sesión para ver tu perfil.")
        return redirect('iniciarsesion')

    try:
        usuario = Usuario.objects.get(cedula=usuario_id)
    except Usuario.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect('iniciarsesion') 
    
    """
    Vista para la gestión de proyectos con búsqueda, filtros y estadísticas
    """
    # Obtener la fecha actual y el inicio del mes
    fecha_actual = timezone.now()
    inicio_mes = fecha_actual.replace(day=1)
    
    # Obtener todos los proyectos
    proyectos_list = Proyecto.objects.all().prefetch_related('semilleros')
    
    #  Actualizar estados de TODOS los proyectos primero
    for proyecto in proyectos_list:
        verificar_y_actualizar_estados_entregables(proyecto)
        actualizar_progreso_proyecto(proyecto)  # ✅ AGREGAR ESTA LÍNEA
    
    # --- ESTADÍSTICAS GENERALES ---
    total_proyectos = proyectos_list.count()
    
    # Proyectos por estado
    proyectos_desarrollo = proyectos_list.filter(
        Q(estado_pro='planeacion') | Q(estado_pro='ejecucion')
    ).count()
    proyectos_completados = proyectos_list.filter(estado_pro='completado').count()
    proyectos_pendientes = proyectos_list.filter(estado_pro='diagnostico').count()
    
    # Proyectos creados este mes
    proyectos_mes = proyectos_list.filter(
        fecha_creacion__gte=inicio_mes
    ).count()
    
    # Proyectos en desarrollo este mes
    desarrollo_mes = proyectos_list.filter(
        Q(estado_pro='planeacion') | Q(estado_pro='ejecucion'),
        fecha_creacion__gte=inicio_mes
    ).count()
    
    # Proyectos completados este mes
    completados_mes = proyectos_list.filter(
        estado_pro='completado'
    ).count()
    
    # Proyectos pendientes este mes
    pendientes_mes = proyectos_list.filter(
        estado_pro='diagnostico',
        fecha_creacion__gte=inicio_mes
    ).count()
    
    # --- FILTROS Y BÚSQUEDA ---
    
    # Búsqueda por nombre
    buscar = request.GET.get('buscar', '').strip()
    if buscar:
        proyectos_list = proyectos_list.filter(
            Q(nom_pro__icontains=buscar) |
            Q(semilleros__nombre__icontains=buscar)
        ).distinct()
    
    # Filtro por estado
    estado = request.GET.get('estado', '').strip()
    if estado:
        proyectos_list = proyectos_list.filter(estado_pro=estado)
    
    # Filtro por tipo (si el campo tipo existe en tu modelo)
    tipo = request.GET.get('tipo', '').strip()
    if tipo:
        proyectos_list = proyectos_list.filter(tipo=tipo)
    
    # Ordenamiento
    orden = request.GET.get('orden', '').strip()
    if orden == 'nombre':
        proyectos_list = proyectos_list.order_by('nom_pro')
    elif orden == 'fecha_creacion':
        proyectos_list = proyectos_list.order_by('fecha_creacion')
    else:
        # Ordenamiento por defecto: más recientes primero
        proyectos_list = proyectos_list.order_by('-fecha_creacion')

    # Obtener todos los tipos de proyecto únicos
    tipos_proyecto = Proyecto.objects.values_list('tipo', flat=True).exclude(tipo__isnull=True).exclude(tipo='').distinct().order_by('tipo')
    
    # Contexto para el template
    context = {
        # Estadísticas
        'total_proyectos': total_proyectos,
        'proyectos_desarrollo': proyectos_desarrollo,
        'proyectos_completados': proyectos_completados,
        'proyectos_pendientes': proyectos_pendientes,
        'proyectos_mes': proyectos_mes,
        'desarrollo_mes': desarrollo_mes,
        'completados_mes': completados_mes,
        'pendientes_mes': pendientes_mes,
        'proyectos': proyectos_list,
        'tipos_proyecto': tipos_proyecto,
        'usuario' : usuario,
    }
    return render(request, 'paginas/proyectos.html', context)

# VISTAS DE MIEMBROS
def miembros(request):
    usuario_id = request.session.get('cedula')
    if not usuario_id:
        messages.error(request, "Debes iniciar sesión para ver tu perfil.")
        return redirect('iniciarsesion')

    # Obtener usuario
    try:
        usuario = Usuario.objects.get(cedula=usuario_id)
    except Usuario.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect('iniciarsesion')

    vista = request.GET.get('vista', 'tarjeta')
    estado_filtro = request.GET.get('estado', '')
    rol_filtro = request.GET.get('rol', 'todos')
    busqueda = request.GET.get('busqueda', '').strip().lower()
    miembro_id = request.GET.get('miembro_id')


    if request.method == "POST":
        cedula = request.POST.get("cedula")
        nuevo_estado = request.POST.get("estado")

        if cedula and nuevo_estado:
            
            usuario = Usuario.objects.filter(cedula=cedula).first()
            aprendiz = Aprendiz.objects.filter(cedula_apre=cedula).first()
            if usuario:
                usuario.estado = nuevo_estado
                usuario.save()
                messages.success(request, f"Estado de {usuario.nom_usu} actualizado a {nuevo_estado}.")
            elif aprendiz:
                aprendiz.estado_apre = nuevo_estado
                aprendiz.save()
                messages.success(request, f"Estado de {aprendiz.nombre} actualizado a {nuevo_estado}.")

        return redirect(f"{request.path}?miembro_id={cedula}")

    usuarios = Usuario.objects.all()
    aprendices = Aprendiz.objects.all()

    if busqueda:
        usuarios = usuarios.filter(
            Q(nom_usu__icontains=busqueda) |
            Q(ape_usu__icontains=busqueda) |
            Q(cedula__icontains=busqueda)
        )
        aprendices = aprendices.filter(
            Q(nombre__icontains=busqueda) |
            Q(apellido__icontains=busqueda) |
            Q(cedula_apre__icontains=busqueda)
        )

    # Solo filtrar si estado_filtro existe Y no es 'todos'
    if estado_filtro and estado_filtro != 'todos':
        usuarios = usuarios.filter(estado=estado_filtro)
        aprendices = aprendices.filter(estado_apre=estado_filtro)

    rol_filtro = request.GET.get('rol', 'todos').strip().lower()

    if rol_filtro == 'investigadores':
        usuarios = usuarios.filter(rol__iexact='Investigador')
        aprendices = aprendices.none()

    elif rol_filtro == 'instructores':
        usuarios = usuarios.filter(rol__iexact='Instructor')
        aprendices = aprendices.none()

    elif rol_filtro == 'lider_semillero':
        # Coincide con "Lider de Semillero", "Líder Semillero", etc.
        usuarios = usuarios.filter(rol__iregex=r'l[ií]der(\s+de)?\s+semillero')
        aprendices = aprendices.none()

    elif rol_filtro == 'dinamizador':
        usuarios = usuarios.filter(rol__iexact='Dinamizador')
        aprendices = aprendices.none()

    elif rol_filtro == 'lider_proyecto':
        # Coincide con "Lider de Proyecto", "Líder Proyecto", etc.
        usuarios = usuarios.filter(rol__iregex=r'l[ií]der(\s+de)?\s+proyecto')
        aprendices = aprendices.none()

    elif rol_filtro == 'aprendices':
        usuarios = usuarios.none()


    miembros = []

    for u in usuarios:
        ultimo_acceso = "Sin registro"
        if u.last_login:
            tiempo = now() - u.last_login
            dias, segundos = tiempo.days, tiempo.seconds

            if dias == 0:
                if segundos < 60:
                    ultimo_acceso = "Hace unos segundos"
                elif segundos < 3600:
                    minutos = segundos // 60
                    ultimo_acceso = f"Hace {minutos} minuto{'s' if minutos != 1 else ''}"
                else:
                    horas = segundos // 3600
                    ultimo_acceso = f"Hace {horas} hora{'s' if horas != 1 else ''}"
            elif dias == 1:
                ultimo_acceso = "Ayer"
            elif dias < 7:
                ultimo_acceso = f"Hace {dias} día{'s' if dias != 1 else ''}"
            elif dias < 30:
                semanas = dias // 7
                ultimo_acceso = f"Hace {semanas} semana{'s' if semanas != 1 else ''}"
            elif dias < 365:
                meses = dias // 30
                ultimo_acceso = f"Hace {meses} mes{'es' if meses != 1 else ''}"
            else:
                años = dias // 365
                ultimo_acceso = f"Hace {años} año{'s' if años != 1 else ''}"

        miembros.append({
            'id': u.cedula,
            'nombres': u.nom_usu,
            'apellidos': u.ape_usu,
            'correo_sena': u.correo_ins,
            'celular': u.telefono,
            'rol': u.rol,
            'ultima_sesion': ultimo_acceso,
            'tipo': 'usuario',
            'imagen_perfil': u.imagen_perfil.url if u.imagen_perfil else None,
            'objeto': u
        })

    for a in aprendices:
        miembros.append({
            'id': a.cedula_apre,
            'nombres': a.nombre,
            'apellidos': a.apellido,
            'correo_sena': a.correo_ins,
            'celular': a.telefono,
            'rol': 'Aprendiz',
            'ultima_sesion': None,
            'tipo': 'aprendiz',
            'objeto': a
        })

    total_instructores = Usuario.objects.filter(rol='Instructor').count()
    total_investigadores = Usuario.objects.filter(rol='Investigador').count()
    total_aprendices = Aprendiz.objects.count()

    miembro_seleccionado = None
    tipo_miembro = None

    if miembro_id:
        usuario = Usuario.objects.filter(cedula=miembro_id).first()
        if usuario:
            tipo_miembro = 'usuario'
            miembro_seleccionado = {
                'cedula': usuario.cedula,
                'nombres': usuario.nom_usu,
                'apellidos': usuario.ape_usu,
                'fecha_nacimiento': usuario.fecha_nacimiento,
                'correo_personal': usuario.correo_per,
                'correo_sena': usuario.correo_ins,
                'celular': usuario.telefono,
                'vinculacion': usuario.vinculacion_laboral,
                'dependencia': usuario.dependencia,
                'rol': usuario.rol,
                'imagen_perfil': usuario.imagen_perfil,
                'estado': usuario.estado,
                'semilleros': usuario.semilleros.all() if hasattr(usuario, 'semilleros') else [],
                'proyectos': usuario.proyectos.all() if hasattr(usuario, 'proyectos') else [],
            }
        else:
            aprendiz = Aprendiz.objects.filter(cedula_apre=miembro_id).first()
            if aprendiz:
                tipo_miembro = 'aprendiz'
                miembro_seleccionado = {
                    'cedula': aprendiz.cedula_apre,
                    'nombres': aprendiz.nombre,
                    'apellidos': aprendiz.apellido,
                    'correo_personal': aprendiz.correo_per,
                    'fecha_nacimiento': aprendiz.fecha_nacimiento,
                    'correo_sena': aprendiz.correo_ins,
                    'medio_bancario': aprendiz.medio_bancario,
                    'numero_cuenta': aprendiz.numero_cuenta,
                    'celular': aprendiz.telefono,
                    'ficha': aprendiz.ficha,
                    'programa': aprendiz.programa,
                    'rol': 'Aprendiz',
                    'estado': aprendiz.estado_apre,
                    'semilleros': [aprendiz.id_sem] if aprendiz.id_sem else [],
                    'proyectos': Proyecto.objects.filter(proyectoaprendiz__cedula_apre=aprendiz).distinct(),
                }

    contexto = {
        'miembros': miembros,
        'total_instructores': total_instructores,
        'total_investigadores': total_investigadores,
        'total_aprendices': total_aprendices,
        'miembro_seleccionado': miembro_seleccionado,
        'tipo_miembro': tipo_miembro,
        'vista': vista,
        'estado_filtro': estado_filtro,
        'rol_filtro': rol_filtro,
        'busqueda': busqueda,
        'usuario': usuario
    }

    return render(request, 'paginas/miembros.html', contexto)

# VISTAS DE CENTRO DE AYUDA
def centroayuda(request):
    usuario_id = request.session.get('cedula')
    if not usuario_id:
        messages.error(request, "Debes iniciar sesión para ver tu perfil.")
        return redirect('iniciarsesion')

    # Obtener usuario
    try:
        usuario = Usuario.objects.get(cedula=usuario_id)
    except Usuario.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect('iniciarsesion')
    
    contexto = {
        'usuario': usuario
    }
    return render(request, 'paginas/centroayuda.html', contexto)

# VISTAS DE REPORTES
def reportes(request):
    usuario_id = request.session.get('cedula')
    if not usuario_id:
        messages.error(request, "Debes iniciar sesión para ver tu perfil.")
        return redirect('iniciarsesion')

    # Obtener usuario
    try:
        usuario = Usuario.objects.get(cedula=usuario_id)
    except Usuario.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect('iniciarsesion')
    
    contexto = {
        'usuario': usuario
    }
    return render(request, 'paginas/reportes.html', contexto)

def reporte_general_semilleros(request):

    # Crear archivo Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Semilleros"

    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )

    ws.append([
        "Código Semillero",
        "Siglas",
        "Nombre Semillero",
        "Descripción",
        "Objetivos",
        "Fecha Creación",
        "Cantidad de Miembros",
        "Número de Proyectos",
        "Estado",
        "Progreso General",
        "Lider de Semillero"
    ])

    semilleros = Semillero.objects.all()

    for s in semilleros:

        cantidad_miembros = (
            SemilleroUsuario.objects.filter(id_sem=s).count() +
            Aprendiz.objects.filter(id_sem=s).count()
        )

        cantidad_proyectos = s.proyectos.count()

        # Obtener líder del semillero
        lider_sem = SemilleroUsuario.objects.filter(id_sem=s, es_lider=True).first()
        nombre_lider = lider_sem.cedula.nom_usu if lider_sem else "Sin líder"

        # Convertir objetivos a texto separado por comas
        objetivos = ", ".join(s.objetivo.splitlines()) if s.objetivo else ""

        ws.append([
            s.cod_sem,
            s.sigla,
            s.nombre,
            s.desc_sem,
            objetivos,
            s.fecha_creacion.strftime("%Y-%m-%d %H:%M"),
            cantidad_miembros,
            cantidad_proyectos,
            s.estado,
            s.progreso_sem,
            nombre_lider
        ])
    fila_inicial = 1
    fila_final = ws.max_row
    columna_final = 12

    for row in ws.iter_rows(min_row=fila_inicial, max_row=fila_final,
                            min_col=1, max_col=columna_final):
        for cell in row:
            cell.border = thin_border

    # Respuesta Excel
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="reporte_semilleros.xlsx"'
    
    # GRAFICO: Miembros por semillero
    categorias = Reference(ws, min_col=3, min_row=2, max_row=ws.max_row)  # nombre semillero
    valores = Reference(ws, min_col=7, min_row=1, max_row=ws.max_row)     # cant miembros
    crear_grafico_barras(ws, "Miembros por Semillero", categorias, valores, "L2")

    # GRAFICO: Proyectos por semillero
    categorias = Reference(ws, min_col=3, min_row=2, max_row=ws.max_row)
    valores = Reference(ws, min_col=8, min_row=1, max_row=ws.max_row)
    crear_grafico_barras(ws, "Proyectos por Semillero", categorias, valores, "L20")

    # GRAFICO: Progreso por semillero (líneas)
    categorias = Reference(ws, min_col=3, min_row=2, max_row=ws.max_row)
    valores = Reference(ws, min_col=10, min_row=1, max_row=ws.max_row)
    crear_grafico_lineas(ws, "Progreso de Semilleros", categorias, valores, "L38")

    # GRAFICO: Estados (pastel)
    estados_count = {}

    for s in semilleros:
        if s.estado:
            estados_count[s.estado] = estados_count.get(s.estado, 0) + 1

    if estados_count:
        fila_tabla = ws.max_row + 2
        ws.cell(row=fila_tabla, column=1, value="Estado").font = Font(bold=True)
        ws.cell(row=fila_tabla, column=2, value="Cantidad").font = Font(bold=True)

        # Llenar tabla
        fila = fila_tabla
        for estado, cantidad in estados_count.items():
            fila += 1
            ws.append([estado, cantidad])

        # Bordes
        for row in ws.iter_rows(min_row=fila_tabla, max_row=fila, min_col=1, max_col=2):
            for cell in row:
                cell.border = thin_border

        # Gráfico
        data = Reference(ws, min_col=2, min_row=fila_tabla, max_row=fila)
        labels = Reference(ws, min_col=1, min_row=fila_tabla+1, max_row=fila)

        chart = PieChart()
        chart.title = "Estados de los Semilleros"
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(labels)

        ws.add_chart(chart, "N55")

    wb.save(response)
    return response

def reporte_general_proyectos(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Proyectos"

    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )

    # Encabezados
    ws.append([
        "Nombre Proyecto",
        "Tipo",
        "Descripción",
        "Líneas Tecnologicas",
        "Líneas de Investigación",
        "Líneas de Semillero",
        "Notas Adicionales",
        "Cantidad de Miembros",
        "Cantidad de Entregables",
        "Fecha Creación",
        "Estado Actual",
        "Progreso",
        "Lider de Proyecto"
    ])

    proyectos = Proyecto.objects.all()

    for p in proyectos:

        cantidad_miembros = (
            UsuarioProyecto.objects.filter(cod_pro=p).count() +
            ProyectoAprendiz.objects.filter(cod_pro=p).count()
        )

        cantidad_entregables = Entregable.objects.filter(cod_pro=p).count()

        # Obtener líder del proyecto
        lider_pro = UsuarioProyecto.objects.filter(cod_pro=p, es_lider_pro=True).first()
        nombre_lider = lider_pro.cedula.nom_usu if lider_pro else "Sin líder"

        # Convertir a texto separado por comas
        lineas_tec = ", ".join([l.strip() for l in p.linea_tec.split("\n") if l.strip()]) if p.linea_tec else ""
        lineas_inv = ", ".join([l.strip() for l in p.linea_inv.split("\n") if l.strip()]) if p.linea_inv else ""
        lineas_sem = ", ".join([l.strip() for l in p.linea_sem.split("\n") if l.strip()]) if p.linea_sem else ""
        notas = ", ".join([l.strip() for l in p.notas.split("\n") if l.strip()]) if p.notas else ""

        ws.append([
            p.nom_pro,
            p.tipo,
            p.desc_pro,
            lineas_tec,
            lineas_inv,
            lineas_sem,
            notas,
            cantidad_miembros,
            cantidad_entregables,
            p.fecha_creacion.strftime("%Y-%m-%d %H:%M"),
            p.estado_pro,
            p.progreso,
            nombre_lider
        ])
    fila_inicial = 1
    fila_final = ws.max_row
    columna_final = 13  # tus 13 columnas fijas

    for row in ws.iter_rows(min_row=fila_inicial, max_row=fila_final,
        min_col=1, max_col=columna_final):
        for cell in row:
            cell.border = thin_border

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="reporte_proyectos.xlsx"'


    # GRAFICO: Progreso por proyecto
    categorias = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)   # nombre proyecto
    valores = Reference(ws, min_col=12, min_row=1, max_row=ws.max_row)     # progreso
    crear_grafico_lineas(ws, "Progreso por Proyecto", categorias, valores, "N2")

    # GRAFICO: Miembros por proyecto
    categorias = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)
    valores = Reference(ws, min_col=8, min_row=1, max_row=ws.max_row)
    crear_grafico_barras(ws, "Miembros por Proyecto", categorias, valores, "N20")

    # GRAFICO: Entregables por proyecto
    categorias = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)
    valores = Reference(ws, min_col=9, min_row=1, max_row=ws.max_row)
    crear_grafico_barras(ws, "Entregables por Proyecto", categorias, valores, "N38")

    # GRAFICO: ESTADOS DE LOS PROYECTOS 
    estados_count = {}

    for p in proyectos:
        if p.estado_pro:
            estados_count[p.estado_pro] = estados_count.get(p.estado_pro, 0) + 1

    if estados_count:
        fila_tabla = ws.max_row + 2
        ws.cell(row=fila_tabla, column=1, value="Estado").font = Font(bold=True)
        ws.cell(row=fila_tabla, column=2, value="Cantidad").font = Font(bold=True)

        # Llenar tabla
        fila = fila_tabla
        for estado, cantidad in estados_count.items():
            fila += 1
            ws.append([estado, cantidad])

        # Bordes
        for row in ws.iter_rows(min_row=fila_tabla, max_row=fila, min_col=1, max_col=2):
            for cell in row:
                cell.border = thin_border

        # Gráfico
        data = Reference(ws, min_col=2, min_row=fila_tabla, max_row=fila)
        labels = Reference(ws, min_col=1, min_row=fila_tabla+1, max_row=fila)

        chart = PieChart()
        chart.title = "Estados de los Proyectos"
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(labels)

        ws.add_chart(chart, "N55")

    # GRAFICO: LÍNEAS TECNOLÓGICAS 
    lineas_tec_count = {}

    for p in proyectos:
        if p.linea_tec:
            for linea in [l.strip() for l in p.linea_tec.split("\n") if l.strip()]:
                lineas_tec_count[linea] = lineas_tec_count.get(linea, 0) + 1

    if lineas_tec_count:
        fila_tabla = ws.max_row + 2
        ws.cell(row=fila_tabla, column=1, value="Línea Tecnológica").font = Font(bold=True)
        ws.cell(row=fila_tabla, column=2, value="Cantidad").font = Font(bold=True)

        fila = fila_tabla
        for linea, cantidad in lineas_tec_count.items():
            fila += 1
            ws.append([linea, cantidad])

        # Bordes
        for row in ws.iter_rows(min_row=fila_tabla, max_row=fila, min_col=1, max_col=2):
            for cell in row:
                cell.border = thin_border

        data = Reference(ws, min_col=2, min_row=fila_tabla, max_row=fila)
        labels = Reference(ws, min_col=1, min_row=fila_tabla+1, max_row=fila)

        chart = BarChart()
        chart.title = "Proyectos por Línea Tecnológica"
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(labels)

        ws.add_chart(chart, "N72")

    # GRAFICO: LÍNEAS DE INVESTIGACIÓN
    lineas_inv_count = {}

    for p in proyectos:
        if p.linea_inv:
            for linea in [l.strip() for l in p.linea_inv.split("\n") if l.strip()]:
                lineas_inv_count[linea] = lineas_inv_count.get(linea, 0) + 1

    if lineas_inv_count:
        fila_tabla = ws.max_row + 2
        ws.cell(row=fila_tabla, column=1, value="Línea Investigación").font = Font(bold=True)
        ws.cell(row=fila_tabla, column=2, value="Cantidad").font = Font(bold=True)

        fila = fila_tabla
        for linea, cantidad in lineas_inv_count.items():
            fila += 1
            ws.append([linea, cantidad])

        for row in ws.iter_rows(min_row=fila_tabla, max_row=fila, min_col=1, max_col=2):
            for cell in row:
                cell.border = thin_border

        data = Reference(ws, min_col=2, min_row=fila_tabla, max_row=fila)
        labels = Reference(ws, min_col=1, min_row=fila_tabla+1, max_row=fila)

        chart = PieChart()
        chart.title = "Proyectos por Línea de Investigación"
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(labels)

        ws.add_chart(chart, "N90")

    # GRAFICO: LÍNEAS DE SEMILLERO
    lineas_sem_count = {}

    for p in proyectos:
        if p.linea_sem:
            for linea in [l.strip() for l in p.linea_sem.split("\n") if l.strip()]:
                lineas_sem_count[linea] = lineas_sem_count.get(linea, 0) + 1

    if lineas_sem_count:
        fila_tabla = ws.max_row + 2
        ws.cell(row=fila_tabla, column=1, value="Línea Semillero").font = Font(bold=True)
        ws.cell(row=fila_tabla, column=2, value="Cantidad").font = Font(bold=True)

        fila = fila_tabla
        for linea, cantidad in lineas_sem_count.items():
            fila += 1
            ws.append([linea, cantidad])

        for row in ws.iter_rows(min_row=fila_tabla, max_row=fila, min_col=1, max_col=2):
            for cell in row:
                cell.border = thin_border

        data = Reference(ws, min_col=2, min_row=fila_tabla, max_row=fila)
        labels = Reference(ws, min_col=1, min_row=fila_tabla+1, max_row=fila)

        chart = BarChart()
        chart.title = "Proyectos por Línea de Semillero"
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(labels)

        ws.add_chart(chart, "N108")

    wb.save(response)
    return response

def reporte_entregables(request):

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Entregables"

    # Encabezados base
    encabezados = [
        "Proyecto",
        "Nombre Entregable",
        "Fecha Inicio",
        "Fecha Fin",
        "Descripción",
        "Estado",
        "Fechas de Subida"
    ]

    ws.append(encabezados)

    entregables = Entregable.objects.all()

    for e in entregables:

        archivos = Archivo.objects.filter(entregable=e)

        # Obtener fechas
        fechas_subida = ", ".join([
            a.fecha_subida.strftime("%Y-%m-%d %H:%M")
            for a in archivos
        ]) if archivos else ""

        # Crear fila base
        fila = [
            e.cod_pro.nom_pro,
            e.nom_entre,
            e.fecha_inicio,
            e.fecha_fin,
            e.desc_entre,
            e.estado,
            fechas_subida,
        ]

        # Agregar fila a Excel
        ws.append(fila)
        row = ws.max_row

        # -------------------------------
        #   AGREGAR ARCHIVOS EN COLUMNAS
        # -------------------------------
        col_base = len(encabezados) + 1  # Comienza después de Fechas

        for i, archivo in enumerate(archivos, start=1):

            col = col_base + i - 1
            cell = ws.cell(row=row, column=col)

            # Texto en la celda
            cell.value = f"Descargar archivo {i}"

            # Hipervínculo real
            url_archivo = request.build_absolute_uri(archivo.archivo.url)
            cell.hyperlink = url_archivo

            # Formato azul subrayado
            cell.style = "Hyperlink"

            # Agregar encabezado dinámico
            ws.cell(row=1, column=col).value = f"Archivo {i}"

    # Descargar el archivo
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="reporte_entregables.xlsx"'

    # GRAFICO: Entregables por estado

    estados_count = {}
    for e in entregables:
        if e.estado:
            estados_count[e.estado] = estados_count.get(e.estado, 0) + 1

    if estados_count:

        fila_tabla = ws.max_row + 2
        ws.cell(row=fila_tabla, column=1, value="Estado").font = Font(bold=True)
        ws.cell(row=fila_tabla, column=2, value="Cantidad").font = Font(bold=True)

        fila = fila_tabla
        for estado, cantidad in estados_count.items():
            fila += 1
            ws.append([estado, cantidad])

        # Crear gráfico real
        data = Reference(ws, min_col=2, min_row=fila_tabla, max_row=fila)
        labels = Reference(ws, min_col=1, min_row=fila_tabla + 1, max_row=fila)

        chart = PieChart()
        chart.title = "Estados de los Entregables"
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(labels)

        ws.add_chart(chart, "L2")

    # GRAFICO: Entregables por proyecto
    proyectos_count = {}
    for e in entregables:
        nom = e.cod_pro.nom_pro
        proyectos_count[nom] = proyectos_count.get(nom, 0) + 1

    if proyectos_count:

        fila_tabla = ws.max_row + 2
        ws.cell(row=fila_tabla, column=1, value="Proyecto").font = Font(bold=True)
        ws.cell(row=fila_tabla, column=2, value="Cantidad").font = Font(bold=True)

        fila = fila_tabla
        for proyecto, cantidad in proyectos_count.items():
            fila += 1
            ws.append([proyecto, cantidad])

        data = Reference(ws, min_col=2, min_row=fila_tabla, max_row=fila)
        labels = Reference(ws, min_col=1, min_row=fila_tabla + 1, max_row=fila)

        chart = BarChart()
        chart.title = "Entregables por Proyecto"
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(labels)

        ws.add_chart(chart, "L20")

    wb.save(response)
    return response

def reporte_participantes(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Participantes"

    # Encabezados sin fecha de nacimiento
    encabezados = [
        "Nombre",
        "Rol",
        "Proyecto",
        "Semillero",
        "Correo Personal",
        "Correo Institucional",
        "Estado"
    ]
    ws.append(encabezados)

    # -------------------------------
    #   APRENDICES
    # -------------------------------
    aprendices = Aprendiz.objects.all()
    for a in aprendices:
        semillero_nombre = a.id_sem.nombre if a.id_sem else "Sin semillero"
        proyectos_apre = ProyectoAprendiz.objects.filter(cedula_apre=a)

        if not proyectos_apre.exists():
            fila = [
                f"{a.nombre} {a.apellido}",
                "Aprendiz",
                "Sin proyecto",
                semillero_nombre,
                a.correo_per,
                a.correo_ins,
                a.estado_apre
            ]
            ws.append(fila)
        else:
            for pa in proyectos_apre:
                fila = [
                    f"{a.nombre} {a.apellido}",
                    "Aprendiz",
                    pa.cod_pro.nom_pro,
                    semillero_nombre,
                    a.correo_per,
                    a.correo_ins,
                    a.estado_apre
                ]
                ws.append(fila)

    # -------------------------------
    #   USUARIOS (Instructores e Investigadores)
    # -------------------------------
    usuarios = Usuario.objects.filter(rol__in=["Instructor", "Investigador"])
    for u in usuarios:
        proyectos_usuario = UsuarioProyecto.objects.filter(cedula=u, estado="activo")
        semilleros_usuario = SemilleroUsuario.objects.filter(cedula=u)
        semillero_nombre = ", ".join([s.id_sem.nombre for s in semilleros_usuario]) if semilleros_usuario else "Sin semillero"

        if not proyectos_usuario.exists():
            fila = [
                f"{u.nom_usu} {u.ape_usu}",
                u.rol,
                "Sin proyecto",
                semillero_nombre,
                u.correo_per,
                u.correo_ins,
                u.estado or ""
            ]
            ws.append(fila)
        else:
            for up in proyectos_usuario:
                fila = [
                    f"{u.nom_usu} {u.ape_usu}",
                    u.rol,
                    up.cod_pro.nom_pro,
                    semillero_nombre,
                    u.correo_per,
                    u.correo_ins,
                    u.estado or ""
                ]
                ws.append(fila)

    # -------------------------------
    # GRAFICO: Participantes por rol
    # -------------------------------
    roles_count = {}
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=2, max_col=2, values_only=True):
        rol = row[0]
        roles_count[rol] = roles_count.get(rol, 0) + 1

    if roles_count:
        fila_tabla = ws.max_row + 2
        ws.cell(row=fila_tabla, column=1, value="Rol").font = Font(bold=True)
        ws.cell(row=fila_tabla, column=2, value="Cantidad").font = Font(bold=True)

        fila = fila_tabla
        for rol, cantidad in roles_count.items():
            fila += 1
            ws.append([rol, cantidad])

        data = Reference(ws, min_col=2, min_row=fila_tabla, max_row=fila)
        labels = Reference(ws, min_col=1, min_row=fila_tabla + 1, max_row=fila)

        chart = PieChart()
        chart.title = "Participantes por Rol"
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(labels)
        ws.add_chart(chart, "H2")

    # -------------------------------
    # GRAFICO: Participantes por proyecto
    # -------------------------------
    proyectos_count = {}
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=3, max_col=3, values_only=True):
        proyecto = row[0] or "Sin proyecto"
        proyectos_count[proyecto] = proyectos_count.get(proyecto, 0) + 1

    if proyectos_count:
        fila_tabla = ws.max_row + 2
        ws.cell(row=fila_tabla, column=1, value="Proyecto").font = Font(bold=True)
        ws.cell(row=fila_tabla, column=2, value="Cantidad").font = Font(bold=True)

        fila = fila_tabla
        for proyecto, cantidad in proyectos_count.items():
            fila += 1
            ws.append([proyecto, cantidad])

        data = Reference(ws, min_col=2, min_row=fila_tabla, max_row=fila)
        labels = Reference(ws, min_col=1, min_row=fila_tabla + 1, max_row=fila)

        chart = BarChart()
        chart.title = "Participantes por Proyecto"
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(labels)
        ws.add_chart(chart, "H20")

    # Descargar archivo
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="reporte_participantes.xlsx"'
    wb.save(response)
    return response

def generar_reporte_excel(request):

    if request.method != "POST":
        return redirect("constructor_reportes")

    # NOMBRE DEL ARCHIVO
    nombre_archivo = request.POST.get("nombre_plantilla", "").strip()
    if not nombre_archivo:
        nombre_archivo = "reporte_personalizado"

    # Crear respuesta
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{nombre_archivo}.xlsx"'

    # CATEGORÍAS
    categorias = request.POST.getlist("categoria")

    if not categorias:
        messages.error(request, "Debes seleccionar al menos una categoría.")
        return redirect("constructor_reportes")

    # CAMPOS MARCADOS
    campos = {
        "semilleros": request.POST.getlist("campo_semilleros"),
        "proyectos": request.POST.getlist("campo_proyectos"),
        "miembros": request.POST.getlist("campo_miembros"),
        "entregables": request.POST.getlist("campo_entregables"),
    }

    # CREAR EXCEL
    wb = Workbook()
    hoja_default = wb.active
    wb.remove(hoja_default)
    
    # Crear estilo de borde
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # ==================== SEMILLEROS ====================
    if "semilleros" in categorias:
        ws = wb.create_sheet("Semilleros")
        
        # Título en negrita
        ws.cell(row=1, column=1, value="SEMILLEROS").font = Font(bold=True)
        
        # Encabezados en negrita
        fila_encabezado = 2
        for col_idx, campo in enumerate(campos["semilleros"], start=1):
            cell = ws.cell(row=fila_encabezado, column=col_idx, value=campo)
            cell.font = Font(bold=True)
        
        semilleros = Semillero.objects.all()
        fila_inicio_datos = 3

        for s in semilleros:
            fila = []
            for campo in campos["semilleros"]:
                match campo:
                    case "Código de Semillero": 
                        fila.append(s.cod_sem)
                    case "Nombre del Semillero": 
                        fila.append(s.nombre)
                    case "Siglas": 
                        fila.append(s.sigla)
                    case "Descripción": 
                        fila.append(s.desc_sem)
                    case "Progreso": 
                        fila.append(s.progreso_sem)
                    case "Objetivos": 
                        objetivos = s.objetivo.replace('\n', ', ') if s.objetivo else "Sin objetivos"
                        fila.append(objetivos)
                    case "Líder de Semillero":
                        lider = SemilleroUsuario.objects.filter(id_sem=s, es_lider=True).first()
                        fila.append(lider.cedula.nom_usu if lider else "Sin líder")
                    case "Fecha de Creación": 
                        fila.append(s.fecha_creacion.strftime("%Y-%m-%d"))
                    case "Estado Actual": 
                        fila.append(s.estado)
                    case "Número de Integrantes":
                        usuarios_sem = SemilleroUsuario.objects.filter(id_sem=s).select_related('cedula')
                        aprendices_sem = Aprendiz.objects.filter(id_sem=s)
                        roles_count = {}
                        for u_rel in usuarios_sem:
                            rol = u_rel.cedula.rol
                            roles_count[rol] = roles_count.get(rol, 0) + 1
                        cant_aprendices = aprendices_sem.count()
                        if cant_aprendices > 0:
                            roles_count['Aprendiz'] = cant_aprendices
                        total = sum(roles_count.values())
                        fila.append(total)
                    case "Cantidad de Proyectos": 
                        fila.append(s.proyectos.count())
                        
            ws.append(fila)
        
        # APLICAR BORDES A TABLA DE SEMILLEROS
        fila_fin = ws.max_row
        for row in ws.iter_rows(min_row=fila_encabezado, max_row=fila_fin, 
                                min_col=1, max_col=len(campos["semilleros"])):
            for cell in row:
                cell.border = thin_border

        # DESGLOSE DE INTEGRANTES POR ROL (en columnas SEPARADAS de Estado)
        if "Número de Integrantes" in campos["semilleros"]:
            col_inicio_roles = len(campos["semilleros"]) + 2
            
            ws.cell(row=fila_encabezado, column=col_inicio_roles, value="Rol").font = Font(bold=True)
            ws.cell(row=fila_encabezado, column=col_inicio_roles + 1, value="Cantidad por Rol").font = Font(bold=True)
            
            todos_roles = {}
            for s in semilleros:
                usuarios_sem = SemilleroUsuario.objects.filter(id_sem=s).select_related('cedula')
                aprendices_sem = Aprendiz.objects.filter(id_sem=s)
                
                for u_rel in usuarios_sem:
                    rol = u_rel.cedula.rol
                    todos_roles[rol] = todos_roles.get(rol, 0) + 1
                
                cant_aprendices = aprendices_sem.count()
                if cant_aprendices > 0:
                    todos_roles['Aprendiz'] = todos_roles.get('Aprendiz', 0) + cant_aprendices
            
            fila_actual = fila_inicio_datos
            for rol, cantidad in todos_roles.items():
                ws.cell(row=fila_actual, column=col_inicio_roles, value=rol)
                ws.cell(row=fila_actual, column=col_inicio_roles + 1, value=cantidad)
                fila_actual += 1
            
            # Bordes para tabla de roles
            for row in ws.iter_rows(min_row=fila_encabezado, max_row=fila_actual - 1, 
                                    min_col=col_inicio_roles, max_col=col_inicio_roles + 1):
                for cell in row:
                    cell.border = thin_border

        # GRÁFICO DE BARRAS - CANTIDAD DE PROYECTOS POR SEMILLERO
        if "Cantidad de Proyectos" in campos["semilleros"]:
            # Ubicar columna de cantidad de proyectos
            col_proyectos = campos["semilleros"].index("Cantidad de Proyectos") + 1
            col_nombre = campos["semilleros"].index("Nombre del Semillero") + 1 if "Nombre del Semillero" in campos["semilleros"] else 1
            
            # Crear tabla auxiliar para el gráfico - COLUMNA DIFERENTE
            col_inicio_tabla_proy = len(campos["semilleros"]) + 8
            
            ws.cell(row=fila_encabezado, column=col_inicio_tabla_proy, value="Semillero").font = Font(bold=True)
            ws.cell(row=fila_encabezado, column=col_inicio_tabla_proy + 1, value="Cantidad de Proyectos").font = Font(bold=True)
            
            fila_actual = fila_inicio_datos
            
            # Copiar datos de nombre y cantidad
            for row in ws.iter_rows(min_row=fila_inicio_datos, max_row=fila_fin, 
                                min_col=col_nombre, max_col=col_nombre, values_only=True):
                nombre_sem = row[0]
                # Obtener cantidad de proyectos de la columna correspondiente
                cant_proyectos = ws.cell(row=fila_actual, column=col_proyectos).value
                
                ws.cell(row=fila_actual, column=col_inicio_tabla_proy, value=nombre_sem)
                ws.cell(row=fila_actual, column=col_inicio_tabla_proy + 1, value=cant_proyectos)
                fila_actual += 1
            
            # Aplicar bordes a tabla auxiliar
            for row in ws.iter_rows(min_row=fila_encabezado, max_row=fila_actual - 1, 
                                min_col=col_inicio_tabla_proy, max_col=col_inicio_tabla_proy + 1):
                for cell in row:
                    cell.border = thin_border
            
            # Crear gráfico de barras
            chart_proy = BarChart()
            chart_proy.title = "Cantidad de Proyectos por Semillero"
            chart_proy.y_axis.title = "Número de Proyectos"
            chart_proy.x_axis.title = "Semilleros"
            
            data = Reference(ws, min_col=col_inicio_tabla_proy + 1, min_row=fila_encabezado, max_row=fila_actual - 1)
            labels = Reference(ws, min_col=col_inicio_tabla_proy, min_row=fila_inicio_datos, max_row=fila_actual - 1)
            
            chart_proy.add_data(data, titles_from_data=True)
            chart_proy.set_categories(labels)
            chart_proy.height = 15
            chart_proy.width = 20
            
            ws.add_chart(chart_proy, "N56")

        # GRÁFICO DE BARRAS - PROGRESO DE SEMILLEROS
        if "Progreso" in campos["semilleros"]:
            # Ubicar columnas necesarias
            col_progreso = campos["semilleros"].index("Progreso") + 1
            col_nombre = campos["semilleros"].index("Nombre del Semillero") + 1 if "Nombre del Semillero" in campos["semilleros"] else 1
            
            # Crear tabla auxiliar para el gráfico - COLUMNA MÁS A LA DERECHA
            col_inicio_tabla_prog = len(campos["semilleros"]) + 11
            
            ws.cell(row=fila_encabezado, column=col_inicio_tabla_prog, value="Semillero").font = Font(bold=True)
            ws.cell(row=fila_encabezado, column=col_inicio_tabla_prog + 1, value="Progreso (%)").font = Font(bold=True)
            
            fila_actual = fila_inicio_datos
            
            # Copiar datos de nombre y progreso
            for row_idx in range(fila_inicio_datos, fila_fin + 1):
                nombre_sem = ws.cell(row=row_idx, column=col_nombre).value
                progreso = ws.cell(row=row_idx, column=col_progreso).value
                
                # Asegurar que el progreso sea numérico
                if progreso is None or progreso == "":
                    progreso = 0
                else:
                    try:
                        progreso = float(progreso)
                    except:
                        progreso = 0
                
                ws.cell(row=fila_actual, column=col_inicio_tabla_prog, value=nombre_sem)
                ws.cell(row=fila_actual, column=col_inicio_tabla_prog + 1, value=progreso)
                fila_actual += 1
            
            # Aplicar bordes a tabla auxiliar
            for row in ws.iter_rows(min_row=fila_encabezado, max_row=fila_actual - 1, 
                                min_col=col_inicio_tabla_prog, max_col=col_inicio_tabla_prog + 1):
                for cell in row:
                    cell.border = thin_border
            
            # Crear gráfico de barras
            chart_prog = BarChart()
            chart_prog.title = "Progreso de Semilleros"
            chart_prog.y_axis.title = "Progreso (%)"
            chart_prog.x_axis.title = "Semilleros"
            
            data = Reference(ws, min_col=col_inicio_tabla_prog + 1, min_row=fila_encabezado, max_row=fila_actual - 1)
            labels = Reference(ws, min_col=col_inicio_tabla_prog, min_row=fila_inicio_datos, max_row=fila_actual - 1)
            
            chart_prog.add_data(data, titles_from_data=True)
            chart_prog.set_categories(labels)
            chart_prog.height = 15
            chart_prog.width = 20
            
            ws.add_chart(chart_prog, "N74")

        # GRÁFICO: Estados de semilleros (EN COLUMNAS DIFERENTES)
        if "Estado Actual" in campos["semilleros"]:
            try:
                col_estado = campos["semilleros"].index("Estado Actual") + 1
                
                estados = {}
                for row in ws.iter_rows(min_row=fila_inicio_datos, max_row=ws.max_row, min_col=col_estado, max_col=col_estado, values_only=True):
                    estado = row[0]
                    if estado:
                        estados[estado] = estados.get(estado, 0) + 1
                
                if estados:
                    col_inicio_estados = len(campos["semilleros"]) + 5
                    
                    ws.cell(row=fila_encabezado, column=col_inicio_estados, value="Estado").font = Font(bold=True)
                    ws.cell(row=fila_encabezado, column=col_inicio_estados + 1, value="Cantidad por Estado").font = Font(bold=True)
                    
                    fila_actual = fila_inicio_datos
                    for estado, cantidad in estados.items():
                        ws.cell(row=fila_actual, column=col_inicio_estados, value=estado)
                        ws.cell(row=fila_actual, column=col_inicio_estados + 1, value=cantidad)
                        fila_actual += 1
                    
                    # Bordes para tabla de estados
                    for row in ws.iter_rows(min_row=fila_encabezado, max_row=fila_actual - 1, 
                                            min_col=col_inicio_estados, max_col=col_inicio_estados + 1):
                        for cell in row:
                            cell.border = thin_border
                    
                    chart = PieChart()
                    chart.title = "Distribución por Estado"
                    
                    data = Reference(ws, min_col=col_inicio_estados + 1, min_row=fila_encabezado, max_row=fila_actual - 1)
                    labels = Reference(ws, min_col=col_inicio_estados, min_row=fila_inicio_datos, max_row=fila_actual - 1)
                    
                    chart.add_data(data, titles_from_data=True)
                    chart.set_categories(labels)
                    chart.height = 10
                    chart.width = 15
                    
                    ws.add_chart(chart, "N20")
            except ValueError:
                pass

        # GRÁFICO: Distribución de integrantes por rol
        if "Número de Integrantes" in campos["semilleros"]:
            try:
                col_inicio_roles = len(campos["semilleros"]) + 2
                
                ultima_fila_desglose = fila_encabezado
                for row in ws.iter_rows(min_row=fila_inicio_datos, min_col=col_inicio_roles, max_col=col_inicio_roles, values_only=True):
                    if row[0]:
                        ultima_fila_desglose += 1
                
                if ultima_fila_desglose > fila_encabezado:
                    chart = PieChart()
                    chart.title = "Distribución de Integrantes por Rol"
                    
                    data = Reference(ws, min_col=col_inicio_roles + 1, min_row=fila_encabezado, max_row=ultima_fila_desglose)
                    labels = Reference(ws, min_col=col_inicio_roles, min_row=fila_inicio_datos, max_row=ultima_fila_desglose)
                    
                    chart.add_data(data, titles_from_data=True)
                    chart.set_categories(labels)
                    chart.height = 10
                    chart.width = 15
                    
                    ws.add_chart(chart, "N38")
            except ValueError:
                pass

    # ==================== PROYECTOS ====================
    if "proyectos" in categorias:
        ws = wb.create_sheet("Proyectos")

        # Título en negrita
        ws.cell(row=1, column=1, value="PROYECTOS").font = Font(bold=True)

        # Encabezados en negrita (fila_encabezado = 2)
        fila_encabezado = 2
        num_cols = len(campos["proyectos"])
        for col_idx, campo in enumerate(campos["proyectos"], start=1):
            cell = ws.cell(row=fila_encabezado, column=col_idx, value=campo)
            cell.font = Font(bold=True)

        proyectos = list(Proyecto.objects.all())
        fila_inicio_datos = 3

        # --- Construir filas garantizando la longitud y posición correcta de cada columna ---
        for p_idx, p in enumerate(proyectos):
            # Crear lista con placeholders vacíos (una celda por cada encabezado)
            fila_vals = [""] * num_cols

            for i, campo in enumerate(campos["proyectos"]):
                # columna i -> index i
                match campo:
                    case "Título del Proyecto":
                        fila_vals[i] = p.nom_pro or ""
                    case "Tipo de Proyecto":
                        fila_vals[i] = p.tipo or ""
                    case "Estado":
                        fila_vals[i] = p.estado_pro or ""
                    case "Fecha de Creación":
                        fila_vals[i] = p.fecha_creacion.strftime("%Y-%m-%d") if getattr(p, "fecha_creacion", None) else ""
                    case "Porcentaje de Avance":
                        fila_vals[i] = p.progreso if p.progreso is not None else ""
                    case "Lider":
                        lider = UsuarioProyecto.objects.filter(cod_pro=p, es_lider_pro=True).select_related('cedula').first()
                        fila_vals[i] = lider.cedula.nom_usu if lider else "Sin líder"
                    case "Línea Tecnológica":
                        if getattr(p, "linea_tec", None):
                            lista = [s.strip() for s in p.linea_tec.splitlines() if s.strip()]
                            fila_vals[i] = ", ".join(lista)
                        else:
                            fila_vals[i] = ""
                    case "Línea de Investigación":
                        if getattr(p, "linea_inv", None):
                            lista = [s.strip() for s in p.linea_inv.splitlines() if s.strip()]
                            fila_vals[i] = ", ".join(lista)
                        else:
                            fila_vals[i] = ""
                    case "Línea de Semillero":
                        if getattr(p, "linea_sem", None):
                            lista = [s.strip() for s in p.linea_sem.splitlines() if s.strip()]
                            fila_vals[i] = ", ".join(lista)
                        else:
                            fila_vals[i] = ""
                    case "Participantes De Proyecto":
                        usuarios_pro = UsuarioProyecto.objects.filter(cod_pro=p).select_related('cedula')
                        aprendices_pro = ProyectoAprendiz.objects.filter(cod_pro=p)
                        fila_vals[i] = usuarios_pro.count() + aprendices_pro.count()
                    case "Notas":
                        fila_vals[i] = ", ".join([s.strip() for s in p.notas.splitlines() if s.strip()]) if getattr(p, "notas", None) else ""
                    case "Programa de Formación":
                        fila_vals[i] = p.programa_formacion if getattr(p, "programa_formacion", None) else ""

            # Ahora escribimos la fila completa en la hoja (esto preserva columnas vacías)
            ws.append(fila_vals)

        # APLICAR BORDES A TABLA DE PROYECTOS (uso len(campos["proyectos"]) para evitar desbordes)
        fila_fin = ws.max_row
        for row in ws.iter_rows(min_row=fila_encabezado, max_row=fila_fin,
                                min_col=1, max_col=len(campos["proyectos"])):
            for cell in row:
                cell.border = thin_border

        # DESGLOSE DE PARTICIPANTES POR ROL (proyectos)
        if "Participantes De Proyecto" in campos["proyectos"]:

            col_inicio = len(campos["proyectos"]) + 2

            ws.cell(row=fila_encabezado, column=col_inicio, value="Rol").font = Font(bold=True)
            ws.cell(row=fila_encabezado, column=col_inicio + 1, value="Cantidad").font = Font(bold=True)

            roles_count = {}

            for p in proyectos:
                usuarios = UsuarioProyecto.objects.filter(cod_pro=p).select_related('cedula')
                aprendices = ProyectoAprendiz.objects.filter(cod_pro=p)

                for rel in usuarios:
                    rol = rel.cedula.rol
                    roles_count[rol] = roles_count.get(rol, 0) + 1

                count_apre = aprendices.count()
                if count_apre > 0:
                    roles_count["Aprendiz"] = roles_count.get("Aprendiz", 0) + count_apre

            fila_actual = fila_inicio_datos
            for rol, cant in roles_count.items():
                ws.cell(row=fila_actual, column=col_inicio, value=rol)
                ws.cell(row=fila_actual, column=col_inicio + 1, value=cant)
                fila_actual += 1
            
            # Bordes para tabla de roles
            for row in ws.iter_rows(min_row=fila_encabezado, max_row=fila_actual - 1, 
                                    min_col=col_inicio, max_col=col_inicio + 1):
                for cell in row:
                    cell.border = thin_border

            # GRÁFICO 
            chart = PieChart()
            chart.title = "Participantes por Rol"

            data = Reference(ws, min_col=col_inicio + 1, min_row=fila_encabezado, max_row=fila_actual - 1)
            labels = Reference(ws, min_col=col_inicio, min_row=fila_inicio_datos, max_row=fila_actual - 1)

            chart.add_data(data, titles_from_data=True)
            chart.set_categories(labels)
            chart.height = 10
            chart.width = 15

            ws.add_chart(chart, "N2")
                
        # TABLA Y GRÁFICO – TIPO DE PROYECTO
        if "Tipo de Proyecto" in campos["proyectos"]:

            col_inicio = len(campos["proyectos"]) + 8
            ws.cell(row=fila_encabezado, column=col_inicio, value="Tipo").font = Font(bold=True)
            ws.cell(row=fila_encabezado, column=col_inicio + 1, value="Cantidad").font = Font(bold=True)

            tipos = {}

            for p in proyectos:
                if p.tipo:
                    tipos[p.tipo] = tipos.get(p.tipo, 0) + 1

            fila_actual = fila_inicio_datos
            for tipo, cantidad in tipos.items():
                ws.cell(row=fila_actual, column=col_inicio, value=tipo)
                ws.cell(row=fila_actual, column=col_inicio + 1, value=cantidad)
                fila_actual += 1
            
            # Bordes
            for row in ws.iter_rows(min_row=fila_encabezado, max_row=fila_actual - 1, 
                                    min_col=col_inicio, max_col=col_inicio + 1):
                for cell in row:
                    cell.border = thin_border

            chart = PieChart()
            chart.title = "Proyectos por Tipo"
            data = Reference(ws, min_col=col_inicio + 1, min_row=fila_encabezado, max_row=fila_actual - 1)
            labels = Reference(ws, min_col=col_inicio, min_row=fila_inicio_datos, max_row=fila_actual - 1)

            chart.add_data(data, titles_from_data=True)
            chart.set_categories(labels)
            chart.height = 10
            chart.width = 15

            ws.add_chart(chart, "N38")

        # TABLA Y GRÁFICO – AVANCE
        if "Porcentaje de Avance" in campos["proyectos"]:
            # Ubicar columnas necesarias
            col_avance = campos["proyectos"].index("Porcentaje de Avance") + 1
            col_nombre = campos["proyectos"].index("Título del Proyecto") + 1 if "Título del Proyecto" in campos["proyectos"] else 1
            
            # Crear tabla auxiliar para el gráfico - COLUMNA MÁS A LA DERECHA
            col_inicio = len(campos["proyectos"]) + 11

            # Encabezados
            ws.cell(row=fila_encabezado, column=col_inicio, value="Proyecto").font = Font(bold=True)
            ws.cell(row=fila_encabezado, column=col_inicio + 1, value="Avance (%)").font = Font(bold=True)

            fila_actual = fila_inicio_datos

            # Copiar datos de nombre y avance
            for row_idx in range(fila_inicio_datos, fila_fin + 1):
                nombre_pro = ws.cell(row=row_idx, column=col_nombre).value
                avance = ws.cell(row=row_idx, column=col_avance).value
                
                # Asegurar que el avance sea numérico
                if avance is None or avance == "":
                    avance = 0
                else:
                    try:
                        avance = float(avance)
                    except:
                        avance = 0
                
                ws.cell(row=fila_actual, column=col_inicio, value=nombre_pro)
                ws.cell(row=fila_actual, column=col_inicio + 1, value=avance)
                fila_actual += 1

            # Bordes
            for row in ws.iter_rows(
                min_row=fila_encabezado,
                max_row=fila_actual - 1,
                min_col=col_inicio,
                max_col=col_inicio + 1
            ):
                for cell in row:
                    cell.border = thin_border

            # Referencias para el gráfico
            data = Reference(ws, min_col=col_inicio + 1, min_row=fila_encabezado, max_row=fila_actual - 1)
            labels = Reference(ws, min_col=col_inicio, min_row=fila_inicio_datos, max_row=fila_actual - 1)

            # Crear gráfico de barras
            chart = BarChart()
            chart.title = "Porcentaje de Avance por Proyecto"
            chart.y_axis.title = "Avance (%)"
            chart.x_axis.title = "Proyectos"
            
            chart.add_data(data, titles_from_data=True)
            chart.set_categories(labels)
            chart.height = 15
            chart.width = 20

            ws.add_chart(chart, "N56")
            
        # TABLA Y GRÁFICO – LÍNEA TECNOLÓGICA 
        if "Línea Tecnológica" in campos["proyectos"]:

            col_inicio = len(campos["proyectos"]) + 14
            ws.cell(row=fila_encabezado, column=col_inicio, value="Línea Tec.").font = Font(bold=True)
            ws.cell(row=fila_encabezado, column=col_inicio + 1, value="Cantidad").font = Font(bold=True)

            lineas_tec = {}

            # Leer directamente desde el objeto proyecto
            for p in proyectos:
                if p.linea_tec and p.linea_tec.strip():
                    # Dividir por saltos de línea y contar cada línea
                    lineas_lista = [l.strip() for l in p.linea_tec.split('\n') if l.strip()]
                    for linea in lineas_lista:
                        lineas_tec[linea] = lineas_tec.get(linea, 0) + 1

            # Solo crear tabla y gráfico si hay datos
            if lineas_tec:
                fila_actual = fila_inicio_datos
                for linea, cant in lineas_tec.items():
                    ws.cell(row=fila_actual, column=col_inicio, value=linea)
                    ws.cell(row=fila_actual, column=col_inicio + 1, value=cant)
                    fila_actual += 1
                
                # Bordes
                for row in ws.iter_rows(
                    min_row=fila_encabezado, max_row=fila_actual - 1, 
                    min_col=col_inicio, max_col=col_inicio + 1
                ):
                    for cell in row:
                        cell.border = thin_border

                chart = PieChart()
                chart.title = "Proyectos por Línea Tecnológica"
                data = Reference(ws, min_col=col_inicio + 1, min_row=fila_encabezado, max_row=fila_actual - 1)
                labels = Reference(ws, min_col=col_inicio, min_row=fila_inicio_datos, max_row=fila_actual - 1)

                chart.add_data(data, titles_from_data=True)
                chart.set_categories(labels)
                chart.height = 10
                chart.width = 15

                ws.add_chart(chart, "N74")

        # TABLA Y GRÁFICO – LÍNEA DE INVESTIGACIÓN 
        if "Línea de Investigación" in campos["proyectos"]:

            col_inicio = len(campos["proyectos"]) + 17
            ws.cell(row=fila_encabezado, column=col_inicio, value="Línea Inv.").font = Font(bold=True)
            ws.cell(row=fila_encabezado, column=col_inicio + 1, value="Cantidad").font = Font(bold=True)

            lineas_inv = {}

            # Leer directamente desde el objeto proyecto
            for p in proyectos:
                if p.linea_inv and p.linea_inv.strip():
                    # Dividir por saltos de línea y contar cada línea
                    lineas_lista = [l.strip() for l in p.linea_inv.split('\n') if l.strip()]
                    for linea in lineas_lista:
                        lineas_inv[linea] = lineas_inv.get(linea, 0) + 1

            # Solo crear tabla y gráfico si hay datos
            if lineas_inv:
                fila_actual = fila_inicio_datos
                for linea, cant in lineas_inv.items():
                    ws.cell(row=fila_actual, column=col_inicio, value=linea)
                    ws.cell(row=fila_actual, column=col_inicio + 1, value=cant)
                    fila_actual += 1
                
                # Bordes
                for row in ws.iter_rows(
                    min_row=fila_encabezado, max_row=fila_actual - 1, 
                    min_col=col_inicio, max_col=col_inicio + 1
                ):
                    for cell in row:
                        cell.border = thin_border

                chart = PieChart()
                chart.title = "Proyectos por Línea de Investigación"
                data = Reference(ws, min_col=col_inicio + 1, min_row=fila_encabezado, max_row=fila_actual - 1)
                labels = Reference(ws, min_col=col_inicio, min_row=fila_inicio_datos, max_row=fila_actual - 1)

                chart.add_data(data, titles_from_data=True)
                chart.set_categories(labels)
                chart.height = 10
                chart.width = 15

                ws.add_chart(chart, "N92")

        # TABLA Y GRÁFICO – LÍNEA DE SEMILLERO 
        if "Línea de Semillero" in campos["proyectos"]:

            col_inicio = len(campos["proyectos"]) + 20
            ws.cell(row=fila_encabezado, column=col_inicio, value="Línea Sem.").font = Font(bold=True)
            ws.cell(row=fila_encabezado, column=col_inicio + 1, value="Cantidad").font = Font(bold=True)

            lineas_sem = {}

            # Leer directamente desde el objeto proyecto
            for p in proyectos:
                if p.linea_sem and p.linea_sem.strip():
                    # Dividir por saltos de línea y contar cada línea
                    lineas_lista = [l.strip() for l in p.linea_sem.split('\n') if l.strip()]
                    for linea in lineas_lista:
                        lineas_sem[linea] = lineas_sem.get(linea, 0) + 1

            # Solo crear tabla y gráfico si hay datos
            if lineas_sem:
                fila_actual = fila_inicio_datos
                for linea, cant in lineas_sem.items():
                    ws.cell(row=fila_actual, column=col_inicio, value=linea)
                    ws.cell(row=fila_actual, column=col_inicio + 1, value=cant)
                    fila_actual += 1
                
                # Bordes
                for row in ws.iter_rows(min_row=fila_encabezado, max_row=fila_actual - 1, 
                                        min_col=col_inicio, max_col=col_inicio + 1):
                    for cell in row:
                        cell.border = thin_border

                chart = PieChart()
                chart.title = "Proyectos por Línea de Semillero"
                data = Reference(ws, min_col=col_inicio + 1, min_row=fila_encabezado, max_row=fila_actual - 1)
                labels = Reference(ws, min_col=col_inicio, min_row=fila_inicio_datos, max_row=fila_actual - 1)

                chart.add_data(data, titles_from_data=True)
                chart.set_categories(labels)
                chart.height = 10
                chart.width = 15

                ws.add_chart(chart, "N110")

            # TABLA Y GRÁFICO – PROGRAMA DE FORMACIÓN (PROYECTOS)
            if "Programa de Formación" in campos["proyectos"]:

                col_inicio = len(campos["proyectos"]) + 23

                ws.cell(row=fila_encabezado, column=col_inicio, value="Programa de Formación").font = Font(bold=True)
                ws.cell(row=fila_encabezado, column=col_inicio + 1, value="Cantidad").font = Font(bold=True)

                programas_count = {}

                for p in proyectos:
                    programa = p.programa_formacion.strip() if p.programa_formacion else "Sin programa"
                    programas_count[programa] = programas_count.get(programa, 0) + 1

                fila_actual = fila_inicio_datos
                for programa, cantidad in programas_count.items():
                    ws.cell(row=fila_actual, column=col_inicio, value=programa)
                    ws.cell(row=fila_actual, column=col_inicio + 1, value=cantidad)
                    fila_actual += 1
                
                # Bordes
                for row in ws.iter_rows(min_row=fila_encabezado, max_row=fila_actual - 1, 
                                        min_col=col_inicio, max_col=col_inicio + 1):
                    for cell in row:
                        cell.border = thin_border

                chart = PieChart()
                chart.title = "Proyectos por Programa de Formación"

                data = Reference(ws, min_col=col_inicio + 1, min_row=fila_encabezado, max_row=fila_actual - 1)
                labels = Reference(ws, min_col=col_inicio, min_row=fila_inicio_datos, max_row=fila_actual - 1)

                chart.add_data(data, titles_from_data=True)
                chart.set_categories(labels)
                chart.height = 10
                chart.width = 15

                ws.add_chart(chart, "N128")

            # GRÁFICO: Estados de proyectos (COLUMNAS SEPARADAS)
            if "Estado" in campos["proyectos"]:
                try:
                    col_estado = campos["proyectos"].index("Estado") + 1
                    
                    estados = {}
                    for row in ws.iter_rows(min_row=fila_inicio_datos, max_row=ws.max_row, min_col=col_estado, max_col=col_estado, values_only=True):
                        estado = row[0]
                        if estado:
                            estados[estado] = estados.get(estado, 0) + 1
                    
                    if estados:
                        col_inicio_estados = len(campos["proyectos"]) + 5
                        
                        ws.cell(row=fila_encabezado, column=col_inicio_estados, value="Estado del Proyecto").font = Font(bold=True)
                        ws.cell(row=fila_encabezado, column=col_inicio_estados + 1, value="Cantidad por Estado").font = Font(bold=True)
                        
                        fila_actual = fila_inicio_datos
                        for estado, cantidad in estados.items():
                            ws.cell(row=fila_actual, column=col_inicio_estados, value=estado)
                            ws.cell(row=fila_actual, column=col_inicio_estados + 1, value=cantidad)
                            fila_actual += 1
                        
                        # Bordes
                        for row in ws.iter_rows(min_row=fila_encabezado, max_row=fila_actual - 1, 
                                                min_col=col_inicio_estados, max_col=col_inicio_estados + 1):
                            for cell in row:
                                cell.border = thin_border
                        
                        chart = PieChart()
                        chart.title = "Distribución por Estado"
                        
                        data = Reference(ws, min_col=col_inicio_estados + 1, min_row=fila_encabezado, max_row=fila_actual - 1)
                        labels = Reference(ws, min_col=col_inicio_estados, min_row=fila_inicio_datos, max_row=fila_actual - 1)
                        
                        chart.add_data(data, titles_from_data=True)
                        chart.set_categories(labels)
                        chart.height = 10
                        chart.width = 15
                        
                        ws.add_chart(chart, "N20")

                except ValueError:
                    pass
    
    # ==================== MIEMBROS ====================
    if "miembros" in categorias:

        ws = wb.create_sheet("Miembros")

        campos_seleccionados = campos["miembros"]

        # === TABLA 1: USUARIOS (NO APRENDICES)
        
        # Filtrar campos para usuarios 
        campos_usuarios = [c for c in campos_seleccionados 
            if c not in ["Programa", "Ficha", "Modalidad", "Programa de Formación"]]
        
        fila_actual = 1
        
        # Solo crear tabla de usuarios si hay campos para mostrar
        if campos_usuarios:
            # TÍTULO
            ws.cell(row=fila_actual, column=1, value="USUARIOS").font = Font(bold=True)
            fila_actual += 1
            
            # ENCABEZADOS en negrita
            fila_inicio_usuarios = fila_actual
            for col_idx, campo in enumerate(campos_usuarios, start=1):
                cell = ws.cell(row=fila_actual, column=col_idx, value=campo)
                cell.font = Font(bold=True)
            fila_actual += 1

            usuarios = Usuario.objects.all()

            for u in usuarios:

                if u.rol.lower() == "aprendiz":
                    continue

                fila = []
                for campo in campos_usuarios:

                    match campo:
                        case "Nombre Completo":
                            fila.append(f"{u.nom_usu} {u.ape_usu}")

                        case "Tipo de Documento":
                            fila.append("Cédula")

                        case "Documento":
                            fila.append(u.cedula)

                        case "Rol":
                            fila.append(u.rol)

                        case "Email":
                            fila.append(u.correo_ins or u.correo_per)

                        case "Teléfono":
                            fila.append(u.telefono)

                ws.append(fila)
            
            # APLICAR BORDES A TABLA DE USUARIOS
            fila_fin_usuarios = ws.max_row
            for row in ws.iter_rows(min_row=fila_inicio_usuarios, max_row=fila_fin_usuarios, 
                                    min_col=1, max_col=len(campos_usuarios)):
                for cell in row:
                    cell.border = thin_border

        # === SEPARADOR VISUAL

        fila_sep = ws.max_row + 2
        ws.cell(row=fila_sep, column=1, value="APRENDICES").font = Font(bold=True)

        # === TABLA 2: APRENDICES

        fila_inicio_ap = fila_sep + 1

        aprendices = Aprendiz.objects.all()

        # Encabezados en negrita
        for col_idx, campo in enumerate(campos_seleccionados, start=1):
            cell = ws.cell(row=fila_inicio_ap, column=col_idx, value=campo)
            cell.font = Font(bold=True)
        
        fila_inicio_ap_datos = fila_inicio_ap + 1

        # CONTENIDO DE APRENDICES
        for a in aprendices:

            fila = []

            for campo in campos_seleccionados:
                match campo:
                    case "Nombre Completo":
                        fila.append(f"{a.nombre} {a.apellido}")

                    case "Tipo de Documento":
                        fila.append(a.tipo_doc)

                    case "Documento":
                        fila.append(a.cedula_apre)

                    case "Rol":
                        fila.append("Aprendiz")

                    case "Email":
                        fila.append(a.correo_ins or a.correo_per)

                    case "Teléfono":
                        fila.append(a.telefono)

                    case "Programa" | "Programa de Formación":
                        fila.append(a.programa if hasattr(a, 'programa') else "")

                    case "Ficha":
                        fila.append(a.ficha if hasattr(a, 'ficha') else "")

                    case "Modalidad":
                        fila.append(a.modalidad if hasattr(a, 'modalidad') else "")

            ws.append(fila)
        
        # APLICAR BORDES A TABLA DE APRENDICES
        fila_fin_aprendices = ws.max_row
        for row in ws.iter_rows(min_row=fila_inicio_ap, max_row=fila_fin_aprendices, 
                                min_col=1, max_col=len(campos_seleccionados)):
            for cell in row:
                cell.border = thin_border

        # GRÁFICOS

        fila_inicio_graficos = fila_inicio_ap + len(aprendices) + 3
        
        # Calcular desplazamiento de columnas según si existe tabla de roles
        desplazamiento_col = 0

        # ----------- TABLA Y GRÁFICO DE ROLES (TODOS LOS MIEMBROS) -----------
        if "Rol" in campos_seleccionados:
            col_inicio_roles = len(campos_seleccionados) + 2
            
            ws.cell(row=fila_inicio_ap, column=col_inicio_roles, value="Rol").font = Font(bold=True)
            ws.cell(row=fila_inicio_ap, column=col_inicio_roles + 1, value="Cantidad").font = Font(bold=True)
            
            # Contar roles de TODOS los usuarios (no aprendices)
            roles_count = {}
            usuarios = Usuario.objects.all()
            
            for u in usuarios:
                if u.rol.lower() != "aprendiz":
                    rol = u.rol
                    roles_count[rol] = roles_count.get(rol, 0) + 1
            
            # Agregar aprendices
            cant_aprendices = aprendices.count()
            if cant_aprendices > 0:
                roles_count["Aprendiz"] = cant_aprendices
            
            # Escribir datos en tabla
            fila_g = fila_inicio_ap + 1
            for rol, cant in roles_count.items():
                ws.cell(row=fila_g, column=col_inicio_roles, value=rol)
                ws.cell(row=fila_g, column=col_inicio_roles + 1, value=cant)
                fila_g += 1
            
            # Bordes para tabla de roles
            for row in ws.iter_rows(min_row=fila_inicio_ap, max_row=fila_g - 1, 
                                    min_col=col_inicio_roles, max_col=col_inicio_roles + 1):
                for cell in row:
                    cell.border = thin_border
            
            # GRÁFICO DE ROLES
            chart = PieChart()
            chart.title = "Distribución de Miembros por Rol"
            data = Reference(ws, min_col=col_inicio_roles + 1, min_row=fila_inicio_ap, max_row=fila_g - 1)
            labels = Reference(ws, min_col=col_inicio_roles, min_row=fila_inicio_ap + 1, max_row=fila_g - 1)
            chart.add_data(data, titles_from_data=True)
            chart.set_categories(labels)
            chart.height = 10
            chart.width = 15
            ws.add_chart(chart, f"N{fila_inicio_graficos}")
            
            desplazamiento_col = 4  # Espacio para tabla de roles

        # ----------- PROGRAMA -----------
        if "Programa" in campos_seleccionados or "Programa de Formación" in campos_seleccionados:

            col_inicio = len(campos_seleccionados) + 2 + desplazamiento_col

            ws.cell(row=fila_inicio_ap, column=col_inicio, value="Programa").font = Font(bold=True)
            ws.cell(row=fila_inicio_ap, column=col_inicio + 1, value="Cantidad").font = Font(bold=True)

            programas = {}
            for a in aprendices:
                prog = (a.programa if hasattr(a, 'programa') else None) or "Sin programa"
                programas[prog] = programas.get(prog, 0) + 1

            fila_g = fila_inicio_ap + 1
            for prog, cant in programas.items():
                ws.cell(row=fila_g, column=col_inicio, value=prog)
                ws.cell(row=fila_g, column=col_inicio + 1, value=cant)
                fila_g += 1
            
            # Bordes
            for row in ws.iter_rows(min_row=fila_inicio_ap, max_row=fila_g - 1, 
                                    min_col=col_inicio, max_col=col_inicio + 1):
                for cell in row:
                    cell.border = thin_border

            chart = PieChart()
            chart.title = "Aprendices por Programa"
            data = Reference(ws, min_col=col_inicio + 1, min_row=fila_inicio_ap, max_row=fila_g - 1)
            labels = Reference(ws, min_col=col_inicio, min_row=fila_inicio_ap + 1, max_row=fila_g - 1)
            chart.add_data(data, titles_from_data=True)
            chart.set_categories(labels)
            chart.height = 10
            chart.width = 15
            
            # Ajustar posición según si existe tabla de roles
            pos_grafico = fila_inicio_graficos + 18 if desplazamiento_col > 0 else fila_inicio_graficos
            ws.add_chart(chart, f"N{pos_grafico}")

        # ----------- FICHA -----------
        if "Ficha" in campos_seleccionados:

            col_inicio = len(campos_seleccionados) + 6 + desplazamiento_col

            ws.cell(row=fila_inicio_ap, column=col_inicio, value="Ficha").font = Font(bold=True)
            ws.cell(row=fila_inicio_ap, column=col_inicio + 1, value="Cantidad").font = Font(bold=True)

            fichas = {}
            for a in aprendices:
                f = (a.ficha if hasattr(a, 'ficha') else None) or "Sin ficha"
                fichas[f] = fichas.get(f, 0) + 1

            fila_g = fila_inicio_ap + 1
            for f, cant in fichas.items():
                ws.cell(row=fila_g, column=col_inicio, value=f)
                ws.cell(row=fila_g, column=col_inicio + 1, value=cant)
                fila_g += 1
            
            # Bordes
            for row in ws.iter_rows(min_row=fila_inicio_ap, max_row=fila_g - 1, 
                                    min_col=col_inicio, max_col=col_inicio + 1):
                for cell in row:
                    cell.border = thin_border

            chart = PieChart()
            chart.title = "Aprendices por Ficha"
            data = Reference(ws, min_col=col_inicio + 1, min_row=fila_inicio_ap, max_row=fila_g - 1)
            labels = Reference(ws, min_col=col_inicio, min_row=fila_inicio_ap + 1, max_row=fila_g - 1)
            chart.add_data(data, titles_from_data=True)
            chart.set_categories(labels)
            chart.height = 10
            chart.width = 15
            
            # Ajustar posición según si existe tabla de roles
            pos_grafico = fila_inicio_graficos + 36 if desplazamiento_col > 0 else fila_inicio_graficos + 18
            ws.add_chart(chart, f"N{pos_grafico}")


        # ----------- MODALIDAD -----------
        if "Modalidad" in campos_seleccionados:

            col_inicio = len(campos_seleccionados) + 10 + desplazamiento_col

            ws.cell(row=fila_inicio_ap, column=col_inicio, value="Modalidad").font = Font(bold=True)
            ws.cell(row=fila_inicio_ap, column=col_inicio + 1, value="Cantidad").font = Font(bold=True)

            modalidades = {}
            for a in aprendices:
                mod = (a.modalidad if hasattr(a, 'modalidad') else None) or "Sin modalidad"
                modalidades[mod] = modalidades.get(mod, 0) + 1

            fila_g = fila_inicio_ap + 1
            for mod, cant in modalidades.items():
                ws.cell(row=fila_g, column=col_inicio, value=mod)
                ws.cell(row=fila_g, column=col_inicio + 1, value=cant)
                fila_g += 1
            
            # Bordes
            for row in ws.iter_rows(min_row=fila_inicio_ap, max_row=fila_g - 1, 
                                    min_col=col_inicio, max_col=col_inicio + 1):
                for cell in row:
                    cell.border = thin_border

            chart = PieChart()
            chart.title = "Aprendices por Modalidad"
            data = Reference(ws, min_col=col_inicio + 1, min_row=fila_inicio_ap, max_row=fila_g - 1)
            labels = Reference(ws, min_col=col_inicio, min_row=fila_inicio_ap + 1, max_row=fila_g - 1)
            chart.add_data(data, titles_from_data=True)
            chart.set_categories(labels)
            chart.height = 10
            chart.width = 15
            
            # Ajustar posición según si existe tabla de roles
            pos_grafico = fila_inicio_graficos + 54 if desplazamiento_col > 0 else fila_inicio_graficos + 36
            ws.add_chart(chart, f"N{pos_grafico}")

        # ----------- TIPO DE DOCUMENTO -----------
        if "Tipo de Documento" in campos_seleccionados:
            
            col_inicio = len(campos_seleccionados) + 14 + desplazamiento_col
            
            ws.cell(row=fila_inicio_ap, column=col_inicio, value="Tipo de Documento").font = Font(bold=True)
            ws.cell(row=fila_inicio_ap, column=col_inicio + 1, value="Cantidad").font = Font(bold=True)
            
            tipos_doc = {}
            
            # Contar tipos de documento de USUARIOS (todos tienen Cédula)
            usuarios = Usuario.objects.all()
            for u in usuarios:
                if u.rol.lower() != "aprendiz":
                    tipos_doc["Cédula"] = tipos_doc.get("Cédula", 0) + 1
            
            # Contar tipos de documento de APRENDICES
            for a in aprendices:
                tipo = (a.tipo_doc if hasattr(a, 'tipo_doc') else None) or "Cédula"
                tipos_doc[tipo] = tipos_doc.get(tipo, 0) + 1
            
            # Escribir datos en tabla
            fila_g = fila_inicio_ap + 1
            for tipo, cant in tipos_doc.items():
                ws.cell(row=fila_g, column=col_inicio, value=tipo)
                ws.cell(row=fila_g, column=col_inicio + 1, value=cant)
                fila_g += 1
            
            # Aplicar bordes
            for row in ws.iter_rows(min_row=fila_inicio_ap, max_row=fila_g - 1, 
                                    min_col=col_inicio, max_col=col_inicio + 1):
                for cell in row:
                    cell.border = thin_border
            
            # Crear gráfico
            chart = PieChart()
            chart.title = "Distribución por Tipo de Documento"
            data = Reference(ws, min_col=col_inicio + 1, min_row=fila_inicio_ap, max_row=fila_g - 1)
            labels = Reference(ws, min_col=col_inicio, min_row=fila_inicio_ap + 1, max_row=fila_g - 1)
            chart.add_data(data, titles_from_data=True)
            chart.set_categories(labels)
            chart.height = 10
            chart.width = 15
            
            # Ajustar posición según si existe tabla de roles
            pos_grafico = fila_inicio_graficos + 72 if desplazamiento_col > 0 else fila_inicio_graficos + 54
            ws.add_chart(chart, f"N{pos_grafico}")

    # ==================== ENTREGABLES ====================
    if "entregables" in categorias:
        ws = wb.create_sheet("Entregables")
        
        # Título en negrita
        ws.cell(row=1, column=1, value="ENTREGABLES").font = Font(bold=True)
        
        # Encabezados en negrita
        fila_encabezado = 2
        for col_idx, campo in enumerate(campos["entregables"], start=1):
            cell = ws.cell(row=fila_encabezado, column=col_idx, value=campo)
            cell.font = Font(bold=True)

        entregables = Entregable.objects.all()
        fila_inicio_datos = 3

        for e in entregables:
            fila = []
            for campo in campos["entregables"]:
                match campo:
                    case "Nombre del Entregable":
                        fila.append(e.nom_entre)
                    case "Estado":
                        fila.append(e.estado)
                    case "Fecha de Entrega":
                        fila.append(e.fecha_fin.strftime("%Y-%m-%d") if e.fecha_fin else "")
                    case "Proyecto Asociado":
                        fila.append(e.cod_pro.nom_pro)
                    case "Responsable":
                        resp = UsuarioProyecto.objects.filter(cod_pro=e.cod_pro, es_lider_pro=True).first()
                        fila.append(resp.cedula.nom_usu if resp else "Sin responsable")
            ws.append(fila)
        
        # APLICAR BORDES A TABLA DE ENTREGABLES
        fila_fin = ws.max_row
        for row in ws.iter_rows(min_row=fila_encabezado, max_row=fila_fin, 
                                min_col=1, max_col=len(campos["entregables"])):
            for cell in row:
                cell.border = thin_border

        # GRÁFICO: Estados de entregables
        if "Estado" in campos["entregables"]:
            try:
                col_estado = campos["entregables"].index("Estado") + 1
                
                estados = {}
                for row in ws.iter_rows(min_row=fila_inicio_datos, max_row=ws.max_row, min_col=col_estado, max_col=col_estado, values_only=True):
                    estado = row[0]
                    if estado:
                        estados[estado] = estados.get(estado, 0) + 1
                
                if estados:
                    col_inicio_grafico = len(campos["entregables"]) + 2
                    
                    ws.cell(row=fila_encabezado, column=col_inicio_grafico, value="Estado").font = Font(bold=True)
                    ws.cell(row=fila_encabezado, column=col_inicio_grafico + 1, value="Cantidad").font = Font(bold=True)
                    
                    fila_actual = fila_inicio_datos
                    for estado, cantidad in estados.items():
                        ws.cell(row=fila_actual, column=col_inicio_grafico, value=estado)
                        ws.cell(row=fila_actual, column=col_inicio_grafico + 1, value=cantidad)
                        fila_actual += 1
                    
                    # Bordes
                    for row in ws.iter_rows(min_row=fila_encabezado, max_row=fila_actual - 1, 
                                            min_col=col_inicio_grafico, max_col=col_inicio_grafico + 1):
                        for cell in row:
                            cell.border = thin_border
                    
                    chart = PieChart()
                    chart.title = "Entregables por Estado"
                    
                    data = Reference(ws, min_col=col_inicio_grafico + 1, min_row=fila_encabezado, max_row=fila_actual - 1)
                    labels = Reference(ws, min_col=col_inicio_grafico, min_row=fila_inicio_datos, max_row=fila_actual - 1)
                    
                    chart.add_data(data, titles_from_data=True)
                    chart.set_categories(labels)
                    chart.height = 10
                    chart.width = 15
                    
                    ws.add_chart(chart, "H2")
            except ValueError:
                pass

        # GRÁFICO: Proyectos Asociados
        if "Proyecto Asociado" in campos["entregables"]:
            try:
                col_proyecto = campos["entregables"].index("Proyecto Asociado") + 1
                
                proyectos = {}
                for row in ws.iter_rows(min_row=fila_inicio_datos, max_row=ws.max_row, min_col=col_proyecto, max_col=col_proyecto, values_only=True):
                    proyecto = row[0]
                    if proyecto:
                        proyectos[proyecto] = proyectos.get(proyecto, 0) + 1
                
                if proyectos:
                    col_inicio_proyectos = len(campos["entregables"]) + 5
                    
                    ws.cell(row=fila_encabezado, column=col_inicio_proyectos, value="Proyecto").font = Font(bold=True)
                    ws.cell(row=fila_encabezado, column=col_inicio_proyectos + 1, value="Cantidad de Entregables").font = Font(bold=True)
                    
                    fila_actual = fila_inicio_datos
                    for proyecto, cantidad in proyectos.items():
                        ws.cell(row=fila_actual, column=col_inicio_proyectos, value=proyecto)
                        ws.cell(row=fila_actual, column=col_inicio_proyectos + 1, value=cantidad)
                        fila_actual += 1
                    
                    # Bordes
                    for row in ws.iter_rows(min_row=fila_encabezado, max_row=fila_actual - 1, 
                                            min_col=col_inicio_proyectos, max_col=col_inicio_proyectos + 1):
                        for cell in row:
                            cell.border = thin_border
                    
                    chart = PieChart()
                    chart.title = "Entregables por Proyecto"
                    
                    data = Reference(ws, min_col=col_inicio_proyectos + 1, min_row=fila_encabezado, max_row=fila_actual - 1)
                    labels = Reference(ws, min_col=col_inicio_proyectos, min_row=fila_inicio_datos, max_row=fila_actual - 1)
                    
                    chart.add_data(data, titles_from_data=True)
                    chart.set_categories(labels)
                    chart.height = 10
                    chart.width = 15
                    
                    ws.add_chart(chart, "H20")
            except ValueError:
                pass

    wb.save(response)
    return response

def crear_grafico_barras(ws, titulo, rango_categorias, rango_valores, celda_pos):
    chart = BarChart()
    chart.title = titulo
    chart.add_data(rango_valores, titles_from_data=True)
    chart.set_categories(rango_categorias)
    ws.add_chart(chart, celda_pos)

def crear_grafico_lineas(ws, titulo, rango_categorias, rango_valores, celda_pos):
    chart = LineChart()
    chart.title = titulo
    chart.add_data(rango_valores, titles_from_data=True)
    chart.set_categories(rango_categorias)
    ws.add_chart(chart, celda_pos)

def crear_grafico_pie(ws, titulo, rango_labels, rango_valores, celda_pos):
    chart = PieChart()
    chart.title = titulo
    chart.add_data(rango_valores, titles_from_data=True)
    chart.set_categories(rango_labels)
    ws.add_chart(chart, celda_pos)

def generar_reporte_dinamico(request):
    if request.method != "POST":
        return redirect("reportes")

    # Obtener formato seleccionado
    formato = request.POST.get("formato", "excel")
    
    if formato == "pdf":
        return generar_reporte_pdf(request)
    else:
        return generar_reporte_excel(request)

def generar_reporte_pdf(request):
    # NOMBRE DEL ARCHIVO
    nombre_archivo = request.POST.get("nombre_plantilla", "").strip()
    if not nombre_archivo:
        nombre_archivo = "reporte_personalizado"

    # Crear respuesta HTTP para PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}.pdf"'

    # Crear buffer y documento
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(A4),
        rightMargin=30, 
        leftMargin=30,
        topMargin=30, 
        bottomMargin=18
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#34495E'),
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )
    
    # Estilos para las celdas de las tablas
    style_header = ParagraphStyle(
        'HeaderCell',
        fontSize=9,
        textColor=colors.whitesmoke,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        leading=11,
        wordWrap='CJK'
    )
    
    style_celda = ParagraphStyle(
        'DataCell',
        fontSize=8,
        alignment=TA_CENTER,
        leading=10,
        wordWrap='CJK'
    )
    
    # Contenedor de elementos
    elements = []
    
    # CATEGORÍAS
    categorias = request.POST.getlist("categoria")
    
    if not categorias:
        messages.error(request, "Debes seleccionar al menos una categoría.")
        return redirect("constructor_reportes")

    # CAMPOS MARCADOS
    campos = {
        "semilleros": request.POST.getlist("campo_semilleros"),
        "proyectos": request.POST.getlist("campo_proyectos"),
        "miembros": request.POST.getlist("campo_miembros"),
        "entregables": request.POST.getlist("campo_entregables"),
    }

    # ==================== SEMILLEROS ====================
    if "semilleros" in categorias:
        elements.append(Paragraph("REPORTE DE SEMILLEROS", title_style))
        elements.append(Spacer(1, 12))
        
        semilleros = Semillero.objects.all()
        
        # Preparar datos para la tabla
        data = [campos["semilleros"]]  # Encabezados
        
        for s in semilleros:
            fila = []
            for campo in campos["semilleros"]:
                valor = ""  # ✅ Valor por defecto
                
                if campo == "Código de Semillero":
                    valor = str(s.cod_sem) if s.cod_sem else ""
                elif campo == "Nombre del Semillero":
                    valor = str(s.nombre) if s.nombre else ""
                elif campo == "Siglas":
                    valor = str(s.sigla) if s.sigla else ""
                elif campo == "Descripción":
                    valor = str(s.desc_sem) if s.desc_sem else ""
                elif campo == "Progreso":
                    valor = f"{s.progreso_sem}%" if s.progreso_sem is not None else "0%"
                elif campo == "Objetivos":
                    valor = s.objetivo.replace('\n', ', ') if s.objetivo else ""
                elif campo == "Líder de Semillero":
                    lider = SemilleroUsuario.objects.filter(id_sem=s, es_lider=True).first()
                    valor = lider.cedula.nom_usu if lider else ""
                elif campo == "Fecha de Creación":
                    valor = s.fecha_creacion.strftime("%Y-%m-%d") if s.fecha_creacion else ""
                elif campo == "Estado Actual":
                    valor = str(s.estado) if s.estado else ""
                elif campo == "Número de Integrantes":
                    usuarios_sem = SemilleroUsuario.objects.filter(id_sem=s).count()
                    aprendices_sem = Aprendiz.objects.filter(id_sem=s).count()
                    valor = str(usuarios_sem + aprendices_sem)
                elif campo == "Cantidad de Proyectos":
                    valor = str(s.proyectos.count())
                
                fila.append(valor)  # ✅ Siempre agregar valor (aunque sea vacío)
            
            data.append(fila)
        
        # Convertir todos los datos a Paragraphs
        for i in range(len(data)):
            for j in range(len(data[i])):
                if i == 0:  # Encabezado
                    data[i][j] = Paragraph(str(data[i][j]), style_header)
                else:  # Celdas de datos
                    data[i][j] = Paragraph(str(data[i][j]) if data[i][j] else " ", style_celda)  # ✅ Espacio si está vacío
        
        # Calcular anchos de forma inteligente
        ancho_disponible = landscape(A4)[0] - 60
        col_widths = []
        for campo in campos["semilleros"]:
            if campo in ["Código de Semillero", "Siglas", "Progreso", "Estado Actual"]:
                col_widths.append(50)
            elif campo in ["Fecha de Creación", "Número de Integrantes", "Cantidad de Proyectos"]:
                col_widths.append(70)
            elif campo in ["Nombre del Semillero", "Líder de Semillero"]:
                col_widths.append(100)
            else:
                col_widths.append(150)
        
        total_width = sum(col_widths)
        if total_width > ancho_disponible:
            factor = ancho_disponible / total_width
            col_widths = [w * factor for w in col_widths]
        
        t = Table(data, repeatRows=1, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(t)
        elements.append(PageBreak())

    # ==================== PROYECTOS ====================
    if "proyectos" in categorias:
        elements.append(Paragraph("REPORTE DE PROYECTOS", title_style))
        elements.append(Spacer(1, 12))
        
        proyectos = Proyecto.objects.all()
        data = [campos["proyectos"]]
        
        for p in proyectos:
            fila = []
            for campo in campos["proyectos"]:
                valor = ""  # ✅ Valor por defecto
                
                if campo == "Título del Proyecto":
                    valor = str(p.nom_pro) if p.nom_pro else ""
                elif campo == "Tipo de Proyecto":
                    valor = str(p.tipo) if p.tipo else ""
                elif campo == "Estado":
                    valor = str(p.estado_pro) if p.estado_pro else ""
                elif campo == "Fecha de Creación":
                    valor = p.fecha_creacion.strftime("%Y-%m-%d") if hasattr(p, "fecha_creacion") and p.fecha_creacion else ""
                elif campo == "Porcentaje de Avance":
                    valor = f"{p.progreso}%" if p.progreso is not None else "0%"
                elif campo == "Lider":
                    lider = UsuarioProyecto.objects.filter(cod_pro=p, es_lider_pro=True).first()
                    valor = lider.cedula.nom_usu if lider else ""
                elif campo == "Línea Tecnológica":
                    if p.linea_tec:
                        valor = ", ".join([l.strip() for l in p.linea_tec.splitlines() if l.strip()])
                elif campo == "Línea de Investigación":
                    if p.linea_inv:
                        valor = ", ".join([l.strip() for l in p.linea_inv.splitlines() if l.strip()])
                elif campo == "Línea de Semillero":
                    if p.linea_sem:
                        valor = ", ".join([l.strip() for l in p.linea_sem.splitlines() if l.strip()])
                elif campo == "Participantes De Proyecto":
                    usuarios = UsuarioProyecto.objects.filter(cod_pro=p).count()
                    aprendices = ProyectoAprendiz.objects.filter(cod_pro=p).count()
                    valor = str(usuarios + aprendices)
                elif campo == "Programa de Formación":
                    valor = str(p.programa_formacion) if p.programa_formacion else ""
                elif campo == "Notas":  # ✅ AGREGADO
                    valor = ", ".join([s.strip() for s in p.notas.splitlines() if s.strip()]) if hasattr(p, "notas") and p.notas else ""
                
                fila.append(valor)  # ✅ Siempre agregar valor
            
            data.append(fila)
        
        # Convertir todos los datos a Paragraphs
        for i in range(len(data)):
            for j in range(len(data[i])):
                if i == 0:
                    data[i][j] = Paragraph(str(data[i][j]), style_header)
                else:
                    data[i][j] = Paragraph(str(data[i][j]) if data[i][j] else " ", style_celda)  # ✅ Espacio si está vacío
        
        ancho_disponible = landscape(A4)[0] - 60
        col_widths = []
        for campo in campos["proyectos"]:
            if campo in ["Estado", "Porcentaje de Avance", "Participantes De Proyecto"]:
                col_widths.append(60)
            elif campo in ["Tipo de Proyecto", "Fecha de Creación"]:
                col_widths.append(80)
            elif campo in ["Título del Proyecto", "Lider", "Programa de Formación"]:
                col_widths.append(100)
            elif campo == "Notas":  # ✅ AGREGADO
                col_widths.append(150)
            else:
                col_widths.append(120)
        
        total_width = sum(col_widths)
        if total_width > ancho_disponible:
            factor = ancho_disponible / total_width
            col_widths = [w * factor for w in col_widths]
        
        t = Table(data, repeatRows=1, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E74C3C')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(t)
        elements.append(PageBreak())

    # ==================== MIEMBROS (CORRECCIÓN) ====================
    if "miembros" in categorias:
        elements.append(Paragraph("REPORTE DE MIEMBROS", title_style))
        elements.append(Spacer(1, 12))
        
        # USUARIOS
        elements.append(Paragraph("Usuarios", heading_style))
        usuarios = Usuario.objects.exclude(rol__iexact="aprendiz")
        
        # ✅ Filtrar campos que no aplican a Usuarios
        campos_usuarios = [c for c in campos["miembros"] 
            if c not in ["Programa", "Ficha", "Modalidad", "Programa de Formación"]]
        
        if campos_usuarios and usuarios.exists():  # ✅ Verificar que hay datos
            data = [campos_usuarios]
            
            for u in usuarios:
                fila = []
                for campo in campos_usuarios:
                    valor = ""
                    
                    if campo == "Nombre Completo":
                        valor = f"{u.nom_usu or ''} {u.ape_usu or ''}".strip()
                    elif campo == "Tipo de Documento":
                        valor = "Cédula"
                    elif campo == "Documento":
                        valor = str(u.cedula) if u.cedula else ""
                    elif campo == "Rol":
                        valor = str(u.rol) if u.rol else ""
                    elif campo == "Email":
                        valor = u.correo_ins or u.correo_per or ""
                    elif campo == "Teléfono":
                        valor = str(u.telefono) if u.telefono else ""
                    
                    fila.append(valor)
                
                data.append(fila)
            
            # Convertir a Paragraphs
            for i in range(len(data)):
                for j in range(len(data[i])):
                    if i == 0:
                        data[i][j] = Paragraph(str(data[i][j]), style_header)
                    else:
                        data[i][j] = Paragraph(str(data[i][j]) if data[i][j] else " ", style_celda)
            
            # Calcular anchos
            ancho_disponible = landscape(A4)[0] - 60
            col_widths = []
            for campo in campos_usuarios:
                if campo in ["Tipo de Documento", "Documento", "Rol", "Teléfono"]:
                    col_widths.append(70)
                elif campo == "Nombre Completo":
                    col_widths.append(120)
                elif campo == "Email":
                    col_widths.append(150)
                else:
                    col_widths.append(100)  # ✅ Ancho por defecto
            
            total_width = sum(col_widths)
            if total_width > ancho_disponible:
                factor = ancho_disponible / total_width
                col_widths = [w * factor for w in col_widths]
            
            t = Table(data, repeatRows=1, colWidths=col_widths)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27AE60')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 20))
        
        # APRENDICES
        elements.append(Paragraph("Aprendices", heading_style))
        aprendices = Aprendiz.objects.all()
        
        # ✅ Usar TODOS los campos seleccionados (incluyendo los específicos de aprendices)
        if campos["miembros"] and aprendices.exists():  # ✅ Verificar que hay datos
            data = [campos["miembros"]]
            
            for a in aprendices:
                fila = []
                for campo in campos["miembros"]:
                    valor = ""
                    
                    if campo == "Nombre Completo":
                        valor = f"{a.nombre or ''} {a.apellido or ''}".strip()
                    elif campo == "Tipo de Documento":
                        valor = str(a.tipo_doc) if a.tipo_doc else "Cédula"
                    elif campo == "Documento":
                        valor = str(a.cedula_apre) if a.cedula_apre else ""
                    elif campo == "Rol":
                        valor = "Aprendiz"
                    elif campo == "Email":
                        valor = a.correo_ins or a.correo_per or ""
                    elif campo == "Teléfono":
                        valor = str(a.telefono) if a.telefono else ""
                    elif campo in ["Programa", "Programa de Formación"]:
                        valor = str(a.programa) if hasattr(a, 'programa') and a.programa else ""
                    elif campo == "Ficha":
                        valor = str(a.ficha) if hasattr(a, 'ficha') and a.ficha else ""
                    elif campo == "Modalidad":
                        valor = str(a.modalidad) if hasattr(a, 'modalidad') and a.modalidad else ""
                    
                    fila.append(valor)
                
                data.append(fila)
            
            # Convertir a Paragraphs
            for i in range(len(data)):
                for j in range(len(data[i])):
                    if i == 0:
                        data[i][j] = Paragraph(str(data[i][j]), style_header)
                    else:
                        data[i][j] = Paragraph(str(data[i][j]) if data[i][j] else " ", style_celda)
            
            # Calcular anchos
            ancho_disponible = landscape(A4)[0] - 60
            col_widths = []
            for campo in campos["miembros"]:
                if campo in ["Tipo de Documento", "Documento", "Rol", "Teléfono", "Ficha", "Modalidad"]:
                    col_widths.append(70)
                elif campo == "Nombre Completo":
                    col_widths.append(120)
                elif campo == "Email":
                    col_widths.append(150)
                elif campo in ["Programa", "Programa de Formación"]:
                    col_widths.append(130)
                else:
                    col_widths.append(100)  # ✅ Ancho por defecto
            
            total_width = sum(col_widths)
            if total_width > ancho_disponible:
                factor = ancho_disponible / total_width
                col_widths = [w * factor for w in col_widths]
            
            t = Table(data, repeatRows=1, colWidths=col_widths)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27AE60')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(t)
        
        elements.append(PageBreak())

    # ==================== ENTREGABLES (CORRECCIÓN) ====================
    if "entregables" in categorias:
        elements.append(Paragraph("REPORTE DE ENTREGABLES", title_style))
        elements.append(Spacer(1, 12))
        
        entregables = Entregable.objects.all()
        
        if campos["entregables"] and entregables.exists():  # ✅ Verificar que hay datos
            data = [campos["entregables"]]
            
            for e in entregables:
                fila = []
                for campo in campos["entregables"]:
                    valor = ""
                    
                    if campo == "Nombre del Entregable":
                        valor = str(e.nom_entre) if e.nom_entre else ""
                    elif campo == "Estado":
                        valor = str(e.estado) if e.estado else ""
                    elif campo == "Fecha de Entrega":
                        valor = e.fecha_fin.strftime("%Y-%m-%d") if e.fecha_fin else ""
                    elif campo == "Proyecto Asociado":
                        # ✅ Verificar que cod_pro no sea None antes de acceder a nom_pro
                        if e.cod_pro and hasattr(e.cod_pro, 'nom_pro') and e.cod_pro.nom_pro:
                            valor = str(e.cod_pro.nom_pro)
                        else:
                            valor = "Sin proyecto"
                    elif campo == "Responsable":
                        # ✅ Verificar que cod_pro existe antes de buscar el líder
                        if e.cod_pro:
                            resp = UsuarioProyecto.objects.filter(
                                cod_pro=e.cod_pro, 
                                es_lider_pro=True
                            ).first()
                            valor = resp.cedula.nom_usu if resp and resp.cedula else ""
                        else:
                            valor = ""
                    
                    fila.append(valor)
                
                data.append(fila)
            
            # Convertir a Paragraphs
            for i in range(len(data)):
                for j in range(len(data[i])):
                    if i == 0:
                        data[i][j] = Paragraph(str(data[i][j]), style_header)
                    else:
                        data[i][j] = Paragraph(str(data[i][j]) if data[i][j] else " ", style_celda)
            
            # Calcular anchos
            ancho_disponible = landscape(A4)[0] - 60
            col_widths = []
            for campo in campos["entregables"]:
                if campo in ["Estado", "Fecha de Entrega"]:
                    col_widths.append(80)
                elif campo in ["Nombre del Entregable", "Proyecto Asociado", "Responsable"]:
                    col_widths.append(150)
                else:
                    col_widths.append(100)  # ✅ Ancho por defecto
            
            total_width = sum(col_widths)
            if total_width > ancho_disponible:
                factor = ancho_disponible / total_width
                col_widths = [w * factor for w in col_widths]
            
            t = Table(data, repeatRows=1, colWidths=col_widths)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9B59B6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(t)
    # Construir PDF
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response

# VISTA DE LOGOUT
def logout(request):
    # Clear all session data
    request.session.flush()
    messages.success(request, "Has cerrado sesión correctamente")
    return redirect('iniciarsesion')
