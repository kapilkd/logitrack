const dropdown = document.getElementById('statusDropdown');
let _activeBadge = null;

function openDropdown(badge) {
  _activeBadge = badge;
  const rect = badge.getBoundingClientRect();
  dropdown.style.top  = (rect.bottom + window.scrollY + 4) + 'px';
  dropdown.style.left = (rect.left  + window.scrollX)      + 'px';
  dropdown.hidden = false;
  dropdown.querySelectorAll('.status-dropdown-item').forEach(item => {
    item.classList.toggle(
      'status-dropdown-item--current',
      item.dataset.value === badge.dataset.status
    );
  });
}

function closeDropdown() {
  dropdown.hidden = true;
  _activeBadge = null;
}

document.querySelectorAll('.status-badge--clickable').forEach(badge => {
  badge.addEventListener('click', e => {
    e.stopPropagation();
    if (!dropdown.hidden && _activeBadge === badge) {
      closeDropdown();
    } else {
      openDropdown(badge);
    }
  });
  badge.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      badge.click();
    }
  });
});

document.addEventListener('click', e => {
  if (!dropdown.hidden && !dropdown.contains(e.target)) closeDropdown();
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeDropdown();
});

dropdown.querySelectorAll('.status-dropdown-item').forEach(item => {
  item.addEventListener('click', () => {
    const newStatus = item.dataset.value;
    const badge     = _activeBadge;
    const id        = badge.dataset.id;
    closeDropdown();

    fetch(`/shipments/${id}/status`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ status: newStatus }),
    })
    .then(r => r.json())
    .then(data => {
      if (!data.ok) return;
      if (newStatus === 'CLOSED') {
        location.reload();
        return;
      }
      [...badge.classList]
        .filter(c => c.startsWith('status-badge--') && c !== 'status-badge--clickable')
        .forEach(c => badge.classList.remove(c));
      badge.classList.add('status-badge--' + newStatus.toLowerCase().replace(/_/g, '-'));
      badge.textContent    = newStatus;
      badge.dataset.status = newStatus;
    });
  });
});

const closedToggle = document.getElementById('closedToggle');
const closedBody   = document.getElementById('closedShipmentsBody');

if (closedToggle && closedBody) {
  closedToggle.addEventListener('click', () => {
    const expanded = closedToggle.getAttribute('aria-expanded') === 'true';
    closedToggle.setAttribute('aria-expanded', String(!expanded));
    closedBody.hidden = expanded;
    closedToggle.querySelector('.closed-toggle-chevron').textContent = expanded ? '▾' : '▴';
  });
}
