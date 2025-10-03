from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.

def bienvenido(request):
    return render(request, 'paginas/bienvenido.html')

def base(request):
    return render(request, 'base.html')

def home(request):
    return render(request, 'paginas/home.html')

def perfil(request):
    return render(request, 'paginas/perfil.html')

def registro(request):
    return render(request, 'paginas/registro.html')

def semilleros(request):
    return render(request, 'paginas/semilleros.html')

def base2(request):
    return render(request, 'base2.html')

def resumen(request):
    return render(request, 'paginas/resumen.html', 
    {'current_page': 'resumen'})


def resu_miembros(request):
    return render(request, 'paginas/resu-miembros.html', 
    {'current_page': 'resu_miembros'})

def resu_proyectos(request):
    return render(request, 'paginas/resu-proyectos.html', 
    {'current_page': 'resu_proyectos'})

def recursos(request):
    return render(request, 'paginas/recursos.html', 
    {'current_page': 'recursos'})

def proyectos(request):
    return render(request, 'paginas/proyectos.html', 
    {'current_page': 'proyectos'})

def miembros(request):
    return render(request, 'paginas/miembros.html',
    {'current_page': 'miembros'})

