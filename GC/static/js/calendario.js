// Objeto para guardar todas las instancias de flatpickr
let pickers = {};

function abrirCalendario(idInput) {
    // Obtener el número del entregable desde el ID
    const numero = idInput.split('_')[1];
    
    // Si no existe un picker para este input, crearlo
    if (!pickers[idInput]) {
        pickers[idInput] = flatpickr(`#${idInput}`, {
            mode: "range",
            dateFormat: "Y-m-d",
            locale: "es",
            onChange: function(selectedDates, dateStr, instance) {
                // Cuando se seleccionan ambas fechas
                if (selectedDates.length === 2) {
                    // Guardar fecha de inicio
                    const fechaInicio = selectedDates[0].toISOString().split('T')[0];
                    document.getElementById(`fecha_inicio_${numero}`).value = fechaInicio;
                    
                    // Guardar fecha de fin
                    const fechaFin = selectedDates[1].toISOString().split('T')[0];
                    document.getElementById(`fecha_fin_${numero}`).value = fechaFin;
                    
                    console.log(`Entregable ${numero}: ${fechaInicio} hasta ${fechaFin}`);
                }
            }
        });
    }
    
    // Abrir el calendario
    pickers[idInput].open();
}
  