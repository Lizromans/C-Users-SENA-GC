// Función para hacer que los mensajes de alerta desaparezcan
function setupAutoHideAlerts(duration = 1800) {
  // Selecciona todos los elementos con las clases de alerta
  const alerts = document.querySelectorAll('.alert-info, .alert-danger, .alert-success');
  
  // Para cada alerta, configura un temporizador para ocultarla
  alerts.forEach(alert => {
    // Primero asegúrate que la posición sea relativa para los efectos
    alert.style.position = 'relative';
    
    // Agrega transición para un efecto suave
    alert.style.transition = 'opacity 0.5s ease-in-out';
    
    // Configura el temporizador para ocultar la alerta después del tiempo especificado
    setTimeout(() => {
      // Reduce la opacidad primero
      alert.style.opacity = '0';
      
      // Después de que termine la transición, oculta completamente el elemento
      setTimeout(() => {
        alert.style.display = 'none';
      }, 500);
    }, duration);
  });
}

// Ejecutar la función cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
  // Llamar a la función con 2000ms (2 segundos) como duración predeterminada
  setupAutoHideAlerts(2000);
  
  // Para alertas nuevas que puedan ser agregadas dinámicamente
  // Define un observador de mutaciones
  const observer = new MutationObserver(mutations => {
    mutations.forEach(mutation => {
      if (mutation.addedNodes && mutation.addedNodes.length > 0) {
        // Comprueba si alguno de los nodos agregados es una alerta
        mutation.addedNodes.forEach(node => {
          if (node.nodeType === 1 && // Es un elemento
              (node.classList.contains('alert-info') || 
               node.classList.contains('alert-danger') || 
               node.classList.contains('alert-success'))) {
            // Configura el ocultamiento automático para esta nueva alerta
            setupAutoHideAlerts.call([node], 2000);
          }
        });
      }
    });
  });
  
  // Configurar y comenzar la observación del documento
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
});