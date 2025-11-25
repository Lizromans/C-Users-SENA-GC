// FORMULARIO DE REGISTRO APRENDIZ SENA - VALIDACIÓN COMPLETA

document.addEventListener('DOMContentLoaded', function() {
    
    // ===== ELEMENTOS DEL DOM =====
    const form = document.getElementById('aprendizForm');
    const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
    const autosaveIndicator = document.getElementById('autosaveIndicator');
    
    // Variables de control
    let currentSection = 1;
    
    // ===== DETECTAR ERRORES DEL BACKEND Y NAVEGAR =====
    function detectAndNavigateToErrors() {
        // Buscar todos los campos con errores
        const invalidFields = document.querySelectorAll('.is-invalid');
        
        if (invalidFields.length > 0) {
            // Encontrar la primera sección con error
            const firstInvalidField = invalidFields[0];
            const section = firstInvalidField.closest('.form-section');
            
            if (section) {
                const sectionNumber = parseInt(section.getAttribute('data-section'));
                
                // Navegar a esa sección
                goToSection(sectionNumber);
                
                // Scroll al primer campo con error
                setTimeout(() => {
                    firstInvalidField.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'center' 
                    });
                    
                    // Resaltar el campo con error
                    firstInvalidField.focus();
                    
                    // Mostrar mensaje
                    console.log(`⚠️ Error encontrado en Sección ${sectionNumber}`);
                }, 400);
                
                // Marcar pasos con errores en el sidebar
                markSectionsWithErrors();
            }
        }
    }
    
    // Marcar visualmente las secciones con errores
    function markSectionsWithErrors() {
        const sections = document.querySelectorAll('.form-section[data-section]');
        
        sections.forEach(section => {
            const sectionNumber = parseInt(section.getAttribute('data-section'));
            const hasErrors = section.querySelectorAll('.is-invalid').length > 0;
            const progressStep = document.querySelector(`.progress-step[data-step="${sectionNumber}"]`);
            
            if (progressStep) {
                const stepNumber = progressStep.querySelector('.step-number');
                
                if (hasErrors) {
                    // Marcar con error
                    progressStep.classList.remove('completed');
                    progressStep.classList.add('has-error');
                    
                    if (stepNumber) {
                        stepNumber.style.borderColor = '#dc3545';
                        stepNumber.style.borderWidth = '3px';
                        stepNumber.style.background = 'rgba(220, 53, 69, 0.1)';
                    }
                } else {
                    progressStep.classList.remove('has-error');
                    
                    if (stepNumber) {
                        stepNumber.style.borderColor = '';
                        stepNumber.style.borderWidth = '';
                        stepNumber.style.background = '';
                    }
                }
            }
        });
    }
    
    // Ejecutar detección de errores al cargar
    setTimeout(detectAndNavigateToErrors, 100);
    
    // ===== INICIALIZAR TOOLTIPS =====
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // ===== ACTUALIZAR PROGRESO Y MARCAR SECCIONES COMPLETAS =====
    function updateProgress() {
        const sections = document.querySelectorAll('.form-section[data-section]');
        
        sections.forEach((section, index) => {
            const sectionNumber = parseInt(section.getAttribute('data-section'));
            const inputs = section.querySelectorAll('input, select');
            let allFilled = true;
            
            inputs.forEach(input => {
                if (input.type === 'checkbox') {
                    if (!input.checked && input.hasAttribute('required')) {
                        allFilled = false;
                    }
                } else {
                    if (!input.value.trim() || input.classList.contains('is-invalid')) {
                        allFilled = false;
                    }
                }
            });
            
            // Actualizar el paso en el sidebar
            const progressStep = document.querySelector(`.progress-step[data-step="${sectionNumber}"]`);
            if (progressStep) {
                if (allFilled) {
                    progressStep.classList.add('completed');
                    // Cambiar el número por un check
                    const stepNumber = progressStep.querySelector('.step-number');
                    if (stepNumber && !stepNumber.classList.contains('checked')) {
                        stepNumber.classList.add('checked');
                        stepNumber.innerHTML = '<i class="bi bi-check-lg"></i>';
                    }
                } else {
                    progressStep.classList.remove('completed');
                    // Restaurar el número
                    const stepNumber = progressStep.querySelector('.step-number');
                    if (stepNumber && stepNumber.classList.contains('checked')) {
                        stepNumber.classList.remove('checked');
                        stepNumber.textContent = sectionNumber;
                    }
                }
            }
        });
    }
    
    // ===== NAVEGACIÓN ENTRE SECCIONES =====
    const nextButtons = document.querySelectorAll('.btn-next');
    const prevButtons = document.querySelectorAll('.btn-prev');
    
    nextButtons.forEach(button => {
        button.addEventListener('click', function() {
            const nextSection = parseInt(this.getAttribute('data-next'));
            const currentSectionEl = document.querySelector('.form-section.active');
            
            // Validar sección actual antes de avanzar
            const inputs = currentSectionEl.querySelectorAll('input, select');
            let allValid = true;
            
            inputs.forEach(input => {
                if (!validateField(input)) {
                    allValid = false;
                }
            });
            
            if (!allValid) {
                // Mostrar alerta
                const errorCount = currentSectionEl.querySelectorAll('.is-invalid').length;
                alert(`Por favor, completa correctamente ${errorCount} campo(s) antes de continuar.`);
                
                // Scroll al primer error
                const firstError = currentSectionEl.querySelector('.is-invalid');
                if (firstError) {
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    firstError.focus();
                }
                return;
            }
            
            // Cambiar de sección
            goToSection(nextSection);
        });
    });
    
    prevButtons.forEach(button => {
        button.addEventListener('click', function() {
            const prevSection = parseInt(this.getAttribute('data-prev'));
            goToSection(prevSection);
        });
    });
    
    function goToSection(sectionNumber) {
        // Ocultar sección actual
        document.querySelectorAll('.form-section').forEach(section => {
            section.classList.remove('active');
        });
        
        // Mostrar nueva sección
        const targetSection = document.querySelector(`.form-section[data-section="${sectionNumber}"]`);
        if (targetSection) {
            targetSection.classList.add('active');
        }
        
        // Actualizar sidebar
        document.querySelectorAll('.progress-step').forEach(step => {
            step.classList.remove('active');
        });
        
        const activeStep = document.querySelector(`.progress-step[data-step="${sectionNumber}"]`);
        if (activeStep) {
            activeStep.classList.add('active');
        }
        
        currentSection = sectionNumber;
        
        // Scroll al inicio del formulario
        window.scrollTo({ top: 0, behavior: 'smooth' });
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
            // Remover error mientras escribe
            if (this.classList.contains('is-invalid')) {
                validateField(this);
            }
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
            
            // Teléfono (solo números, 10 dígitos, comienza con 3)
            if (field.name === 'telefono' || field.id.includes('telefono')) {
                const phoneRegex = /^3\d{9}$/;
                isValid = phoneRegex.test(value.replace(/\D/g, ''));
            }
            
            // Número de documento
            if (field.name === 'cedula_apre' || field.id.includes('cedula')) {
                const docRegex = /^\d{7,10}$/;
                isValid = docRegex.test(value);
            }
            
            // Número de cuenta
            if (field.name === 'numero_cuenta') {
                const accountRegex = /^\d{6,20}$/;
                isValid = accountRegex.test(value);
            }
            
            // Fecha de nacimiento (debe tener entre 14 y 100 años)
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
        
        // Checkbox requerido
        if (field.type === 'checkbox' && field.hasAttribute('required')) {
            isValid = field.checked;
        }
        
        // Aplicar clases visuales
        if (isValid && (value || field.type === 'checkbox')) {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
        } else if (!isValid) {
            field.classList.add('is-invalid');
            field.classList.remove('is-valid');
        } else {
            field.classList.remove('is-invalid', 'is-valid');
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
    
    // ===== FORMATO AUTOMÁTICO DE NÚMERO DE CUENTA =====
    const accountInput = document.querySelector('input[name="numero_cuenta"]');
    if (accountInput) {
        accountInput.addEventListener('input', function(e) {
            let value = this.value.replace(/\D/g, '');
            if (value.length > 20) {
                value = value.slice(0, 20);
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
            // Encontrar sección con error y navegar
            detectAndNavigateToErrors();
            
            const errorCount = document.querySelectorAll('.is-invalid').length;
            alert(`Se encontraron ${errorCount} error(es). Por favor, corrígelos antes de continuar.`);
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
        
        // Limpiar localStorage después del envío
        localStorage.removeItem('aprendizFormData');
        
        // Enviar formulario
        form.submit();
    });
    
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
    
    console.log('✅ Formulario de Aprendiz SENA inicializado correctamente');
});