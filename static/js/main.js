// SIDEBAR ACCORDION
document.querySelectorAll('.sidebar-group-toggle').forEach(toggle => {
    toggle.addEventListener('click', () => {
        toggle.closest('.sidebar-group').classList.toggle('is-open');
    });
});

// MOBILE SIDEBAR TOGGLE
const hamburger = document.getElementById('navHamburger');
const sidebar = document.getElementById('profileSidebar');
const overlay = document.getElementById('sidebarOverlay');

if (hamburger) {
    if (!sidebar) {
        hamburger.style.display = 'none';
    } else {
        hamburger.addEventListener('click', () => {
            sidebar.classList.toggle('is-mobile-open');
            if (overlay) overlay.classList.toggle('is-visible');
        });

        if (overlay) {
            overlay.addEventListener('click', () => {
                sidebar.classList.remove('is-mobile-open');
                overlay.classList.remove('is-visible');
            });
        }

        // Close sidebar when a nav link is clicked on mobile
        sidebar.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    sidebar.classList.remove('is-mobile-open');
                    if (overlay) overlay.classList.remove('is-visible');
                }
            });
        });

        // Clean up when resizing back to desktop
        window.addEventListener('resize', () => {
            if (window.innerWidth > 768) {
                sidebar.classList.remove('is-mobile-open');
                if (overlay) overlay.classList.remove('is-visible');
            }
        });
    }
}
