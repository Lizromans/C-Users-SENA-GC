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

    setupModalListeners() {
        const btnCrear = document.querySelector('[data-bs-target="#modal-crear"]');
        if (btnCrear) {
            btnCrear.addEventListener('click', (e) => {
                e.preventDefault();
                this.abrirModal('modal-crear');
            });
        }

        document.querySelectorAll('a[href^="#modal-"]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const modalId = link.getAttribute('href').substring(1);
                this.abrirModal(modalId);
            });
        });
    }

    setupCloseButtons() {
        document.querySelectorAll('.modal-cerrar').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.cerrarModal();
            });
        });

        document.querySelectorAll('.modal-btn-cancelar, .btn-cancelar').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.cerrarModal();
            });
        });
    }
    setupOverlayClicks() {
        document.querySelectorAll('.modal-overlay, .modal').forEach(overlay => {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    this.cerrarModal();
                }
            });
        });
    }

    checkInitialModal() {
        const modalEditarActivo = document.querySelector('.modal-overlay.activo');
        if (modalEditarActivo) {
            this.modalActual = modalEditarActivo.id;
            this.bloquearScroll();
            return;
        }

        const modalGestionarActivo = document.querySelector('#modal-gestionar-miembros.activo');
        if (modalGestionarActivo) {
            this.modalActual = 'modal-gestionar-miembros';
            this.bloquearScroll();
            return;
        }

        if (window.location.hash.startsWith('#modal-')) {
            const modalId = window.location.hash.substring(1);
            this.abrirModal(modalId, false);
        }
    }

    abrirModal(modalId, actualizarHistorial = true) {
        if (this.modalActual) {
            this.cerrarModalInterno();
        }

        const modal = document.getElementById(modalId);
        if (!modal) return;

        if (modal.classList.contains('modal-overlay')) {
            modal.style.display = 'flex';
            setTimeout(() => modal.classList.add('activo'), 10);
        } else if (modal.classList.contains('modal')) {
            modal.style.display = 'flex';
        }

        this.modalActual = modalId;
        this.bloquearScroll();

        if (actualizarHistorial) {
            history.pushState(
                { modal: modalId },
                '',
                `${window.location.pathname}${window.location.search}#${modalId}`
            );
        }
    }

    cerrarModal() {
        if (!this.modalActual) return;

        this.cerrarModalInterno();
        this.desbloquearScroll();
        this.modalActual = null;

        const urlSinHash = window.location.pathname + window.location.search;
        history.replaceState(null, '', urlSinHash);
    }

    cerrarModalInterno() {
        const modal = document.getElementById(this.modalActual);
        if (!modal) return;

        if (modal.classList.contains('modal-overlay')) {
            modal.classList.remove('activo');
            setTimeout(() => {
                modal.style.display = 'none';
            }, 150);
        } else if (modal.classList.contains('modal')) {
            modal.style.display = 'none';
        }
    }

    bloquearScroll() {
        document.body.style.overflow = 'hidden';
        document.body.style.paddingRight = this.getScrollbarWidth() + 'px';
    }

    desbloquearScroll() {
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
    }

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

const modalManager = new ModalManager();

window.addEventListener('popstate', (e) => {
    if (e.state && e.state.modal) {
        modalManager.abrirModal(e.state.modal, false);
    } else {
        modalManager.cerrarModal();
    }
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modalManager.modalActual) {
        modalManager.cerrarModal();
    }
});

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