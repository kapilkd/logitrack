# Spec: Vendor Reports

## Overview

This feature adds a Vendor Reports page at `/reports/vendors` that provides a roll-up financial view across all vendors — distinct from the per-vendor ledger page (`/vendors/<id>/ledger`) which shows one vendor's history. The page shows a filterable summary table (one row per vendor) with total payables, receivables, net position, shipment count, and pending count, plus four summary cards aggregating across all filtered vendors. It also wires the remaining `href="#"` sidebar sub-link for "Vendor Reports". This completes the third and final step in the Reports module.

## Depends on

- Step 03 — Login and logout (session management)
- Step 04/05 — Profile page (sidebar layout, `active_section` pattern)
- Vendors feature — vendors table, vendor CRUD, vendor ledger
- Reports step 01 — Shipment Reports (reports sidebar group, CSS, table patterns)
- Reports step 02 — Financial Reports (filter bar CSS classes already present)

## Routes

- `GET /reports/vendors` — render Vendor Reports dashboard with optional `vendor_type`, `vendor_category`, `vendor_status`, `from_date`, `to_date` query params — logged-in

## Database changes

No new tables or columns.

Add two new query functions to `database/queries.py`:

**`get_vendor_report_rows(user_id, vendor_type=None, vendor_category=None, vendor_status=None, from_date=None, to_date=None)`**

Returns a list of dicts, one per vendor belonging to `user_id`, sorted by `vendor_name ASC`. Uses a LEFT JOIN from vendors → shipment_vendors → shipments so vendors with no billing entries still appear with zero amounts.

Each dict:
- `vendor_id` — int
- `vendor_code` — string
- `vendor_name` — string
- `vendor_category` — string
- `vendor_type` — string
- `status` — string
- `total_payable` — float, SUM(sv.amount) WHERE billing_type='PAYABLE'
- `total_receivable` — float, SUM(sv.amount) WHERE billing_type='RECEIVABLE'
- `net_position` — float, total_receivable − total_payable
- `shipment_count` — int, COUNT(DISTINCT sv.shipment_id) for this vendor
- `pending_count` — int, COUNT(sv rows) WHERE payment_status IN ('PENDING','PARTIAL','OVERDUE')

Optional filters on the `vendors` table: `vendor_type`, `vendor_category`, `vendor_status`.
Optional date range filters applied to `shipments.shipment_date` (via the JOIN): `from_date` → `s.shipment_date >= ?`, `to_date` → `s.shipment_date <= ?`.

**`get_vendor_report_summary(user_id, vendor_type=None, vendor_category=None, vendor_status=None, from_date=None, to_date=None)`**

Single-row aggregate. Returns a dict:
- `vendor_count` — int, COUNT(DISTINCT v.id) of matching vendors
- `total_payable` — float, SUM across all matching vendors
- `total_receivable` — float, SUM across all matching vendors
- `total_shipments` — int, COUNT(DISTINCT sv.shipment_id) across all matching vendors
- `overdue_count` — int, COUNT(sv rows) WHERE payment_status='OVERDUE'

Same filter parameters as `get_vendor_report_rows`.

## Templates

- **Create:** `templates/vendor_reports.html` — two-column shell (sidebar + main), dropdown filter bar (vendor_type, vendor_category, vendor_status, from_date, to_date), 4 summary cards, vendor summary table
- **Modify:** `templates/_sidebar.html` — wire "Vendor Reports" sub-link (currently `href="#"`) to `url_for('vendor_reports')` with active-state class

## Files to change

- `database/queries.py` — add `get_vendor_report_rows` and `get_vendor_report_summary`
- `app.py` — add `GET /reports/vendors` route; extend queries import
- `templates/_sidebar.html` — wire the Vendor Reports sub-link

## Files to create

- `templates/vendor_reports.html`

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw SQLite via `get_db()`
- Parameterised queries only — `?` placeholders, never f-strings in SQL
- Passwords hashed with werkzeug (not applicable here)
- Use CSS variables — never hardcode hex values; use variables from `:root` in `style.css`
- All templates extend `base.html`
- DB CRUD helpers go in `database/db.py`; complex read queries go in `database/queries.py`
- Pass `active_section="reports"` to `render_template()` so the sidebar Reports group expands
- Query params: read `vendor_type`, `vendor_category`, `vendor_status`, `from_date`, `to_date` from `request.args` with `.strip() or None`; pass them back to the template for form retention
- Vendor type/category/status filter values must be validated against allowed sets before appending to SQL (same pattern as `get_filtered_vendors` in `queries.py`)
- Date filters applied to `shipments.shipment_date` (not `shipment_vendors` columns — there is no row-level date on `shipment_vendors`)
- Amount formatting in template: `"%.2f"|format(amount)` preceded by ₹
- The "Vendor Reports" active-state check in the sidebar uses `{% if request.endpoint == 'vendor_reports' %} sidebar-sub-link--active{% endif %}`
- Reuse existing CSS classes from `billing.css` (stat cards), `profile.css` (filter bar), `reports.css` (table, two-col layout) — no new CSS file needed; add any new classes to `reports.css`
- Each row in the vendor table links to `url_for('vendor_ledger', vendor_id=row.vendor_id)` so users can drill into the per-vendor detail

## Definition of done

- [ ] Visiting `/reports/vendors` while logged in renders the full dashboard (not a placeholder)
- [ ] The sidebar Reports group is expanded; "Vendor Reports" sub-link is highlighted on `/reports/vendors`
- [ ] Four summary cards show: Vendors (count), Total Payables (₹), Total Receivables (₹), Total Shipments (count)
- [ ] Vendor table lists one row per vendor with code, name, category, type, status badge, total payable, total receivable, net position (coloured), shipment count, pending count, and a link to the vendor ledger
- [ ] Vendors with no billing entries appear in the table with ₹0.00 amounts and 0 counts
- [ ] Vendor Type, Vendor Category, and Status dropdowns filter the table and cards correctly
- [ ] Date range inputs (From / To on shipment date) filter correctly and retain values after submit
- [ ] Clearing all filters returns the full vendor list
- [ ] Empty state: if no vendors match the filters, the table shows a "No vendors found" message
- [ ] Net position column: positive = green (`reports-net-positive`), negative = red (`reports-net-negative`), zero = muted (`reports-net-zero`)
- [ ] Clicking a vendor row's ledger link navigates to `/vendors/<id>/ledger`
- [ ] `/reports/vendors` returns 302 to `/login` when accessed without a session
- [ ] Page is styled consistently with the existing reports pages using CSS variables only
