# Spec: Financial Reports

## Overview

This feature adds a Financial Reports page at `/reports/financial` that gives users an expense-centric view of their finances — distinct from the Shipment Reports page which is shipment-centric. The page shows a date-filterable summary (total expenses, transaction count, shipment-linked vs. standalone split), a category breakdown table, and a month-by-month expense trend table. It also wires the existing `href="#"` sidebar sub-links for both "Shipment Reports" and "Financial Reports" to their real routes. This completes the second step in the Reports module.

## Depends on

- Step 03 — Login and logout (session management)
- Step 04/05 — Profile page (sidebar layout, `active_section` pattern, date filter presets pattern)
- Step 07 — Add Expense (expenses table, EXPENSE_CATEGORIES)
- Reports step 01 — Shipment Reports (the `/reports` route already exists; Financial Reports adds `/reports/financial`)

## Routes

- `GET /reports/financial` — render Financial Reports dashboard with optional `from_date` / `to_date` query params and preset shortcuts — logged-in

## Database changes

No new tables or columns.

Add two new query functions to `database/queries.py`:

**`get_monthly_expense_trend(user_id, from_date=None, to_date=None)`**

Groups expenses by calendar month using `STRFTIME('%Y-%m', date)`. Returns a list of dicts sorted by month ASC:
- `month` — string like `"2026-05"` (for sorting/display)
- `month_label` — formatted like `"May 2026"` (for display)
- `total` — float, SUM of expenses in that month
- `count` — int, number of expense rows

Optional filters applied to `expenses.date`:
- `from_date`: `WHERE date >= ?`
- `to_date`: `WHERE date <= ?`

Always filters by `user_id`.

**`get_expense_link_summary(user_id, from_date=None, to_date=None)`**

Single-row aggregate over the `expenses` table. Returns a dict:
- `total` — float, SUM(amount) for all expenses
- `total_count` — int, COUNT of all expenses
- `linked_total` — float, SUM(amount) WHERE shipment_id IS NOT NULL
- `linked_count` — int, COUNT WHERE shipment_id IS NOT NULL
- `standalone_total` — float, SUM(amount) WHERE shipment_id IS NULL
- `standalone_count` — int, COUNT WHERE shipment_id IS NULL

Optional `from_date` / `to_date` filters applied to `expenses.date`. Always filters by `user_id`.

## Templates

- **Create:** `templates/financial_reports.html` — two-column shell (sidebar + main), preset date filter bar, 4 summary cards, category breakdown table, monthly trend table
- **Modify:** `templates/_sidebar.html` — wire "Shipment Reports" sub-link (line 136) and "Financial Reports" sub-link (line 137) from `href="#"` to real routes with active-state classes

## Files to change

- `database/queries.py` — add `get_monthly_expense_trend` and `get_expense_link_summary`
- `app.py` — add `GET /reports/financial` route; extend queries import; wire preset date logic (mirror the profile route's preset computation)
- `templates/_sidebar.html` — wire the two Reports sub-links
- `static/css/reports.css` — extend with new classes for the financial reports page sections

## Files to create

- `templates/financial_reports.html`

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
- Date presets: compute `this_month`, `last_month`, `last_3_months` in the route using the same logic as the profile route (lines 165–172 of `app.py`); pass them as a `presets` dict to the template
- `active_preset`: compute which preset is currently active ("all_time", "this_month", "last_month", "last_3_months", or "custom") by comparing the current `(from_date, to_date)` tuple against preset values; pass as `active_preset` to the template
- Query params: read `from_date` and `to_date` from `request.args` with `.strip() or None`; pass them back to the template as `from_date` and `to_date` (empty string if None)
- Reuse `get_category_breakdown(uid, from_date, to_date)` from `database.queries` — already imported
- The monthly trend table must render months in chronological order (ASC)
- Amount formatting in template: use `"%.2f"|format(amount)` consistent with the rest of the app; amounts preceded by ₹
- The "Financial Reports" active-state check in the sidebar uses `{% if request.endpoint == 'financial_reports' %} sidebar-sub-link--active{% endif %}`
- The "Shipment Reports" active-state check uses `{% if request.endpoint == 'reports' %} sidebar-sub-link--active{% endif %}`
- Do not modify the existing `reports()` route or `reports.html`

## Definition of done

- [ ] Visiting `/reports/financial` while logged in renders the full dashboard (not a placeholder)
- [ ] The sidebar Reports group is expanded; "Financial Reports" sub-link is highlighted on `/reports/financial`; "Shipment Reports" sub-link is highlighted on `/reports`
- [ ] The preset buttons (All Time, This Month, Last Month, Last 3 Months) are clickable and correctly filter the data
- [ ] The active preset button is visually distinct from the others
- [ ] The custom date range form retains entered values after submit
- [ ] Four summary cards show: Total Expenses (₹), Total Transactions (count), Shipment-Linked (₹ + count), Standalone (₹ + count)
- [ ] Category breakdown table lists all categories with amounts and percentage
- [ ] Monthly trend table lists months in chronological order with amount and transaction count
- [ ] All amounts update correctly when date filters are applied
- [ ] Empty state: if no expenses in the selected range, all amounts show ₹0.00 and tables show "No data" messages
- [ ] `/reports/financial` returns 302 to `/login` when accessed without a session
- [ ] Page is styled consistently with the existing reports page using CSS variables only
