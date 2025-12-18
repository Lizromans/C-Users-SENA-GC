// Objeto para guardar todas las instancias de flatpickr
let pickers = {};

function abrirCalendario(idInput) {
    // Determinar los IDs de los campos hidden según el input
    let idInicio, idFin, numero;
    
    if (idInput === 'fechaRango_investigacion') {
        // Para proyectos Sennova/Capacidad Instalada
        idInicio = 'fecha_inicio_7';
        idFin = 'fecha_fin_7';
        numero = 'investigacion';
    } else {
        // Para proyectos formativos (fechaRango_1, fechaRango_2, etc.)
        numero = idInput.split('_')[1];
        idInicio = `fecha_inicio_${numero}`;
        idFin = `fecha_fin_${numero}`;
    }
    
    // Verificar que los campos existen
    const campoInicio = document.getElementById(idInicio);
    const campoFin = document.getElementById(idFin);
    
    if (!campoInicio || !campoFin) {
        console.error(`❌ Error: No se encontraron los campos ${idInicio} o ${idFin}`);
        return;
    }
    
    // Si no existe un picker para este input, crearlo
    if (!pickers[idInput]) {
        pickers[idInput] = flatpickr(`#${idInput}`, {
            mode: "range",
            dateFormat: "Y-m-d",
            locale: "es",
            minDate: "today", // No permitir fechas pasadas
            onChange: function(selectedDates, dateStr, instance) {
                // Cuando se seleccionan ambas fechas
                if (selectedDates.length === 2) {
                    // Guardar fecha de inicio
                    const fechaInicio = selectedDates[0].toISOString().split('T')[0];
                    campoInicio.value = fechaInicio;
                    
                    // Guardar fecha de fin
                    const fechaFin = selectedDates[1].toISOString().split('T')[0];
                    campoFin.value = fechaFin;
                    
                    // Actualizar el campo visible con formato legible
                    const formatoLegible = `${formatearFecha(selectedDates[0])} - ${formatearFecha(selectedDates[1])}`;
                    instance.input.value = formatoLegible;
                    
                    // Debug en consola
                    console.log(`✅ Fechas guardadas para entregable ${numero}:`);
                    console.log(`   - ${idInicio}: ${fechaInicio}`);
                    console.log(`   - ${idFin}: ${fechaFin}`);
                }
            },
            onClose: function(selectedDates, dateStr, instance) {
                // Validar que se seleccionaron ambas fechas al cerrar
                if (selectedDates.length < 2) {
                    console.warn(`⚠️ Advertencia: No se seleccionó un rango completo para ${idInput}`);
                    // Limpiar los campos si no se seleccionó rango completo
                    campoInicio.value = '';
                    campoFin.value = '';
                    instance.input.value = '';
                }
            }
        });
    }
    
    // Abrir el calendario
    pickers[idInput].open();
}

// Función auxiliar para formatear fechas de forma legible (DD/MM/YYYY)
function formatearFecha(fecha) {
    const dia = String(fecha.getDate()).padStart(2, '0');
    const mes = String(fecha.getMonth() + 1).padStart(2, '0');
    const anio = fecha.getFullYear();
    return `${dia}/${mes}/${anio}`;
}

// Validación adicional al enviar el formulario
document.addEventListener('DOMContentLoaded', function() {
    const formCrear = document.querySelector('form[action*="crear_proyecto"]');
    
    if (formCrear) {
        formCrear.addEventListener('submit', function(e) {
            const tipoSelect = document.getElementById('tipo');
            if (!tipoSelect) return;
            
            const tipo = tipoSelect.value;
            
            // Validar fechas según el tipo de proyecto
            if (tipo === 'sennova' || tipo === 'capacidadinstalada') {
                // Validar entregable único para Sennova/Capacidad Instalada
                const fechaInicio7 = document.getElementById('fecha_inicio_7');
                const fechaFin7 = document.getElementById('fecha_fin_7');
                
                if (!fechaInicio7 || !fechaInicio7.value || !fechaFin7 || !fechaFin7.value) {
                    e.preventDefault();
                    alert('⚠️ Error: Debes seleccionar las fechas de inicio y fin del entregable antes de crear el proyecto.');
                    
                    // Resaltar el campo que falta
                    const campoRango = document.getElementById('fechaRango_investigacion');
                    if (campoRango) {
                        campoRango.style.border = '2px solid red';
                        campoRango.focus();
                        setTimeout(() => {
                            campoRango.style.border = '';
                        }, 3000);
                    }
                    return false;
                }
                
                console.log('✅ Validación pasada - Fechas Sennova/Capacidad:');
                console.log(`   - Inicio: ${fechaInicio7.value}`);
                console.log(`   - Fin: ${fechaFin7.value}`);
                
            } else if (tipo === 'formativo') {
                // Validar los 6 entregables formativos
                let faltanFechas = false;
                
                for (let i = 1; i <= 6; i++) {
                    const fechaInicio = document.getElementById(`fecha_inicio_${i}`);
                    const fechaFin = document.getElementById(`fecha_fin_${i}`);
                    
                    if (!fechaInicio || !fechaInicio.value || !fechaFin || !fechaFin.value) {
                        e.preventDefault();
                        alert(`⚠️ Error: Falta seleccionar las fechas del entregable ${i}. Todos los entregables deben tener fechas.`);
                        
                        // Resaltar el campo que falta
                        const campoRango = document.getElementById(`fechaRango_${i}`);
                        if (campoRango) {
                            campoRango.style.border = '2px solid red';
                            campoRango.focus();
                            setTimeout(() => {
                                campoRango.style.border = '';
                            }, 3000);
                        }
                        faltanFechas = true;
                        break;
                    }
                }
                
                if (!faltanFechas) {
                    console.log('✅ Validación pasada - Fechas de todos los entregables formativos');
                }
                
                return !faltanFechas;
            }
        });
    }
});