// ── Add Vendor modal ─────────────────────────────────────────
const addModal    = document.getElementById("addVendorModal");
const openAddBtn  = document.getElementById("openAddVendorModal");
const closeAddBtn = document.getElementById("closeAddVendorModal");

if (openAddBtn)  openAddBtn.addEventListener("click", () => { addModal.style.display = "flex"; });
if (closeAddBtn) closeAddBtn.addEventListener("click", () => { addModal.style.display = "none"; });
if (addModal)    addModal.addEventListener("click", (e) => { if (e.target === addModal) addModal.style.display = "none"; });

// ── Edit Vendor modal ─────────────────────────────────────────
const editModal    = document.getElementById("editVendorModal");
const editForm     = document.getElementById("editVendorForm");
const closeEditBtn = document.getElementById("closeEditVendorModal");

if (closeEditBtn) closeEditBtn.addEventListener("click", () => { editModal.style.display = "none"; });
if (editModal)    editModal.addEventListener("click", (e) => { if (e.target === editModal) editModal.style.display = "none"; });

// Field name → element id mapping for the edit modal
const EDIT_FIELD_MAP = {
    vendor_code:        "editVendorCode",
    vendor_name:        "editVendorName",
    vendor_type:        "editVendorType",
    vendor_category:    "editVendorCategory",
    company_name:       "editCompanyName",
    owner_name:         "editOwnerName",
    status:             "editStatus",
    email:              "editEmail",
    phone:              "editPhone",
    alternate_phone:    "editAlternatePhone",
    website:            "editWebsite",
    address_line1:      "editAddressLine1",
    address_line2:      "editAddressLine2",
    city:               "editCity",
    state:              "editState",
    pincode:            "editPincode",
    gst_number:         "editGstNumber",
    pan_number:         "editPanNumber",
    iec_code:           "editIecCode",
    bank_name:          "editBankName",
    account_number:     "editAccountNumber",
    ifsc_code:          "editIfscCode",
    upi_id:             "editUpiId",
    currency:           "editCurrency",
    credit_limit:       "editCreditLimit",
    payment_terms_days: "editPaymentTermsDays",
    notes:              "editNotes",
};

document.querySelectorAll(".vendor-edit-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        const vendor = JSON.parse(btn.dataset.vendor);

        // Set form POST action
        editForm.action = `/vendors/${vendor.id}/edit`;

        // Populate every field
        for (const [field, elId] of Object.entries(EDIT_FIELD_MAP)) {
            const el = document.getElementById(elId);
            if (!el) continue;
            el.value = vendor[field] ?? "";
        }

        editModal.style.display = "flex";
    });
});

// ── Contacts modal ────────────────────────────────────────────
const contactsModal        = document.getElementById("contactsModal");
const closeContactsBtn     = document.getElementById("closeContactsModal");
const contactsListEl       = document.getElementById("contactsList");
const contactsVendorNameEl = document.getElementById("contactsModalVendorName");
const addContactForm       = document.getElementById("addContactForm");
const addContactLabel      = document.getElementById("addContactLabel");
const editContactSection   = document.getElementById("editContactSection");
const editContactForm      = document.getElementById("editContactForm");
const cancelEditContact    = document.getElementById("cancelEditContact");

let _activeVendorId = null;

if (closeContactsBtn) closeContactsBtn.addEventListener("click", () => {
    contactsModal.style.display = "none";
    _activeVendorId = null;
});
if (contactsModal) contactsModal.addEventListener("click", (e) => {
    if (e.target === contactsModal) {
        contactsModal.style.display = "none";
        _activeVendorId = null;
    }
});

