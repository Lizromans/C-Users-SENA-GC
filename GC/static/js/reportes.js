// Script para campos dinámicos del constructor de reportes
document.addEventListener('DOMContentLoaded', function() {
    const checkboxes = document.querySelectorAll('input[name="categoria"]');
    const camposDinamicos = document.getElementById('campos-dinamicos');
    
    const camposPorCategoria = {
        semilleros: [
            'Código de Semillero',
            'Nombre del Semillero',
            'Siglas',
            'Descripción',
            'Progreso',
            'Objetivos',
            'Líder de Semillero',
            'Fecha de Creación',
            'Estado Actual',
            'Número de Integrantes',
            'Cantidad de Proyectos'
        ],
        proyectos: [
            'Título del Proyecto',
            'Tipo de Proyecto',
            'Estado',
            'Fecha de Creación',
            'Porcentaje de Avance',
            'Lider',
            'Línea Tecnológica',
            'Línea de Investigación',
            'Línea de Semillero',
            'Participantes De Proyecto',
            'Notas',
            'Programa de Formación'
        ],
        miembros: [
            'Nombre Completo',
            'Tipo de Documento',
            'Documento',
            'Rol',
            'Email',
            'Teléfono',
            'Programa de Formación',
            'Ficha',
            'Modalidad'
        ],
        entregables: [
            'Nombre del Entregable',
            'Estado',
            'Descripción',
            'Fecha de Entrega',
            'Proyecto Asociado',
            'Responsable'
        ]
    };
    
    // Event listener para actualizar campos dinámicos
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', actualizarCampos);
    });
    
    function actualizarCampos() {
        const categoriasSeleccionadas = Array.from(checkboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.value);
        
        if (categoriasSeleccionadas.length === 0) {
            camposDinamicos.innerHTML = `
                <p class="info-texto">
                    <i class="fas fa-info-circle"></i> 
                    Selecciona las categorías para ver los campos disponibles
                </p>
            `;
            return;
        }
        
        let html = '<div class="campos-grid">';
        
        categoriasSeleccionadas.forEach(categoria => {
            html += `<div class="categoria-campos">
                <h4 class="categoria-titulo">${categoria.charAt(0).toUpperCase() + categoria.slice(1)}</h4>
                <div class="campos-lista">`;
            
            camposPorCategoria[categoria].forEach(campo => {
                html += `
                    <label class="campo-check">
                        <input type="checkbox" name="campo_${categoria}" value="${campo}">
                        <span>${campo}</span>
                    </label>
                `;
            });
            
            html += '</div></div>';
        });
        
        html += '</div>';
        camposDinamicos.innerHTML = html;
    }

    // VALIDACIÓN Y ENVÍO DEL FORMULARIO
    document.getElementById('btn-generar').addEventListener('click', function(e) {
        e.preventDefault();
        
        // 1. Validar categorías
        const categoriasSeleccionadas = document.querySelectorAll('input[name="categoria"]:checked');
        
        if (categoriasSeleccionadas.length === 0) {
            mostrarMensajeExito('⚠️ Debe seleccionar al menos una categoría para crear el reporte', 'warning');
            
            // Hacer scroll hacia las categorías
            document.querySelector('.contenedor-categorias').scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center' 
            });
            
            return false;
        }
        
        // 2. Validar formato
        const formatoSeleccionado = document.querySelector('input[name="formato"]:checked');
        
        if (!formatoSeleccionado) {
            mostrarMensajeExito('⚠️ Debe seleccionar un formato de exportación (Excel o PDF)', 'warning');
            
            document.getElementById('formato').scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center' 
            });
            
            return false;
        }
        
        // 3. Log para debug (opcional)
        const categoriasTexto = Array.from(categoriasSeleccionadas)
            .map(c => c.value)
            .join(', ');
        
        console.log(`Generando reporte con categorías: ${categoriasTexto}`);
        console.log(`Formato seleccionado: ${formatoSeleccionado.value}`);
        
        // 4. Mostrar mensaje de éxito y enviar formulario
        mostrarMensajeExito('✓ Generando reporte personalizado...', 'info');
        
        // Pequeño delay para que el usuario vea el mensaje
        setTimeout(() => {
            document.getElementById('form-reportes').submit();
        }, 500);
    });

    // BOTÓN LIMPIAR
    document.getElementById('btn-limpiar').addEventListener('click', function() {
        // Desmarcar todas las categorías
        document.querySelectorAll('input[name="categoria"]:checked').forEach(checkbox => {
            checkbox.checked = false;
        });
        
        // Resetear campos dinámicos
        camposDinamicos.innerHTML = `
            <p class="info-texto">
                <i class="fas fa-info-circle"></i> 
                Selecciona las categorías para ver los campos disponibles
            </p>
        `;
        
        // Limpiar nombre de plantilla
        const nombrePlantilla = document.getElementById('nombre-plantilla');
        if (nombrePlantilla) {
            nombrePlantilla.value = '';
        }
        
        // Marcar Excel como formato por defecto
        const excelRadio = document.querySelector('input[name="formato"][value="excel"]');
        if (excelRadio) {
            excelRadio.checked = true;
        }
        
        mostrarMensajeExito('✓ Formulario limpiado correctamente', 'success');
    });
});

// FUNCIÓN PARA MOSTRAR MENSAJES
function mostrarMensajeExito(mensaje, tipo) {
    const estilos = {
        success: {
            background: "#dff0d8",
            border: "1px solid #d6e9c6",
            color: "#3c763d"
        },
        error: {
            background: "#f2dede",
            border: "1px solid #ebccd1",
            color: "#a94442"
        },
        danger: {
            background: "#f2dede",
            border: "1px solid #ebccd1",
            color: "#a94442"
        },
        warning: {
            background: "#fcf8e3",
            border: "1px solid #faebcc",
            color: "#8a6d3b"
        },
        info: {
            background: "#d9edf7",
            border: "1px solid #bce8f1",
            color: "black"
        }
    };

    const estiloSeleccionado = estilos[tipo] || estilos.info;

    const mensajeDiv = document.createElement('div');
    mensajeDiv.textContent = mensaje;
    mensajeDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${estiloSeleccionado.background};
        color: ${estiloSeleccionado.color};
        border: ${estiloSeleccionado.border};
        padding: 15px 30px 15px 20px;
        border-radius: 8px;
        z-index: 10000;
        box-shadow: 0 2px 8px rgba(0,0,0,0.25);
        font-weight: 500;
        opacity: 0;
        transform: translateY(-20px);
        transition: opacity .3s ease, transform .3s ease;
    `;

    // Botón de cerrar
    const closeBtn = document.createElement('button');
    closeBtn.innerHTML = '&times;';
    closeBtn.style.cssText = `
        position: absolute;
        top: 2px;
        right: 10px;
        background: none;
        border: none;
        font-size: 20px;
        cursor: pointer;
        color: inherit;
    `;
    
    closeBtn.onclick = function() {
        mensajeDiv.style.opacity = "0";
        mensajeDiv.style.transform = "translateY(-20px)";
        setTimeout(() => mensajeDiv.remove(), 300);
    };

    mensajeDiv.appendChild(closeBtn);
    document.body.appendChild(mensajeDiv);

    // Animación de entrada
    setTimeout(() => {
        mensajeDiv.style.opacity = "1";
        mensajeDiv.style.transform = "translateY(0)";
    }, 50);

    // Auto-cierre después de 4 segundos
    setTimeout(() => {
        mensajeDiv.style.opacity = "0";
        mensajeDiv.style.transform = "translateY(-20px)";
        setTimeout(() => mensajeDiv.remove(), 300);
    }, 4000);
}