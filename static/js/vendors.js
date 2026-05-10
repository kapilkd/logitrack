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
