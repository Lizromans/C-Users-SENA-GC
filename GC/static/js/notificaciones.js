class NotificationSystem {
    constructor() {
        this.storageKey   = 'notifications_state';
        this.dismissedKey = 'dismissed_notifications';
        this.state        = this.loadState();
        this.dismissedNotifications = this.loadDismissed(); // ✅ ahora es {} con TTL
        this.notifications          = [];
        this.filteredNotifications  = [];
        this.currentFilter          = 'all';

        console.log('✅ NotificationSystem inicializado');
    }

    init() {
        this.setupEventListeners();
        this.loadNotifications();
        setInterval(() => this.loadNotifications(), 120000);
        console.log('✅ Sistema de notificaciones activo');
    }

    // =========================================================================
    // ESTADO (leídas)
    // =========================================================================
    loadState() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            return saved ? JSON.parse(saved) : {};
        } catch {
            return {};
        }
    }

    saveState() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.state));
        } catch (e) {
            console.error('Error guardando estado:', e);
        }
    }

    isRead(notificationId) {
        return this.state[notificationId] === true;
    }

    markAsRead(notificationId) {
        this.state[notificationId] = true;
        this.saveState();
        this.updateUI();
    }

    // =========================================================================
    // DISMISS CON TTL  ← FIX PRINCIPAL
    // Antes: array permanente → las notificaciones nunca volvían
    // Ahora: objeto { id: timestampExpira } con TTL de 24h
    // =========================================================================
    loadDismissed() {
        try {
            const raw = localStorage.getItem(this.dismissedKey);
            if (!raw) return {};

            const parsed = JSON.parse(raw);

            // ✅ Migración automática: si era array antiguo → borrarlo
            if (Array.isArray(parsed)) {
                localStorage.removeItem(this.dismissedKey);
                console.log('🧹 Dismissed antiguo (array permanente) limpiado');
                return {};
            }

            // Eliminar entradas ya expiradas
            const now   = Date.now();
            const clean = {};
            for (const [id, expira] of Object.entries(parsed)) {
                if (expira > now) clean[id] = expira;
            }
            return clean;
        } catch {
            localStorage.removeItem(this.dismissedKey);
            return {};
        }
    }

    saveDismissed() {
        try {
            localStorage.setItem(this.dismissedKey, JSON.stringify(this.dismissedNotifications));
        } catch (e) {
            console.error('Error guardando dismissed:', e);
        }
    }

    // ✅ Comprueba expiración en vez de .includes()
    isDismissed(notificationId) {
        const expira = this.dismissedNotifications[notificationId];
        if (!expira) return false;
        if (Date.now() > expira) {
            delete this.dismissedNotifications[notificationId];
            return false;
        }
        return true;
    }

    // ✅ Guarda con TTL en vez de push al array
    dismissNotification(notificationId, horasTTL = 24) {
        this.dismissedNotifications[notificationId] = Date.now() + horasTTL * 3600 * 1000;
        this.saveDismissed();
    }

    // =========================================================================
    // ID ÚNICO DE NOTIFICACIÓN
    // =========================================================================
    getNotificationId(notification) {
        return `${notification.tipo}_${notification.titulo}_${notification.fecha}`
            .replace(/\s+/g, '_');
    }

    // =========================================================================
    // CARGA DESDE API
    // =========================================================================
    async loadNotifications() {
        try {
            console.log('📡 Cargando notificaciones...');

            const response = await fetch('/api/notificaciones/', {
                method: 'GET',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                credentials: 'same-origin'
            });

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

            const data = await response.json();
            console.log('📥 Datos recibidos:', data);

            if (data.notificaciones && Array.isArray(data.notificaciones)) {
                // ✅ Solo filtra las que tienen dismiss vigente (TTL activo)
                this.notifications = data.notificaciones.filter(notif => {
                    return !this.isDismissed(this.getNotificationId(notif));
                });

                console.log('✅ Notificaciones cargadas:', this.notifications.length);
                this.updateUI();
            }
        } catch (error) {
            console.error('❌ Error cargando notificaciones:', error);
            this.showError();
        }
    }

    // =========================================================================
    // ACTUALIZAR UI
    // =========================================================================
    updateUI() {
        this.updateBadge();
        this.updateDropdown();
        const drawer = document.getElementById('notifications-drawer');
        if (drawer && drawer.classList.contains('show')) {
            this.updateDrawer();
        }
    }

    updateBadge() {
        const badge = document.getElementById('notification-count');
        if (!badge) return;

        const unreadCount = this.notifications.filter(notif =>
            !this.isRead(this.getNotificationId(notif))
        ).length;

        if (unreadCount > 0) {
            badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
            badge.style.display = 'flex';
            badge.classList.toggle('many', unreadCount > 9);
        } else {
            badge.style.display = 'none';
        }
    }

    updateDropdown() {
        const listContainer = document.getElementById('notification-list');
        if (!listContainer) return;

        listContainer.innerHTML = '';

        if (this.notifications.length === 0) {
            listContainer.innerHTML = this.getEmptyState();
            return;
        }

        this.notifications.slice(0, 5).forEach(notif => {
            const id     = this.getNotificationId(notif);
            const isRead = this.isRead(id);
            const { clase, icono } = this.getIconConfig(notif);

            const item = document.createElement('div');
            item.className = `notification-item ${!isRead ? 'unread' : ''}`;
            item.innerHTML = `
                <div class="notification-icon-type ${clase}">
                    <i class="fa ${icono}"></i>
                </div>
                <div class="notification-content">
                    <div class="notification-title">${this.escapeHtml(notif.titulo)}</div>
                    <div class="notification-message">${this.escapeHtml(notif.mensaje)}</div>
                    <div class="notification-time">${this.escapeHtml(notif.tiempo)}</div>
                </div>`;

            item.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleNotificationClick(id, notif.url);
            });

            listContainer.appendChild(item);
        });
    }

    updateDrawer() {
        const drawerBody = document.getElementById('drawer-body');
        if (!drawerBody) return;

        console.log('🎨 Actualizando drawer...');
        this.applyCurrentFilter();
        drawerBody.innerHTML = '';

        if (this.filteredNotifications.length === 0) {
            drawerBody.innerHTML = this.getDrawerEmptyState();
            return;
        }

        const grouped = this.groupByDate(this.filteredNotifications);
        const order   = { 'Hoy': 0, 'Ayer': 1, 'Esta semana': 2, 'Anteriores': 3 };

        Object.keys(grouped)
            .sort((a, b) => order[a] - order[b])
            .forEach(dateLabel => {
                if (grouped[dateLabel].length === 0) return;

                const section = document.createElement('div');
                section.className = 'notification-section';

                const title = document.createElement('div');
                title.className = 'notification-section-title';
                title.textContent = dateLabel;
                section.appendChild(title);

                grouped[dateLabel].forEach(notif => {
                    const id     = this.getNotificationId(notif);
                    const isRead = this.isRead(id);
                    const { clase, icono } = this.getIconConfig(notif);

                    const item = document.createElement('div');
                    item.className = `drawer-notification-item ${!isRead ? 'unread' : ''}`;
                    item.innerHTML = `
                        <div class="notification-icon-type ${clase}">
                            <i class="fa ${icono}"></i>
                        </div>
                        <div class="notification-content">
                            <div class="notification-title">${this.escapeHtml(notif.titulo)}</div>
                            <div class="notification-message">${this.escapeHtml(notif.mensaje)}</div>
                            <div class="notification-time">${this.escapeHtml(notif.tiempo)}</div>
                        </div>`;

                    item.addEventListener('click', (e) => {
                        e.stopPropagation();
                        this.handleNotificationClick(id, notif.url);
                    });

                    section.appendChild(item);
                });

                drawerBody.appendChild(section);
            });

        console.log('✅ Drawer actualizado');
    }

    // =========================================================================
    // FILTROS
    // =========================================================================
    applyCurrentFilter() {
        switch (this.currentFilter) {
            case 'unread':
                this.filteredNotifications = this.notifications.filter(n =>
                    !this.isRead(this.getNotificationId(n))
                );
                break;
            case 'eventos':
                this.filteredNotifications = this.notifications.filter(n =>
                    n.tipo.includes('evento')
                );
                break;
            case 'proyectos':
                this.filteredNotifications = this.notifications.filter(n =>
                    n.tipo.includes('proyecto')
                );
                break;
            case 'entregables':
                this.filteredNotifications = this.notifications.filter(n =>
                    n.tipo.includes('entregable')
                );
                break;
            case 'semilleros':
                this.filteredNotifications = this.notifications.filter(n =>
                    ['semillero', 'miembro', 'lider'].some(k => n.tipo.includes(k))
                );
                break;
            default:
                this.filteredNotifications = [...this.notifications];
        }
        console.log(`🔍 Filtro: ${this.currentFilter} → ${this.filteredNotifications.length} resultados`);
    }

    applyFilter(filter) {
        this.currentFilter = filter;
        console.log('🔍 Cambiando filtro a:', filter);
        this.updateDrawer();
    }

    // =========================================================================
    // AGRUPAR POR FECHA
    // =========================================================================
    groupByDate(notifications) {
        const today     = new Date(); today.setHours(0, 0, 0, 0);
        const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1);
        const weekAgo   = new Date(today); weekAgo.setDate(weekAgo.getDate() - 7);
        const grouped   = { 'Hoy': [], 'Ayer': [], 'Esta semana': [], 'Anteriores': [] };

        notifications.forEach(notif => {
            try {
                const d = new Date(notif.fecha);
                if (isNaN(d.getTime())) { grouped['Anteriores'].push(notif); return; }
                d.setHours(0, 0, 0, 0);

                if      (d.getTime() === today.getTime())     grouped['Hoy'].push(notif);
                else if (d.getTime() === yesterday.getTime()) grouped['Ayer'].push(notif);
                else if (d >= weekAgo)                        grouped['Esta semana'].push(notif);
                else                                          grouped['Anteriores'].push(notif);
            } catch {
                grouped['Anteriores'].push(notif);
            }
        });

        return grouped;
    }

    // =========================================================================
    // ACCIONES
    // =========================================================================
    handleNotificationClick(notificationId, url) {
        console.log('👆 Click en notificación:', notificationId);
        this.markAsRead(notificationId);
        this.closeDropdown();
        this.closeDrawer();
        if (url && url !== '#') window.location.href = url;
    }

    markAllAsRead() {
        this.notifications.forEach(notif => {
            this.state[this.getNotificationId(notif)] = true;
        });
        this.saveState();
        this.updateUI();
        this.showToast('Todas las notificaciones marcadas como leídas', 'success');
    }

    // ✅ FIX: oculta 24h en vez de borrar permanentemente
    clearAllNotifications() {
        if (!confirm('¿Estás seguro de que deseas limpiar todas las notificaciones?')) return;

        this.notifications.forEach(notif => {
            this.dismissNotification(this.getNotificationId(notif), 24);
        });

        this.state = {};
        localStorage.removeItem(this.storageKey);
        this.notifications          = [];
        this.filteredNotifications  = [];
        this.updateUI();
        this.closeDrawer();

        this.showToast('Notificaciones ocultadas por 24 horas', 'success');
    }

    // =========================================================================
    // DROPDOWN / DRAWER
    // =========================================================================
    toggleDropdown() {
        document.getElementById('notification-dropdown')?.classList.toggle('show');
    }

    closeDropdown() {
        document.getElementById('notification-dropdown')?.classList.remove('show');
    }

    openDrawer() {
        const drawer  = document.getElementById('notifications-drawer');
        const overlay = document.getElementById('notifications-drawer-overlay');
        if (drawer && overlay) {
            drawer.classList.add('show');
            overlay.classList.add('show');
            document.body.style.overflow = 'hidden';
            this.updateDrawer();
        }
    }

    closeDrawer() {
        const drawer  = document.getElementById('notifications-drawer');
        const overlay = document.getElementById('notifications-drawer-overlay');
        if (drawer && overlay) {
            drawer.classList.remove('show');
            overlay.classList.remove('show');
            document.body.style.overflow = '';
        }
    }

    // =========================================================================
    // EVENT LISTENERS
    // =========================================================================
    setupEventListeners() {
        document.getElementById('notification-bell')?.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            this.toggleDropdown();
        });

        document.getElementById('close-notifications')?.addEventListener('click', (e) => {
            e.stopPropagation();
            e.stopImmediatePropagation();
            this.closeDropdown();
        });

        document.getElementById('view-all-notifications')?.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.closeDropdown();
            this.openDrawer();
        });

        document.getElementById('drawer-close-btn')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.closeDrawer();
        });

        document.getElementById('notifications-drawer-overlay')?.addEventListener('click', () => {
            this.closeDrawer();
        });

        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.applyFilter(btn.dataset.filter);
            });
        });

        document.getElementById('mark-all-read')?.addEventListener('click', () => {
            this.markAllAsRead();
        });

        document.getElementById('clear-all-notifications')?.addEventListener('click', () => {
            this.clearAllNotifications();
        });

        document.addEventListener('click', (e) => {
            const dropdown = document.getElementById('notification-dropdown');
            const bell     = document.getElementById('notification-bell');
            if (dropdown && bell &&
                dropdown.classList.contains('show') &&
                !dropdown.contains(e.target) &&
                !bell.contains(e.target)) {
                this.closeDropdown();
            }
        }, false);

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const drawer = document.getElementById('notifications-drawer');
                if (drawer && drawer.classList.contains('show')) this.closeDrawer();
            }
        });

        console.log('✅ Event listeners configurados');
    }

    // =========================================================================
    // ICONOS POR TIPO
    // =========================================================================
    getIconConfig(notif) {
        // Prioridad 1: el backend ya manda clase_icono e icono
        if (notif.clase_icono && notif.icono) {
            return { clase: notif.clase_icono, icono: notif.icono };
        }

        const ref = `${notif.tipo || ''} ${notif.titulo || ''}`.toLowerCase();

        const mapa = [
            // Archivos
            { keys: ['archivo_nuevo', 'nuevo archivo', 'archivo subido'],
              clase: 'notif-archivo',     icono: 'fa-file-circle-plus' },
            { keys: ['archivo eliminado', 'archivo borrado'],
              clase: 'notif-archivo-del', icono: 'fa-file-circle-xmark' },
            { keys: ['archivo'],
              clase: 'notif-archivo',     icono: 'fa-folder-open' },

            // Estado proyecto
            { keys: ['completado', 'terminado', 'cancelado', 'aprobado', 'rechazado'],
              clase: 'notif-estado-proy', icono: 'fa-arrows-rotate' },

            // Aprendices
            { keys: ['aprendiz', 'ficha'],
              clase: 'notif-aprendiz',    icono: 'fa-user-graduate' },

            // Líder / Rol
            { keys: ['líder', 'lider', 'nuevo rol', 'rol asignado'],
              clase: 'notif-lider',       icono: 'fa-crown' },

            // Proyectos
            { keys: ['proyecto_nuevo', 'nuevo proyecto'],
              clase: 'notif-proyecto',    icono: 'fa-diagram-project' },
            { keys: ['proyecto'],
              clase: 'notif-proyecto',    icono: 'fa-chart-gantt' },

            // Miembros
            { keys: ['nuevo miembro', 'miembro agregado', 'se unió', 'miembro_asignado'],
              clase: 'notif-miembro',     icono: 'fa-user-plus' },
            { keys: ['miembro eliminado', 'miembro removido'],
              clase: 'notif-miembro-del', icono: 'fa-user-minus' },
            { keys: ['miembro', 'asignado'],
              clase: 'notif-miembro',     icono: 'fa-users' },

            // Eventos
            { keys: ['evento_proximo', 'evento próximo', 'próximo evento'],
              clase: 'notif-evento-prox', icono: 'fa-calendar-check' },
            { keys: ['evento_nuevo', 'nuevo evento'],
              clase: 'notif-evento',      icono: 'fa-calendar-plus' },
            { keys: ['evento cancelado', 'evento eliminado', 'sin cerrar'],
              clase: 'notif-evento-del',  icono: 'fa-calendar-xmark' },
            { keys: ['evento'],
              clase: 'notif-evento',      icono: 'fa-calendar-days' },

            // Entregables
            { keys: ['entregable_vencido', 'entregable vencido', 'vence hoy'],
              clase: 'notif-entregable-ven', icono: 'fa-file-circle-exclamation' },
            { keys: ['entregable'],
              clase: 'notif-entregable',  icono: 'fa-file-lines' },

            // Semilleros
            { keys: ['semillero_nuevo', 'nuevo semillero'],
              clase: 'notif-semillero',   icono: 'fa-seedling' },
            { keys: ['semillero'],
              clase: 'notif-semillero',   icono: 'fa-leaf' },

            // Usuario
            { keys: ['activo', 'cuenta activada'],
              clase: 'notif-user-on',     icono: 'fa-user-check' },
            { keys: ['inactivo', 'cuenta desactivada'],
              clase: 'notif-user-off',    icono: 'fa-user-slash' },
            { keys: ['usuario', 'perfil'],
              clase: 'notif-usuario',     icono: 'fa-circle-user' },

            // Privacidad
            { keys: ['contraseña', 'password', 'privacidad', 'acceso'],
              clase: 'notif-privacidad',  icono: 'fa-shield-halved' },

            // Alertas / errores
            { keys: ['error', 'fallo'],
              clase: 'notif-error',       icono: 'fa-circle-xmark' },
            { keys: ['alerta', 'advertencia'],
              clase: 'notif-alerta',      icono: 'fa-triangle-exclamation' },

            // Mensajes
            { keys: ['mensaje', 'comentario'],
              clase: 'notif-mensaje',     icono: 'fa-comment-dots' },

            // Sistema
            { keys: ['sistema', 'actualización', 'mantenimiento'],
              clase: 'notif-sistema',     icono: 'fa-gear' },
        ];

        for (const entry of mapa) {
            for (const key of entry.keys) {
                if (new RegExp(key, 'i').test(ref)) {
                    return { clase: entry.clase, icono: entry.icono };
                }
            }
        }

        return { clase: 'notif-default', icono: 'fa-bell' };
    }

    // =========================================================================
    // HELPERS UI
    // =========================================================================
    getEmptyState() {
        return `<div class="notification-empty">
                    <i class="fa fa-bell-slash"></i>
                    <p>No tienes notificaciones</p>
                </div>`;
    }

    getDrawerEmptyState() {
        return `<div class="drawer-empty-state">
                    <i class="fa fa-bell-slash"></i>
                    <h4>No hay notificaciones</h4>
                    <p>Estás al día con todo</p>
                </div>`;
    }

    showError() {
        const listContainer = document.getElementById('notification-list');
        if (listContainer) {
            listContainer.innerHTML = `
                <div class="notification-empty">
                    <i class="fa fa-exclamation-triangle"></i>
                    <p>Error cargando notificaciones</p>
                    <button onclick="window.notificationSystem.loadNotifications()"
                            style="margin-top:10px;padding:5px 15px;border:none;
                                   background:#39A900;color:white;border-radius:5px;cursor:pointer;">
                        Reintentar
                    </button>
                </div>`;
        }
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.innerHTML = `
            <i class="fa ${type === 'success' ? 'fa-check-circle' : 'fa-info-circle'}"></i>
            <span>${message}</span>`;
        Object.assign(toast.style, {
            position:     'fixed',
            bottom:       '20px',
            right:        '20px',
            background:   type === 'success' ? '#39A900' : '#1976d2',
            color:        'white',
            padding:      '12px 20px',
            borderRadius: '8px',
            boxShadow:    '0 4px 12px rgba(0,0,0,0.15)',
            zIndex:       '10000',
            display:      'flex',
            alignItems:   'center',
            gap:          '10px',
            fontSize:     '14px',
            fontWeight:   '500',
            animation:    'slideInUp 0.3s ease',
            maxWidth:     '400px'
        });
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.animation = 'slideOutDown 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// =============================================================================
// ESTILOS GLOBALES
// =============================================================================
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInUp {
        from { transform: translateY(100%); opacity: 0; }
        to   { transform: translateY(0);    opacity: 1; }
    }
    @keyframes slideOutDown {
        from { transform: translateY(0);    opacity: 1; }
        to   { transform: translateY(100%); opacity: 0; }
    }
    .notification-toast { transition: all 0.3s ease; }
    .notification-toast:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,0,0,0.2); }

    /* Ícono: círculo perfecto */
    .notification-icon-type {
        flex-shrink: 0 !important; flex-grow: 0 !important;
        align-self: center !important;
        width: 40px !important; height: 40px !important;
        min-width: 40px !important; min-height: 40px !important;
        max-width: 40px !important; max-height: 40px !important;
        border-radius: 50% !important;
        display: flex !important; align-items: center !important;
        justify-content: center !important; font-size: 1.1rem !important;
        background: linear-gradient(135deg, #e3f2fd, #bbdefb) !important;
        box-sizing: border-box !important;
    }

    /* Items */
    .notification-item, .drawer-notification-item {
        display: flex !important; flex-direction: row !important;
        align-items: center !important; gap: 12px !important;
        border-left: 3px solid transparent !important;
        box-sizing: border-box !important;
    }
    .notification-item.unread, .drawer-notification-item.unread {
        border-left: 3px solid #39A900 !important;
    }
    .notification-item.unread::before { display: none !important; }
    .notification-item .notification-content,
    .drawer-notification-item .notification-content {
        flex: 1 !important; min-width: 0 !important;
    }

    /* Colores por tipo */
    .notification-icon-type.notif-archivo        { background: linear-gradient(135deg, #ede9fe, #c4b5fd) !important; color: #6d28d9 !important; }
    .notification-icon-type.notif-archivo-del    { background: linear-gradient(135deg, #fce7f3, #f9a8d4) !important; color: #be185d !important; }
    .notification-icon-type.notif-estado-proy    { background: linear-gradient(135deg, #ffedd5, #fed7aa) !important; color: #c2410c !important; }
    .notification-icon-type.notif-proyecto       { background: linear-gradient(135deg, #dbeafe, #bfdbfe) !important; color: #1d4ed8 !important; }
    .notification-icon-type.notif-miembro        { background: linear-gradient(135deg, #ccfbf1, #99f6e4) !important; color: #0f766e !important; }
    .notification-icon-type.notif-miembro-del    { background: linear-gradient(135deg, #fee2e2, #fca5a5) !important; color: #b91c1c !important; }
    .notification-icon-type.notif-evento-prox    { background: linear-gradient(135deg, #fef9c3, #fde047) !important; color: #a16207 !important; }
    .notification-icon-type.notif-evento         { background: linear-gradient(135deg, #fff7ed, #fed7aa) !important; color: #c2410c !important; }
    .notification-icon-type.notif-evento-del     { background: linear-gradient(135deg, #fee2e2, #fca5a5) !important; color: #991b1b !important; }
    .notification-icon-type.notif-entregable     { background: linear-gradient(135deg, #fdf4ff, #e9d5ff) !important; color: #7e22ce !important; }
    .notification-icon-type.notif-entregable-ven { background: linear-gradient(135deg, #fff1f2, #fecdd3) !important; color: #be123c !important; }
    .notification-icon-type.notif-semillero      { background: linear-gradient(135deg, #f0fdf4, #bbf7d0) !important; color: #15803d !important; }
    .notification-icon-type.notif-lider          { background: linear-gradient(135deg, #fefce8, #fef08a) !important; color: #b45309 !important; }
    .notification-icon-type.notif-aprendiz       { background: linear-gradient(135deg, #e0e7ff, #c7d2fe) !important; color: #4338ca !important; }
    .notification-icon-type.notif-alerta         { background: linear-gradient(135deg, #fffde7, #fff9c4) !important; color: #f57f17 !important; }
    .notification-icon-type.notif-error          { background: linear-gradient(135deg, #ffebee, #ffcdd2) !important; color: #c62828 !important; }
    .notification-icon-type.notif-usuario        { background: linear-gradient(135deg, #e3f2fd, #bbdefb) !important; color: #1565c0 !important; }
    .notification-icon-type.notif-mensaje        { background: linear-gradient(135deg, #e0f7fa, #b2ebf2) !important; color: #00838f !important; }
    .notification-icon-type.notif-sistema        { background: linear-gradient(135deg, #eceff1, #cfd8dc) !important; color: #455a64 !important; }
    .notification-icon-type.notif-default        { background: linear-gradient(135deg, #f1f3f5, #e2e8f0) !important; color: #64748b !important; }
    .notification-icon-type.notif-user-on        { background: linear-gradient(135deg, #e8f5e9, #c8e6c9) !important; color: #388e3c !important; }
    .notification-icon-type.notif-user-off       { background: linear-gradient(135deg, #fff3e0, #ffe0b2) !important; color: #e65100 !important; }
    .notification-icon-type.notif-privacidad     { background: linear-gradient(135deg, #f3e8ff, #d8b4fe) !important; color: #7c3aed !important; }

    /* Colores por clase_icono del backend (success/warning/error/info) */
    .notification-icon-type.success { background: linear-gradient(135deg, #f0fdf4, #bbf7d0) !important; color: #15803d !important; }
    .notification-icon-type.warning { background: linear-gradient(135deg, #fefce8, #fef08a) !important; color: #b45309 !important; }
    .notification-icon-type.error   { background: linear-gradient(135deg, #ffebee, #ffcdd2) !important; color: #c62828 !important; }
    .notification-icon-type.info    { background: linear-gradient(135deg, #e3f2fd, #bbdefb) !important; color: #1565c0 !important; }
`;
document.head.appendChild(style);

// =============================================================================
// ARRANQUE
// =============================================================================
document.addEventListener('DOMContentLoaded', function () {
    setTimeout(() => {
        // ✅ Limpiar el localStorage antiguo (array permanente) si existe
        try {
            const old = localStorage.getItem('dismissed_notifications');
            if (old && Array.isArray(JSON.parse(old))) {
                localStorage.removeItem('dismissed_notifications');
                console.log('🧹 Cache antiguo de dismissed limpiado automáticamente');
            }
        } catch {
            localStorage.removeItem('dismissed_notifications');
        }

        console.log('🚀 Inicializando sistema de notificaciones...');
        window.notificationSystem = new NotificationSystem();
        window.notificationSystem.init();
    }, 100);
});

if (typeof module !== 'undefined' && module.exports) {
    module.exports = NotificationSystem;
}