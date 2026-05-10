# Spec: Shipment Management and Vendor Billing Setup

## Overview

This feature introduces Shipments as the primary logistics entity in logitrack, establishing a
**Vendor → Shipment → Expense** hierarchy. A Shipment represents a logistics movement (sea/air
freight job). Expenses are cost line items that belong to a Shipment. Vendors are assigned to
Shipments in operational roles (Transporter, Customer, Consignee, Clearing Agent) with invoice
and payment tracking via the `shipment_vendors` junction table.

The `/shipments` routes are replaced: they now manage Shipment entities. Expense management
moves into the Shipment detail page. A standalone `/expenses/...` route set is added for the
profile page's unlinked expense modals.

## Depends on

- `vendors/01-vendor-management-database-setup` — vendors table and CRUD helpers
- `vendors/02-vendor-internal-contacts` — vendor_contacts table
- Existing expense CRUD helpers in `database/db.py`

## Routes

| Route | Method | Description | Access |
|---|---|---|---|
| `/shipments` | GET | List all shipments for the logged-in user | Login required |
| `/shipments/add` | GET | Add shipment form | Login required |
| `/shipments/add` | POST | Create shipment | Login required |
| `/shipments/<id>` | GET | Shipment detail: expenses + vendor assignments | Login required |
| `/shipments/<id>/edit` | GET | Edit shipment form | Login required, owner only |
| `/shipments/<id>/edit` | POST | Update shipment | Login required, owner only |
| `/shipments/<id>/delete` | POST | Delete shipment → `{"ok": true}` | Login required, owner only |
| `/shipments/<id>/expenses/add` | POST | Add expense to shipment | Login required, owner only |
| `/shipments/<id>/expenses/<eid>/edit` | POST | Edit expense in shipment | Login required, owner only |
| `/shipments/<id>/expenses/<eid>/delete` | POST | Delete expense → `{"ok": true}` | Login required, owner only |
| `/shipments/<id>/vendors/add` | POST | Assign vendor to shipment | Login required, owner only |
| `/shipments/<id>/vendors/<sv_id>/edit` | POST | Update vendor assignment | Login required, owner only |
| `/shipments/<id>/vendors/<sv_id>/delete` | POST | Remove vendor assignment → `{"ok": true}` | Login required, owner only |
| `/expenses/add` | POST | Create standalone expense (profile page) | Login required |
| `/expenses/<id>/edit` | POST | Edit standalone expense | Login required, owner only |
| `/expenses/<id>/delete` | POST | Delete expense → `{"ok": true}` | Login required, owner only |

## Database changes

### New table: `shipments`

```sql
CREATE TABLE IF NOT EXISTS shipments (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL REFERENCES users(id),
    shipment_number   TEXT    NOT NULL,
    origin            TEXT,
    destination       TEXT,
    carrier           TEXT,
    status            TEXT    NOT NULL DEFAULT 'DRAFT',
    shipment_date     TEXT,
    etd               TEXT,
    eta               TEXT,
    port_of_loading   TEXT,
    port_of_discharge TEXT,
    incoterms         TEXT,
    description       TEXT,
    created_at        TEXT    DEFAULT (datetime('now')),
    updated_at        TEXT
);
```

Status values: `DRAFT`, `ACTIVE`, `IN_TRANSIT`, `DELIVERED`, `CANCELLED`
Incoterms: `EXW`, `FCA`, `FOB`, `CFR`, `CIF`, `CPT`, `CIP`, `DAP`, `DPU`, `DDP`

### Modify: `expenses` table — add `shipment_id`

```sql
ALTER TABLE expenses ADD COLUMN shipment_id INTEGER REFERENCES shipments(id) ON DELETE SET NULL;
```

Fresh installs: included in `CREATE TABLE IF NOT EXISTS expenses` DDL.
Existing DBs: `init_db()` runs the ALTER in a `try/except` for idempotency.

### New table: `shipment_vendors`

