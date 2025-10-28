/* ==== Generador automático de colores cíclicos para avatares ==== */

(function() {
    // Definir los 10 colores base
    const coloresBase = [
        'linear-gradient(135deg, #00C9FF, #92FE9D)',
        'linear-gradient(135deg, #FEE140, #FA709A)',
        'linear-gradient(135deg, #84FAB0, #8FD3F4)',
        'linear-gradient(135deg, #A1C4FD, #C2E9FB)',
        'linear-gradient(135deg, #F6D365, #FDA085)',
        'linear-gradient(135deg, #FCCB90, #D57EEB)',
        'linear-gradient(135deg, #F093FB, #F5576C)',
        'linear-gradient(135deg, #667EEA, #764BA2)',
        'linear-gradient(135deg, #43E97B, #38F9D7)',
        'linear-gradient(135deg, #FF9A9E, #FAD0C4)'
    ];

    // Función para generar estilos CSS dinámicamente
    function generarEstilosAvatares() {
        // Encontrar el data-color más alto en el documento
        const avatares = document.querySelectorAll('.avatar-miembro[data-color]');
        let maxColor = 10; // Mínimo 10
        
        avatares.forEach(avatar => {
            const colorId = parseInt(avatar.getAttribute('data-color'));
            if (colorId > maxColor) {
                maxColor = colorId;
            }
        });

        // Generar CSS para todos los colores necesarios
        let estilosCSS = '';
        for (let i = 1; i <= maxColor; i++) {
            const indiceColor = (i - 1) % 10; // Ciclo de 0 a 9
            estilosCSS += `.avatar-miembro[data-color="${i}"] { background: ${coloresBase[indiceColor]}; }\n`;
        }

        // Crear e inyectar la hoja de estilos
        const styleElement = document.createElement('style');
        styleElement.id = 'avatar-colors-dynamic';
        styleElement.textContent = estilosCSS;
        
        // Remover estilos anteriores si existen
        const existente = document.getElementById('avatar-colors-dynamic');
        if (existente) {
            existente.remove();
        }
        
        document.head.appendChild(styleElement);
    }

    // Ejecutar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', generarEstilosAvatares);
    } else {
        generarEstilosAvatares();
    }

    // Exponer función globalmente para contenido dinámico (AJAX, modales, etc.)
    window.actualizarColoresAvatares = generarEstilosAvatares;
})();