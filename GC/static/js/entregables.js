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
        toggle.addEventListener('change', function() {
            if (this.checked) {
                cerrarTodosEntregables(this);
            }
            actualizarChevron(this);
        });
        
        const label = document.querySelector(`label[for="${toggle.id}"]`);
        const chevron = label?.querySelector('.entregable-chevron, .fa-chevron-down, .fa-chevron-right');
        
        if (chevron) {
            chevron.style.transition = 'transform 0.3s ease';
            actualizarChevron(toggle);
        }
    });
    
    window.cerrarTodosEntregables = function() {
        cerrarTodosEntregables();
    };
    
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
    
    const tipoSelect = document.getElementById('tipo');
    const contenedor = document.getElementById('entregables-container');
    const entregableInvestigacion = document.querySelector('.entregable-investigacion');
    const entregablesFormativos = document.querySelector('.formativos');
    
    function actualizarEntregables() {
        if (!tipoSelect || !contenedor) return;
        
        const tipo = tipoSelect.value;
        
        if (entregableInvestigacion) entregableInvestigacion.style.display = 'none';
        if (entregablesFormativos) entregablesFormativos.style.display = 'none';
        
        if (!tipo) {
            contenedor.style.display = 'none';
            return;
        }
        
        contenedor.style.display = 'block';
        if (tipo === 'sennova' || tipo === 'capacidadinstalada') {
            if (entregableInvestigacion) {
                entregableInvestigacion.style.display = 'block';
            }
        }
        
        if (tipo === 'formativo') {
            if (entregablesFormativos) {
                entregablesFormativos.style.display = 'grid';
            }
        }
    }
    
    if (tipoSelect) {
        actualizarEntregables();
        tipoSelect.addEventListener('change', actualizarEntregables);
    }
    
    const formCrear = document.querySelector('form[action*="crear_proyecto"]');
    if (formCrear) {
        formCrear.addEventListener('submit', function(e) {
            const tipo = tipoSelect?.value;
            
            if (!tipo) {
                e.preventDefault();
                alert('Por favor, seleccione un tipo de proyecto.');
                tipoSelect?.focus();
                return;
            }
            
            if (tipo === 'sennova' || tipo === 'capacidadinstalada') {
                const fechaInput = document.getElementById('fechaRango_investigacion');
                if (fechaInput && !fechaInput.value) {
                    e.preventDefault();
                    alert('Por favor, seleccione las fechas para el entregable de Resultados y Productos de Investigación.');
                    fechaInput.focus();
                    return;
                }
            }
            
            if (tipo === 'formativo') {
                const fechasFormativo = [
                    'fechaRango_1', 'fechaRango_2', 'fechaRango_3',
                    'fechaRango_4', 'fechaRango_5', 'fechaRango_6'
                ];
                
                for (let i = 0; i < fechasFormativo.length; i++) {
                    const fechaInput = document.getElementById(fechasFormativo[i]);
                    if (fechaInput && !fechaInput.value) {
                        e.preventDefault();
                        alert(`Por favor, complete todas las fechas de los entregables formativos (Entregable ${i + 1}).`);
                        fechaInput.focus();
                        return;
                    }
                }
            }
        });
    }
});

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

window.cerrarModal = function(event, modalId) {
    if (event) event.preventDefault();
    
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('activo', 'show');
        modal.style.display = 'none';
    }
    
    // Limpiar backdrop
    const backdrop = document.querySelector('.modal-backdrop');
    if (backdrop) backdrop.remove();
    
    document.body.classList.remove('modal-open');
    document.body.style.overflow = 'auto';
    document.body.style.paddingRight = '';
};

window.abrirModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('activo', 'show');
        modal.style.display = 'flex';
        
        document.body.classList.add('modal-open');
        document.body.style.overflow = 'hidden';
    }
};

document.addEventListener('DOMContentLoaded', function() {
    const inputsArchivo = document.querySelectorAll('input[type="file"][id^="archivo_"]');
    
    inputsArchivo.forEach(input => {
        input.addEventListener('change', function() {
            const files = this.files;
            const codEntregable = this.id.replace('archivo_', '');
            const previewContainer = document.getElementById(`preview-archivos-${codEntregable}`);
            
            if (!previewContainer) return;
            
            previewContainer.innerHTML = '';
            
            if (files.length === 0) return;
            
            previewContainer.innerHTML = '<p style="margin: 10px 0; font-weight: 600;">Archivos seleccionados:</p>';
            
            const lista = document.createElement('ul');
            lista.style.cssText = 'list-style: none; padding: 0; margin: 10px 0;';
            
            Array.from(files).forEach(file => {
                const item = document.createElement('li');
                item.style.cssText = 'padding: 8px; margin-bottom: 5px; background: #f1f5f9; border-radius: 4px; display: flex; align-items: center; gap: 8px;';
                
                const icon = document.createElement('i');
                icon.className = 'fas fa-file';
                icon.style.color = '#64748b';
                
                const nombre = document.createElement('span');
                nombre.textContent = file.name;
                nombre.style.flex = '1';
                
                const tamano = document.createElement('span');
                tamano.textContent = formatearTamano(file.size);
                tamano.style.cssText = 'font-size: 0.875rem; color: #64748b;';
                
                item.appendChild(icon);
                item.appendChild(nombre);
                item.appendChild(tamano);
                lista.appendChild(item);
            });
            
            previewContainer.appendChild(lista);
        });
    });
});

function formatearTamano(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}