```sql
CREATE TABLE IF NOT EXISTS shipment_vendors (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id         INTEGER NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    shipment_id       INTEGER NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    relationship_type TEXT    NOT NULL,
    billing_type      TEXT    NOT NULL,
    amount            REAL    DEFAULT 0,
    currency          TEXT    DEFAULT 'INR',
    invoice_number    TEXT,
    invoice_date      TEXT,
    due_date          TEXT,
    payment_status    TEXT    NOT NULL DEFAULT 'PENDING',
    notes             TEXT
);
```

Relationship types: `CUSTOMER`, `TRANSPORTER`, `CONSIGNEE`, `CLEARING_AGENT`
Billing types: `PAYABLE`, `RECEIVABLE`
Payment statuses: `PENDING`, `PARTIAL`, `PAID`, `OVERDUE`

## Templates

**Create:**
- `templates/shipments.html` — shipments list with status badges, vendor counts, payables/receivables
- `templates/shipment_detail.html` — detail page: meta header, 6-stat row, vendor assignments table, expenses table, 4 modals (add/edit vendor, add/edit expense)
- `templates/add_shipment.html` — form with two-column grid layout, full logistics fields
- `templates/edit_shipment.html` — same fields as add, pre-populated from shipment row
- `static/css/shipments.css` — status/role/billing/payment badges, form grid, detail layout
- `static/js/shipment_detail.js` — modal open/close, edit data population, delete fetch handlers

**Modify:**
- `templates/profile.html` — Add Expense form action: `url_for('add_expense')`
- `static/js/profile.js` — edit/delete fetch URLs: `/expenses/<id>/edit`, `/expenses/<id>/delete`

## Files to change

- `database/db.py` — `init_db()` DDL, `seed_db()` vendor/shipment/mapping blocks, expense helpers updated, new shipment and shipment-vendor CRUD helpers
- `app.py` — imports updated, `/shipments` routes replaced, new routes added, standalone `/expenses` routes added
- `templates/profile.html` — form action URL
- `static/js/profile.js` — fetch URL prefixes

## Files to create

- `templates/shipments.html` (replaces existing)
- `templates/shipment_detail.html`
- `templates/add_shipment.html`
- `templates/edit_shipment.html`
- `static/css/shipments.css`
- `static/js/shipment_detail.js`

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw sqlite3 only
- Parameterised queries only — never f-strings in SQL
- `PRAGMA foreign_keys = ON` already set by `get_db()` — do not duplicate
- `init_db()` must remain idempotent — `CREATE TABLE IF NOT EXISTS` + `try/except` ALTER
- `seed_db()` guards prevent double-seeding (`COUNT(*) == 0` per table)
- All templates extend `base.html`
- Use CSS variables — never hardcode hex colour values
- Form values cast safely: `int(v) if v else None`, `float(v) if v else 0`
- Ownership checks: `abort(403)` if shipment belongs to another user

## Definition of done

- [ ] App starts without errors (`python app.py`)
- [ ] `shipments` table exists with all 16 columns
- [ ] `expenses` table has `shipment_id` column
- [ ] `shipment_vendors` table exists with correct schema
- [ ] `seed_db()` inserts 5 vendors, 3 shipments, 7 vendor-shipment mappings (only once each)
- [ ] Seeded expenses have `shipment_id` assigned by date range
- [ ] `GET /shipments` shows 3 seeded shipments with vendor counts and payable/receivable totals
- [ ] Add shipment form creates a shipment and redirects to list
- [ ] Duplicate shipment number is rejected with an error message
- [ ] Shipment detail page shows vendor assignments and expenses
- [ ] Expense can be added to a shipment from the detail page modal
- [ ] Expense edit modal pre-populates and saves correctly
- [ ] Expense delete removes the row (JSON `{"ok": true}`)
- [ ] Vendor can be assigned from the detail page modal
- [ ] Vendor assignment edit updates the record
- [ ] Vendor assignment delete removes the row (JSON `{"ok": true}`)
- [ ] Deleting a shipment removes it from the list
- [ ] Profile page Add Expense / Edit / Delete still works via `/expenses/...` routes
- [ ] All existing pytest tests pass unchanged
