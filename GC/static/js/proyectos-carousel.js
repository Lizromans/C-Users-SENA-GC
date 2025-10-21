// ====== CARRUSEL 3D DE PROYECTOS ======
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar todos los carruseles en la página
    const secciones = document.querySelectorAll('.seccion');
    
    secciones.forEach(seccion => {
        const container = seccion.querySelector('.proyectos-carousel-container');
        if (!container) return;
        
        const track = container.querySelector('.proyectos-carousel-track');
        const cards = Array.from(track.querySelectorAll('.proyecto-card'));
        const leftArrow = container.querySelector('.carousel-nav-arrow.left');
        const rightArrow = container.querySelector('.carousel-nav-arrow.right');
        const dotsContainer = seccion.querySelector('.carousel-dots');
        const dots = dotsContainer ? Array.from(dotsContainer.querySelectorAll('.carousel-dot')) : [];
        
        if (cards.length === 0) return;
        
        let currentIndex = 0;
        
        // Función para actualizar posiciones de las tarjetas
        function updateCarousel() {
            cards.forEach((card, index) => {
                // Remover todas las clases de posición
                card.classList.remove('center', 'left-1', 'left-2', 'right-1', 'right-2', 'hidden');
                
                // Calcular posición relativa
                const diff = index - currentIndex;
                
                if (diff === 0) {
                    card.classList.add('center');
                } else if (diff === -1 || diff === cards.length - 1) {
                    card.classList.add('left-1');
                } else if (diff === -2 || diff === cards.length - 2) {
                    card.classList.add('left-2');
                } else if (diff === 1 || diff === -(cards.length - 1)) {
                    card.classList.add('right-1');
                } else if (diff === 2 || diff === -(cards.length - 2)) {
                    card.classList.add('right-2');
                } else {
                    card.classList.add('hidden');
                }
            });
            
            // Actualizar dots
            if (dots.length > 0) {
                dots.forEach((dot, index) => {
                    dot.classList.toggle('active', index === currentIndex);
                });
            }
            
            // Actualizar visibilidad de flechas si solo hay 1 tarjeta
            if (cards.length === 1) {
                if (leftArrow) leftArrow.style.display = 'none';
                if (rightArrow) rightArrow.style.display = 'none';
            }
        }
        
        // Navegar hacia la izquierda
        function navigateLeft() {
            currentIndex = (currentIndex - 1 + cards.length) % cards.length;
            updateCarousel();
        }
        
        // Navegar hacia la derecha
        function navigateRight() {
            currentIndex = (currentIndex + 1) % cards.length;
            updateCarousel();
        }
        
        // Event listeners para las flechas
        if (leftArrow) {
            leftArrow.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                navigateLeft();
            });
        }
        
        if (rightArrow) {
            rightArrow.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                navigateRight();
            });
        }
        
        // Event listeners para los dots
        dots.forEach((dot, index) => {
            dot.addEventListener('click', () => {
                currentIndex = index;
                updateCarousel();
            });
        });
        
        // Soporte para teclado (solo si el carrusel está en foco)
        container.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                navigateLeft();
            } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                navigateRight();
            }
        });
        
        // Hacer el container focusable
        container.setAttribute('tabindex', '0');
        
        // Navegación táctil (swipe)
        let touchStartX = 0;
        let touchEndX = 0;
        
        container.addEventListener('touchstart', (e) => {
            touchStartX = e.changedTouches[0].screenX;
        }, { passive: true });
        
        container.addEventListener('touchend', (e) => {
            touchEndX = e.changedTouches[0].screenX;
            handleSwipe();
        }, { passive: true });
        
        function handleSwipe() {
            const swipeThreshold = 50;
            const diff = touchStartX - touchEndX;
            
            if (Math.abs(diff) > swipeThreshold) {
                if (diff > 0) {
                    // Swipe left - navegar derecha
                    navigateRight();
                } else {
                    // Swipe right - navegar izquierda
                    navigateLeft();
                }
            }
        }
        
        // Click en tarjetas laterales para navegar
        cards.forEach((card, index) => {
            card.addEventListener('click', () => {
                if (index !== currentIndex) {
                    currentIndex = index;
                    updateCarousel();
                }
            });
        });
        
        // Inicializar el carrusel
        updateCarousel();
        
        // Auto-play opcional (descomentado si lo deseas)
        /*
        let autoPlayInterval = setInterval(() => {
            navigateRight();
        }, 5000);
        
        // Pausar auto-play al hover
        container.addEventListener('mouseenter', () => {
            clearInterval(autoPlayInterval);
        });
        
        container.addEventListener('mouseleave', () => {
            autoPlayInterval = setInterval(() => {
                navigateRight();
            }, 5000);
        });
        */
    });
    
    // ====== MANEJO DE TABS (Resumen / Entregables) ======
    const tabRadios = document.querySelectorAll('.tab-radio');
    
    tabRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            const card = this.closest('.proyecto-card');
            if (!card) return;
            
            // Ocultar todos los tab-content de esta card
            const tabContents = card.querySelectorAll('.tab-content');
            tabContents.forEach(content => {
                content.classList.remove('active');
            });
            
            // Mostrar el tab-content correspondiente
            if (this.id.includes('resumen')) {
                const resumenContent = card.querySelector('.tab-content[data-tab="resumen"]');
                if (resumenContent) resumenContent.classList.add('active');
            } else if (this.id.includes('entregables')) {
                const entregablesContent = card.querySelector('.tab-content[data-tab="entregables"]');
                if (entregablesContent) entregablesContent.classList.add('active');
            }
        });
    });
    
    // Inicializar el primer tab como activo en cada card
    document.querySelectorAll('.proyecto-card').forEach(card => {
        const firstRadio = card.querySelector('.tab-radio:checked');
        if (firstRadio) {
            const resumenContent = card.querySelector('.tab-content[data-tab="resumen"]');
            if (resumenContent) resumenContent.classList.add('active');
        }
    });
});

// ====== FUNCIÓN PARA PREVENIR CLICKS EN ELEMENTOS INTERNOS DE PROPAGARSE ======
document.addEventListener('click', function(e) {
    // Prevenir que clicks en tabs y labels cierren o naveguen el carrusel
    if (e.target.closest('.tab') || e.target.closest('.tabs-header')) {
        e.stopPropagation();
    }
}, true);