// FORMULARIO DE REGISTRO APRENDIZ SENA - VALIDACIÓN

document.addEventListener('DOMContentLoaded', function() {
    
    // ===== ELEMENTOS DEL DOM =====
    const form = document.getElementById('aprendizForm');
    const submitBtn = document.getElementById('submitBtn');
    const progressBar = document.getElementById('progressBar');
    const progressLabel = document.getElementById('progressLabel');
    const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
    const autosaveIndicator = document.getElementById('autosaveIndicator');
    
    // ===== INICIALIZAR TOOLTIPS =====
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // ===== ACTUALIZAR BARRA DE PROGRESO =====
    function updateProgress() {
        const sections = document.querySelectorAll('fieldset[data-section]');
        const totalSections = sections.length;
        let completedSections = 0;
        
        sections.forEach((section, index) => {
            const inputs = section.querySelectorAll('input, select');
            let allFilled = true;
            
            inputs.forEach(input => {
                if (input.type === 'checkbox') {
                    if (!input.checked && input.hasAttribute('required')) {
                        allFilled = false;
                    }
                } else {
                    if (!input.value.trim()) {
                        allFilled = false;
                    }
                }
            });
            
            if (allFilled) {
                completedSections++;
            }
        });
        
        const progressPercentage = (completedSections / totalSections) * 100;
        progressBar.style.width = progressPercentage + '%';
        progressBar.setAttribute('aria-valuenow', progressPercentage);
        
        const currentSection = Math.min(completedSections + 1, totalSections);
        progressLabel.textContent = `Sección ${currentSection} de ${totalSections}`;
    }
    
    // ===== VALIDACIÓN EN TIEMPO REAL =====
    const inputs = document.querySelectorAll('input, select');
    
    inputs.forEach(input => {
        // Validar al salir del campo
        input.addEventListener('blur', function() {
            validateField(this);
            updateProgress();
        });
        
        // Actualizar progreso mientras escribe
        input.addEventListener('input', function() {
            updateProgress();
            updateCharCounter(this);
        });
        
        // Inicializar contadores
        updateCharCounter(input);
    });
    
    // ===== FUNCIÓN DE VALIDACIÓN DE CAMPO =====
    function validateField(field) {
        const value = field.value.trim();
        let isValid = true;
        
        // Verificar si está vacío y es requerido
        if (field.hasAttribute('required') && !value) {
            isValid = false;
        }
        
        // Validaciones específicas por tipo
        if (value) {
            // Email
            if (field.type === 'email') {
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                isValid = emailRegex.test(value);
            }
            
            // Teléfono (solo números, 10 dígitos)
            if (field.name === 'telefono' || field.id.includes('telefono')) {
                const phoneRegex = /^\d{10}$/;
                isValid = phoneRegex.test(value.replace(/\D/g, ''));
            }
            
            // Número de documento
            if (field.name === 'cedula_apre' || field.id.includes('cedula')) {
                const docRegex = /^\d{6,10}$/;
                isValid = docRegex.test(value);
            }
            
            // Fecha de nacimiento (debe ser mayor de edad)
            if (field.type === 'date' && field.name === 'fecha_nacimiento') {
                const birthDate = new Date(value);
                const today = new Date();
                let age = today.getFullYear() - birthDate.getFullYear();
                const monthDiff = today.getMonth() - birthDate.getMonth();
                
                if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
                    age--;
                }
                
                isValid = age >= 14 && age <= 100;
            }
        }
        
        // Aplicar clases visuales
        if (isValid && value) {
            field.classList.remove('is-invalid');
            field.classList.add('valid');
        } else if (!isValid) {
            field.classList.add('is-invalid');
            field.classList.remove('valid');
        } else {
            field.classList.remove('is-invalid', 'valid');
        }
        
        return isValid;
    }
    
    // ===== CONTADOR DE CARACTERES =====
    function updateCharCounter(input) {
        const counter = document.querySelector(`.char-counter[data-field="${input.name}"], .char-counter[data-field="${input.id}"]`);
        if (counter) {
            const current = input.value.length;
            const max = parseInt(counter.dataset.max);
            const currentSpan = counter.querySelector('.current');
            
            if (currentSpan) {
                currentSpan.textContent = current;
                
                // Cambiar color según proximidad al límite
                if (current >= max * 0.9) {
                    counter.classList.add('danger');
                    counter.classList.remove('warning');
                } else if (current >= max * 0.7) {
                    counter.classList.add('warning');
                    counter.classList.remove('danger');
                } else {
                    counter.classList.remove('warning', 'danger');
                }
            }
        }
    }
    
    // ===== AUTO-CAPITALIZACIÓN DE NOMBRES =====
    const nameInputs = document.querySelectorAll('input[name="nombre"], input[name="apellido"]');
    nameInputs.forEach(input => {
        input.addEventListener('blur', function() {
            this.value = this.value
                .toLowerCase()
                .split(' ')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ');
        });
    });
    
    // ===== FORMATO AUTOMÁTICO DE TELÉFONO =====
    const phoneInput = document.querySelector('input[name="telefono"]');
    if (phoneInput) {
        phoneInput.addEventListener('input', function(e) {
            let value = this.value.replace(/\D/g, '');
            if (value.length > 10) {
                value = value.slice(0, 10);
            }
            this.value = value;
        });
    }
    
    // ===== GUARDADO AUTOMÁTICO (localStorage) =====
    let saveTimeout;
    
    function autosave() {
        clearTimeout(saveTimeout);
        saveTimeout = setTimeout(() => {
            const formData = {};
            
            inputs.forEach(input => {
                if (input.type === 'checkbox') {
                    formData[input.name || input.id] = input.checked;
                } else {
                    formData[input.name || input.id] = input.value;
                }
            });
            
            localStorage.setItem('aprendizFormData', JSON.stringify(formData));
            showAutosaveIndicator('Guardado', true);
        }, 2000);
        
        showAutosaveIndicator('Guardando...', false);
    }
    
    function showAutosaveIndicator(message, saved) {
        const messageSpan = autosaveIndicator.querySelector('.message');
        const spinner = autosaveIndicator.querySelector('.spinner');
        
        messageSpan.textContent = message;
        autosaveIndicator.classList.add('show');
        
        if (saved) {
            spinner.style.display = 'none';
            autosaveIndicator.classList.add('saved');
            
            setTimeout(() => {
                autosaveIndicator.classList.remove('show', 'saved');
                spinner.style.display = 'block';
            }, 2000);
        } else {
            spinner.style.display = 'block';
            autosaveIndicator.classList.remove('saved');
        }
    }
    
    // Escuchar cambios para autosave
    inputs.forEach(input => {
        input.addEventListener('input', autosave);
        input.addEventListener('change', autosave);
    });
    
    // ===== CARGAR DATOS GUARDADOS =====
    function loadSavedData() {
        const savedData = localStorage.getItem('aprendizFormData');
        
        if (savedData) {
            const formData = JSON.parse(savedData);
            
            Object.keys(formData).forEach(key => {
                const input = document.querySelector(`[name="${key}"], #${key}`);
                if (input) {
                    if (input.type === 'checkbox') {
                        input.checked = formData[key];
                    } else {
                        input.value = formData[key];
                    }
                    validateField(input);
                    updateCharCounter(input);
                }
            });
            
            updateProgress();
        }
    }
    
    // Cargar datos al inicio
    loadSavedData();
    
    // ===== MODAL DE CONFIRMACIÓN =====
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Validar todos los campos
        let allValid = true;
        inputs.forEach(input => {
            if (!validateField(input)) {
                allValid = false;
            }
        });
        
        if (!allValid) {
            alert('Por favor, completa todos los campos requeridos correctamente.');
            // Scroll al primer error
            const firstError = document.querySelector('.is-invalid');
            if (firstError) {
                firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                firstError.focus();
            }
            return;
        }
        
        // Generar resumen
        generateSummary();
        
        // Mostrar modal
        confirmModal.show();
    });
    
    // ===== GENERAR RESUMEN PARA MODAL =====
    function generateSummary() {
        const summaryContent = document.getElementById('summaryContent');
        let html = '';
        
        const sections = [
            { title: 'Información Personal', fields: ['tipo_doc', 'cedula_apre', 'nombre', 'apellido', 'fecha_nacimiento', 'telefono'] },
            { title: 'Información Académica', fields: ['ficha', 'modalidad', 'programa', 'correo_per', 'correo_ins'] },
            { title: 'Información Bancaria', fields: ['medio_bancario', 'numero_cuenta'] }
        ];
        
        sections.forEach(section => {
            html += `<h6 class="fw-bold mt-3 mb-2"><i class="bi bi-chevron-right"></i> ${section.title}</h6>`;
            
            section.fields.forEach(fieldName => {
                const input = document.querySelector(`[name="${fieldName}"], #id_${fieldName}`);
                if (input) {
                    const label = document.querySelector(`label[for="${input.id}"]`);
                    let value = input.value;
                    
                    if (input.tagName === 'SELECT') {
                        value = input.options[input.selectedIndex].text;
                    }
                    
                    // Ocultar parcialmente datos sensibles
                    if (fieldName === 'numero_cuenta') {
                        value = '****' + value.slice(-4);
                    }
                    
                    html += `
                        <div class="summary-item">
                            <span class="summary-label">${label ? label.textContent.replace('*', '').replace('?', '').trim() : fieldName}:</span>
                            <span class="summary-value">${value}</span>
                        </div>
                    `;
                }
            });
        });
        
        summaryContent.innerHTML = html;
    }
    
    // ===== CONFIRMAR Y ENVIAR =====
    document.getElementById('confirmSubmit').addEventListener('click', function() {
        confirmModal.hide();
        submitForm();
    });
    
    function submitForm() {
        // Mostrar loading en botón
        submitBtn.classList.add('btn-loading');
        submitBtn.disabled = true;
        submitBtn.querySelector('.spinner-border').classList.remove('d-none');
        submitBtn.querySelector('.btn-text').textContent = 'Enviando...';
        
        // Limpiar localStorage después del envío
        localStorage.removeItem('aprendizFormData');
        
        // Enviar formulario
        form.submit();
    }
    
    // ===== ADVERTENCIA AL SALIR SIN GUARDAR =====
    let formModified = false;
    
    inputs.forEach(input => {
        input.addEventListener('change', () => {
            formModified = true;
        });
    });
    
    window.addEventListener('beforeunload', function(e) {
        if (formModified) {
            e.preventDefault();
            e.returnValue = '¿Estás seguro de que quieres salir? Los cambios no guardados se perderán.';
        }
    });
    
    // No mostrar advertencia después del submit
    form.addEventListener('submit', function() {
        formModified = false;
    });
    
    // ===== INICIALIZAR PROGRESO =====
    updateProgress();
    
    // ===== ACCESIBILIDAD: ANUNCIAR ERRORES =====
    function announceErrors() {
        const errors = document.querySelectorAll('.is-invalid');
        if (errors.length > 0) {
            const announcement = document.createElement('div');
            announcement.setAttribute('role', 'alert');
            announcement.setAttribute('aria-live', 'assertive');
            announcement.className = 'sr-only';
            announcement.textContent = `Se encontraron ${errors.length} errores en el formulario. Por favor, corrígelos antes de continuar.`;
            document.body.appendChild(announcement);
            
            setTimeout(() => {
                document.body.removeChild(announcement);
            }, 3000);
        }
    }
    
    console.log('✅ Formulario de Aprendiz SENA inicializado correctamente');
});