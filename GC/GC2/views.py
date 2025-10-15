from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from .forms import UsuarioRegistroForm
from .models import Usuario, Semillero
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
from .models import Semillero, Usuario, SemilleroUsuario, Aprendiz


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

def iniciarsesion(request):
    error_user = None
    error_password = None
    error_rol = None

    if request.method == 'POST':
        cedula = request.POST.get('cedula')
        contraseña = request.POST.get('password')
        rol = request.POST.get('rol')

        # Validaciones básicas
        if not rol:
            error_rol = "Debe seleccionar un rol."
        
        if not cedula:
            error_user = 'La cédula es obligatoria'
        
        if not contraseña:
            error_password = 'La contraseña es obligatoria'

        # Si hay errores de validación, mostrar formulario nuevamente
        if error_user or error_password or error_rol:
            return render(request, 'paginas/registro.html', {
                'error_user': error_user,
                'error_password': error_password,
                'error_rol': error_rol,
                'cedula': cedula,
                'rol': rol,
                'show_login': True,
                'current_page_name': 'Iniciar Sesión'
            })

        # Intentar autenticar
        try:
            usuario = Usuario.objects.get(cedula=cedula, rol=rol)
            
            # Verificar contraseña
            if check_password(contraseña, usuario.contraseña):
                # VERIFICAR SI EL EMAIL ESTÁ VERIFICADO
                if not usuario.email_verificado:
                    error_user = 'Debes verificar tu correo electrónico antes de iniciar sesión. Revisa tu bandeja de entrada.'
                    return render(request, 'paginas/registro.html', {
                        'error_user': error_user,
                        'cedula': cedula,
                        'rol': rol,
                        'show_login': True,
                        'current_page_name': 'Iniciar Sesión'
                    })
                
                # AUTENTICACIÓN EXITOSA
                request.session['cedula'] = usuario.cedula
                request.session['nom_usu'] = usuario.nom_usu
                request.session['ape_usu'] = usuario.ape_usu
                request.session['rol'] = usuario.rol
                return redirect('home')
            else:
                # Contraseña incorrecta
                error_password = 'Contraseña incorrecta'
        
        except Usuario.DoesNotExist:
            # Usuario no encontrado
            error_user = 'Usuario no encontrado con ese rol y cédula'

        # Si llegamos aquí, hubo un error de autenticación
        return render(request, 'paginas/registro.html', {
            'error_user': error_user,
            'error_password': error_password,
            'cedula': cedula,
            'rol': rol,
            'show_login': True,
            'current_page_name': 'Iniciar Sesión'
        })
    
    # GET request - mostrar formulario de login
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
    return render(request, 'paginas/home.html')

# VISTAS PERFIL
def perfil(request):
    return render(request, 'paginas/perfil.html')

# VISTAS SEMILLEROS
def semilleros(request):
    semilleros = Semillero.objects.all()

    return render(request, 'paginas/semilleros.html', 
    {'semilleros': semilleros
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
    semillero = Semillero.objects.get(id_sem=id_sem)
    
    # Convertir los objetivos a lista
    objetivos_lista = []
    if semillero.objetivo:  
        objetivos_lista = semillero.objetivo.split('\n')
        objetivos_lista = [obj.strip() for obj in objetivos_lista if obj.strip()]
    
    return render(request, 'paginas/resumen.html', {
        'current_page': 'resumen',
        'semillero': semillero,
        'objetivos_lista': objetivos_lista
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

    # Verificar si hay instructores y aprendices
    tiene_instructores = any(u.rol.lower() == 'instructor' for u in usuarios)

    context = {
        'current_page': 'resu_miembros',
        'semillero': semillero,
        'usuarios': usuarios,
        'aprendices': aprendices,
        'Usuarios': usuarios_disponibles,
        'total_miembros': total_miembros,
        'tiene_instructores': tiene_instructores,
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

def detalle_semillero(request, id_sem):
    semillero = get_object_or_404(Semillero, id_sem=id_sem)

    # Obtener todos los miembros del semillero
    miembros = SemilleroUsuario.objects.filter(id_sem=semillero)
    
    # Filtrar solo instructores e investigadores activos QUE YA ESTÁN EN EL SEMILLERO
    instructores = miembros.filter(
        cedula__rol__in=['Instructor', 'Investigador'],
        cedula__estado=True
    ).select_related('cedula')

    context = {
        'semillero': semillero,
        'instructores': instructores,
        'miembros': miembros,
    }
    return render(request, 'paginas/resu-miembros.html', context)


def asignar_lider_semillero(request, id_semillero):
    semillero = get_object_or_404(Semillero, id_sem=id_semillero)
    
    if request.method == 'POST':
        lider_cedula = request.POST.get('lider_semillero')
        
        if lider_cedula:
            try:
                # Buscar el instructor
                instructor = Usuario.objects.get(cedula=lider_cedula)
                
                # Verificar que el instructor esté en el semillero
                miembro_semillero = SemilleroUsuario.objects.filter(
                    id_sem=semillero,
                    cedula=instructor
                ).exists()
                
                if not miembro_semillero:
                    messages.error(request, 'El instructor seleccionado no pertenece a este semillero.')
                    return redirect('resu-miembros', id_semillero)
                
                # Asignar líder (ajusta según tu modelo)
                # Opción 1: Si tienes campo lider en Semillero
                semillero.lider = instructor
                semillero.save()
                
                # Opción 2: Si el líder se marca en SemilleroUsuario
                # SemilleroUsuario.objects.filter(id_sem=semillero, es_lider=True).update(es_lider=False)
                # SemilleroUsuario.objects.filter(id_sem=semillero, cedula=instructor).update(es_lider=True)
                
                messages.success(request, f'Líder {instructor.nom_usu} {instructor.ape_usu} asignado correctamente.')
                
            except Usuario.DoesNotExist:
                messages.error(request, 'El instructor seleccionado no existe.')
            except Exception as e:
                messages.error(request, f'Error al asignar líder: {str(e)}')
        else:
            messages.warning(request, 'No se seleccionó ningún instructor.')
        
        return redirect('resu-miembros', id_semillero)
    
    # Si no es POST, redirigir
    return redirect('resu-miembros', id_semillero)


def resu_proyectos(request):
    return render(request, 'paginas/resu-proyectos.html', 
    {'current_page': 'resu_proyectos'})

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
