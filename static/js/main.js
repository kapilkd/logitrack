// SIDEBAR ACCORDION
document.querySelectorAll('.sidebar-group-toggle').forEach(toggle => {
    toggle.addEventListener('click', () => {
        toggle.closest('.sidebar-group').classList.toggle('is-open');
    });
});

// MOBILE SIDEBAR / NAV TOGGLE
const hamburger = document.getElementById('navHamburger');
const sidebar = document.getElementById('profileSidebar');
const overlay = document.getElementById('sidebarOverlay');

if (hamburger) {
    if (!sidebar) {
        // Public pages (landing, login, register, etc.) — hamburger opens a nav dropdown
        const navLinks = document.querySelector('.nav-links');
        if (navLinks) {
            document.body.classList.add('no-sidebar');
            hamburger.addEventListener('click', (e) => {
                e.stopPropagation();
                navLinks.classList.toggle('is-nav-open');
            });
            document.addEventListener('click', () => {
                navLinks.classList.remove('is-nav-open');
            });
        } else {
            hamburger.style.display = 'none';
        }
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

        sidebar.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    sidebar.classList.remove('is-mobile-open');
                    if (overlay) overlay.classList.remove('is-visible');
                }
            });
        });

        window.addEventListener('resize', () => {
            if (window.innerWidth > 768) {
                sidebar.classList.remove('is-mobile-open');
                if (overlay) overlay.classList.remove('is-visible');
            }
        });
    }
}
