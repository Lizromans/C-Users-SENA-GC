document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const sidebar       = document.querySelector('.sidebar');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const body          = document.body;

    function isMobile() { return window.innerWidth < 768; }

    function openSidebar() {
        sidebar.classList.add('mobile-open');
        sidebarOverlay.classList.add('show');
        body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        sidebar.classList.remove('mobile-open');
        sidebarOverlay.classList.remove('show');
        body.style.overflow = '';
    }

    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            sidebar.classList.contains('mobile-open') ? closeSidebar() : openSidebar();
        });
    }

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', closeSidebar);
    }

    // Close when nav link is tapped on mobile
    document.querySelectorAll('.sidebar .nav-link').forEach(link => {
        link.addEventListener('click', function() {
            if (isMobile()) closeSidebar();
        });
    });

    // On resize: close mobile sidebar if switching to desktop
    window.addEventListener('resize', function() {
        if (!isMobile()) {
            sidebar.classList.remove('mobile-open');
            sidebarOverlay.classList.remove('show');
            body.style.overflow = '';
        }
        // Show/hide hamburger button
        if (mobileMenuBtn) {
            mobileMenuBtn.style.display = isMobile() ? 'flex' : 'none';
        }
    });

    // Initial state of hamburger
    if (mobileMenuBtn) {
        mobileMenuBtn.style.display = isMobile() ? 'flex' : 'none';
    }
});