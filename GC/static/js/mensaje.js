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
        max-width: 400px;
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
        line-height: 1;
        opacity: 0.7;
        transition: opacity 0.2s;
    `;
    
    closeBtn.onmouseover = function() {
        closeBtn.style.opacity = "1";
    };
    
    closeBtn.onmouseout = function() {
        closeBtn.style.opacity = "0.7";
    };
    
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