document.addEventListener('DOMContentLoaded', function() {
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
        
        function updateCarousel() {
            cards.forEach((card, index) => {
                card.classList.remove('center', 'left-1', 'left-2', 'right-1', 'right-2', 'hidden');
                
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
            
            if (dots.length > 0) {
                dots.forEach((dot, index) => {
                    dot.classList.toggle('active', index === currentIndex);
                });
            }

            if (cards.length === 1) {
                if (leftArrow) leftArrow.style.display = 'none';
                if (rightArrow) rightArrow.style.display = 'none';
            }
        }
        
        function navigateLeft() {
            currentIndex = (currentIndex - 1 + cards.length) % cards.length;
            updateCarousel();
        }
        
        function navigateRight() {
            currentIndex = (currentIndex + 1) % cards.length;
            updateCarousel();
        }
        
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
        
        dots.forEach((dot, index) => {
            dot.addEventListener('click', () => {
                currentIndex = index;
                updateCarousel();
            });
        });
        
        container.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                navigateLeft();
            } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                navigateRight();
            }
        });
        container.setAttribute('tabindex', '0');
        
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
                    navigateRight();
                } else {
                    navigateLeft();
                }
            }
        }
        cards.forEach((card, index) => {
            card.addEventListener('click', () => {
                if (index !== currentIndex) {
                    currentIndex = index;
                    updateCarousel();
                }
            });
        });
        
        updateCarousel();
    });
    
    const tabRadios = document.querySelectorAll('.tab-radio');
    
    tabRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            const card = this.closest('.proyecto-card');
            if (!card) return;
            
            const tabContents = card.querySelectorAll('.tab-content');
            tabContents.forEach(content => {
                content.classList.remove('active');
            });
            
            if (this.id.includes('resumen')) {
                const resumenContent = card.querySelector('.tab-content[data-tab="resumen"]');
                if (resumenContent) resumenContent.classList.add('active');
            } else if (this.id.includes('entregables')) {
                const entregablesContent = card.querySelector('.tab-content[data-tab="entregables"]');
                if (entregablesContent) entregablesContent.classList.add('active');
            }
        });
    });
    
    document.querySelectorAll('.proyecto-card').forEach(card => {
        const firstRadio = card.querySelector('.tab-radio:checked');
        if (firstRadio) {
            const resumenContent = card.querySelector('.tab-content[data-tab="resumen"]');
            if (resumenContent) resumenContent.classList.add('active');
        }
    });
});

document.addEventListener('click', function(e) {
    if (e.target.closest('.tab') || e.target.closest('.tabs-header')) {
        e.stopPropagation();
    }
}, true);