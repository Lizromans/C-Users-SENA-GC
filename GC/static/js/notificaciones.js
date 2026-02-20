class NotificationSystem {
    constructor() {
        this.storageKey = 'notifications_state';
        this.dismissedKey = 'dismissed_notifications';
        this.state = this.loadState();
        this.dismissedNotifications = this.loadDismissed();
        this.notifications = [];
        this.filteredNotifications = [];
        this.currentFilter = 'all';
        
        console.log('✅ NotificationSystem inicializado');
    }

    init() {
        this.setupEventListeners();
        this.loadNotifications();
        
        setInterval(() => this.loadNotifications(), 120000);
        console.log('✅ Sistema de notificaciones activo');
    }

    /* ─────────────────────────────────────────────────────────────────────
       getIconConfig: asigna color e ícono único a cada tipo de notificación.
       Prioridad:
         1) Si el backend manda clase_icono e icono → los usa tal cual.
         2) Si no → busca por palabras clave en notif.tipo (fallback visual).
    ──────────────────────────────────────────────────────────────────────── */
    getIconConfig(notif) {
        if (notif.clase_icono && notif.icono) {
            return { clase: notif.clase_icono, icono: notif.icono };
        }

        const tipo = (notif.tipo || '').toLowerCase();
        const titulo = (notif.titulo || '').toLowerCase();
        const ref = tipo + ' ' + titulo;

        /* Orden: más específico primero */
        const mapa = [
            // 📁 Archivos
            { keys: ['archivo_nuevo', 'nuevo archivo', 'archivo subido', 'subió un archivo'],
              clase: 'notif-archivo',    icono: 'fa-file-circle-plus'        },
            { keys: ['archivo eliminado', 'archivo borrado'],
              clase: 'notif-archivo-del', icono: 'fa-file-circle-xmark'     },
            { keys: ['archivo'],
              clase: 'notif-archivo',    icono: 'fa-folder-open'             },

            // 🔄 Estado de proyecto / usuario
            { keys: ['estado_proyecto', 'cambio de estado', 'estado del proyecto',
                     'completado', 'en curso', 'pausado', 'terminado', 'cancelado',
                     'aprobado', 'rechazado'],
              clase: 'notif-estado-proy', icono: 'fa-arrows-rotate'          },

            // 🎓 Aprendices
            { keys: ['aprendiz asignado', 'nuevo aprendiz', 'aprendiz agregado',
                     'aprendiz', 'ficha'],
              clase: 'notif-aprendiz',   icono: 'fa-user-graduate'           },

            // 👑 Lider / Rol
            { keys: ['líder', 'lider', 'nuevo rol', 'rol asignado', 'ahora lideras',
                     'cambio de rol', 'nuevo lider'],
              clase: 'notif-lider',      icono: 'fa-crown'                   },

            // 📊 Proyectos (general)
            { keys: ['proyecto_nuevo', 'nuevo proyecto', 'proyecto creado'],
              clase: 'notif-proyecto',   icono: 'fa-diagram-project'         },
            { keys: ['proyecto'],
              clase: 'notif-proyecto',   icono: 'fa-chart-gantt'             },

            // 👥 Miembros / asignaciones
            { keys: ['miembro_asignado', 'asignación de miembro', 'asignado al',
                     'nuevo miembro', 'miembro agregado', 'se unió'],
              clase: 'notif-miembro',    icono: 'fa-user-plus'               },
            { keys: ['miembro eliminado', 'miembro removido', 'expulsado'],
              clase: 'notif-miembro-del', icono: 'fa-user-minus'             },
            { keys: ['miembro', 'asignado'],
              clase: 'notif-miembro',    icono: 'fa-users'                   },

            // 📅 Eventos
            { keys: ['evento_proximo', 'evento próximo', 'próximo evento', 'evento mañana'],
              clase: 'notif-evento-prox', icono: 'fa-calendar-check'        },
            { keys: ['evento_nuevo', 'nuevo evento', 'evento creado'],
              clase: 'notif-evento',     icono: 'fa-calendar-plus'           },
            { keys: ['evento cancelado', 'evento eliminado'],
              clase: 'notif-evento-del', icono: 'fa-calendar-xmark'         },
            { keys: ['evento'],
              clase: 'notif-evento',     icono: 'fa-calendar-days'           },

            // 📋 Entregables
            { keys: ['entregable_enviado', 'entregable enviado', 'entregable subido'],
              clase: 'notif-entregable', icono: 'fa-file-export'             },
            { keys: ['entregable_vencido', 'entregable vencido', 'entregable vence'],
              clase: 'notif-entregable-ven', icono: 'fa-file-circle-exclamation' },
            { keys: ['entregable'],
              clase: 'notif-entregable', icono: 'fa-file-lines'              },

            // 🌱 Semilleros
            { keys: ['semillero_nuevo', 'nuevo semillero', 'semillero creado'],
              clase: 'notif-semillero',  icono: 'fa-seedling'                },
            { keys: ['semillero'],
              clase: 'notif-semillero',  icono: 'fa-leaf'                    },

            // 👤 Estado de usuario
            { keys: ['activo', 'usuario activo', 'cuenta activada'],
              clase: 'notif-user-on',   icono: 'fa-user-check'               },
            { keys: ['inactivo', 'usuario inactivo', 'cuenta desactivada'],
              clase: 'notif-user-off',  icono: 'fa-user-slash'               },
            { keys: ['usuario', 'perfil'],
              clase: 'notif-usuario',   icono: 'fa-circle-user'              },

            // 🔐 Privacidad / contraseña
            { keys: ['contraseña', 'password', 'privacidad', 'acceso'],
              clase: 'notif-privacidad', icono: 'fa-shield-halved'           },

            // ⚠️ Alertas y errores
            { keys: ['error', 'fallo', 'falla'],
              clase: 'notif-error',     icono: 'fa-circle-xmark'             },
            { keys: ['alerta', 'advertencia', 'atención'],
              clase: 'notif-alerta',    icono: 'fa-triangle-exclamation'     },

            // 💬 Mensajes / comentarios
            { keys: ['mensaje', 'comentario', 'respuesta'],
              clase: 'notif-mensaje',   icono: 'fa-comment-dots'             },

            // 📢 General / sistema
            { keys: ['sistema', 'actualización', 'mantenimiento'],
              clase: 'notif-sistema',   icono: 'fa-gear'                     },
        ];

        for (const entry of mapa) {
            for (const key of entry.keys) {
                const regex = new RegExp(key, 'i');
                if (regex.test(ref)) {
                    return { clase: entry.clase, icono: entry.icono };
                }
            }
        }

        return { clase: 'notif-default', icono: 'fa-bell' };
    }
    /* ──────────────────────────────────────────────────────────────────── */

    setupEventListeners() {
        const bell = document.getElementById('notification-bell');
        if (bell) {
            bell.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                this.toggleDropdown();
            });
        }

        const closeBtn = document.getElementById('close-notifications');
        if (closeBtn) {
            closeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                e.stopImmediatePropagation();
                this.closeDropdown();
            });
        }

        const viewAll = document.getElementById('view-all-notifications');
        if (viewAll) {
            viewAll.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.closeDropdown();
                this.openDrawer();
            });
        }

        const drawerCloseBtn = document.getElementById('drawer-close-btn');
        const drawerOverlay  = document.getElementById('notifications-drawer-overlay');
        
        if (drawerCloseBtn) {
            drawerCloseBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.closeDrawer();
            });
        }
        
        if (drawerOverlay) {
            drawerOverlay.addEventListener('click', () => this.closeDrawer());
        }

        const filterBtns = document.querySelectorAll('.filter-btn');
        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.applyFilter(btn.dataset.filter);
            });
        });

        const markAllRead = document.getElementById('mark-all-read');
        if (markAllRead) {
            markAllRead.addEventListener('click', () => this.markAllAsRead());
        }

        const clearAll = document.getElementById('clear-all-notifications');
        if (clearAll) {
            clearAll.addEventListener('click', () => this.clearAllNotifications());
        }

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
                if (drawer && drawer.classList.contains('show')) {
                    this.closeDrawer();
                }
            }
        });

        console.log('✅ Event listeners configurados');
    }

    loadState() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            return saved ? JSON.parse(saved) : {};
        } catch (e) {
            console.error('Error cargando estado:', e);
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

    loadDismissed() {
        try {
            const saved = localStorage.getItem(this.dismissedKey);
            return saved ? JSON.parse(saved) : [];
        } catch (e) {
            console.error('Error cargando notificaciones descartadas:', e);
            return [];
        }
    }

    saveDismissed() {
        try {
            localStorage.setItem(this.dismissedKey, JSON.stringify(this.dismissedNotifications));
        } catch (e) {
            console.error('Error guardando notificaciones descartadas:', e);
        }
    }

    getNotificationId(notification) {
        return `${notification.tipo}_${notification.titulo}_${notification.fecha}`.replace(/\s+/g, '_');
    }

    isRead(notificationId) {
        return this.state[notificationId] === true;
    }

    markAsRead(notificationId) {
        this.state[notificationId] = true;
        this.saveState();
        this.updateUI();
    }

    isDismissed(notificationId) {
        return this.dismissedNotifications.includes(notificationId);
    }

    dismissNotification(notificationId) {
        if (!this.dismissedNotifications.includes(notificationId)) {
            this.dismissedNotifications.push(notificationId);
            this.saveDismissed();
        }
    }

    async loadNotifications() {
        try {
            console.log('📡 Cargando notificaciones...');
            
            const response = await fetch('/api/notificaciones/', {
                method: 'GET',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('📥 Datos recibidos:', data);
            
            if (data.notificaciones && Array.isArray(data.notificaciones)) {
                this.notifications = data.notificaciones.filter(notif => {
                    const id = this.getNotificationId(notif);
                    return !this.isDismissed(id);
                });
                
                console.log('✅ Notificaciones cargadas:', this.notifications.length);
                this.updateUI();
            }
        } catch (error) {
            console.error('❌ Error cargando notificaciones:', error);
            this.showError();
        }
    }

    updateUI() {
        this.updateBadge();
        this.updateDropdown();
        if (document.getElementById('notifications-drawer').classList.contains('show')) {
            this.updateDrawer();
        }
    }

    updateBadge() {
        const badge = document.getElementById('notification-count');
        if (!badge) return;

        const unreadCount = this.notifications.filter(notif => {
            const id = this.getNotificationId(notif);
            return !this.isRead(id);
        }).length;

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

        const recentNotifications = this.notifications.slice(0, 5);

        recentNotifications.forEach(notif => {
            const id     = this.getNotificationId(notif);
            const isRead = this.isRead(id);

            /* ── usa getIconConfig para garantizar clase e ícono ── */
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
                </div>
            `;
            
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

        Object.keys(grouped).sort((a, b) => {
            const order = { 'Hoy': 0, 'Ayer': 1, 'Esta semana': 2, 'Anteriores': 3 };
            return order[a] - order[b];
        }).forEach(dateLabel => {
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

                /* ── usa getIconConfig para garantizar clase e ícono ── */
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
                    </div>
                `;
                
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

    applyCurrentFilter() {
        switch(this.currentFilter) {
            case 'unread':
                this.filteredNotifications = this.notifications.filter(notif => {
                    const id = this.getNotificationId(notif);
                    return !this.isRead(id);
                });
                break;
            case 'eventos':
                this.filteredNotifications = this.notifications.filter(notif => 
                    notif.tipo.includes('evento')
                );
                break;
            case 'proyectos':
                this.filteredNotifications = this.notifications.filter(notif => 
                    notif.tipo.includes('proyecto')
                );
                break;
            case 'entregables':
                this.filteredNotifications = this.notifications.filter(notif => 
                    notif.tipo.includes('entregable')
                );
                break;
            default:
                this.filteredNotifications = [...this.notifications];
        }
        console.log(`🔍 Filtro aplicado: ${this.currentFilter} -> ${this.filteredNotifications.length} resultados`);
    }

    applyFilter(filter) {
        this.currentFilter = filter;
        console.log('🔍 Cambiando filtro a:', filter);
        this.updateDrawer();
    }

    groupByDate(notifications) {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        
        const weekAgo = new Date(today);
        weekAgo.setDate(weekAgo.getDate() - 7);

        const grouped = { 'Hoy': [], 'Ayer': [], 'Esta semana': [], 'Anteriores': [] };

        notifications.forEach(notif => {
            try {
                const notifDate = new Date(notif.fecha);
                if (isNaN(notifDate.getTime())) {
                    grouped['Anteriores'].push(notif);
                    return;
                }
                notifDate.setHours(0, 0, 0, 0);

                if      (notifDate.getTime() === today.getTime())     grouped['Hoy'].push(notif);
                else if (notifDate.getTime() === yesterday.getTime()) grouped['Ayer'].push(notif);
                else if (notifDate >= weekAgo)                        grouped['Esta semana'].push(notif);
                else                                                  grouped['Anteriores'].push(notif);
            } catch (e) {
                console.error('Error procesando fecha:', e);
                grouped['Anteriores'].push(notif);
            }
        });

        return grouped;
    }

    handleNotificationClick(notificationId, url) {
        console.log('👆 Click en notificación:', notificationId);
        this.markAsRead(notificationId);
        this.closeDropdown();
        this.closeDrawer();
        if (url && url !== '#') {
            window.location.href = url;
        }
    }

    markAllAsRead() {
        this.notifications.forEach(notif => {
            const id = this.getNotificationId(notif);
            this.state[id] = true;
        });
        this.saveState();
        this.updateUI();
        this.showToast('Todas las notificaciones marcadas como leídas', 'success');
    }

    clearAllNotifications() {
        if (!confirm('¿Estás seguro de que deseas limpiar todas las notificaciones?')) return;

        this.notifications.forEach(notif => {
            const id = this.getNotificationId(notif);
            if (!this.dismissedNotifications.includes(id)) {
                this.dismissedNotifications.push(id);
            }
        });

        this.saveDismissed();
        this.state = {};
        localStorage.removeItem(this.storageKey);
        this.notifications = [];
        this.filteredNotifications = [];
        this.updateUI();
        this.closeDrawer();

        const countSpan = document.getElementById('notification-count');
        if (countSpan) countSpan.textContent = '0';

        this.showToast('Todas las notificaciones fueron eliminadas', 'success');
    }

    toggleDropdown() {
        const dropdown = document.getElementById('notification-dropdown');
        if (dropdown) dropdown.classList.toggle('show');
    }

    closeDropdown() {
        const dropdown = document.getElementById('notification-dropdown');
        if (dropdown) dropdown.classList.remove('show');
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

    getEmptyState() {
        return `
            <div class="notification-empty">
                <i class="fa fa-bell-slash"></i>
                <p>No tienes notificaciones</p>
            </div>
        `;
    }

    getDrawerEmptyState() {
        return `
            <div class="drawer-empty-state">
                <i class="fa fa-bell-slash"></i>
                <h4>No hay notificaciones</h4>
                <p>Estás al día con todo</p>
            </div>
        `;
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
                </div>
            `;
        }
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.innerHTML = `
            <i class="fa ${type === 'success' ? 'fa-check-circle' : 'fa-info-circle'}"></i>
            <span>${message}</span>
        `;
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

/* ─── Animaciones del toast ─── */
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
`;
document.head.appendChild(style);

/* ─── Arranque ─── */
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        console.log('🚀 Inicializando sistema de notificaciones...');
        window.notificationSystem = new NotificationSystem();
        window.notificationSystem.init();
    }, 100);
});

if (typeof module !== 'undefined' && module.exports) {
    module.exports = NotificationSystem;
}