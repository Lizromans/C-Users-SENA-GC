from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from django.db import connection
from .models import Usuario


@receiver(pre_save, sender=Usuario)
def guardar_rol_anterior(sender, instance, **kwargs):
    """
    Guarda el rol anterior antes de actualizar el usuario.
    """
    if instance.pk:  # Si el usuario ya existe
        try:
            usuario_anterior = Usuario.objects.get(pk=instance.pk)
            instance._rol_anterior = usuario_anterior.rol
        except Usuario.DoesNotExist:
            instance._rol_anterior = None
    else:
        instance._rol_anterior = None


@receiver(post_save, sender=Usuario)
def asignar_grupo_por_rol(sender, instance, created, **kwargs):
    """
    Inserta o actualiza el grupo del usuario en la tabla 'usuario_grupos'
    según el campo 'rol' del modelo Usuario.
    Se ejecuta tanto en creación como en actualización del rol.
    """
    
    # Verificar si el rol cambió o si es un nuevo usuario
    rol_cambio = created or (
        hasattr(instance, '_rol_anterior') and 
        instance._rol_anterior != instance.rol
    )
    
    if not rol_cambio:
        return  # No hacer nada si el rol no cambió

    if not instance.rol:
        print(f"⚠️ Usuario {instance.nom_usu} sin rol definido.")
        return

    # Normalizamos el texto del rol
    rol_normalizado = (
        instance.rol.lower()
        .strip()
        .replace('í', 'i')
        .replace('ó', 'o')
        .replace('é', 'e')
        .replace('á', 'a')
    )

    # Diccionario de equivalencias rol → nombre del grupo
    mapa_roles = {
        'dinamizador': 'Dinamizador',
        'lider de semilleros': 'Lider de semilleros',
        'lider de semillero': 'Lider semillero',
        'lider de proyecto': 'Lider proyecto',
        'instructor': 'Instructor',
        'investigador': 'Instructor'
    }

    nombre_grupo = mapa_roles.get(rol_normalizado)
    if not nombre_grupo:
        print(f"⚠️ No existe grupo configurado para el rol '{rol_normalizado}'.")
        return

    try:
        # Buscar el ID del grupo según el nombre
        grupo = Group.objects.get(name=nombre_grupo)
        group_id = grupo.id

        # Conexión directa a la base de datos
        with connection.cursor() as cursor:
            # Verificar si ya existe una fila para la cédula
            cursor.execute("SELECT id FROM usuario_grupos WHERE cedula = %s", [instance.cedula])
            existente = cursor.fetchone()

            if existente:
                # Actualizar el group_id existente
                cursor.execute(
                    "UPDATE usuario_grupos SET group_id = %s WHERE cedula = %s",
                    [group_id, instance.cedula]
                )
                accion = "actualizado" if not created else "asignado"
                print(f"🔄 Grupo '{nombre_grupo}' {accion} para {instance.nom_usu}.")
            else:
                # Insertar nuevo registro
                cursor.execute(
                    "INSERT INTO usuario_grupos (cedula, group_id) VALUES (%s, %s)",
                    [instance.cedula, group_id]
                )
                print(f"✅ Grupo '{nombre_grupo}' asignado a {instance.nom_usu}.")

    except Group.DoesNotExist:
        print(f"⚠️ El grupo '{nombre_grupo}' no existe en la tabla 'auth_group'.")
    except Exception as e:
        print(f"❌ Error al asignar grupo: {e}")