def navigation_context(request):
    """
    Context processor que añade automáticamente la sección activa
    """
    # Obtener el nombre de la URL actual
    url_name = request.resolver_match.url_name if request.resolver_match else None
    
    return {
        'current_url_name': url_name,
        'seccion_activa': url_name,  # Para usar en templates
    }
