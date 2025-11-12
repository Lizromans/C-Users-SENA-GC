// ====== GESTOR CENTRALIZADO DE MODALES ======
class ModalManager {
    constructor() {
        this.modalActual = null;
        this.initialize();
    }

    initialize() {
        document.addEventListener('DOMContentLoaded', () => {
            this.setupModalListeners();
            this.setupCloseButtons();
            this.setupOverlayClicks();
            this.checkInitialModal();
        });
    }

    // Configura listeners para abrir modales
    setupModalListeners() {
        // Botón crear proyecto
        const btnCrear = document.querySelector('[data-bs-target="#modal-crear"]');
        if (btnCrear) {
            btnCrear.addEventListener('click', (e) => {
                e.preventDefault();
                this.abrirModal('modal-crear');
            });
        }

        // Enlaces que abren modales
        document.querySelectorAll('a[href^="#modal-"]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const modalId = link.getAttribute('href').substring(1);
                this.abrirModal(modalId);
            });
        });
    }

    // Configura botones de cerrar (X)
    setupCloseButtons() {
        document.querySelectorAll('.modal-cerrar').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.cerrarModal();
            });
        });

        // Botones cancelar
        document.querySelectorAll('.modal-btn-cancelar, .btn-cancelar').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.cerrarModal();
            });
        });
    }

    // Configura clics en overlay
    setupOverlayClicks() {
        document.querySelectorAll('.modal-overlay, .modal').forEach(overlay => {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    this.cerrarModal();
                }
            });
        });
    }

    // Verifica si hay un modal que debe abrirse al cargar
    checkInitialModal() {
        // Modal de editar (con clase .activo)
        const modalEditarActivo = document.querySelector('.modal-overlay.activo');
        if (modalEditarActivo) {
            this.modalActual = modalEditarActivo.id;
            this.bloquearScroll();
            return;
        }

        // Modal de gestionar (con clase .activo)
        const modalGestionarActivo = document.querySelector('#modal-gestionar-miembros.activo');
        if (modalGestionarActivo) {
            this.modalActual = 'modal-gestionar-miembros';
            this.bloquearScroll();
            return;
        }

        // Modal desde hash en URL
        if (window.location.hash.startsWith('#modal-')) {
            const modalId = window.location.hash.substring(1);
            this.abrirModal(modalId, false);
        }
    }

    // Abrir modal
    abrirModal(modalId, actualizarHistorial = true) {
        // Cerrar modal actual si existe
        if (this.modalActual) {
            this.cerrarModalInterno();
        }

        const modal = document.getElementById(modalId);
        if (!modal) return;

        // Activar modal
        if (modal.classList.contains('modal-overlay')) {
            modal.style.display = 'flex';
            // Pequeño delay para la animación
            setTimeout(() => modal.classList.add('activo'), 10);
        } else if (modal.classList.contains('modal')) {
            modal.style.display = 'flex';
        }

        this.modalActual = modalId;
        this.bloquearScroll();

        // Actualizar URL sin recargar página
        if (actualizarHistorial) {
            history.pushState(
                { modal: modalId },
                '',
                `${window.location.pathname}${window.location.search}#${modalId}`
            );
        }
    }

    // Cerrar modal actual
    cerrarModal() {
        if (!this.modalActual) return;

        this.cerrarModalInterno();
        this.desbloquearScroll();
        this.modalActual = null;

        // Limpiar URL sin afectar el historial
        const urlSinHash = window.location.pathname + window.location.search;
        history.replaceState(null, '', urlSinHash);
    }

    // Cerrar modal internamente (sin cambiar estado global)
    cerrarModalInterno() {
        const modal = document.getElementById(this.modalActual);
        if (!modal) return;

        if (modal.classList.contains('modal-overlay')) {
            modal.classList.remove('activo');
            // Esperar animación antes de ocultar (reducido a 150ms)
            setTimeout(() => {
                modal.style.display = 'none';
            }, 150);
        } else if (modal.classList.contains('modal')) {
            modal.style.display = 'none';
        }
    }

    // Bloquear scroll del body
    bloquearScroll() {
        document.body.style.overflow = 'hidden';
        document.body.style.paddingRight = this.getScrollbarWidth() + 'px';
    }

    // Desbloquear scroll del body
    desbloquearScroll() {
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
    }

    // Calcular ancho de scrollbar
    getScrollbarWidth() {
        const outer = document.createElement('div');
        outer.style.visibility = 'hidden';
        outer.style.overflow = 'scroll';
        document.body.appendChild(outer);
        
        const inner = document.createElement('div');
        outer.appendChild(inner);
        
        const scrollbarWidth = outer.offsetWidth - inner.offsetWidth;
        outer.parentNode.removeChild(outer);
        
        return scrollbarWidth;
    }
}

