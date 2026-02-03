(function() {
  const savedState = localStorage.getItem('sidebarState');
  
  if (savedState === 'collapsed') {
    document.documentElement.classList.add('sidebar-collapsed');
  }
})();

document.addEventListener('DOMContentLoaded', () => { 
  const sidebar   = document.querySelector('.sidebar');
  const toggleBtn = document.querySelector('.btn-open');

  const savedState = localStorage.getItem('sidebarState');

  if (savedState === 'collapsed') {
    sidebar.classList.add('collapsed');
    document.body.classList.add('sidebar-collapsed');
  } else {
    sidebar.classList.remove('collapsed');
    document.body.classList.remove('sidebar-collapsed');
    document.documentElement.classList.remove('sidebar-collapsed');
  }

  document.querySelectorAll('.sidebar a, .sidebar button:not(.btn-open)').forEach(item => {
    item.addEventListener('click', (e) => {
      e.stopPropagation();
    });
  });

  toggleBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    e.preventDefault();

    const isCollapsed = sidebar.classList.contains('collapsed');
    
    sidebar.classList.toggle('collapsed');
    document.body.classList.toggle('sidebar-collapsed');
    document.documentElement.classList.toggle('sidebar-collapsed');

    localStorage.setItem(
      'sidebarState',
      sidebar.classList.contains('collapsed') ? 'collapsed' : 'expanded'
    );
  });

  sidebar.addEventListener('click', (e) => {
    if (e.target !== toggleBtn && !toggleBtn.contains(e.target)) {
      e.stopPropagation();
    }
  });
});