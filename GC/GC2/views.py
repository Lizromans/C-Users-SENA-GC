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