// notificaciones.js
document.addEventListener('DOMContentLoaded', function() {
    const notificationBell = document.getElementById('notification-bell');
    const notificationDropdown = document.getElementById('notification-dropdown');
    const notificationCount = document.getElementById('notification-count');
    const notificationList = document.getElementById('notification-list');
    const closeNotifications = document.getElementById('close-notifications');

    // Cargar notificaciones al iniciar
    cargarNotificaciones();

    // Actualizar cada 2 minutos
    setInterval(cargarNotificaciones, 120000);

    // Toggle dropdown
    notificationBell.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        notificationDropdown.classList.toggle('show');
    });

    // Cerrar dropdown
    closeNotifications.addEventListener('click', function(e) {
        e.stopPropagation();
        notificationDropdown.classList.remove('show');
    });

    // Cerrar al hacer clic fuera
    document.addEventListener('click', function(e) {
        if (!notificationDropdown.contains(e.target) && e.target !== notificationBell) {
            notificationDropdown.classList.remove('show');
        }
    });

    // Función para cargar notificaciones
    function cargarNotificaciones() {
        fetch('/api/notificaciones/')
            .then(response => response.json())
            .then(data => {
                actualizarNotificaciones(data.notificaciones, data.count);
            })
            .catch(error => {
                console.error('Error al cargar notificaciones:', error);
                mostrarError();
            });
    }

    // Actualizar UI con notificaciones
    function actualizarNotificaciones(notificaciones, count) {
        // Actualizar contador
        if (count > 0) {
            notificationCount.textContent = count > 99 ? '99+' : count;
            notificationCount.style.display = 'inline-block';
        } else {
            notificationCount.style.display = 'none';
        }

        // Actualizar lista
        if (notificaciones.length === 0) {
            notificationList.innerHTML = `
                <div class="notification-empty">
                    <i class="fa fa-bell-slash" style="font-size: 32px; margin-bottom: 10px; opacity: 0.3;"></i>
                    <p>No hay notificaciones nuevas</p>
                </div>
            `;
            return;
        }

        notificationList.innerHTML = notificaciones.map(notif => `
            <div class="notification-item" onclick="window.location.href='${notif.url}'">
                <div class="notification-icon-type ${notif.clase_icono}">
                    <i class="fa ${notif.icono}"></i>
                </div>
                <div class="notification-content">
                    <div class="notification-title">${notif.titulo}</div>
                    <div class="notification-message">${notif.mensaje}</div>
                    <div class="notification-time">${notif.tiempo}</div>
                </div>
            </div>
        `).join('');
    }

    // Mostrar error
    function mostrarError() {
        notificationList.innerHTML = `
            <div class="notification-empty">
                <i class="fa fa-exclamation-triangle" style="font-size: 32px; margin-bottom: 10px; color: #dc3545;"></i>
                <p>Error al cargar notificaciones</p>
            </div>
        `;
    }
});