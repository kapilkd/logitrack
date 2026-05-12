# Spec: Shipment Wise Vendor Billing Dashboard

## Overview

This feature replaces the `/billing` placeholder with a functional billing dashboard
that presents vendor billing data grouped by shipment. Each shipment row shows aggregated
payables (amounts owed to vendors) and receivables (amounts due from customers), along
with a payment-status breakdown. Four summary stat cards at the top give the user a
quick financial snapshot across all their shipments. The page supports filtering by
billing type and payment status so users can focus on outstanding or overdue items.

## Depends on

- `shipments/01-vendor-shipments-alignments.md` — `shipments` table, `shipment_vendors`
  junction table, and all related CRUD helpers must be in place.
- `vendors/01-vendor-management-database-setup.md` — `vendors` table and master data.

## Routes

- `GET /billing` — Billing dashboard; renders shipment-wise vendor billing summary.
  Access: logged-in users only. Accepts optional query params:
  - `payment_status` — filter rows by payment status (`PENDING`, `PARTIAL`, `PAID`, `OVERDUE`)
  - `billing_type` — filter rows by billing type (`PAYABLE`, `RECEIVABLE`)

No other new routes.

## Database changes

No new tables or columns. All required data lives in:

- `shipment_vendors` — `billing_type`, `amount`, `currency`, `payment_status`,
  `invoice_number`, `invoice_date`, `due_date`, `relationship_type`
- `shipments` — `shipment_number`, `origin`, `destination`, `status`, `shipment_date`
- `vendors` — `vendor_name`, `vendor_code`, `vendor_category`

## Templates

- **Create:** `templates/billing.html` — extends `base.html`; two-column layout
  matching `profile.html` (left sidebar + right main content area)
- **Create:** `static/css/billing.css` — page-specific styles for stat cards,
  billing table, filter bar, status badges, and the per-shipment vendor sub-rows

## Files to change

- `app.py` — replace the existing `GET /billing` placeholder implementation with a
  real route that queries billing data, applies filters, and renders `billing.html`
- `database/queries.py` — add two new query helpers (see below)

## Files to create

- `templates/billing.html`
- `static/css/billing.css`

## New dependencies

No new dependencies.

## Query helpers to add in `database/queries.py`

### `get_billing_stats(user_id)`

Returns a dict with four aggregate values across all the user's shipment-vendor records:

```python
{
    "total_payable":     float,   # SUM(amount) WHERE billing_type='PAYABLE'
    "total_receivable":  float,   # SUM(amount) WHERE billing_type='RECEIVABLE'
    "pending_amount":    float,   # SUM(amount) WHERE payment_status IN ('PENDING','PARTIAL','OVERDUE')
    "overdue_count":     int,     # COUNT(*) WHERE payment_status='OVERDUE'
}
```

Join `shipment_vendors` → `shipments` on `shipment_id` filtered by `shipments.user_id`.

### `get_shipment_billing_list(user_id, payment_status=None, billing_type=None)`

Returns a list of dicts, one per shipment that has at least one vendor billing record,
ordered by `shipment_date DESC`. Each dict contains:

```python
{
    "shipment_id":        int,
    "shipment_number":    str,
    "origin":             str,
    "destination":        str,
    "shipment_status":    str,   # shipments.status
    "shipment_date":      str,   # YYYY-MM-DD
    "total_payable":      float,
    "total_receivable":   float,
    "vendor_count":       int,   # COUNT(DISTINCT vendor_id)
    "pending_count":      int,   # COUNT(*) WHERE payment_status IN ('PENDING','PARTIAL','OVERDUE')
    "overdue_count":      int,   # COUNT(*) WHERE payment_status='OVERDUE'
    "vendors": [                 # list of individual vendor billing lines for this shipment
        {
            "sv_id":             int,
            "vendor_name":       str,
            "vendor_code":       str,
            "vendor_category":   str,
            "relationship_type": str,
            "billing_type":      str,   # PAYABLE | RECEIVABLE
            "amount":            float,
            "currency":          str,
            "invoice_number":    str,
            "invoice_date":      str,
            "due_date":          str,
            "payment_status":    str,   # PENDING | PARTIAL | PAID | OVERDUE
        },
        ...
    ]
}
```

