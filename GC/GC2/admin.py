from django.contrib import admin
from .models import Usuario, UsuarioGrupos

# Register your models here.

class UsuarioGruposInline(admin.TabularInline):
    model = UsuarioGrupos
    extra = 1  # Muestra 1 fila vacía para agregar rápido

class UsuarioAdmin(admin.ModelAdmin):
    #DESPLEGAR LOS DATOS DE LA TABLA
    list_display = ("cedula", "nom_usu", "ape_usu", "correo_ins", "rol", "contraseña", "conf_contraseña")
    inlines = [UsuarioGruposInline]  # Aquí vinculamos la tabla intermedia

admin.site.register(Usuario, UsuarioAdmin)