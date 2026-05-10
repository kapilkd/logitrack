const shipmentId = window.location.pathname.split('/')[2];

function openModal(id) {
    document.getElementById(id).style.display = 'flex';
}

function closeModal(id) {
    document.getElementById(id).style.display = 'none';
}

// Close on backdrop click
window.addEventListener('click', e => {
    ['addVendorModal', 'editVendorModal', 'addExpenseModal', 'editExpenseModal'].forEach(id => {
        const el = document.getElementById(id);
        if (el && e.target === el) closeModal(id);
    });
});

// Add vendor modal
document.getElementById('openAddVendorModal')?.addEventListener('click', () => openModal('addVendorModal'));
document.getElementById('closeAddVendorModal')?.addEventListener('click', () => closeModal('addVendorModal'));

// Edit vendor modal
document.getElementById('closeEditVendorModal')?.addEventListener('click', () => closeModal('editVendorModal'));

document.querySelectorAll('.edit-sv-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const svId = btn.dataset.id;
        document.getElementById('editSvRelType').value       = btn.dataset.relationshipType;
        document.getElementById('editSvBillingType').value   = btn.dataset.billingType;
        document.getElementById('editSvAmount').value        = btn.dataset.amount;
        document.getElementById('editSvCurrency').value      = btn.dataset.currency;
        document.getElementById('editSvInvoiceNumber').value = btn.dataset.invoiceNumber;
        document.getElementById('editSvInvoiceDate').value   = btn.dataset.invoiceDate;
        document.getElementById('editSvDueDate').value       = btn.dataset.dueDate;
        document.getElementById('editSvPaymentStatus').value = btn.dataset.paymentStatus;
        document.getElementById('editSvNotes').value         = btn.dataset.notes;
        document.getElementById('editVendorForm').action     = `/shipments/${shipmentId}/vendors/${svId}/edit`;
        openModal('editVendorModal');
    });
});

// Delete vendor assignment
document.querySelectorAll('.delete-sv-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        if (!confirm('Remove this vendor assignment? This cannot be undone.')) return;
        fetch(`/shipments/${shipmentId}/vendors/${btn.dataset.id}/delete`, { method: 'POST' })
            .then(r => r.json())
            .then(d => { if (d.ok) location.reload(); });
    });
});

// Add expense modal
document.getElementById('openAddExpenseModal')?.addEventListener('click', () => openModal('addExpenseModal'));
document.getElementById('closeAddExpenseModal')?.addEventListener('click', () => closeModal('addExpenseModal'));

// Edit expense modal
document.getElementById('closeEditExpenseModal')?.addEventListener('click', () => closeModal('editExpenseModal'));

document.querySelectorAll('.edit-expense-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const expId = btn.dataset.id;
        document.getElementById('editExpAmount').value      = btn.dataset.amount;
        document.getElementById('editExpCategory').value   = btn.dataset.category;
        document.getElementById('editExpDate').value        = btn.dataset.date;
        document.getElementById('editExpDescription').value = btn.dataset.description;
        document.getElementById('editExpenseForm').action  = `/shipments/${shipmentId}/expenses/${expId}/edit`;
        openModal('editExpenseModal');
    });
});

// Delete expense
document.querySelectorAll('.delete-expense-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        if (!confirm('Delete this expense? This cannot be undone.')) return;
        fetch(`/shipments/${shipmentId}/expenses/${btn.dataset.id}/delete`, { method: 'POST' })
            .then(r => r.json())
            .then(d => { if (d.ok) location.reload(); });
    });
});
