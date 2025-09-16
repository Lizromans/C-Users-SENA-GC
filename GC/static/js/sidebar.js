document.addEventListener('DOMContentLoaded', () => {
  const sidebar   = document.querySelector('.sidebar');
  const toggleBtn = document.querySelector('.btn-open');

  // Arranca abierto
  sidebar.classList.remove('collapsed');
  document.body.classList.remove('sidebar-collapsed');

  toggleBtn.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
    document.body.classList.toggle('sidebar-collapsed');
  });
});