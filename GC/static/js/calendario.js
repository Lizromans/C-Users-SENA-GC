let pickers = {};

function abrirCalendario(idInput) {
    let idInicio, idFin, numero;
    
    if (idInput === 'fechaRango_investigacion') {
        idInicio = 'fecha_inicio_7';
        idFin = 'fecha_fin_7';
        numero = 'investigacion';
    } else {
        numero = idInput.split('_')[1];
        idInicio = `fecha_inicio_${numero}`;
        idFin = `fecha_fin_${numero}`;
    }
    
    const campoInicio = document.getElementById(idInicio);
    const campoFin = document.getElementById(idFin);
    
    if (!campoInicio || !campoFin) {
        console.error(`❌ Error: No se encontraron los campos ${idInicio} o ${idFin}`);
        return;
    }
    
    if (!pickers[idInput]) {
        pickers[idInput] = flatpickr(`#${idInput}`, {
            mode: "range",
            dateFormat: "Y-m-d",
            locale: "es",
            minDate: "today", 
            onChange: function(selectedDates, dateStr, instance) {
                if (selectedDates.length === 2) {
                    const fechaInicio = selectedDates[0].toISOString().split('T')[0];
                    campoInicio.value = fechaInicio;
                    
                    const fechaFin = selectedDates[1].toISOString().split('T')[0];
                    campoFin.value = fechaFin;
                    
                    const formatoLegible = `${formatearFecha(selectedDates[0])} - ${formatearFecha(selectedDates[1])}`;
                    instance.input.value = formatoLegible;
                    
                    console.log(`✅ Fechas guardadas para entregable ${numero}:`);
                    console.log(`   - ${idInicio}: ${fechaInicio}`);
                    console.log(`   - ${idFin}: ${fechaFin}`);
                }
            },
            onClose: function(selectedDates, dateStr, instance) {
                if (selectedDates.length < 2) {
                    console.warn(`⚠️ Advertencia: No se seleccionó un rango completo para ${idInput}`);
                    campoInicio.value = '';
                    campoFin.value = '';
                    instance.input.value = '';
                }
            }
        });
    }
    
    pickers[idInput].open();
}

function formatearFecha(fecha) {
    const dia = String(fecha.getDate()).padStart(2, '0');
    const mes = String(fecha.getMonth() + 1).padStart(2, '0');
    const anio = fecha.getFullYear();
    return `${dia}/${mes}/${anio}`;
}

document.addEventListener('DOMContentLoaded', function() {
    const formCrear = document.querySelector('form[action*="crear_proyecto"]');
    
    if (formCrear) {
        formCrear.addEventListener('submit', function(e) {
            const tipoSelect = document.getElementById('tipo');
            if (!tipoSelect) return;
            
            const tipo = tipoSelect.value;
            
            if (tipo === 'sennova' || tipo === 'capacidadinstalada') {
                const fechaInicio7 = document.getElementById('fecha_inicio_7');
                const fechaFin7 = document.getElementById('fecha_fin_7');
                
                if (!fechaInicio7 || !fechaInicio7.value || !fechaFin7 || !fechaFin7.value) {
                    e.preventDefault();
                    alert('⚠️ Error: Debes seleccionar las fechas de inicio y fin del entregable antes de crear el proyecto.');
                    
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
                let faltanFechas = false;
                
                for (let i = 1; i <= 6; i++) {
                    const fechaInicio = document.getElementById(`fecha_inicio_${i}`);
                    const fechaFin = document.getElementById(`fecha_fin_${i}`);
                    
                    if (!fechaInicio || !fechaInicio.value || !fechaFin || !fechaFin.value) {
                        e.preventDefault();
                        alert(`⚠️ Error: Falta seleccionar las fechas del entregable ${i}. Todos los entregables deben tener fechas.`);
                        
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