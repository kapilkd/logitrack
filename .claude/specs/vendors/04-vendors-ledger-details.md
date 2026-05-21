# Spec: Vendors Ledger Details

## Overview

This feature adds a per-vendor ledger page (`/vendors/<id>/ledger`) that gives a complete financial picture for a single vendor across all shipments. The page shows a transaction table of every `shipment_vendors` billing entry linked to the vendor, along with summary stats (total payable, total receivable, outstanding balance, overdue count). It complements the existing billing dashboard (`/billing`, which is shipment-wise) with a vendor-centric view — useful for reconciling invoices and tracking payment history with a specific vendor.

## Depends on

- `vendors/01-vendor-management-database-setup.md` — vendors table and CRUD
- `vendors/02-vendor-internal-contacts.md` — vendor contacts
- `vendors/03-add-filters-type-category-status.md` — vendor list with filters
- `shipments/01-vendor-shipments-alignments.md` — shipment_vendors table, billing types, payment statuses

## Routes

- `GET /vendors/<int:vendor_id>/ledger` — per-vendor ledger detail page — logged-in, ownership check

## Database changes

No new tables or columns. All data is in the existing `shipment_vendors`, `shipments`, and `vendors` tables.

A new query helper `get_vendor_ledger(vendor_id)` must be added to `database/queries.py` returning:
- All `shipment_vendors` rows for the vendor joined with `shipments` (number, origin, destination, status, shipment_date)
- Ordered by `shipments.shipment_date DESC`, then `shipment_vendors.id ASC`

A new query helper `get_vendor_ledger_stats(vendor_id)` must be added to `database/queries.py` returning:
- `total_payable` — SUM(amount) WHERE billing_type = 'PAYABLE'
- `total_receivable` — SUM(amount) WHERE billing_type = 'RECEIVABLE'
- `pending_amount` — SUM(amount) WHERE payment_status IN ('PENDING', 'PARTIAL', 'OVERDUE')
- `overdue_count` — COUNT(*) WHERE payment_status = 'OVERDUE'

## Templates

- **Create:** `templates/vendor_ledger.html` — per-vendor ledger page extending `base.html`, with sidebar, stat cards, transaction table
- **Modify:** `templates/vendors.html` — add a "Ledger" action button per vendor row linking to `/vendors/<id>/ledger`

## Files to change

- `app.py` — add `GET /vendors/<int:vendor_id>/ledger` route
- `database/queries.py` — add `get_vendor_ledger()` and `get_vendor_ledger_stats()`
- `templates/vendors.html` — add Ledger button per vendor row
- `static/css/vendors.css` — extend with ledger page styles (stat cards, transaction table)

## Files to create

- `templates/vendor_ledger.html`

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw SQLite with `get_db()`
- Parameterised queries only — never f-strings in SQL
- Passwords hashed with werkzeug (no changes to auth)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- The ledger route must verify `vendor["user_id"] == session["user_id"]` after the 404 check; `abort(403)` if not
- Pass `active_section="vendors"` to `render_template()` — the sidebar must pre-expand Vendors
- The Ledger button on the vendors list must use `url_for('vendor_ledger', vendor_id=vendor.id)`
- The transaction table must show: Shipment No., Route (origin → destination), Relationship Type, Billing Type badge (red = PAYABLE, green = RECEIVABLE), Amount + Currency, Invoice No., Invoice Date, Due Date, Payment Status badge, Notes
- Stat cards: Total Payable, Total Receivable, Outstanding (pending_amount), Overdue Count — use the same card style as `billing.html`
- Billing type badges and payment status badges must reuse the exact CSS classes from `billing.css` / `vendors.css` — no new badge styles
- Dense layout — no excess whitespace; compact padding consistent with existing pages
- The page header must include the vendor name and vendor code, plus a "← Back to Vendors" link
- Empty state: if the vendor has no billing entries show a centered message "No ledger entries yet."

## Definition of done

- [ ] `GET /vendors/<id>/ledger` renders for the logged-in user who owns the vendor
- [ ] `GET /vendors/<id>/ledger` returns 403 for a vendor belonging to another user
- [ ] `GET /vendors/<id>/ledger` returns 404 for a non-existent vendor
- [ ] Stat cards display correct totals (Total Payable, Total Receivable, Outstanding, Overdue)
- [ ] Transaction table lists all `shipment_vendors` rows for the vendor, each row showing shipment number, route, relationship type, billing type, amount, invoice number, invoice date, due date, payment status, notes
- [ ] Rows are ordered by shipment date descending
- [ ] PAYABLE rows show red badge; RECEIVABLE rows show green badge (matching billing.html style)
- [ ] Payment status badges (PENDING, PARTIAL, PAID, OVERDUE) display with correct colours
- [ ] Vendors list page shows a "Ledger" button per row that navigates to the correct ledger URL
- [ ] Empty state message appears when vendor has zero billing entries
- [ ] Sidebar Vendors group is pre-expanded and active on the ledger page
- [ ] "← Back to Vendors" link returns to `/vendors`
