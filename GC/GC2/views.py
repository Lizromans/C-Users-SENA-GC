from django.shortcuts import render

# Create your views here.
def bienvenido(request):
    return render(request, 'paginas/bienvenido.html')