document.addEventListener('DOMContentLoaded', function() {
    const particles = document.querySelectorAll('.particle');
    
    function animateParticles() {
        particles.forEach((particle, index) => {
            const randomX = Math.random() * 40 - 20;
            const randomY = Math.random() * 40 - 20;
            particle.style.transform += ` translate(${randomX}px, ${randomY}px)`;
        });
    }
    
    setInterval(animateParticles, 3000);
    document.addEventListener('mousemove', (e) => {
        const mouseX = e.clientX / window.innerWidth;
        const mouseY = e.clientY / window.innerHeight;
        
        particles.forEach((particle, index) => {
            const moveX = (mouseX - 0.5) * 10 * (index + 1);
            const moveY = (mouseY - 0.5) * 10 * (index + 1);
            
            particle.style.transform = `translate(${moveX}px, ${moveY}px)`;
        });
    });
});