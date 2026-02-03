from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from django.db import connection
from .models import Usuario


@receiver(pre_save, sender=Usuario)
def guardar_rol_anterior(sender, instance, **kwargs):
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
    rol_cambio = created or (
        hasattr(instance, '_rol_anterior') and 
        instance._rol_anterior != instance.rol
    )
    
    if not rol_cambio:
        return  

    if not instance.rol:
        return

    rol_normalizado = (
        instance.rol.lower()
        .strip()
        .replace('í', 'i')
        .replace('ó', 'o')
        .replace('é', 'e')
        .replace('á', 'a')
    )

    mapa_roles = {
        'dinamizador': 'Dinamizador',
        'coordinador semillero': 'Coordinador semillero',
        'lider de semillero': 'Lider semillero',
        'lider de proyecto': 'Lider proyecto',
        'instructor': 'Instructor',
        'investigador': 'Instructor'
    }

    nombre_grupo = mapa_roles.get(rol_normalizado)
    if not nombre_grupo:
        return

    try:
        grupo = Group.objects.get(name=nombre_grupo)
        group_id = grupo.id

        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM usuario_grupos WHERE cedula = %s", [instance.cedula])
            existente = cursor.fetchone()

            if existente:
                cursor.execute(
                    "UPDATE usuario_grupos SET group_id = %s WHERE cedula = %s",
                    [group_id, instance.cedula]
                )
            else:
                cursor.execute(
                    "INSERT INTO usuario_grupos (cedula, group_id) VALUES (%s, %s)",
                    [instance.cedula, group_id]
                )

    except Group.DoesNotExist:
        print(f"⚠️ El grupo '{nombre_grupo}' no existe en la tabla 'auth_group'.")
    except Exception as e:
        print(f"❌ Error al asignar grupo: {e}")