Apply `payment_status` and `billing_type` filters at the SQL level using parameterised
`WHERE` clauses — never Python-side filtering. A shipment row is included only if it
has at least one `shipment_vendor` record matching the active filters.

## Route implementation in `app.py`

```python
@app.route('/billing')
@login_required
def billing():
    payment_status = request.args.get('payment_status', '').strip() or None
    billing_type   = request.args.get('billing_type',   '').strip() or None

    stats    = get_billing_stats(session['user_id'])
    shipments = get_shipment_billing_list(
        session['user_id'],
        payment_status=payment_status,
        billing_type=billing_type,
    )
    return render_template(
        'billing.html',
        stats=stats,
        shipments=shipments,
        active_payment_status=payment_status,
        active_billing_type=billing_type,
    )
```

Import `get_billing_stats` and `get_shipment_billing_list` from `database.queries`.

## Template structure (`billing.html`)

Extends `base.html`. Mirrors the two-column layout from `profile.html`:

```
<div class="shell">
  <!-- left sidebar (same nav items as profile.html, Billing link active) -->
  <aside class="sidebar"> … </aside>

  <!-- right main content -->
  <main class="main-content">

    <!-- Page header -->
    <h2>Billing</h2>

    <!-- 4 stat cards (total_payable, total_receivable, pending_amount, overdue_count) -->
    <div class="stat-cards"> … </div>

    <!-- Filter bar: payment_status select + billing_type select + Apply button -->
    <div class="filter-bar"> … </div>

    <!-- Shipment billing table -->
    <!-- Each shipment is a collapsible/accordion section showing vendor sub-rows -->
    <div class="billing-table"> … </div>

  </main>
</div>
```

**Shipment rows** show: shipment number, origin → destination, shipment date,
total payable, total receivable, vendor count, pending/overdue badge.

**Vendor sub-rows** (always visible, no JS collapse needed for step 01) show:
vendor name, relationship type, billing type badge (PAYABLE in red, RECEIVABLE
in green), amount + currency, invoice number, due date, payment status badge.

**Status badges** use CSS classes: `.badge-pending`, `.badge-partial`, `.badge-paid`,
`.badge-overdue` — styled with CSS variables, never hardcoded hex colours.

**Empty state:** if no shipments match the active filters, show a centred message:
"No billing records found" with a link to `/shipments`.

## CSS (`billing.css`)

- `.billing-stat-cards` — 4-column flex grid matching profile stat card layout
- `.billing-filter-bar` — flex row with selects and submit button
- `.billing-shipment-row` — card-style container per shipment
- `.billing-vendor-row` — table row for each vendor under a shipment
- `.billing-type-badge` — inline badge: PAYABLE (`--color-danger`), RECEIVABLE (`--color-success`)
- `.payment-badge-*` — one class per payment status using CSS variables only

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()` only
- Parameterised queries only (`?` placeholders) — no f-strings in SQL
- Passwords hashed with werkzeug (not relevant here but kept for consistency)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- `login_required` decorator must guard the `/billing` route
- No new pip packages
- DB logic in `database/queries.py` — nothing inline in the route
- `url_for('billing')` for all internal links to this page

## Definition of done

- [ ] `GET /billing` (logged out) redirects to `/login`
- [ ] `GET /billing` (logged in) renders without error and shows the four stat cards
- [ ] Total payable and total receivable stat cards show correct sums matching the
      seeded `shipment_vendors` data for the demo user
- [ ] Overdue count badge shows the correct count of OVERDUE records
- [ ] Each seeded shipment with vendor billing appears as a row in the dashboard
- [ ] Each vendor billing line (from `shipment_vendors`) appears under its shipment
- [ ] Filtering by `payment_status=OVERDUE` hides shipments with no OVERDUE records
- [ ] Filtering by `billing_type=PAYABLE` hides RECEIVABLE-only entries
- [ ] Clearing filters (no query params) restores the full list
- [ ] PAYABLE badge renders in danger colour; RECEIVABLE badge in success colour
- [ ] OVERDUE and PENDING status badges render in distinct colours (CSS vars only)
- [ ] Sidebar "Billing" link is visually active/highlighted on this page
- [ ] Page is accessible without JS — filters work via standard form GET submission
- [ ] No hardcoded hex values in `billing.css`
- [ ] No SQL queries inside `app.py` — all queries in `database/queries.py`
