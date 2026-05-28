const shipmentId = window.location.pathname.split('/')[2];

function openModal(id) {
    document.getElementById(id).style.display = 'flex';
}

function closeModal(id) {
    document.getElementById(id).style.display = 'none';
}

// Close on backdrop click
window.addEventListener('click', e => {
    ['addPaymentModal', 'addVendorModal', 'editVendorModal', 'addExpenseModal', 'editExpenseModal',
     'addParticularModal', 'editParticularModal', 'assignVendorModal'].forEach(id => {
        const el = document.getElementById(id);
        if (el && e.target === el) closeModal(id);
    });
});

// Add payment modal
document.getElementById('closeAddPaymentModal')?.addEventListener('click', () => closeModal('addPaymentModal'));

document.querySelectorAll('.add-payment-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const svId    = btn.dataset.svId;
        const label   = btn.dataset.label;
        const total   = parseFloat(btn.dataset.total);
        const paid    = parseFloat(btn.dataset.paid);
        const balance = parseFloat(btn.dataset.balance);

        document.getElementById('paymentModalLabel').textContent  = label;
        document.getElementById('paymentModalTotal').textContent   = '₹' + total.toFixed(2);
        document.getElementById('paymentModalPaid').textContent    = '₹' + paid.toFixed(2);
        document.getElementById('paymentModalBalance').textContent = '₹' + balance.toFixed(2);
        document.getElementById('paymentMaxHint').textContent      = 'Max: ₹' + balance.toFixed(2);
        document.getElementById('paymentAmount').max               = balance;
        document.getElementById('paymentAmount').value             = '';
        document.getElementById('paymentReference').value         = '';
        document.getElementById('paymentNotes').value             = '';
        document.getElementById('addPaymentForm').action =
            `/shipments/${shipmentId}/vendors/${svId}/payments/add`;
        openModal('addPaymentModal');
    });
});

// Add vendor modal
document.getElementById('openAddVendorModal')?.addEventListener('click', () => openModal('addVendorModal'));
document.getElementById('closeAddVendorModal')?.addEventListener('click', () => closeModal('addVendorModal'));

document.getElementById('addVendorId')?.addEventListener('change', function () {
    const display = document.getElementById('addSvRelTypeDisplay');
    const hidden  = document.getElementById('addSvRelTypeHidden');
    if (!this.value) {
        display.value = '';
        hidden.value  = '';
        return;
    }
    fetch(`/vendors/${this.value}/info`)
        .then(r => r.json())
        .then(data => {
            hidden.value  = data.vendor_category;
            display.value = data.vendor_category.replace(/_/g, ' ');
        });
});

// Edit vendor modal
document.getElementById('closeEditVendorModal')?.addEventListener('click', () => closeModal('editVendorModal'));

