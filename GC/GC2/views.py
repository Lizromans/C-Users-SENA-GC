from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from .forms import UsuarioRegistroForm
from .models import Usuario, Semillero,SemilleroUsuario, Aprendiz, Proyecto, UsuarioProyecto, SemilleroProyecto, Entregable
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


# Create your views here.

def bienvenido(request):
    return render(request, 'paginas/bienvenido.html')

# VISTAS DE LOGIN
def registro(request):
    if request.method == 'POST':
        form = UsuarioRegistroForm(request.POST)
        
        if form.is_valid():
            try:
                # Guardar el usuario con las contraseñas hasheadas pero como no verificado
                usuario = form.save(commit=False)
                
                # IMPORTANTE: Hashear ambas contraseñas antes de guardar
                usuario.contraseña = make_password(form.cleaned_data['contraseña'])
                usuario.conf_contraseña = make_password(form.cleaned_data['conf_contraseña'])
                usuario.email_verificado = False
                usuario.save()
                
                # Generar token de verificación y enviar correo
                usuario.generar_token_verificacion()
                usuario.enviar_email_verificacion(request)
                
                messages.success(
                    request, 
                    "¡Registro exitoso! Por favor, verifica tu correo electrónico para activar tu cuenta."
                )
                return redirect('iniciarsesion')
                
            except Exception as e:
                # Si hay error al guardar o enviar el correo, mostrarlo
                messages.error(request, f"Error al registrar usuario: {str(e)}")
        else:
            # El formulario tiene errores de validación, se mostrarán automáticamente
            pass
    else:
        form = UsuarioRegistroForm()
    
    return render(request, 'paginas/registro.html', {
        'form': form,
        'current_page_name': 'registro'
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
        # --- Obtener datos del formulario ---
        cedula = request.POST.get('cedula')
        contraseña = request.POST.get('password')
        rol = request.POST.get('rol')

        # --- Validaciones básicas ---
        errores = {}

        if not rol:
            errores['error_rol'] = "Debe seleccionar un rol."
        if not cedula:
            errores['error_user'] = "La cédula es obligatoria."
        if not contraseña:
            errores['error_password'] = "La contraseña es obligatoria."

        # Si hay errores, regresar al formulario
        if errores:
            return render(request, 'paginas/registro.html', {
                **errores,
                'cedula': cedula,
                'rol': rol,
                'show_login': True,
                'current_page_name': 'Iniciar Sesión'
            })

        # --- Autenticación ---
        try:
            usuario = Usuario.objects.get(cedula=cedula, rol=rol)

            if not check_password(contraseña, usuario.contraseña):
                return render(request, 'paginas/registro.html', {
                    'error_password': 'Contraseña incorrecta',
                    'cedula': cedula,
                    'rol': rol,
                    'show_login': True,
                    'current_page_name': 'Iniciar Sesión'
                })

            # --- Verificar si el correo está verificado ---
            if not usuario.email_verificado:
                return render(request, 'paginas/registro.html', {
                    'error_user': 'Debes verificar tu correo electrónico antes de iniciar sesión. Revisa tu bandeja de entrada.',
                    'cedula': cedula,
                    'rol': rol,
                    'show_login': True,
                    'current_page_name': 'Iniciar Sesión'
                })
            
            

            # --- Inicio de sesión exitoso ---
            request.session['cedula'] = usuario.cedula
            request.session['nom_usu'] = usuario.nom_usu
            request.session['ape_usu'] = usuario.ape_usu
            request.session['rol'] = usuario.rol

            # ✅ Registrar el último acceso
            usuario.last_login = now()
            usuario.save(update_fields=['last_login'])

            return redirect('home')

        except Usuario.DoesNotExist:
            return render(request, 'paginas/registro.html', {
                'error_user': 'Usuario no encontrado con ese rol y cédula.',
                'cedula': cedula,
                'rol': rol,
                'show_login': True,
                'current_page_name': 'Iniciar Sesión'
            })

    # --- Si es GET, mostrar formulario ---
    return render(request, 'paginas/registro.html', {
        'show_login': True,
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
    Vista para mostrar el formulario de restablecimiento de contraseña
    cuando el usuario hace clic en el enlace del correo
    """
    try:
        # Decodificar el uid para obtener el ID del usuario
        uid = force_str(urlsafe_base64_decode(uidb64))
        admin = Usuario.objects.get(pk=uid)
        
        # Verificar que el token sea válido
        if default_token_generator.check_token(admin, token):
            print(f"Token válido para el usuario: {admin.nom_usu}")
            return render(request, 'paginas/reset_password.html', {
                'valid': True,
                'uidb64': uidb64,
                'token': token,
                'current_page_name': 'Restablecer Contraseña'
            })
        else:
            print("Token inválido o expirado")
            messages.error(request, "El enlace de restablecimiento no es válido o ha expirado.")
            return redirect('iniciarsesion')
            
    except Exception as e:
        print(f"Error en reset_password: {e}")
        messages.error(request, f"Error al procesar el enlace de restablecimiento: {e}")
        return redirect('iniciarsesion')
    
def reset_password_confirm(request):
    """
    Vista para procesar el formulario de restablecimiento de contraseña
    """
    if request.method == 'POST':
        uidb64 = request.POST.get('uidb64')
        token = request.POST.get('token')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Validar que ambas contraseñas coincidan
        if password1 != password2:
            return render(request, 'paginas/reset_password.html', {
                'valid': True,
                'uidb64': uidb64,
                'token': token,
                'error': 'Las contraseñas no coinciden',
                'current_page_name': 'Restablecer Contraseña'
            })
        
        try:
            # Decodificar el uid para obtener el ID del usuario
            uid = force_str(urlsafe_base64_decode(uidb64))
            admin = Usuario.objects.get(pk=uid)
            
            # Verificar que el token sea válido
            if default_token_generator.check_token(admin, token):
                # Cambiar la contraseña usando el nombre correcto del campo (contraseña con ñ)
                admin.contraseña = make_password(password1)
                admin.confcontraseña = make_password(password1)  # Actualizar también la confirmación
                admin.save()
                
                messages.success(request, "Tu contraseña ha sido restablecida con éxito. Ahora puedes iniciar sesión.")
                return redirect('iniciarsesion')
            else:
                messages.error(request, "El enlace de restablecimiento no es válido o ha expirado.")
                return redirect('iniciarsesion')
                
        except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
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
            
            if not check_password(contraseña_actual, usuario.contraseña):
                messages.error(request, "La contraseña actual es incorrecta")
                return redirect('privacidad')
            
            if nueva_contraseña != confirmar_contraseña:
                messages.error(request, "Las contraseñas no coinciden")
                return redirect('privacidad')
            
            if len(nueva_contraseña) < 8:
                messages.error(request, "La contraseña debe tener al menos 8 caracteres")
                return redirect('privacidad')
            
            usuario.contraseña = make_password(nueva_contraseña)
            usuario.save()

            messages.success(request, "Contraseña actualizada correctamente")
            return redirect('home')
            
    except Usuario.DoesNotExist:
        messages.error(request, "Usuario no encontrado. Por favor inicie sesión nuevamente")
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
        semillero.total_proyectos = 0  # Ajusta según tu lógica
        semillero.total_entregables = 0  # Ajusta según tu lógica
    
    return render(request, 'paginas/semilleros.html', {
        'semilleros': semilleros,
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

    # Obtener miembros con el campo es_lider ya incluido
    miembros = SemilleroUsuario.objects.filter(
        id_sem=semillero
    ).select_related('cedula')

    # Obtener proyectos del semillero
    proyectos = Proyecto.objects.filter(semilleroproyecto__id_sem=semillero)
    codigos_proyectos = proyectos.values_list('cod_pro', flat=True)

    # Agregar información de líder de proyecto a cada miembro
    # Solo considerando proyectos del semillero actual
    for miembro in miembros:
        # Verificar si este usuario es líder de algún proyecto del semillero
        miembro.es_lider_proyecto = UsuarioProyecto.objects.filter(
            cedula=miembro.cedula,
            cod_pro__in=codigos_proyectos,  # Solo proyectos de este semillero
            es_lider=True
        ).exists()
        
        # Opcional: Obtener nombres de los proyectos que lidera (para mostrar tooltip)
        if miembro.es_lider_proyecto:
            proyectos_liderados = UsuarioProyecto.objects.filter(
                cedula=miembro.cedula,
                cod_pro__in=codigos_proyectos,
                es_lider=True
            ).select_related('cod_pro').values_list('cod_pro__nom_pro', flat=True)
            miembro.proyectos_liderados = list(proyectos_liderados)

    # Verificar si hay instructores
    tiene_instructores = any(
        m.cedula.rol.lower() in ['instructor', 'investigador'] 
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
        'total_entregables': total_entregables
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
            lider = SemilleroUsuario.objects.get(semusu_id=id_relacion, id_sem=semillero)
        except SemilleroUsuario.DoesNotExist:
            messages.error(request, "El usuario seleccionado no pertenece a este semillero.")
            return redirect("resu-miembros", semillero.id_sem)

        # Quitar liderazgo anterior
        SemilleroUsuario.objects.filter(id_sem=semillero, es_lider=True).update(es_lider=False)

        # Asignar nuevo líder
        lider.es_lider = True
        lider.save()

        messages.success(request, f"{lider.cedula.nom_usu} ha sido asignado como líder del semillero.")
        return redirect("resu-miembros", semillero.id_sem)

def asignar_lider_proyecto(request, id_sem):
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

            # Paso 1: Quitar liderazgo anterior del proyecto
            UsuarioProyecto.objects.filter(
                cod_pro=proyecto,
                es_lider=True
            ).update(es_lider=False)

            # Paso 2: Buscar si ya existe la relación usuario-proyecto
            try:
                relacion = UsuarioProyecto.objects.get(
                    cedula=instructor,
                    cod_pro=proyecto
                )
                # Si existe, actualizar el liderazgo
                relacion.es_lider = True
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

def resu_proyectos(request, id_sem):
    semillero = get_object_or_404(Semillero, id_sem=id_sem)
    
    # Obtener todos los proyectos asociados al semillero
    proyectos = semillero.proyectos.all()
    
    # Filtrar por tipo
    proyectos_sennova = list(proyectos.filter(tipo__iexact="sennova"))
    proyectos_capacidad = list(proyectos.filter(tipo__iexact="capacidadinstalada"))
    proyectos_formativos = list(proyectos.filter(tipo__iexact="Formativo"))
    
    # Convertir las líneas de texto a listas para cada tipo de proyecto
    for proyecto in proyectos_sennova + proyectos_capacidad + proyectos_formativos:
        proyecto.lineas_tec_lista = [l.strip() for l in proyecto.linea_tec.split('\n') if l.strip()] if proyecto.linea_tec else []
        proyecto.lineas_inv_lista = [l.strip() for l in proyecto.linea_inv.split('\n') if l.strip()] if proyecto.linea_inv else []
        proyecto.lineas_sem_lista = [l.strip() for l in proyecto.linea_sem.split('\n') if l.strip()] if proyecto.linea_sem else []
    
    # Proyectos del semillero
    proyectos = SemilleroProyecto.objects.filter(id_sem=semillero)
    total_proyectos = proyectos.count()

    # Usuarios vinculados al semillero
    usuarios = SemilleroUsuario.objects.filter(id_sem=semillero)

    # Aprendices asociados al semillero
    aprendices = Aprendiz.objects.filter(id_sem=semillero)

    # Total de miembros (usuarios + aprendices)
    total_miembros = usuarios.count() + aprendices.count()

    # Obtener los miembros con el campo es_lider
    miembros = usuarios.select_related('cedula')

    # Entregables asociados a esos proyectos
    total_entregables = Entregable.objects.filter(
        cod_pro__in=proyectos.values('cod_pro')
    ).count()
    
    # Obtener miembros del semillero para el modal de crear proyecto
    usuarios_semillero = SemilleroUsuario.objects.filter(
        id_sem=semillero
    ).select_related('cedula')
    
    aprendices_semillero = Aprendiz.objects.filter(id_sem=semillero)
    
    # Combinar miembros
    miembros_semillero = []
    
    for u in usuarios_semillero:
        miembros_semillero.append({
            'cedula': u.cedula.cedula,
            'nombre_completo': f"{u.cedula.nom_usu} {u.cedula.ape_usu}",
            'iniciales': u.cedula.get_iniciales,
            'tipo': 'Usuario',
            'rol': u.cedula.rol
        })
    
    for a in aprendices_semillero:
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
        'miembros_semillero': miembros_semillero
    }
    
    return render(request, 'paginas/resu-proyectos.html', context)

def crear_proyecto(request, id_sem):
    semillero = get_object_or_404(Semillero, id_sem=id_sem)

    # Obtener los usuarios (instructores/investigadores) del semillero
    usuarios_semillero = SemilleroUsuario.objects.filter(
        id_sem=semillero  # ✅ se usa el objeto, no el id
    ).select_related('cedula')

    # Obtener los aprendices del semillero
    aprendices_semillero = Aprendiz.objects.filter(id_sem=semillero)

    # Combinar miembros (usuarios + aprendices)
    miembros_semillero = []

    # Agregar usuarios
    for u in usuarios_semillero:
        miembros_semillero.append({
            'cedula': u.cedula.cedula,
            'nombre_completo': f"{u.cedula.nom_usu} {u.cedula.ape_usu}",
            'iniciales': u.cedula.get_iniciales,
            'tipo': 'Usuario',
            'rol': u.cedula.rol
        })
    
    # Agregar aprendices
    for a in aprendices_semillero:
        miembros_semillero.append({
            'cedula': a.cedula_apre,
            'nombre_completo': f"{a.nombre} {a.apellido}",
            'iniciales': a.get_iniciales,
            'tipo': 'Aprendiz',
            'rol': 'Aprendiz'
        })

    if request.method == 'POST':
        try:
            # Verificar usuario autenticado
            cedula_usuario = request.session.get('cedula')
            if not cedula_usuario:
                messages.error(request, 'Debes iniciar sesión para crear un proyecto.')
                return redirect('iniciarsesion')

            usuario_actual = Usuario.objects.get(cedula=cedula_usuario)

            # Capturar datos del formulario
            nom_pro = request.POST.get('nom_pro', '').strip()
            tipo = request.POST.get('tipo', '').strip()
            desc_pro = request.POST.get('desc_pro', '').strip()
            lineas_tec = request.POST.getlist('lineastec[]')
            lineas_inv = request.POST.getlist('lineasinv[]')
            lineas_sem = request.POST.getlist('lineassem[]')
            miembros_seleccionados = request.POST.getlist('miembros_proyecto[]')

            # Validar campos requeridos
            if not all([nom_pro, tipo, desc_pro]):
                messages.error(request, 'Todos los campos son obligatorios.')
                return redirect('resu-proyectos', id_sem=id_sem)

            # Generar nuevo código de proyecto
            ultimo_proyecto = Proyecto.objects.order_by('-cod_pro').first()
            nuevo_cod_pro = ultimo_proyecto.cod_pro + 1 if ultimo_proyecto else 1

            # Crear el proyecto
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
            SemilleroProyecto.objects.create(
                id_sem=semillero,
                cod_pro=proyecto
            )

            # Asociar usuario creador al proyecto
            UsuarioProyecto.objects.create(
                cedula=usuario_actual,
                cod_pro=proyecto
            )

            # Asociar miembros seleccionados
            miembros_agregados = 0
            for cedula in miembros_seleccionados:
                if str(cedula) != str(cedula_usuario):
                    try:
                        usuario = Usuario.objects.get(cedula=cedula)
                        if not UsuarioProyecto.objects.filter(cedula=usuario, cod_pro=proyecto).exists():
                            UsuarioProyecto.objects.create(cedula=usuario, cod_pro=proyecto)
                            miembros_agregados += 1
                    except Usuario.DoesNotExist:
                        try:
                            aprendiz = Aprendiz.objects.get(cedula_apre=cedula)
                            # Aquí podrías crear la relación AprendizProyecto si existe el modelo
                            # AprendizProyecto.objects.create(cedula=aprendiz, cod_pro=proyecto)
                            pass
                        except Aprendiz.DoesNotExist:
                            pass

            # Crear entregables con descripciones predeterminadas
            entregables_default = [
                {
                    "nombre": "Formalización de Proyecto",
                    "descripcion": "Documento que establece el marco formal del proyecto, incluyendo título, justificación, alcance, participantes y recursos necesarios."
                },
                {
                    "nombre": "Diagnóstico",
                    "descripcion": "Análisis de la situación actual, identificación de problemáticas, necesidades y oportunidades del contexto donde se desarrollará el proyecto."
                },
                {
                    "nombre": "Planeación",
                    "descripcion": "Planificación detallada con cronograma, actividades, metodología, recursos, responsables y estrategias para el desarrollo del proyecto."
                },
                {
                    "nombre": "Ejecución",
                    "descripcion": "Informe de implementación del proyecto, evidencias de actividades realizadas, resultados obtenidos y ajustes aplicados durante el proceso."
                },
                {
                    "nombre": "Evaluación",
                    "descripcion": "Análisis del cumplimiento de objetivos, medición de impacto, identificación de logros, dificultades y lecciones aprendidas del proyecto."
                },
                {
                    "nombre": "Conclusiones",
                    "descripcion": "Reflexiones finales, recomendaciones para futuros proyectos, aportes al conocimiento y perspectivas de continuidad o réplica del proyecto."
                }
            ]

            ultimo_entregable = Entregable.objects.order_by('-cod_entre').first()
            base_cod = ultimo_entregable.cod_entre if ultimo_entregable else 0

            for i, entregable_data in enumerate(entregables_default, start=1):
                fecha_inicio = request.POST.get(f'fecha_inicio_{i}')
                fecha_fin = request.POST.get(f'fecha_fin_{i}')
                
                # 🔹 Se eliminó el messages.error aquí para evitar el SyntaxError

                Entregable.objects.create(
                    cod_entre=base_cod + i,
                    nom_entre=entregable_data["nombre"],
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    desc_entre=entregable_data["descripcion"],
                    estado="Pendiente",
                    archivo="",
                    cod_pro=proyecto
                )

            messages.success(
                request,
                f'Proyecto "{nom_pro}" creado correctamente con {miembros_agregados} miembro(s) asignado(s).'
            )
            return redirect('resu-proyectos', id_sem=id_sem)

        except Exception as e:
            messages.error(request, f'Error al crear proyecto: {str(e)}')
            return redirect('resu-proyectos', id_sem=id_sem)

    return render(request, 'crear_proyecto.html', {
        'semillero': semillero,
        'miembros_semillero': miembros_semillero
    })


def recursos(request):
    return render(request, 'paginas/recursos.html', 
    {'current_page': 'recursos'})

# VISTAS DE PROYECTOS
def proyectos(request):
    return render(request, 'paginas/proyectos.html', 
    {'current_page': 'proyectos'})

# VISTAS DE MIEMBROS
def miembros(request):
    return render(request, 'paginas/miembros.html',
    {'current_page': 'miembros'})

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