function _esc(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function _showAddForm() {
    addContactForm.style.display    = "";
    addContactLabel.style.display   = "";
    editContactSection.style.display = "none";
}

function _showEditForm() {
    addContactForm.style.display    = "none";
    addContactLabel.style.display   = "none";
    editContactSection.style.display = "";
}

function _resetAddForm() {
    addContactForm.reset();
    document.getElementById("newContactIsPrimaryHidden").value = "0";
}

function _bindContactRowButtons() {
    if (!contactsListEl) return;

    contactsListEl.querySelectorAll(".contact-delete-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            if (!confirm("Delete this contact? This cannot be undone.")) return;
            const cid = btn.dataset.contactId;
            fetch(`/vendors/${_activeVendorId}/contacts/${cid}/delete`, { method: "POST" })
                .then((r) => r.json())
                .then((data) => { if (data.ok) fetchAndRender(_activeVendorId); });
        });
    });

    contactsListEl.querySelectorAll(".contact-edit-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            const c = JSON.parse(btn.dataset.contact);
            document.getElementById("editContactName").value  = c.name  ?? "";
            document.getElementById("editContactTitle").value = c.title ?? "";
            document.getElementById("editContactPhone").value = c.phone ?? "";
            document.getElementById("editContactEmail").value = c.email ?? "";
            document.getElementById("editContactNotes").value = c.notes ?? "";
            const isPrimary = !!c.is_primary;
            document.getElementById("editContactIsPrimary").checked = isPrimary;
            document.getElementById("editContactIsPrimaryHidden").value = isPrimary ? "1" : "0";
            editContactForm.action = `/vendors/${_activeVendorId}/contacts/${c.id}/edit`;
            _showEditForm();
        });
    });
}

function renderContacts(contacts) {
    if (!contactsListEl) return;
    if (!contacts.length) {
        contactsListEl.innerHTML = '<p class="contacts-empty">No contacts yet. Add one below.</p>';
        return;
    }
    contactsListEl.innerHTML = contacts.map((c) => {
        const primaryBadge = c.is_primary
            ? '<span class="contact-primary-badge">Primary</span>'
            : "";
        const detailParts = [c.title, c.phone, c.email].filter(Boolean).map(_esc);
        const detail = detailParts.length
            ? `<span class="contact-row-detail">${detailParts.join(' &middot; ')}</span>`
            : "";
        const notes = c.notes
            ? `<span class="contact-row-notes">${_esc(c.notes)}</span>`
            : "";
        return `
          <div class="contact-row" data-contact-id="${c.id}">
            <div class="contact-row-left">
              <div class="contact-row-top">
                <span class="contact-row-name">${_esc(c.name)}</span>${primaryBadge}${detail}
              </div>
              ${notes}
            </div>
            <div class="contact-row-actions">
              <button class="txn-btn txn-btn--edit contact-edit-btn"
                      data-contact='${JSON.stringify(c).replace(/'/g, "&#39;")}'>Edit</button>
              <button class="txn-btn txn-btn--delete contact-delete-btn"
                      data-contact-id="${c.id}">Delete</button>
            </div>
          </div>`;
    }).join("");
    _bindContactRowButtons();
}

function fetchAndRender(vendorId) {
    contactsListEl.innerHTML = '<p class="contacts-empty">Loading&hellip;</p>';
    fetch(`/vendors/${vendorId}/contacts`)
        .then((r) => r.json())
        .then((data) => renderContacts(data))
        .catch(() => {
            contactsListEl.innerHTML = '<p class="contacts-empty">Failed to load contacts.</p>';
        });
}

document.querySelectorAll(".vendor-contacts-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        _activeVendorId = parseInt(btn.dataset.vendorId, 10);
        contactsVendorNameEl.textContent = btn.dataset.vendorName;
        addContactForm.action = `/vendors/${_activeVendorId}/contacts/add`;
        _resetAddForm();
        _showAddForm();
        fetchAndRender(_activeVendorId);
        contactsModal.style.display = "flex";
    });
});

addContactForm.addEventListener("submit", (e) => {
    e.preventDefault();
    document.getElementById("newContactIsPrimaryHidden").value =
        document.getElementById("newContactIsPrimary").checked ? "1" : "0";
    fetch(addContactForm.action, { method: "POST", body: new FormData(addContactForm) })
        .then(() => { _resetAddForm(); fetchAndRender(_activeVendorId); });
});

editContactForm.addEventListener("submit", (e) => {
    e.preventDefault();
    document.getElementById("editContactIsPrimaryHidden").value =
        document.getElementById("editContactIsPrimary").checked ? "1" : "0";
    fetch(editContactForm.action, { method: "POST", body: new FormData(editContactForm) })
        .then(() => { _showAddForm(); fetchAndRender(_activeVendorId); });
});

cancelEditContact.addEventListener("click", () => { _showAddForm(); });