document.querySelectorAll('.edit-sv-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const svId = btn.dataset.id;
        const relType = btn.dataset.relationshipType;
        document.getElementById('editSvRelType').value        = relType;
        document.getElementById('editSvRelTypeDisplay').value = relType.replace(/_/g, ' ');
        document.getElementById('editSvBillingType').value    = btn.dataset.billingType;
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

// Delete individual payment
document.querySelectorAll('.delete-payment-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        if (!confirm('Delete this payment record? This cannot be undone.')) return;
        const svId      = btn.dataset.svId;
        const paymentId = btn.dataset.paymentId;
        fetch(`/shipments/${shipmentId}/vendors/${svId}/payments/${paymentId}/delete`, { method: 'POST' })
            .then(r => r.json())
            .then(d => { if (d.ok) location.reload(); });
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

// ── Particulars ──────────────────────────────────────────────────────────────

function _n(el) { return parseFloat(el ? el.value : 0) || 0; }
function _fmt(v) { return '₹ ' + v.toFixed(2); }

function setupParticularCalc(prefix) {
    const useFormula = document.getElementById(prefix + 'UseFormula');
    const exRate     = document.getElementById(prefix + 'ExRate');
    const weight     = document.getElementById(prefix + 'Weight');
    const qty        = document.getElementById(prefix + 'Qty');
    const offered    = document.getElementById(prefix + 'OfferedRate');
    const expense    = document.getElementById(prefix + 'Expense');
    const taxRate    = document.getElementById(prefix + 'TaxRate');
    const cgst       = document.getElementById(prefix + 'Cgst');
    const sgst       = document.getElementById(prefix + 'Sgst');
    const igst       = document.getElementById(prefix + 'Igst');
    const totalHid   = document.getElementById(prefix + 'Total');
    const totalDisp  = document.getElementById(prefix + 'TotalDisplay');

    if (!useFormula) return;

    function recalc() {
        if (useFormula.checked) {
            expense.value = (_n(exRate) * _n(weight) * _n(qty) * _n(offered)).toFixed(2);
            expense.readOnly = true;
            expense.style.background = 'var(--surface)';
            expense.style.color = 'var(--ink-muted)';
        } else {
            expense.readOnly = false;
            expense.style.background = '';
            expense.style.color = '';
        }
        if (taxRate.value !== '' && _n(taxRate) > 0) {
            var half = (_n(expense) * _n(taxRate) / 100) / 2;
            cgst.value = half.toFixed(2);
            sgst.value = half.toFixed(2);
        }
        var tot = _n(expense) + _n(cgst) + _n(sgst) + _n(igst);
        if (totalDisp) totalDisp.textContent = _fmt(tot);
        if (totalHid) totalHid.value = tot.toFixed(2);
    }

    useFormula.addEventListener('change', recalc);
    [qty, offered, expense, taxRate].forEach(el => el && el.addEventListener('input', recalc));
    [cgst, sgst, igst].forEach(el => {
        if (el) el.addEventListener('input', () => {
            var tot = _n(expense) + _n(cgst) + _n(sgst) + _n(igst);
            if (totalDisp) totalDisp.textContent = _fmt(tot);
            if (totalHid) totalHid.value = tot.toFixed(2);
        });
    });
}

setupParticularCalc('addPart');
setupParticularCalc('editPart');

// "Other" type toggle — add modal
document.getElementById('addPartTypeSelect')?.addEventListener('change', function () {
    document.getElementById('addCustomLabelGroup').style.display = this.value === 'Other' ? 'block' : 'none';
});
document.getElementById('editPartTypeSelect')?.addEventListener('change', function () {
    document.getElementById('editCustomLabelGroup').style.display = this.value === 'Other' ? 'block' : 'none';
});

// Add particular modal
document.getElementById('openAddParticularModal')?.addEventListener('click', () => openModal('addParticularModal'));
document.getElementById('closeAddParticularModal')?.addEventListener('click', () => closeModal('addParticularModal'));

// Edit particular modal
document.getElementById('closeEditParticularModal')?.addEventListener('click', () => closeModal('editParticularModal'));

document.querySelectorAll('.edit-particular-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const pid = btn.dataset.id;
        const ptype = btn.dataset.particularType;
        const sel = document.getElementById('editPartTypeSelect');

        // If this type is in the dropdown, select it; otherwise select Other
        let found = false;
        for (let opt of sel.options) {
            if (opt.value === ptype) { sel.value = ptype; found = true; break; }
        }
        if (!found) {
            sel.value = 'Other';
            document.getElementById('editCustomLabelGroup').style.display = 'block';
            document.getElementById('editCustomLabel').value = ptype;
        } else {
            document.getElementById('editCustomLabelGroup').style.display = 'none';
        }

        document.getElementById('editPartSacHsn').value       = btn.dataset.sacHsn || '';
        document.getElementById('editPartQty').value           = btn.dataset.qty;
        document.getElementById('editPartExRate').value        = btn.dataset.exRate;
        document.getElementById('editPartWeight').value        = btn.dataset.weight;
        document.getElementById('editPartWeightUnit').value    = btn.dataset.weightUnit;
        document.getElementById('editPartOfferedRate').value   = btn.dataset.offeredRate;
        document.getElementById('editPartUseFormula').checked  = btn.dataset.useFormula === 'true';
        document.getElementById('editPartExpense').value       = btn.dataset.expense;
        document.getElementById('editPartTaxRate').value       = btn.dataset.taxRate;
        document.getElementById('editPartCgst').value          = btn.dataset.cgst;
        document.getElementById('editPartSgst').value          = btn.dataset.sgst;
        document.getElementById('editPartIgst').value          = btn.dataset.igst;
        document.getElementById('editPartTotalHidden').value   = btn.dataset.total;
        document.getElementById('editPartCurrency').value      = btn.dataset.currency;
        const tot = parseFloat(btn.dataset.total) || 0;
        document.getElementById('editPartTotalDisplay').textContent = '₹ ' + tot.toFixed(2);
        document.getElementById('editParticularForm').action =
            `/shipments/${shipmentId}/particulars/${pid}/edit`;
        openModal('editParticularModal');
    });
});

// Delete particular
document.querySelectorAll('.delete-particular-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        if (!confirm('Delete this particular? The linked vendor cost (if any) will remain but be unlinked.')) return;
        fetch(`/shipments/${shipmentId}/particulars/${btn.dataset.id}/delete`, { method: 'POST' })
            .then(r => r.json())
            .then(d => { if (d.ok) location.reload(); });
    });
});

// Assign vendor modal
document.getElementById('closeAssignVendorModal')?.addEventListener('click', () => closeModal('assignVendorModal'));

document.querySelectorAll('.assign-vendor-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const pid = btn.dataset.pid;
        const title = document.getElementById('assignVendorModalTitle');
        if (btn.dataset.svId) {
            if (title) title.textContent = 'Edit Vendor Cost';
        } else {
            if (title) title.textContent = 'Assign Vendor to Particular';
        }
        const vendorSel = document.getElementById('assignVendorId');
        if (btn.dataset.vendorId) vendorSel.value = btn.dataset.vendorId;
        else vendorSel.value = '';
        document.getElementById('assignVendorAmount').value        = btn.dataset.amount || '0';
        document.getElementById('assignVendorCurrency').value      = btn.dataset.currency || 'INR';
        document.getElementById('assignVendorInvoiceNumber').value = btn.dataset.invoiceNumber || '';
        document.getElementById('assignVendorInvoiceDate').value   = btn.dataset.invoiceDate   || '';
        document.getElementById('assignVendorDueDate').value       = btn.dataset.dueDate       || '';
        document.getElementById('assignVendorPaymentStatus').value = btn.dataset.paymentStatus || 'PENDING';
        document.getElementById('assignVendorNotes').value         = btn.dataset.notes         || '';
        document.getElementById('assignVendorForm').action =
            `/shipments/${shipmentId}/particulars/${pid}/assign-vendor`;
        openModal('assignVendorModal');
    });
});
