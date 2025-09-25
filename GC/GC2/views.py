from django.shortcuts import render

# Create your views here.
def bienvenido(request):
    return render(request, 'paginas/bienvenido.html')

def base(request):
    return render(request, 'base.html')

def home(request):
    return render(request, 'paginas/home.html')

def registro(request):
    return render(request, 'paginas/registro.html')