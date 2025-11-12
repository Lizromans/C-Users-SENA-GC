// Script para controlar la apertura/cierre de entregables (acordeón) y dropdown de configuración
document.addEventListener('DOMContentLoaded', function() {
    
    // ====== ACORDEÓN DE ENTREGABLES ======
   
    // Obtener todos los checkboxes de entregables
    const entregableToggles = document.querySelectorAll('.entregable-toggle');
    
    // Función para actualizar el estado de los chevrones
    function actualizarChevron(toggle) {
        const label = document.querySelector(`label[for="${toggle.id}"]`);
        const chevron = label?.querySelector('.entregable-chevron, .fa-chevron-down, .fa-chevron-right');
        
        if (chevron) {
            if (toggle.checked) {
                chevron.style.transform = 'rotate(180deg)';
            } else {
                chevron.style.transform = 'rotate(0deg)';
            }
        }
    }
    
    // Función para cerrar todos los entregables excepto el especificado
    function cerrarTodosEntregables(excepto = null) {
        entregableToggles.forEach(toggle => {
            if (toggle !== excepto) {
                toggle.checked = false;
                actualizarChevron(toggle); // Actualizar chevron al cerrar
            }
        });
    }
    
    // Agregar evento a cada checkbox
    entregableToggles.forEach(toggle => {
        toggle.addEventListener('change', function() {
            // Si se está abriendo este entregable
            if (this.checked) {
                // Cerrar todos los demás entregables
                cerrarTodosEntregables(this);
            }
            // Actualizar el chevron del entregable actual
            actualizarChevron(this);
        });
    });
    
    // Inicializar estado de chevrones al cargar la página
    entregableToggles.forEach(toggle => {
        const label = document.querySelector(`label[for="${toggle.id}"]`);
        const chevron = label?.querySelector('.entregable-chevron, .fa-chevron-down, .fa-chevron-right');
        
        if (chevron) {
            chevron.style.transition = 'transform 0.3s ease';
            actualizarChevron(toggle);
        }
    });
    
    // Función global para cerrar todos los entregables
    window.cerrarTodosEntregables = function() {
        cerrarTodosEntregables();
    };
    
    
    // ====== DROPDOWN DE CONFIGURACIÓN ======
    
    // Obtener todos los checkboxes de dropdown
    const dropdownToggles = document.querySelectorAll('.dropdown-toggle-config');
    
    // Función para cerrar todos los dropdowns excepto el especificado
    function cerrarTodosDropdowns(excepto = null) {
        dropdownToggles.forEach(toggle => {
            if (toggle !== excepto) {
                toggle.checked = false;
            }
        });
    }
    
    // Agregar evento a cada checkbox de dropdown
    dropdownToggles.forEach(toggle => {
        toggle.addEventListener('change', function() {
            // Si se está abriendo este dropdown
            if (this.checked) {
                // Cerrar todos los demás dropdowns
                cerrarTodosDropdowns(this);
            }
        });
    });
    
    // Cerrar dropdown al hacer clic fuera
    document.addEventListener('click', function(event) {
        const clickDentroDropdown = event.target.closest('.config-dropdown-wrapper');
        
        // Si el clic no fue dentro de ningún dropdown
        if (!clickDentroDropdown) {
            cerrarTodosDropdowns();
        }
    });
    
    // Prevenir que el clic en el dropdown lo cierre inmediatamente
    document.querySelectorAll('.config-dropdown-wrapper').forEach(wrapper => {
        wrapper.addEventListener('click', function(event) {
            event.stopPropagation();
        });
    });
    
    // Cerrar dropdown al hacer clic en una opción (excepto si es un enlace con #)
    document.querySelectorAll('.dropdown-item-config').forEach(item => {
        item.addEventListener('click', function(event) {
            // Si el enlace no es solo un ancla (#), cerrar el dropdown
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

// ====== Función alternativa por proyecto específico ======
function inicializarAcordeonProyecto(codProyecto) {
    const togglesProyecto = document.querySelectorAll(
        `input[id^="entregable-${codProyecto}-"].entregable-toggle`
    );
    
    function actualizarChevronProyecto(toggle) {
        const label = document.querySelector(`label[for="${toggle.id}"]`);
        const chevron = label?.querySelector('.entregable-chevron, .fa-chevron-down, .fa-chevron-right');
        
        if (chevron) {
            chevron.style.transform = toggle.checked ? 'rotate(180deg)' : 'rotate(0deg)';
        }
    }
    
    togglesProyecto.forEach(toggle => {
        toggle.addEventListener('change', function() {
            if (this.checked) {
                togglesProyecto.forEach(otroToggle => {
                    if (otroToggle !== this) {
                        otroToggle.checked = false;
                        actualizarChevronProyecto(otroToggle);
                    }
                });
            }
            actualizarChevronProyecto(this);
        });
    });
}

