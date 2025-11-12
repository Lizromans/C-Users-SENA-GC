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
from django.db.models import Q
from datetime import datetime
from django.db.models import Case, When, Value, IntegerField
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
import os
from django.contrib.auth import authenticate, login


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
    """
    Esta vista simplemente muestra la misma plantilla de inicio de sesión
    pero con el modal de recuperación de contraseña visible
    """
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
    usuario = {
        'nom_usu': request.session.get('nom_usu')
    }

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
    semilleros = Semillero.objects.all()
    
    # Calcular totales para cada semillero
    for semillero in semilleros:
        cedulas = SemilleroUsuario.objects.filter(
            id_sem=semillero
        ).values_list('cedula', flat=True)
        
        total_usuarios = Usuario.objects.filter(cedula__in=cedulas).count()
        total_aprendices = Aprendiz.objects.filter(id_sem=semillero).count()
        
        # Agregar como atributo dinámico
        semillero.total_miembros = total_usuarios + total_aprendices

        # Proyectos del semillero
        proyectos = SemilleroProyecto.objects.filter(id_sem=semillero)
        total_proyectos = proyectos.count()
        semillero.total_proyectos = total_proyectos

        # Entregables asociados a esos proyectos
        total_entregables = Entregable.objects.filter(
            cod_pro__in=proyectos.values('cod_pro')
        ).count()
        semillero.total_entregables = total_entregables
        
    return render(request, 'paginas/semilleros.html', {
        'semilleros': semilleros
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
                estado='Activo'
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
                    nombre_semillero = semillero.nombre
                    
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
                    Aprendiz.objects.filter(id_sem=semillero).update(id_sem=None)
                    
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

def resumen(request, id_sem):
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

    return render(request, 'paginas/resumen.html', {
        'current_page': 'resumen',
        'current_page_name': 'Semilleros',
        'semillero': semillero,
        'objetivos_lista': objetivos_lista,
        'total_miembros': total_miembros,
        'total_proyectos': total_proyectos,
        'total_entregables': total_entregables
    })

def resu_miembros(request, id_sem):
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

            lineas_tec = request.POST.getlist('lineastec[]')
            lineas_inv = request.POST.getlist('lineasinv[]')
            lineas_sem = request.POST.getlist('lineassem[]')

            proyecto_editar.linea_tec = "\n".join(lineas_tec)
            proyecto_editar.linea_inv = "\n".join(lineas_inv)
            proyecto_editar.linea_sem = "\n".join(lineas_sem)

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

        lineas_tec_lista = [l.strip() for l in proyecto_editar.linea_tec.split('\n') if l.strip()] if proyecto_editar.linea_tec else []
        lineas_inv_lista = [l.strip() for l in proyecto_editar.linea_inv.split('\n') if l.strip()] if proyecto_editar.linea_inv else []
        lineas_sem_lista = [l.strip() for l in proyecto_editar.linea_sem.split('\n') if l.strip()] if proyecto_editar.linea_sem else []

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
        return JsonResponse({'success': False, 'error': 'No se especificó el miembro'})

    try:
        # Verificar si es usuario o aprendiz
        try:
            relacion = UsuarioProyecto.objects.get(cedula__cedula=cedula_miembro, cod_pro=proyecto)
            
            # 👇 AGREGAR ESTA VALIDACIÓN
            # Verificar si es líder antes de cambiar a inactivo
            if relacion.estado == "activo" and relacion.es_lider_pro:
                return JsonResponse({
                    'success': False, 
                    'error': 'No se puede desactivar al líder del proyecto. Primero asigne otro líder.'
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
                es_lider_pro=False
            )
            es_lider_actual = False
        
        # Si ya es líder, informar
        if es_lider_actual:
            return JsonResponse({
                'success': True,
                'es_lider_pro': True,
                'mensaje': f'{miembro.nom_usu} {miembro.ape_usu} ya es líder de este proyecto'
            })
        
        # Quitar liderazgo al líder anterior
        try:
            relacion_anterior = UsuarioProyecto.objects.get(cod_pro=proyecto, es_lider_pro=True)
            usuario_anterior = relacion_anterior.cedula
            
            # Cambiar rol si era "Líder de Proyecto"
            if usuario_anterior.rol == 'Líder de Proyecto':
                usuario_anterior.rol = 'Instructor'
                usuario_anterior.save()
            
            # Quitar liderazgo
            relacion_anterior.es_lider_pro = False
            relacion_anterior.save()
            
        except UsuarioProyecto.DoesNotExist:
            pass
        
        # Asignar nuevo líder
        relacion_actual.es_lider_pro= True
        relacion_actual.save()
        
        # Actualizar rol del nuevo líder
        miembro.rol = 'Líder de Proyecto'
        miembro.save()
        
        return JsonResponse({
            'success': True,
            'es_lider_pro': True,
            'mensaje': f'{miembro.nom_usu} {miembro.ape_usu} ha sido asignado como líder del proyecto'
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

    #--- (creación del proyecto) ---
    if request.method == 'POST':
        try:
            cedula_usuario = request.session.get('cedula')
            if not cedula_usuario:
                messages.error(request, 'Debes iniciar sesión para crear un proyecto.')
                return redirect('iniciarsesion')

            usuario_actual = Usuario.objects.get(cedula=cedula_usuario)

            nom_pro = request.POST.get('nom_pro', '').strip()
            tipo = request.POST.get('tipo', '').strip().lower()
            desc_pro = request.POST.get('desc_pro', '').strip()
            lineas_tec = request.POST.getlist('lineastec[]')
            lineas_inv = request.POST.getlist('lineasinv[]')
            lineas_sem = request.POST.getlist('lineassem[]')
            miembros_seleccionados = request.POST.getlist('miembros_proyecto[]')

            if not all([nom_pro, tipo, desc_pro]):
                messages.error(request, 'Todos los campos son obligatorios.')
                return redirect('resu-proyectos', id_sem=id_sem)

            # Crear el proyecto
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
                estado_pro="Activo"
            )

            # Asociar proyecto al semillero
            SemilleroProyecto.objects.create(id_sem=semillero, cod_pro=proyecto)

            # Asociar usuario creador
            UsuarioProyecto.objects.create(cedula=usuario_actual, cod_pro=proyecto)

            # Asociar miembros seleccionados
            miembros_agregados = 0
            for cedula in miembros_seleccionados:
                if str(cedula) != str(cedula_usuario):
                    try:
                        usuario = Usuario.objects.get(cedula=cedula)
                        UsuarioProyecto.objects.create(cedula=usuario, cod_pro=proyecto)
                        miembros_agregados += 1
                    except Usuario.DoesNotExist:
                        try:
                            aprendiz = Aprendiz.objects.get(cedula_apre=cedula)
                            ProyectoAprendiz.objects.create(cedula_apre=aprendiz, cod_pro=proyecto)
                            miembros_agregados += 1
                        except Aprendiz.DoesNotExist:
                            pass

            # Entregables por defecto
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
                Entregable.objects.create(
                    cod_entre=base_cod + i,
                    nom_entre=entregable_data["nombre"],
                    desc_entre=entregable_data["descripcion"],
                    estado="Pendiente",
                    cod_pro=proyecto
                )

            messages.success(request, f'Proyecto "{nom_pro}" creado correctamente con {miembros_agregados} miembro(s).')
            return redirect('resu-proyectos', id_sem=id_sem)

        except Exception as e:
            messages.error(request, f'Error al crear proyecto: {str(e)}')
            return redirect('resu-proyectos', id_sem=id_sem)

    # Renderizar con miembros realmente NO asignados
    return render(request, 'crear_proyecto.html', {
        'semillero': semillero,
        'miembros_semillero': miembros_semillero
    })

def subir_archivo_entregable(request, id_sem, cod_pro, cod_entre):
    semillero = get_object_or_404(Semillero, id_sem=id_sem)
    entregable = get_object_or_404(Entregable, cod_pro=cod_pro, cod_entre=cod_entre)

    if request.method == 'POST':
        archivo = request.FILES.get('archivo')

        if not archivo:
            messages.error(request, '⚠️ Debes seleccionar un archivo para subir.')
            return redirect('resu-proyectos', id_sem=id_sem)

        # Guardar registro correctamente en la BD
        Archivo.objects.create(
            entregable=entregable,
            archivo=archivo,
            nombre=archivo.name
        )

        messages.success(
            request,
            f'✅ Archivo "{archivo.name}" subido correctamente al entregable "{entregable.nom_entre}".'
        )
        return redirect('resu-proyectos', id_sem=id_sem)

    messages.error(request, 'Método no permitido.')
    return redirect('resu-proyectos', id_sem=id_sem)

def actualizar_progreso_proyecto(proyecto):
    """
    Función auxiliar para calcular y actualizar el progreso de un proyecto
    basado en el estado de sus entregables
    """
    entregables = Entregable.objects.filter(cod_pro=proyecto)
    total_entregables = entregables.count()
    
    if total_entregables == 0:
        proyecto.progreso = 0
    else:
        entregables_completados = entregables.filter(estado='Completado').count()
        proyecto.progreso = round((entregables_completados / total_entregables) * 100)
    
    proyecto.save(update_fields=['progreso'])

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
        'total_entregables': total_entregables
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
    """
    Vista para la gestión de proyectos con búsqueda, filtros y estadísticas
    """
    # Obtener la fecha actual y el inicio del mes
    fecha_actual = timezone.now()
    inicio_mes = fecha_actual.replace(day=1)
    
    # Obtener todos los proyectos
    proyectos_list = Proyecto.objects.all().prefetch_related('semilleros')
    
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
        # Ajusta 'tipo' según el nombre real del campo en tu modelo
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
    
    # Obtener todos los tipos de proyecto únicos (ajusta según tu modelo)
    # Si tienes un campo 'tipo' en el modelo Proyecto:
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
    }
    return render(request, 'paginas/proyectos.html', context)

# VISTAS DE MIEMBROS
def miembros(request):
    """Vista principal de gestión de miembros."""
    
    # Obtener parámetros GET
    vista = request.GET.get('vista', 'tarjeta')
    estado_filtro = request.GET.get('estado', '')
    rol_filtro = request.GET.get('rol', 'todos')
    busqueda = request.GET.get('busqueda', '').strip().lower()
    miembro_id = request.GET.get('miembro_id')

    # Manejar actualización del estado (POST)
    if request.method == "POST":
        cedula = request.POST.get("cedula")
        nuevo_estado = request.POST.get("estado")

        if cedula and nuevo_estado:
            # Buscar primero en Usuario
            usuario = Usuario.objects.filter(cedula=cedula).first()
            if usuario:
                usuario.estado = nuevo_estado
                usuario.save()
                messages.success(request, f"Estado de {usuario.nom_usu} actualizado a {nuevo_estado}.")
            else:
                # Buscar en Aprendiz
                aprendiz = Aprendiz.objects.filter(cedula_apre=cedula).first()
                if aprendiz:
                    aprendiz.estado_apre = nuevo_estado
                    aprendiz.save()
                    messages.success(request, f"Estado de {aprendiz.nombre} actualizado a {nuevo_estado}.")

        # Redirigir para evitar reenvíos del formulario
        return redirect(f"{request.path}?miembro_id={cedula}")

    # Obtener todos los usuarios y aprendices
    usuarios = Usuario.objects.all()
    aprendices = Aprendiz.objects.all()

    # Aplicar filtros
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

    if estado_filtro:
        usuarios = usuarios.filter(estado=estado_filtro)
        aprendices = aprendices.filter(estado_apre=estado_filtro)

    if rol_filtro == 'investigadores':
        usuarios = usuarios.filter(rol__iexact='Investigador')
        aprendices = aprendices.none()
    elif rol_filtro == 'instructores':
        usuarios = usuarios.filter(rol__iexact='Instructor')
        aprendices = aprendices.none()
    elif rol_filtro == 'aprendices':
        usuarios = usuarios.none()

    # Normalizar miembros
    miembros = []
    for u in usuarios:
        miembros.append({
            'id': u.cedula,
            'nombres': u.nom_usu,
            'apellidos': u.ape_usu,
            'correo_personal': u.correo_per,
            'celular': u.telefono,
            'rol': u.rol,
            'ultima_sesion': u.last_login,
            'tipo': 'usuario',
            'objeto': u
        })
    for a in aprendices:
        miembros.append({
            'id': a.cedula_apre,
            'nombres': a.nombre,
            'apellidos': a.apellido,
            'correo_personal': a.correo_per,
            'celular': a.telefono,
            'rol': 'Aprendiz',
            'ultima_sesion': None,
            'tipo': 'aprendiz',
            'objeto': a
        })

    # Totales
    total_instructores = Usuario.objects.filter(rol='Instructor').count()
    total_investigadores = Usuario.objects.filter(rol='Investigador').count()
    total_aprendices = Aprendiz.objects.count()

    # Miembro seleccionado
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
    }

    return render(request, 'paginas/miembros.html', contexto)

# VISTAS DE CENTRO DE AYUDA
def centroayuda(request):
    return render(request, 'paginas/centroayuda.html',
    {'current_page': 'centroayuda'})

# VISTAS DE REPORTES
def reportes(request):
    return render(request, 'paginas/reportes.html',
    {'current_page': 'reportes'})

# VISTA DE LOGOUT
def logout(request):
    # Clear all session data
    request.session.flush()
    messages.success(request, "Has cerrado sesión correctamente")
    return redirect('iniciarsesion')
