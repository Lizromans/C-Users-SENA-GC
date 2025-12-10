// 🔥 EJECUTAR INMEDIATAMENTE - Antes del DOMContentLoaded
(function() {
  const savedState = localStorage.getItem('sidebarState');
  
  if (savedState === 'collapsed') {
    // Agregar clases inmediatamente al HTML
    document.documentElement.classList.add('sidebar-collapsed');
  }
})();

// Luego cargar el resto normalmente
document.addEventListener('DOMContentLoaded', () => { 
  const sidebar   = document.querySelector('.sidebar');
  const toggleBtn = document.querySelector('.btn-open');

  // 1️⃣ Aplicar el estado guardado
  const savedState = localStorage.getItem('sidebarState');

  if (savedState === 'collapsed') {
    sidebar.classList.add('collapsed');
    document.body.classList.add('sidebar-collapsed');
  } else {
    sidebar.classList.remove('collapsed');
    document.body.classList.remove('sidebar-collapsed');
    document.documentElement.classList.remove('sidebar-collapsed');
  }

  // 2️⃣ Evitar que los clics en enlaces del sidebar activen el toggle
  document.querySelectorAll('.sidebar a, .sidebar button:not(.btn-open)').forEach(item => {
    item.addEventListener('click', (e) => {
      e.stopPropagation();
    });
  });

  // 3️⃣ Solo el botón toggle debe abrir/cerrar
  toggleBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    e.preventDefault();

    const isCollapsed = sidebar.classList.contains('collapsed');
    
    sidebar.classList.toggle('collapsed');
    document.body.classList.toggle('sidebar-collapsed');
    document.documentElement.classList.toggle('sidebar-collapsed');

    // Guardar estado
    localStorage.setItem(
      'sidebarState',
      sidebar.classList.contains('collapsed') ? 'collapsed' : 'expanded'
    );
  });

  // 4️⃣ Prevenir propagación en el sidebar
  sidebar.addEventListener('click', (e) => {
    if (e.target !== toggleBtn && !toggleBtn.contains(e.target)) {
      e.stopPropagation();
    }
  });
});