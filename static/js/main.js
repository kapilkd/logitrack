// SIDEBAR ACCORDION
document.querySelectorAll('.sidebar-group-toggle').forEach(toggle => {
    toggle.addEventListener('click', () => {
        toggle.closest('.sidebar-group').classList.toggle('is-open');
    });
});
