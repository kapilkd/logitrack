# Spec: Shipment Reports

## Overview

This feature replaces the `/reports` placeholder with a real Shipment Reports dashboard that gives users a financial overview of their shipments. The page shows summary cards (total shipments, total expenses, total payables, total receivables), a filter bar (by shipment status and date range), and a per-shipment breakdown table listing expenses, payables, receivables, and net position for each shipment. All data is derived from existing tables — no new tables are needed. This is the first step in the Reports module and fulfils the long-standing Reports stub in the sidebar.

## Depends on

- Step 01 — Database setup (shipments, expenses, shipment_vendors tables)
- Step 03 — Login and logout (session management)
- Step 04/05 — Profile page (sidebar layout, `active_section` pattern)
- Shipments module (shipment data and statuses)
- Billing module (shipment_vendors data, payment statuses)

## Routes

- `GET /reports` — render shipment reports dashboard with optional `status` and `from_date`/`to_date` query params — logged-in

No new routes. The existing `/reports` stub is replaced with the real implementation.

## Database changes

No new tables or columns.

Add one new query function to `database/queries.py`:

**`get_shipment_report_rows(user_id, status=None, from_date=None, to_date=None)`**

Returns a list of per-shipment dicts, each containing:
- `shipment_id`, `shipment_number`, `origin`, `destination`, `status`, `shipment_date`, `carrier`
- `expense_total` — SUM of expenses linked to this shipment (may be 0)
- `total_payable` — SUM of shipment_vendors.amount WHERE billing_type = 'PAYABLE'
- `total_receivable` — SUM of shipment_vendors.amount WHERE billing_type = 'RECEIVABLE'
- `net_position` — total_receivable − total_payable
- `vendor_count` — COUNT of distinct vendors on this shipment

Filters applied in SQL:
- `status`: WHERE shipments.status = ?
- `from_date` / `to_date`: WHERE shipments.shipment_date BETWEEN ? AND ?

The query uses LEFT JOINs so shipments with no expenses or no vendors still appear (with 0 amounts).

Add one summary stats function to `database/queries.py`:

**`get_report_summary_stats(user_id, status=None, from_date=None, to_date=None)`**

Returns a single dict:
- `shipment_count` — total shipments matching the filter
- `expense_total` — total expenses across all matching shipments
- `total_payable` — total payables across all matching shipments
- `total_receivable` — total receivables across all matching shipments

## Templates

- **Create:** `templates/reports.html` — two-column shell (sidebar + main), summary cards row, filter bar, shipment breakdown table
- **Modify:** none

## Files to change

- `app.py` — replace the `/reports` stub with a full GET handler that accepts query params, calls the new query functions, and renders `reports.html`
- `database/queries.py` — add `get_shipment_report_rows` and `get_report_summary_stats`
- `templates/reports.html` — replace placeholder render in current route with this new template

## Files to create

- `templates/reports.html`
- `static/css/reports.css`

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
- Query params: read `status`, `from_date`, `to_date` from `request.args`; pass them back to the template so the filter form stays populated
- Amounts displayed with 2 decimal places and the currency symbol (default INR ₹); use `"{:,.2f}".format(amount)` formatting in the route, not in the template
- Net position: positive = green (receivable > payable), negative = red (payable > receivable), zero = muted — use CSS class toggling in the template
- Filter bar design: follows the billing page's `billing-filter-card` pattern (right-aligned card, dropdowns + date inputs + Apply + Clear)
- Summary cards: follows billing page's `billing-stats-grid` pattern (4 cards in a row)
- Shipment table: standard HTML table inside a card, one row per shipment; columns: Shipment #, Route, Status, Date, Expenses, Payables, Receivables, Net
- Status badge on each row uses the same `.status-badge` pattern as the shipments list page
- The `status` filter dropdown must list exactly: All, DRAFT, IN TRANSIT, CUSTOMS HOLD, DELIVERED, CLOSED (matching `SHIPMENT_STATUSES` from `database.db`)
- Empty state: if no shipments match, show a centred "No shipments found for the selected filters." message inside the table card
- Do not add export/PDF functionality — no new packages are allowed

## Definition of done

- [ ] Visiting `/reports` while logged in renders the full dashboard (not the placeholder)
- [ ] The Reports group in the sidebar is expanded and the Reports sub-link is highlighted
- [ ] Four summary cards show: total shipment count, total expenses, total payables, total receivables
- [ ] The shipment table lists all user shipments (one row per shipment) with correct amounts
- [ ] Filtering by status updates both the summary cards and the table
- [ ] Filtering by date range updates both the summary cards and the table
- [ ] Applying multiple filters together works correctly
- [ ] Clearing filters restores the full unfiltered view
- [ ] Shipments with no expenses or vendors show 0.00 amounts (not null/blank)
- [ ] Net position shows positive in green, negative in red, zero in muted
- [ ] `/reports` returns 302 to `/login` when accessed without a session
- [ ] Page is styled consistently with the rest of the app using CSS variables only
