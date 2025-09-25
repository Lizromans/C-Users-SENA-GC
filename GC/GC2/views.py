from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.

from django import template
from django.urls import reverse, resolve
from django.urls.exceptions import Resolver404

register = template.Library()

@register.simple_tag(takes_context=True)
def active_nav(context, url_name):
    """
    Retorna 'active' si la URL actual coincide con la URL proporcionada
    Uso: {% active_nav 'app_name:url_name' %}
    """
    request = context['request']
    try:
        # Obtener el nombre de la URL actual
        current_url_name = resolve(request.path_info).url_name
        current_namespace = resolve(request.path_info).namespace
        
        # Construir el nombre completo de la URL actual
        if current_namespace:
            current_full_name = f"{current_namespace}:{current_url_name}"
        else:
            current_full_name = current_url_name
            
        # Comparar con la URL proporcionada
        if current_full_name == url_name:
            return 'active'
            
        # También comprobar solo el nombre de la URL sin namespace
        if current_url_name == url_name.split(':')[-1]:
            return 'active'
            
    except (Resolver404, AttributeError):
        pass
    
    return ''

@register.simple_tag(takes_context=True)
def is_active_section(context, section_name):
    """
    Verifica si una sección está activa basándose en el contexto
    Uso: {% is_active_section 'perfil' %}
    """
    seccion_activa = context.get('seccion_activa', '')
    return 'active' if seccion_activa == section_name else ''
def bienvenido(request):
    return render(request, 'paginas/bienvenido.html')

def base(request):
    context = {
        'titulo': 'Dashboard - Inicio',
        'seccion_activa': 'home',
        'usuario': request.user,
    }
    return render(request, 'base.html')

def home(request):
    return render(request, 'paginas/home.html')

def perfil(request):
    return render(request, 'paginas/perfil.html')

def registro(request):
    return render(request, 'paginas/registro.html')