// Instanciar gestor de modales
const modalManager = new ModalManager();

// Manejar navegación del navegador (botón atrás)
window.addEventListener('popstate', (e) => {
    if (e.state && e.state.modal) {
        modalManager.abrirModal(e.state.modal, false);
    } else {
        modalManager.cerrarModal();
    }
});

// Cerrar modal con tecla ESC
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modalManager.modalActual) {
        modalManager.cerrarModal();
    }
});

// ====== FUNCIONES DE COMPATIBILIDAD CON TU CÓDIGO EXISTENTE ======

// Mantener funcionalidad de acordeón de entregables
document.addEventListener('DOMContentLoaded', function() {
    const entregableToggles = document.querySelectorAll('.entregable-toggle');
    
    function actualizarChevron(toggle) {
        const label = document.querySelector(`label[for="${toggle.id}"]`);
        const chevron = label?.querySelector('.entregable-chevron, .fa-chevron-down, .fa-chevron-right');
        
        if (chevron) {
            chevron.style.transform = toggle.checked ? 'rotate(180deg)' : 'rotate(0deg)';
        }
    }
    
    function cerrarTodosEntregables(excepto = null) {
        entregableToggles.forEach(toggle => {
            if (toggle !== excepto) {
                toggle.checked = false;
                actualizarChevron(toggle);
            }
        });
    }
    
    entregableToggles.forEach(toggle => {
        const label = document.querySelector(`label[for="${toggle.id}"]`);
        const chevron = label?.querySelector('.entregable-chevron, .fa-chevron-down, .fa-chevron-right');
        
        if (chevron) {
            chevron.style.transition = 'transform 0.3s ease';
            actualizarChevron(toggle);
        }
        
        toggle.addEventListener('change', function() {
            if (this.checked) {
                cerrarTodosEntregables(this);
            }
            actualizarChevron(this);
        });
    });
    
    window.cerrarTodosEntregables = cerrarTodosEntregables;
});

// Mantener funcionalidad de dropdowns
document.addEventListener('DOMContentLoaded', function() {
    const dropdownToggles = document.querySelectorAll('.dropdown-toggle-config');
    
    function cerrarTodosDropdowns(excepto = null) {
        dropdownToggles.forEach(toggle => {
            if (toggle !== excepto) {
                toggle.checked = false;
            }
        });
    }
    
    dropdownToggles.forEach(toggle => {
        toggle.addEventListener('change', function() {
            if (this.checked) {
                cerrarTodosDropdowns(this);
            }
        });
    });
    
    document.addEventListener('click', function(event) {
        const clickDentroDropdown = event.target.closest('.config-dropdown-wrapper');
        if (!clickDentroDropdown) {
            cerrarTodosDropdowns();
        }
    });
    
    document.querySelectorAll('.config-dropdown-wrapper').forEach(wrapper => {
        wrapper.addEventListener('click', function(event) {
            event.stopPropagation();
        });
    });
    
    document.querySelectorAll('.dropdown-item-config').forEach(item => {
        item.addEventListener('click', function(event) {
            if (this.getAttribute('href') !== '#') {
                const wrapper = this.closest('.config-dropdown-wrapper');
                const toggle = wrapper?.querySelector('.dropdown-toggle-config');
                if (toggle) {
                    toggle.checked = false;
                }
            }
        });
    });
});

// Mantener scroll a sección seleccionada
document.addEventListener("DOMContentLoaded", function () {
    const tipo = document.body.dataset.tipoSeleccionado;
    if (tipo) {
        const seccion = document.getElementById(tipo);
        if (seccion) {
            setTimeout(() => {
                seccion.scrollIntoView({ behavior: "smooth", block: "start" });
            }, 300);
        }
    }
});