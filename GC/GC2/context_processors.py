def current_page_name(request):
    path = request.path

    mapping = {
        '/': 'Inicio',
        '/home/': 'Inicio',
        '/perfil/': 'Mi Perfil',
        '/semilleros/': 'Semilleros',
        '/miembros/': 'Miembros',
        '/proyectos/': 'Proyectos',
        '/centroayuda/': 'Centro de Ayuda',
        '/reportes/': 'Reportes',
    }

    nombre = mapping.get(path, 'Dashboard')
    return {'current_page_name': nombre}

