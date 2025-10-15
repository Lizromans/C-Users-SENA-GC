document.addEventListener('DOMContentLoaded', () => {
    const objetivosContainer = document.getElementById('objetivos-container');
    const btnAgregar = document.getElementById('btn-agregar-objetivo');

    // Función para actualizar la numeración de los objetivos
    function actualizarNumeracion() {
        const objetivos = objetivosContainer.querySelectorAll('.objetivo-item');
        objetivos.forEach((item, index) => {
            const label = item.querySelector('label');
            label.textContent = `Objetivo ${index + 1} *`;
        });

        // Solo el primer objetivo no puede eliminarse
        const botonesEliminar = objetivosContainer.querySelectorAll('.btn-eliminar-objetivo');
        botonesEliminar.forEach((btn, index) => {
            btn.disabled = (index === 0);
            btn.title = index === 0 ? "Mínimo 1 objetivo" : "Eliminar este objetivo";
        });
    }

    // Función para crear un nuevo objetivo
    function crearObjetivo() {
        const numObjetivos = objetivosContainer.querySelectorAll('.objetivo-item').length;
        const nuevoItem = document.createElement('div');
        nuevoItem.classList.add('objetivo-item');

        nuevoItem.innerHTML = `
            <div class="modal-campo">
                <label for="objetivo_${numObjetivos + 1}">Objetivo ${numObjetivos + 1} *</label>
                <div class="objetivo-input-group">
                    <textarea id="objetivo_${numObjetivos + 1}" name="objetivo" class="objetivo-textarea" placeholder="Describe el objetivo del semillero..." required></textarea>
                    <button type="button" class="btn-eliminar-objetivo" title="Eliminar este objetivo">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            </div>
        `;

        objetivosContainer.appendChild(nuevoItem);
        actualizarNumeracion();
    }

    // Evento para agregar un nuevo objetivo
    btnAgregar.addEventListener('click', crearObjetivo);

    // Delegación de eventos para eliminar un objetivo
    objetivosContainer.addEventListener('click', (e) => {
        if (e.target.closest('.btn-eliminar-objetivo')) {
            const objetivos = objetivosContainer.querySelectorAll('.objetivo-item');
            if (objetivos.length > 1) {
                e.target.closest('.objetivo-item').remove();
                actualizarNumeracion();
            }
        }
    });

    // Inicializar numeración correcta
    actualizarNumeracion();
});

