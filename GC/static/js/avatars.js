(function() {
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

    function generarEstilosAvatares() {
        const avatares = document.querySelectorAll('.avatar-miembro[data-color]');
        let maxColor = 10;
        
        avatares.forEach(avatar => {
            const colorId = parseInt(avatar.getAttribute('data-color'));
            if (colorId > maxColor) {
                maxColor = colorId;
            }
        });

        let estilosCSS = '';
        for (let i = 1; i <= maxColor; i++) {
            const indiceColor = (i - 1) % 10; 
            estilosCSS += `.avatar-miembro[data-color="${i}"] { background: ${coloresBase[indiceColor]}; }\n`;
        }

        const styleElement = document.createElement('style');
        styleElement.id = 'avatar-colors-dynamic';
        styleElement.textContent = estilosCSS;
        
        const existente = document.getElementById('avatar-colors-dynamic');
        if (existente) {
            existente.remove();
        }
        
        document.head.appendChild(styleElement);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', generarEstilosAvatares);
    } else {
        generarEstilosAvatares();
    }

    window.actualizarColoresAvatares = generarEstilosAvatares;
})();