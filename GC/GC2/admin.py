from django.contrib import admin
from .models import Usuario, UsuarioGrupos

class UsuarioGruposInline(admin.TabularInline):
    model = UsuarioGrupos
    extra = 1

class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("cedula", "nom_usu", "ape_usu", "correo_per", "rol", "password")
    inlines = [UsuarioGruposInline] 

admin.site.register(Usuario, UsuarioAdmin)